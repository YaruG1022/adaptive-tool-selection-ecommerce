"""Evaluate the frozen DQN and fixed baselines on matching held-out markets."""

import argparse
from collections.abc import Sequence
from dataclasses import asdict, fields, replace
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import platform
from random import Random
from statistics import mean
from tempfile import TemporaryDirectory

from ..controllers.baselines import BASELINE_IDS, make_baselines
from ..environment import DayInput, EnvironmentConfig, MarketInputs, ShopEnvironment, generate_market
from ..policies.replenishment import replenishment_units
from .baseline_comparison import METRIC_FIELDS, _episode_metrics, _source_revision, _write_csv, _write_json
from .protocol import DEFAULT_CONFIG, _require_fields, load_protocol, market_bundle


HELD_OUT = "held_out"
DQN = "dqn"
PRIMARY_METRIC = "final_net_worth_cents"
TOOLS = ("market_report", "forecast")
SENSITIVITIES = {
    "forecast_noise_1": {"forecast_noise": 1},
    "forecast_noise_4": {"forecast_noise": 4},
    "regime_switch_010": {"regime_switch_probability": 0.10},
    "regime_switch_035": {"regime_switch_probability": 0.35},
    "tool_fees_half": {"tool_fee_multiplier": 0.5},
    "tool_fees_double": {"tool_fee_multiplier": 2},
}


def _percentile(ordered: list[float], probability: float) -> float:
    index = probability * (len(ordered) - 1)
    lower = int(index)
    weight = index - lower
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def paired_bootstrap(
    differences: Sequence[Sequence[float]], *, seed: int, replicates: int, confidence_level: float,
) -> tuple[float, float]:
    """Resample both axes of a complete learning-seed by matched-market grid."""
    if not differences or not differences[0]:
        raise ValueError("bootstrap requires a nonempty paired differences grid")
    learning_count = len(differences)
    market_count = len(differences[0])
    if any(len(row) != market_count for row in differences):
        raise ValueError("each learning seed must have a difference for every market")
    if type(replicates) is not int or replicates < 1 or not 0 < confidence_level < 1:
        raise ValueError("bootstrap requires positive replicates and confidence strictly between zero and one")

    rng = Random(seed)
    size = learning_count * market_count
    values = []
    for _ in range(replicates):
        markets = [rng.randrange(market_count) for _ in range(market_count)]
        learnings = [rng.randrange(learning_count) for _ in range(learning_count)]
        total = sum(differences[learning][market] for learning in learnings for market in markets)
        values.append(total / size)
    values.sort()
    tail = (1 - confidence_level) / 2
    return _percentile(values, tail), _percentile(values, 1 - tail)


def _load_selection(training: Path, protocol: dict) -> tuple[dict, dict, dict[int, Path]]:
    recorded_protocol, _ = load_protocol(training / "protocol.json")
    if recorded_protocol != protocol:
        raise ValueError("training protocol does not match the requested frozen protocol")
    training_config = json.loads((training / "training_config.json").read_text(encoding="utf-8"))
    if not isinstance(training_config, dict):
        raise ValueError("training configuration must be a JSON object")
    selection = json.loads((training / "selection.json").read_text(encoding="utf-8"))
    required_fields = {
        "primary_baseline", "candidate_id", "checkpoint_episode", "learning_seeds",
        "checkpoints", "validation_mean_final_net_worth_cents",
    }
    if not isinstance(selection, dict) or not required_fields.issubset(selection):
        raise ValueError("frozen selection is missing required fields")
    if selection["primary_baseline"] not in BASELINE_IDS:
        raise ValueError("selection must specify a registered primary baseline")
    candidate = selection["candidate_id"]
    if not isinstance(candidate, str) or not candidate.strip():
        raise ValueError("selection must identify the frozen DQN candidate")
    checkpoint_episode = selection["checkpoint_episode"]
    if type(checkpoint_episode) is not int or not 1 <= checkpoint_episode <= protocol["selection"]["training_episodes_max"]:
        raise ValueError("selected checkpoint lies outside the preregistered training budget")
    for name in ("validation_mean_final_net_worth_cents", "baseline_validation_mean_final_net_worth_cents"):
        if name in selection and (type(selection[name]) not in (int, float) or not isfinite(selection[name])):
            raise ValueError(f"selection must include a finite {name}")

    expected_seeds = protocol["seeds"]["learning"]
    saved_seeds = selection["learning_seeds"]
    if (not isinstance(saved_seeds, list) or any(type(seed) is not int for seed in saved_seeds)
            or saved_seeds != expected_seeds):
        raise ValueError("selection must include all preregistered learning seeds in protocol order")
    checkpoint_metadata = selection["checkpoints"]
    _require_fields(checkpoint_metadata, {str(seed) for seed in expected_seeds}, "checkpoints")
    paths = {}
    for seed in expected_seeds:
        entry = checkpoint_metadata[str(seed)]
        _require_fields(entry, {"path", "sha256"}, f"checkpoint {seed}")
        if not isinstance(entry["path"], str) or not entry["path"].strip() or Path(entry["path"]).anchor:
            raise ValueError(f"checkpoint {seed} path must be relative to the training directory")
        path = (training / entry["path"]).resolve()
        if not path.is_relative_to(training) or not path.is_file():
            raise ValueError(f"checkpoint {seed} must be a file inside the training directory")
        paths[seed] = path
    return selection, training_config, paths


def _held_out_markets(protocol: dict, config: EnvironmentConfig, inputs: Path | None) -> tuple[MarketInputs, ...]:
    seeds = protocol["seeds"][HELD_OUT]
    if inputs is None:
        return tuple(generate_market(config, seed) for seed in seeds)

    saved = json.loads(inputs.read_text(encoding="utf-8"))
    _require_fields(saved, {"environment_version", "market_model_version", "split", "markets"}, "market inputs")
    for key in ("environment_version", "market_model_version"):
        if saved[key] != protocol[key]:
            raise ValueError(f"market inputs must use the frozen {key}")
    if saved["split"] != HELD_OUT or not isinstance(saved["markets"], list):
        raise ValueError("market inputs must contain a held-out market list")

    by_seed = {}
    day_fields = {field.name for field in fields(DayInput)}
    for row in saved["markets"]:
        _require_fields(row, {"seed", "input_id", "days"}, "market")
        seed = row["seed"]
        if type(seed) is not int or seed not in seeds or seed in by_seed:
            raise ValueError("saved markets must contain each held-out seed exactly once")
        if not isinstance(row["days"], list) or len(row["days"]) != config.days:
            raise ValueError(f"market {seed} must contain {config.days} day rows")
        for day in row["days"]:
            _require_fields(day, day_fields, f"day in market {seed}")
        market = MarketInputs(tuple(DayInput(**day) for day in row["days"]), seed=seed)
        if market.input_id != row["input_id"]:
            raise ValueError(f"market {seed} does not match its input_id fingerprint")
        by_seed[seed] = market
    if set(by_seed) != set(seeds):
        raise ValueError("saved markets must contain each held-out seed exactly once")
    return tuple(by_seed[seed] for seed in seeds)


def _paired_rows(metrics: list[dict]) -> list[dict]:
    baseline_rows = {
        (row["controller_id"], row["market_seed"]): row for row in metrics if row["controller_id"] != DQN
    }
    pairs = []
    for candidate in metrics:
        if candidate["controller_id"] != DQN:
            continue
        for reference_id in BASELINE_IDS:
            reference = baseline_rows[reference_id, candidate["market_seed"]]
            pairs.append({
                "controller_id": DQN,
                "reference_id": reference_id,
                "learning_seed": candidate["learning_seed"],
                "model_id": candidate["model_id"],
                "market_seed": candidate["market_seed"],
                "input_id": candidate["input_id"],
                **{f"delta_{key}": candidate[key] - reference[key] for key in METRIC_FIELDS},
            })
    return pairs


def _summarize(metrics: list[dict], pairs: list[dict], protocol: dict, reference_id: str, scenario_id: str) -> dict:
    seeds = protocol["seeds"]["learning"]
    markets = protocol["seeds"][HELD_OUT]
    by_controller = {}
    for controller_id in (*BASELINE_IDS, DQN):
        group = [row for row in metrics if row["controller_id"] == controller_id]
        by_controller[controller_id] = {
            "episode_count": len(group),
            **{f"mean_{metric}": mean(row[metric] for row in group) for metric in METRIC_FIELDS},
        }

    primary_values = {
        (pair["learning_seed"], pair["market_seed"]): pair[f"delta_{PRIMARY_METRIC}"]
        for pair in pairs if pair["reference_id"] == reference_id
    }
    grid = [[primary_values[seed, market] for market in markets] for seed in seeds]
    analysis = protocol["analysis"]
    confidence_interval = paired_bootstrap(
        grid, seed=analysis["bootstrap_seed"], replicates=analysis["bootstrap_replicates"],
        confidence_level=analysis["confidence_level"],
    )
    secondary = []
    for baseline in BASELINE_IDS:
        group = [pair for pair in pairs if pair["reference_id"] == baseline]
        secondary.append({
            "controller_id": DQN,
            "reference_id": baseline,
            **{f"mean_delta_{metric}": mean(pair[f"delta_{metric}"] for pair in group) for metric in METRIC_FIELDS},
        })

    return {
        "split": HELD_OUT,
        "scenario": scenario_id,
        "market_count": len(markets),
        "learning_seed_count": len(seeds),
        "episode_count": len(metrics),
        "primary_baseline": reference_id,
        "by_controller": by_controller,
        "primary_contrast": {
            "controller_id": DQN,
            "reference_id": reference_id,
            "metric": PRIMARY_METRIC,
            "mean_delta": mean(value for row in grid for value in row),
            "confidence_level": analysis["confidence_level"],
            "confidence_interval": list(confidence_interval),
            "by_learning_seed": {str(seed): mean(row) for seed, row in zip(seeds, grid)},
        },
        "secondary_contrasts": secondary,
    }


def _update_tool_diagnostics(diagnostics: dict, record: dict, config: EnvironmentConfig, learning_seed: int | None) -> None:
    """Mask one purchased result while leaving post-fee cash and other evidence fixed."""
    settlements = {
        day["day"]: day for step in record["transitions"] for day in step["settlements"]
    }
    for step in record["transitions"]:
        if step["action"] != "stop":
            continue
        before = step["before"]
        settlement = settlements[before["day"]]
        actual_order = settlement["ordered_units"]
        today = before["public_today"] if before["market_report"] is None else before["market_report"]
        tomorrow = before["public_tomorrow"] if before["forecast"] is None else before["forecast"]
        for tool in TOOLS:
            if before[tool] is None:
                continue
            stats = diagnostics[record["controller_id"]][tool]
            stats["acquired"] += 1
            masked_order = replenishment_units(
                stock=before["stock"], cash_cents=before["cash_cents"], unit_cost_cents=config.unit_cost_cents,
                expected_today=before["public_today"] if tool == "market_report" else today,
                target_tomorrow=before["public_tomorrow"] if tool == "forecast" else tomorrow,
            )
            if masked_order == actual_order:
                continue
            stats["changed_order"] += 1
            if stats["first_changed_trace"] is None:
                stats["first_changed_trace"] = {
                    "market_seed": record["seed"], "input_id": record["input_id"],
                    "learning_seed": learning_seed, "model_id": record["model_id"],
                    "before_stop": before, "actual_order": actual_order, "masked_order": masked_order,
                    "day_settlement": settlement, "next_day_settlement": settlements[before["day"] + 1],
                }


def _evaluate_scenario(
    folder: Path, protocol: dict, config: EnvironmentConfig, markets: tuple[MarketInputs, ...],
    selection: dict, learned: dict, revision: tuple[str, str | None, str], scenario: dict,
) -> dict:
    source_revision, git_head, source_hash = revision
    scenario_id = scenario["id"]
    folder.mkdir(parents=True)
    controllers = [(controller_id, None, None, policy) for controller_id, policy in make_baselines(config).items()]
    controllers.extend((DQN, seed, model_id, policy) for seed, (model_id, policy) in learned.items())
    diagnostics = {
        controller: {tool: {"acquired": 0, "changed_order": 0, "first_changed_trace": None} for tool in TOOLS}
        for controller in (*BASELINE_IDS, DQN)
    }
    metrics = []
    environment = ShopEnvironment(config)
    with (folder / "episodes.jsonl").open("w", encoding="utf-8", newline="\n") as records:
        for market in markets:
            for controller_id, learning_seed, model_id, policy in controllers:
                observation = environment.reset(market)
                while observation is not None:
                    observation = environment.step(policy(observation)).observation
                record = environment.episode_record(source_revision, controller_id, model_id)
                json.dump(record, records, separators=(",", ":"), allow_nan=False)
                records.write("\n")
                metrics.append({**_episode_metrics(record), "learning_seed": learning_seed, "model_id": model_id})
                _update_tool_diagnostics(diagnostics, record, config, learning_seed)

    pairs = _paired_rows(metrics)
    summary = _summarize(metrics, pairs, protocol, selection["primary_baseline"], scenario_id)
    settings = protocol
    bundle = {**market_bundle(markets), "split": HELD_OUT}
    if scenario_id != "primary":
        settings = {**protocol, "environment": asdict(config), "scenario": scenario}
        bundle["scenario"] = scenario

    _write_json(folder / "config.json", settings)
    _write_json(folder / "market_inputs.json", bundle)
    _write_csv(folder / "metrics.csv", metrics)
    _write_csv(folder / "paired_differences.csv", pairs)
    _write_json(folder / "summary.json", summary)
    _write_json(folder / "tool_diagnostics.json", diagnostics)
    _write_json(folder / "manifest.json", {
        "protocol_version": protocol["protocol_version"],
        "environment_version": protocol["environment_version"],
        "market_model_version": protocol["market_model_version"],
        "episode_schema_version": "1",
        "code_revision": source_revision,
        "git_head": git_head,
        "source_sha256": source_hash,
        "python_version": platform.python_version(),
        "scenario": scenario,
        "split": HELD_OUT,
        "market_seeds": protocol["seeds"][HELD_OUT],
        "learning_seeds": protocol["seeds"]["learning"],
        "market_count": len(markets),
        "episode_count": len(metrics),
        "controller_ids": [*BASELINE_IDS, DQN],
        "candidate_id": selection["candidate_id"],
        "checkpoint_episode": selection["checkpoint_episode"],
        "checkpoint_sha256_by_learning_seed": {
            seed: entry["sha256"] for seed, entry in selection["checkpoints"].items()
        },
        "primary_baseline": selection["primary_baseline"],
    })
    return summary


def run_evaluation(
    training: Path, output: Path, protocol_path: Path = DEFAULT_CONFIG, inputs: Path | None = None,
    *, sensitivity: bool = False,
) -> dict:
    """Write the preregistered comparison and optional follow-up cases to a new directory."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output directory already exists: {output}")
    protocol, config = load_protocol(protocol_path)
    selection, training_config, checkpoints = _load_selection(training.resolve(), protocol)

    from ..controllers.dqn import load_controller

    learned = {}
    for seed, checkpoint in checkpoints.items():
        digest = selection["checkpoints"][str(seed)]["sha256"]
        if sha256(checkpoint.read_bytes()).hexdigest() != digest:
            raise ValueError(f"checkpoint {seed} failed SHA-256 verification")
        candidate_id = selection["candidate_id"]
        episode = selection["checkpoint_episode"]
        model_id = f"{candidate_id}:seed-{seed}:episode-{episode}:sha256:{digest}"
        controller = load_controller(checkpoint, config, expected_identity=(candidate_id, seed, episode))
        learned[seed] = model_id, controller

    markets = _held_out_markets(protocol, config, inputs)
    revision = _source_revision()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".held-out-run-") as pending:
        staging = Path(pending) / "run"
        summary = _evaluate_scenario(
            staging, protocol, config, markets, selection, learned, revision, {"id": "primary", "version": "1"},
        )
        _write_json(staging / "selection.json", selection)
        _write_json(staging / "training_config.json", training_config)
        if sensitivity:
            scenarios = {}
            sensitivity_folder = staging / "sensitivity"
            for name, changes in SENSITIVITIES.items():
                numerator, denominator = changes.get("tool_fee_multiplier", 1).as_integer_ratio()
                scenario_config = replace(
                    config, market_report_fee_cents=config.market_report_fee_cents * numerator // denominator,
                    forecast_fee_cents=config.forecast_fee_cents * numerator // denominator,
                )
                scenario_markets = markets
                if "tool_fee_multiplier" not in changes:
                    scenario_markets = tuple(generate_market(config, seed, **changes) for seed in protocol["seeds"][HELD_OUT])
                scenarios[name] = _evaluate_scenario(
                    sensitivity_folder / name, protocol, scenario_config, scenario_markets, selection, learned,
                    revision, {"id": name, "version": "1", **changes},
                )
            _write_json(sensitivity_folder / "summary.json", scenarios)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"output directory already exists: {output}")
        staging.rename(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True, help="training directory containing the frozen selection")
    parser.add_argument("--output", type=Path, required=True, help="new results directory")
    parser.add_argument("--protocol", type=Path, default=DEFAULT_CONFIG, help="frozen experiment protocol JSON")
    parser.add_argument("--inputs", type=Path, help="replay a saved primary held-out market input bundle")
    parser.add_argument("--sensitivity", action="store_true", help="also run the six preregistered follow-up scenarios")
    args = parser.parse_args()
    try:
        summary = run_evaluation(args.training, args.output, args.protocol, args.inputs, sensitivity=args.sensitivity)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote {summary['episode_count']} held-out episodes across {summary['market_count']} matched markets to {args.output}")
    print(f"Primary reference: {summary['primary_baseline']}")


if __name__ == "__main__":
    main()
