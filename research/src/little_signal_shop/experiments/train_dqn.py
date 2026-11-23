"""Train and select DQN checkpoints using the registered training and validation markets."""

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from hashlib import sha256
import json
from math import isfinite
from multiprocessing import get_context
from os import cpu_count
from pathlib import Path
import platform
from random import Random
import re
from statistics import mean
from typing import TextIO

import torch

from ..controllers.baselines import BASELINE_IDS, make_baselines
from ..controllers.dqn import ACTION_ORDER, CHECKPOINT_VERSION, DQNTrainer, greedy_actions, observation_features
from ..environment import EnvironmentConfig, MarketInputs, ShopEnvironment, generate_market
from .baseline_comparison import _source_revision
from .protocol import DEFAULT_CONFIG, DEVELOPMENT_SPLIT, load_protocol, market_bundle, validation_markets


DEFAULT_TRAINING_CONFIG = DEFAULT_CONFIG.with_name("dqn-v1.json")


def _finite_number(value: object) -> bool:
    return type(value) in (float, int) and isfinite(value)


def load_training_config(path: Path, protocol: dict) -> dict:
    """Validate the complete DQN configuration against the registered selection budgets."""
    settings = json.loads(path.read_text(encoding="utf-8"))
    integer_fields = {
        "episodes", "batch_size", "replay_capacity", "learning_starts", "train_every_steps",
        "target_update_steps", "epsilon_decay_episodes", "reward_scale_cents",
    }
    fields = integer_fields | {
        "version", "checkpoint_episodes", "gamma", "epsilon_start", "epsilon_end",
        "gradient_clip_norm", "candidates",
    }
    if not isinstance(settings, dict) or settings.keys() != fields or settings["version"] != "1":
        raise ValueError("expected the version 1 training configuration with all required fields")
    if any(type(settings[name]) is not int or settings[name] < 1 for name in integer_fields):
        raise ValueError("training counts and reward scale must be positive integers")
    if not settings["batch_size"] <= settings["learning_starts"] <= settings["replay_capacity"]:
        raise ValueError("require batch_size <= learning_starts <= replay_capacity")
    if not _finite_number(settings["gamma"]) or settings["gamma"] != 1:
        raise ValueError("the finite-horizon objective requires gamma = 1")
    epsilon_start, epsilon_end = settings["epsilon_start"], settings["epsilon_end"]
    if (not all(_finite_number(value) for value in (epsilon_start, epsilon_end))
            or not 0 <= epsilon_end <= epsilon_start <= 1):
        raise ValueError("require 0 <= epsilon_end <= epsilon_start <= 1")
    grad_clip = settings["gradient_clip_norm"]
    if not _finite_number(grad_clip) or grad_clip <= 0:
        raise ValueError("gradient_clip_norm must be positive and finite")

    budget = protocol["selection"]
    episodes, checkpoints = settings["episodes"], settings["checkpoint_episodes"]
    if episodes > budget["training_episodes_max"]:
        raise ValueError("training episodes exceed the registered budget")
    if (not isinstance(checkpoints, list) or not 1 <= len(checkpoints) <= budget["validation_checkpoints_max"]
            or any(type(episode) is not int or not 1 <= episode <= episodes for episode in checkpoints)
            or checkpoints != sorted(set(checkpoints)) or checkpoints[-1] != episodes):
        raise ValueError("checkpoint schedule must be unique, increasing, within budget, and end at the episode budget")

    candidates = settings["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= budget["dqn_configurations_max"]:
        raise ValueError("DQN candidates exceed the registered budget or are missing")
    seen_ids = set()
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != {"id", "hidden_sizes", "learning_rate"}:
            raise ValueError("each DQN candidate needs id, hidden_sizes, and learning_rate")
        identifier = candidate["id"]
        if (not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", identifier)
                or identifier in seen_ids):
            raise ValueError("DQN candidate IDs must be unique lowercase identifiers")
        seen_ids.add(identifier)
        sizes, rate = candidate["hidden_sizes"], candidate["learning_rate"]
        if not isinstance(sizes, list) or not sizes or any(type(size) is not int or size < 1 for size in sizes):
            raise ValueError("hidden_sizes must be a nonempty list of positive integers")
        if not _finite_number(rate) or rate <= 0:
            raise ValueError("learning_rate must be positive and finite")
    return settings


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def _write_row(output: TextIO, row: dict) -> None:
    json.dump(row, output, separators=(",", ":"), allow_nan=False)
    output.write("\n")


def _initial_net_worth(config: EnvironmentConfig) -> int:
    return config.opening_cash_cents + config.opening_stock * config.unit_cost_cents


def _frozen_baseline(path: Path, config: EnvironmentConfig, markets: tuple[MarketInputs, ...]) -> tuple[str, float]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("split") != DEVELOPMENT_SPLIT:
        raise ValueError("baseline summary must come from the validation split")
    by_controller = summary.get("by_controller")
    if (summary.get("market_count") != len(markets) or not isinstance(by_controller, dict)
            or set(by_controller) != set(BASELINE_IDS)):
        raise ValueError("baseline summary must include all baseline validation results")
    means = {}
    for controller_id in BASELINE_IDS:
        row = by_controller[controller_id]
        if not isinstance(row, dict) or row.get("market_count") != len(markets):
            raise ValueError(f"baseline summary has a mismatched count for {controller_id}")
        means[controller_id] = row.get("mean_final_net_worth_cents")
        if not _finite_number(means[controller_id]):
            raise ValueError(f"baseline summary has no finite final mean for {controller_id}")
    primary = summary.get("primary_baseline")
    if primary != max(BASELINE_IDS, key=means.__getitem__):
        raise ValueError("baseline summary primary baseline contradicts the registered ranking rule")

    controller = make_baselines(config)[primary]
    env = ShopEnvironment(config, record_transitions=False)
    results = []
    for market in markets:
        observation = env.reset(market)
        net_worth = _initial_net_worth(config)
        while observation is not None:
            step = env.step(controller(observation))
            observation = step.observation
            net_worth += step.reward_cents
        results.append(net_worth)
    if means[primary] != mean(results):
        raise ValueError("frozen baseline mean does not match the supplied validation market rows")
    return primary, means[primary]


def _configure_torch() -> None:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def _scheduled_markets(markets: tuple[MarketInputs, ...], episodes: int, seed: int) -> list[MarketInputs]:
    rng = Random(f"lss-dqn-v1:{seed}:training-market")
    market_order = []
    while len(market_order) < episodes:
        cycle = list(markets)
        rng.shuffle(cycle)
        market_order.extend(cycle)
    return market_order[:episodes]


def _validation_scores(
    trainer: DQNTrainer, config: EnvironmentConfig, markets: tuple[MarketInputs, ...],
) -> list[int]:
    # Batch the active observations at each decision round without coupling the market simulations.
    envs = [ShopEnvironment(config, record_transitions=False) for _ in markets]
    observations = [env.reset(market) for env, market in zip(envs, markets, strict=True)]
    cumulative = [_initial_net_worth(config) for _ in markets]
    trainer.model.eval()
    try:
        active = list(range(len(markets)))
        while active:
            choices = greedy_actions(trainer.model, [observations[index] for index in active], config)
            next_active = []
            for index, action in zip(active, choices, strict=True):
                result = envs[index].step(action)
                cumulative[index] += result.reward_cents
                if result.observation is not None:
                    observations[index] = result.observation
                    next_active.append(index)
            active = next_active
    finally:
        trainer.model.train()
    return cumulative


def _train_seed(
    output: Path, config: EnvironmentConfig, settings: dict, candidate: dict, learning_seed: int,
    training_markets: tuple[MarketInputs, ...], validation: tuple[MarketInputs, ...],
) -> tuple[list[dict], list[dict]]:
    candidate_id = candidate["id"]
    rel_dir = Path("checkpoints") / candidate_id / f"seed-{learning_seed}"
    run_dir = output / rel_dir
    run_dir.mkdir(parents=True)
    checkpoints = []
    rows = []
    try:
        trainer = DQNTrainer(config, settings, candidate, learning_seed)
        env = ShopEnvironment(config, record_transitions=False)
        schedule = _scheduled_markets(training_markets, settings["episodes"], learning_seed)
        with (
            (run_dir / "training_log.jsonl").open("w", encoding="utf-8", newline="\n") as log,
            (run_dir / "validation_metrics.jsonl").open("w", encoding="utf-8", newline="\n") as per_seed_validation,
        ):
            for episode, market in enumerate(schedule, start=1):
                fraction = min(1, (episode - 1) / settings["epsilon_decay_episodes"])
                epsilon = settings["epsilon_start"] + fraction * (settings["epsilon_end"] - settings["epsilon_start"])
                observation = env.reset(market)
                features = observation_features(observation, config)
                net_worth = _initial_net_worth(config)
                losses = []
                first_step = trainer.decision_steps
                while observation is not None:
                    action = trainer.choose(observation, features, epsilon)
                    result = env.step(action)
                    next_observation = result.observation
                    next_features = observation_features(next_observation, config) if next_observation is not None else None
                    loss = trainer.learn(features, action, result.reward_cents, next_features, next_observation)
                    if loss is not None:
                        losses.append(loss)
                    net_worth += result.reward_cents
                    observation = next_observation
                    features = next_features

                _write_row(log, {
                    "episode": episode, "market_seed": market.seed, "input_id": market.input_id,
                    "epsilon": epsilon, "final_net_worth_cents": net_worth,
                    "decision_steps": trainer.decision_steps - first_step,
                    "optimizer_steps": len(losses), "total_optimizer_steps": trainer.optimizer_steps,
                    "mean_loss": mean(losses) if losses else None,
                    "max_loss": max(losses) if losses else None,
                })
                log.flush()
                if episode not in settings["checkpoint_episodes"]:
                    continue
                checkpoint_fields = {
                    "candidate_id": candidate_id, "learning_seed": learning_seed, "checkpoint_episode": episode,
                }
                rel_path = rel_dir / f"episode-{episode}.pt"
                checkpoint = output / rel_path
                torch.save({
                    **checkpoint_fields, "format_version": CHECKPOINT_VERSION,
                    "environment_config": asdict(config), "hidden_sizes": candidate["hidden_sizes"],
                    "action_order": [action.value for action in ACTION_ORDER], "state_dict": trainer.model.state_dict(),
                }, checkpoint)
                checkpoints.append({**checkpoint_fields, "path": rel_path.as_posix(),
                                    "sha256": sha256(checkpoint.read_bytes()).hexdigest()})
                scores = _validation_scores(trainer, config, validation)
                for market, score in zip(validation, scores, strict=True):
                    row = {
                        **checkpoint_fields, "market_seed": market.seed, "input_id": market.input_id,
                        "final_net_worth_cents": score,
                    }
                    rows.append(row)
                    _write_row(per_seed_validation, row)
                per_seed_validation.flush()
        _write_json(run_dir / "checkpoints.json", {"checkpoints": checkpoints})
    except Exception as exc:
        _write_json(run_dir / "failure.json", {"error_type": type(exc).__name__, "error": str(exc)})
        raise
    return checkpoints, rows


def train_and_select(
    protocol_path: Path, training_path: Path, validation_inputs: Path, baseline_summary: Path,
    output: Path, workers: int,
) -> dict:
    """Train the complete seed grid and publish the jointly chosen checkpoints."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output directory already exists: {output}")
    if workers < 1:
        raise ValueError("workers must be positive")
    protocol, config = load_protocol(protocol_path)
    settings = load_training_config(training_path, protocol)
    validation = validation_markets(protocol, config, validation_inputs)
    primary, baseline_mean = _frozen_baseline(baseline_summary, config, validation)
    markets = tuple(generate_market(config, seed) for seed in protocol["seeds"]["train"])
    learning_seeds = protocol["seeds"]["learning"]
    jobs = [(candidate, seed) for candidate in settings["candidates"] for seed in learning_seeds]
    workers = min(workers, len(jobs), cpu_count() or 1, 61)
    code_revision, git_head, source_hash = _source_revision()

    output.mkdir(parents=True)
    for source, name in (
        (protocol_path, "protocol.json"), (training_path, "training_config.json"),
        (validation_inputs, "validation_market_inputs.json"), (baseline_summary, "baseline_summary.json"),
    ):
        (output / name).write_bytes(source.read_bytes())
    bundle = market_bundle(markets)
    bundle["split"] = "train"
    _write_json(output / "training_market_inputs.json", bundle)
    manifest = {
        "status": "running", "code_revision": code_revision, "git_head": git_head,
        "source_sha256": source_hash, "python_version": platform.python_version(),
        "torch_version": str(torch.__version__), "platform": platform.platform(), "device": "cpu",
        "torch_threads_per_worker": 1, "workers": workers, "training_job_count": len(jobs),
        "protocol_version": protocol["protocol_version"], "environment_version": protocol["environment_version"],
        "market_model_version": protocol["market_model_version"], "training_config_version": settings["version"],
        "training_market_count": len(markets), "validation_market_count": len(validation),
        "training_episodes_per_job": settings["episodes"], "validation_checkpoint_episodes": settings["checkpoint_episodes"],
        "input_sha256": {
            name: sha256((output / name).read_bytes()).hexdigest()
            for name in ("protocol.json", "training_config.json", "training_market_inputs.json",
                         "validation_market_inputs.json", "baseline_summary.json")
        },
    }
    _write_json(output / "manifest.json", manifest)

    checkpoint_rows = []
    validation_rows = []
    failures = []

    def collect(candidate: dict, seed: int, result) -> None:
        try:
            checkpoints, scores = result()
        except Exception as exc:
            failures.append({"candidate_id": candidate["id"], "learning_seed": seed, "error": str(exc)})
            print(f"Failed {candidate['id']} seed {seed}: {exc}", flush=True)
        else:
            checkpoint_rows.extend(checkpoints)
            validation_rows.extend(scores)
            print(f"Completed {candidate['id']} seed {seed} ({settings['episodes']} episodes)", flush=True)

    print(f"Training {len(jobs)} DQN runs across {workers} CPU worker(s)", flush=True)
    if workers == 1:
        _configure_torch()
        for candidate, seed in jobs:
            collect(candidate, seed, lambda: _train_seed(output, config, settings, candidate, seed, markets, validation))
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn"), initializer=_configure_torch) as pool:
            pending = {
                pool.submit(_train_seed, output, config, settings, candidate, seed, markets, validation): (candidate, seed)
                for candidate, seed in jobs
            }
            for future in as_completed(pending):
                candidate, seed = pending[future]
                collect(candidate, seed, future.result)

    def row_order(row: dict) -> tuple:
        return row["candidate_id"], row["checkpoint_episode"], row["learning_seed"], row.get("market_seed", 0)

    with (output / "validation_metrics.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in sorted(validation_rows, key=row_order):
            _write_row(stream, row)
    _write_json(output / "checkpoints.json", {"checkpoints": sorted(checkpoint_rows, key=row_order)})
    if failures:
        _write_json(output / "failures.json", {"failures": failures})
        _write_json(output / "manifest.json", {**manifest, "status": "failed"})
        raise RuntimeError(f"{len(failures)} DQN run(s) failed; inspect {output / 'failures.json'}")

    ranking = []
    for candidate in settings["candidates"]:
        for episode in settings["checkpoint_episodes"]:
            objective = [row["final_net_worth_cents"] for row in validation_rows
                         if row["candidate_id"] == candidate["id"] and row["checkpoint_episode"] == episode]
            ranking.append({
                "candidate_id": candidate["id"], "checkpoint_episode": episode,
                "validation_episode_count": len(objective), "validation_total_final_net_worth_cents": sum(objective),
                "validation_mean_final_net_worth_cents": mean(objective),
            })
    ranking.sort(key=lambda row: (-row["validation_total_final_net_worth_cents"],
                                  row["checkpoint_episode"], row["candidate_id"]))
    _write_json(output / "validation_ranking.json", {"ranking": ranking})
    selected = ranking[0]
    selection = {
        **selected, "primary_baseline": primary, "baseline_validation_mean_final_net_worth_cents": baseline_mean,
        "learning_seeds": learning_seeds,
        "checkpoints": {
            str(row["learning_seed"]): {"path": row["path"], "sha256": row["sha256"]}
            for row in checkpoint_rows if row["candidate_id"] == selected["candidate_id"]
            and row["checkpoint_episode"] == selected["checkpoint_episode"]
        },
    }
    _write_json(output / "selection.json", selection)
    _write_json(output / "manifest.json", {**manifest, "status": "complete", "validation_episode_count": len(validation_rows)})
    return selection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-inputs", type=Path, required=True, help="Phase 3 validation market bundle")
    parser.add_argument("--baseline-summary", type=Path, required=True, help="Phase 3 summary.json")
    parser.add_argument("--output", type=Path, required=True, help="new directory for training records and checkpoints")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_CONFIG, help="registered baseline and DQN experiment protocol")
    parser.add_argument("--config", type=Path, default=DEFAULT_TRAINING_CONFIG, help="versioned DQN training configuration")
    parser.add_argument("--workers", type=int, default=1, help="CPU worker processes; each uses one torch thread")
    args = parser.parse_args()
    try:
        selected = train_and_select(args.protocol, args.config, args.validation_inputs, args.baseline_summary,
                                    args.output, args.workers)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Training failed: {exc}\n")
    print(f"Selected {selected['candidate_id']} at episode {selected['checkpoint_episode']} "
          f"with mean validation net worth {selected['validation_mean_final_net_worth_cents']:.2f} cents", flush=True)


if __name__ == "__main__":
    main()
