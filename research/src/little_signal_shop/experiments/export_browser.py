"""Export saved research episodes and their verified summaries for local browser replay."""

import argparse
import csv
from dataclasses import fields
import json
from math import isfinite
import os
from pathlib import Path
from statistics import mean
from tempfile import TemporaryDirectory

from ..controllers.baselines import BASELINE_IDS
from ..environment import DayInput, EnvironmentConfig, MarketInputs
from ..policies.replenishment import replenishment_units
from .baseline_comparison import METRIC_FIELDS, _episode_metrics
from .evaluate_dqn import DQN, HELD_OUT, paired_bootstrap
from .protocol import DEVELOPMENT_SPLIT, ENVIRONMENT_VERSION, MARKET_MODEL_VERSION, PROTOCOL_VERSION, _require_fields, load_protocol


FORMAT = "little-signal-shop-research"
SCHEMA_VERSION = "1"
TOOL_FIELDS = {
    "market_report": ("market_report_fee_cents", "market_report_minutes"),
    "forecast": ("forecast_fee_cents", "forecast_minutes"),
}


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _object(path: Path) -> dict:
    content = json.loads(path.read_text(encoding="utf-8"))
    _check(isinstance(content, dict), f"{path.name} must contain a JSON object")
    return content


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite(value: object) -> bool:
    return type(value) in (int, float) and isfinite(value)


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _load_markets(run: Path, config: EnvironmentConfig, manifest: dict) -> dict[int, MarketInputs]:
    bundle = _object(run / "market_inputs.json")
    for field in ("environment_version", "market_model_version", "split"):
        _check(bundle.get(field) == manifest[field], f"market bundle has a foreign {field}")
    if "scenario" in bundle:
        _check(bundle["scenario"] == manifest.get("scenario"), "market bundle has a foreign scenario")
    seeds = manifest["market_seeds"]
    markets = bundle.get("markets")
    _check(isinstance(markets, list), "market bundle must contain a list of markets")
    day_fields = {field.name for field in fields(DayInput)}
    by_seed = {}
    for row in markets:
        _require_fields(row, {"seed", "input_id", "days"}, "saved market")
        seed = row["seed"]
        _check(type(seed) is int and seed in seeds and seed not in by_seed, "foreign or duplicate market seed")
        _check(isinstance(row["days"], list) and len(row["days"]) == config.days, f"wrong day count for market {seed}")
        for day in row["days"]:
            _require_fields(day, day_fields, f"day input in market {seed}")
        market = MarketInputs(tuple(DayInput(**day) for day in row["days"]), seed=seed)
        _check(market.input_id == row["input_id"], f"market {seed} has a foreign input ID")
        by_seed[seed] = market
    _check(set(by_seed) == set(seeds), "market bundle is missing registered market inputs")
    return by_seed


def _load_metrics(run: Path, split: str) -> dict[tuple, dict]:
    by_key = {}
    numeric = ("total_reward_cents", *METRIC_FIELDS)
    basic_fields = {"market_seed", "input_id", "controller_id", *numeric}
    expected_fields = basic_fields | ({"learning_seed", "model_id"} if split == HELD_OUT else set())
    with (run / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames or []
        _check(set(names) == expected_fields and len(names) == len(expected_fields), "unexpected metrics.csv columns")
        for row in reader:
            _check(None not in row and None not in row.values(), "incomplete metrics.csv row")
            seed = int(row["market_seed"])
            learning_seed = int(row["learning_seed"]) if row.get("learning_seed") else None
            key = seed, row["controller_id"], learning_seed
            _check(key not in by_key, f"duplicate episode metrics for {key}")
            by_key[key] = {
                **row, "market_seed": seed, "learning_seed": learning_seed,
                "model_id": row.get("model_id") or None, **{name: int(row[name]) for name in numeric},
            }
    return by_key


def _models(manifest: dict, settings: dict) -> dict[int, str]:
    if manifest["split"] == DEVELOPMENT_SPLIT:
        _check(manifest.get("controller_ids") == list(BASELINE_IDS), "validation controller IDs do not match the baseline grid")
        return {}
    _check(manifest.get("controller_ids") == [*BASELINE_IDS, DQN], "held-out controller IDs do not match the evaluation grid")
    seeds = settings["seeds"]["learning"]
    _check(manifest.get("learning_seeds") == seeds and bool(seeds), "learning seeds disagree with the protocol")
    candidate = manifest.get("candidate_id")
    episode = manifest.get("checkpoint_episode")
    _check(_nonblank(candidate) and type(episode) is int and episode > 0, "held-out manifest lacks frozen model identity")
    digests = manifest.get("checkpoint_sha256_by_learning_seed")
    _require_fields(digests, {str(seed) for seed in seeds}, "selected checkpoint digests")
    _check(all(_digest(digest) for digest in digests.values()), "invalid selected checkpoint digest")
    return {
        seed: f"{candidate}:seed-{seed}:episode-{episode}:sha256:{digests[str(seed)]}" for seed in seeds
    }


def _close_day(settlement: dict, *, day: int, cash: int, stock: int, received: int, demand: int,
               ordered: int, config: EnvironmentConfig) -> None:
    sold = min(stock, demand)
    closing_stock = stock - sold
    purchase = ordered * config.unit_cost_cents
    revenue = sold * config.selling_price_cents
    closing_cash = cash - purchase + revenue
    write_down = 0
    if day == config.days:
        write_down = closing_stock * max(0, config.unit_cost_cents - config.terminal_unit_nrv_cents)
    inventory = (closing_stock + ordered) * config.unit_cost_cents - write_down
    expected = {
        "day": day, "received_units": received, "opening_stock": stock, "ordered_units": ordered,
        "purchase_cents": purchase, "delivery_day": day + 1 if ordered else None,
        "sold_units": sold, "unfilled_units": demand - sold, "revenue_cents": revenue,
        "closing_stock": closing_stock, "in_transit_units": ordered, "cash_cents": closing_cash,
        "inventory_value_cents": inventory, "terminal_write_down_cents": write_down,
        "net_worth_cents": closing_cash + inventory,
    }
    _check(isinstance(settlement, dict) and settlement == expected, f"day {day} settlement does not reconcile")
    _check(all(type(settlement[key]) is type(value) for key, value in expected.items()), f"day {day} has invalid ledger types")


def _decision_open(config: EnvironmentConfig, day: int, market: DayInput, cash: int, stock: int,
                   sales_yesterday: int | None) -> dict:
    return _with_legal_tools({
        "day": day, "clock_minute": config.opening_minute, "cash_cents": cash, "stock": stock,
        "public_today": market.public_today, "public_tomorrow": market.public_tomorrow,
        "market_report": None, "forecast": None, "sales_yesterday": sales_yesterday,
        "remaining_days": config.days - day + 1, "remaining_calls": len(TOOL_FIELDS),
    }, config)


def _with_legal_tools(observation: dict, config: EnvironmentConfig) -> dict:
    tools = [
        tool for tool, (fee, duration) in TOOL_FIELDS.items()
        if observation[tool] is None and observation["cash_cents"] >= getattr(config, fee)
        and observation["clock_minute"] + getattr(config, duration) <= config.cutoff_minute
    ]
    return {**observation, "legal_actions": ["stop", *tools]}


def _episode_days(record: dict, market: MarketInputs, config: EnvironmentConfig) -> list[dict]:
    opening_cash = config.opening_cash_cents
    opening_worth = opening_cash + config.opening_stock * config.unit_cost_cents
    _check(record["initial_net_worth_cents"] == opening_worth, "episode initial net worth disagrees with configuration")
    _check(record.get("analysis_only") == {"daily_demand": [day.demand for day in market.days]}, "episode demand disagrees with saved market")
    transitions = record.get("transitions")
    _check(isinstance(transitions, list) and bool(transitions), "episode is missing transitions")

    expected = _decision_open(config, 1, market.days[0], opening_cash, config.opening_stock, None)
    worth = opening_worth
    delivered = 0
    days = []
    tools = []
    for transition in transitions:
        _require_fields(transition, {"action", "before", "after", "reward_cents", "net_worth_cents", "fee_cents", "settlements"}, "transition")
        _check(expected is not None and transition["before"] == expected, "decision observation does not reconcile")
        before = expected
        day = before["day"]
        market_day = market.days[day - 1]
        action = transition["action"]
        _check(action in before["legal_actions"], f"day {day} records an illegal action")
        settlements = transition["settlements"]
        fee = 0
        if action != "stop":
            _check(settlements == [], f"day {day} tool action includes a settlement")
            fee_key, minutes_key = TOOL_FIELDS[action]
            fee = getattr(config, fee_key)
            end = before["clock_minute"] + getattr(config, minutes_key)
            estimate = getattr(market_day, action)
            tools.append({"id": action, "start_minute": before["clock_minute"], "end_minute": end, "fee_cents": fee, "estimate": estimate})
            expected = _with_legal_tools({
                **before, action: estimate, "clock_minute": end, "cash_cents": before["cash_cents"] - fee,
                "remaining_calls": before["remaining_calls"] - 1,
            }, config)
            updated_worth = worth - fee
        else:
            terminal_follows = day == config.days - 1
            _check(isinstance(settlements, list) and len(settlements) == 1 + terminal_follows, f"day {day} has incomplete settlements")
            ordered = replenishment_units(
                stock=before["stock"], cash_cents=before["cash_cents"], unit_cost_cents=config.unit_cost_cents,
                expected_today=before["public_today"] if before["market_report"] is None else before["market_report"],
                target_tomorrow=before["public_tomorrow"] if before["forecast"] is None else before["forecast"],
            )
            settled = settlements[0]
            _close_day(settled, day=day, cash=before["cash_cents"], stock=before["stock"], received=delivered,
                       demand=market_day.demand, ordered=ordered, config=config)
            days.append({
                "settlement": settled, "opening_cash_cents": opening_cash, "opening_net_worth_cents": opening_worth,
                "public_today": before["public_today"], "public_tomorrow": before["public_tomorrow"],
                "stop_minute": before["clock_minute"], "tools": tools, "demand": market_day.demand,
            })
            next_market = market.days[day]
            opening_cash, opening_worth = settled["cash_cents"], settled["net_worth_cents"]
            next_stock = settled["closing_stock"] + ordered
            delivered = ordered
            tools = []
            if terminal_follows:
                terminal = settlements[1]
                _close_day(terminal, day=day + 1, cash=opening_cash, stock=next_stock, received=delivered,
                           demand=next_market.demand, ordered=0, config=config)
                days.append({
                    "settlement": terminal, "opening_cash_cents": opening_cash, "opening_net_worth_cents": opening_worth,
                    "public_today": None, "public_tomorrow": None, "stop_minute": None, "tools": [], "demand": next_market.demand,
                })
                updated_worth = terminal["net_worth_cents"]
                expected = None
            else:
                updated_worth = opening_worth
                expected = _decision_open(config, day + 1, next_market, opening_cash, next_stock, settled["sold_units"])
        _check(transition["after"] == expected, f"day {day} result observation does not reconcile")
        _check(transition["fee_cents"] == fee and transition["net_worth_cents"] == updated_worth
               and transition["reward_cents"] == updated_worth - worth, f"day {day} reward or fee does not reconcile")
        worth = updated_worth

    _check(expected is None and len(days) == config.days, "episode ends before its terminal settlement")
    _check(record["final_net_worth_cents"] == worth, "episode final net worth does not reconcile")
    return days


def _training_curves(training: Path, settings: dict, manifest: dict) -> dict:
    _check(manifest["split"] == HELD_OUT and manifest.get("scenario", {}).get("id") == "primary",
           "training curves can only attach to the matching primary held-out run")
    protocol, _ = load_protocol(training / "protocol.json")
    _check(protocol == settings, "training protocol does not match the evaluation run")
    selection = _object(training / "selection.json")
    for key in ("primary_baseline", "candidate_id", "checkpoint_episode", "learning_seeds"):
        _check(selection.get(key) == manifest[key], f"training selection has a foreign {key}")
    seeds = manifest["learning_seeds"]
    checkpoint_entries = selection.get("checkpoints")
    _require_fields(checkpoint_entries, {str(seed) for seed in seeds}, "training selection checkpoints")
    for seed, checkpoint in checkpoint_entries.items():
        _check(isinstance(checkpoint, dict) and checkpoint.get("sha256") == manifest["checkpoint_sha256_by_learning_seed"][seed],
               f"training selection has a foreign checkpoint for learning seed {seed}")

    ranking = _object(training / "validation_ranking.json").get("ranking")
    _check(isinstance(ranking, list) and bool(ranking), "training ranking is missing validation points")
    points_by_candidate = {}
    expected_count = len(seeds) * len(settings["seeds"][DEVELOPMENT_SPLIT])
    for row in ranking:
        _check(isinstance(row, dict), "training ranking contains an invalid row")
        candidate = row.get("candidate_id")
        episode = row.get("checkpoint_episode")
        score = row.get("validation_mean_final_net_worth_cents")
        total = row.get("validation_total_final_net_worth_cents")
        _check(_nonblank(candidate) and type(episode) is int and 0 < episode <= settings["selection"]["training_episodes_max"],
               "training ranking contains an invalid candidate or checkpoint")
        _check(_finite(score) and type(total) is int and row.get("validation_episode_count") == expected_count
               and score == total / expected_count, "training ranking score does not reconcile with its validation count and total")
        points = points_by_candidate.setdefault(candidate, {})
        _check(episode not in points, "training ranking contains a duplicate checkpoint")
        points[episode] = score

    best = min((-score, episode, candidate) for candidate, points in points_by_candidate.items() for episode, score in points.items())
    selected = selection.get("validation_mean_final_net_worth_cents")
    _check(_finite(selected) and best == (-selected, selection["checkpoint_episode"], selection["candidate_id"]),
           "training ranking does not support the frozen selection")
    return {
        "selected_candidate": selection["candidate_id"], "selected_episode": selection["checkpoint_episode"],
        "learning_seeds": seeds, "series": [
            {"candidate_id": candidate, "points": [
                {"episode": episode, "mean_final_net_worth_cents": score} for episode, score in sorted(points.items())
            ]} for candidate, points in sorted(points_by_candidate.items())
        ],
    }


def _evaluation(summary: dict, settings: dict, manifest: dict, rows: dict) -> dict | None:
    split = manifest["split"]
    _check(summary.get("split") == split and summary.get("primary_baseline") == manifest["primary_baseline"]
           and summary.get("market_count") == manifest["market_count"], "summary does not match the archived run")
    controller_summaries = summary.get("by_controller")
    _require_fields(controller_summaries, set(manifest["controller_ids"]), "summary controllers")
    for controller, saved in controller_summaries.items():
        _check(isinstance(saved, dict), f"missing summary metrics for {controller}")
        group = [row for row in rows.values() if row["controller_id"] == controller]
        count_key = "episode_count" if split == HELD_OUT else "market_count"
        _check(saved.get(count_key) == len(group) and all(saved.get(f"mean_{metric}") == mean(row[metric] for row in group)
               for metric in METRIC_FIELDS), f"summary metrics do not reconcile for {controller}")
    reference = manifest["primary_baseline"]
    if split == DEVELOPMENT_SPLIT:
        _check(reference == max(BASELINE_IDS, key=lambda controller: controller_summaries[controller]["mean_final_net_worth_cents"]),
               "validation summary froze a different baseline")
        return None

    contrast = summary.get("primary_contrast")
    _check(isinstance(contrast, dict) and contrast.get("controller_id") == DQN and contrast.get("reference_id") == reference
           and contrast.get("metric") == "final_net_worth_cents", "summary has a foreign primary contrast")
    grid = [[
        rows[market, DQN, learning]["final_net_worth_cents"] - rows[market, reference, None]["final_net_worth_cents"]
        for market in manifest["market_seeds"]
    ] for learning in manifest["learning_seeds"]]
    analysis = settings["analysis"]
    interval = list(paired_bootstrap(grid, seed=analysis["bootstrap_seed"], replicates=analysis["bootstrap_replicates"],
                                    confidence_level=analysis["confidence_level"]))
    _check(contrast.get("mean_delta") == mean(value for row in grid for value in row)
           and contrast.get("confidence_level") == analysis["confidence_level"] and contrast.get("confidence_interval") == interval,
           "archived primary contrast does not reconcile with paired episode outcomes")
    return {
        "reference_id": reference, "mean_delta_cents": contrast["mean_delta"],
        "confidence_level": contrast["confidence_level"], "confidence_interval_cents": contrast["confidence_interval"],
    }


def _bundle(run: Path, training: Path | None) -> dict:
    manifest = _object(run / "manifest.json")
    settings = _object(run / "config.json")
    for key, version in (("protocol_version", PROTOCOL_VERSION), ("environment_version", ENVIRONMENT_VERSION),
                         ("market_model_version", MARKET_MODEL_VERSION)):
        _check(manifest.get(key) == settings.get(key) == version, f"archived {key} does not match the exporter")
    _check(manifest.get("episode_schema_version") == SCHEMA_VERSION and _nonblank(manifest.get("code_revision")),
           "run manifest lacks episode schema or source identity")
    split = manifest.get("split")
    _check(split in (DEVELOPMENT_SPLIT, HELD_OUT), "source must be a validation or held-out run")
    scenario_record = manifest.get("scenario", {"id": "primary"})
    _check(isinstance(scenario_record, dict) and _nonblank(scenario_record.get("id")), "invalid run scenario")
    scenario = scenario_record["id"]
    if scenario != "primary":
        _check(settings.get("scenario") == scenario_record, "sensitivity configuration and manifest differ")
    else:
        _check("scenario" not in settings, "primary configuration must use the registered settings")

    environment = settings.get("environment")
    _require_fields(environment, {field.name for field in fields(EnvironmentConfig)}, "archive environment configuration")
    config = EnvironmentConfig(**environment)
    seed_sets = settings.get("seeds")
    _require_fields(seed_sets, {"train", DEVELOPMENT_SPLIT, HELD_OUT, "learning"}, "archive seed splits")
    all_seeds = set()
    for name, split_seeds in seed_sets.items():
        _check(isinstance(split_seeds, list) and bool(split_seeds) and all(type(seed) is int and seed >= 0 for seed in split_seeds),
               f"invalid {name} seed list")
        _check(len(set(split_seeds)) == len(split_seeds) and not all_seeds.intersection(split_seeds), "archived seed lists overlap")
        all_seeds.update(split_seeds)
    seeds = seed_sets[split]
    _check(manifest.get("market_seeds") == seeds and manifest.get("market_count") == len(seeds), "archived market list differs from the protocol")
    _check(manifest.get("primary_baseline") in BASELINE_IDS, "archive has an unknown primary baseline")
    markets = _load_markets(run, config, manifest)
    models = _models(manifest, settings)
    seed_by_model = {model: seed for seed, model in models.items()}
    expected_keys = {(market, baseline, None) for market in seeds for baseline in BASELINE_IDS}
    expected_keys.update((market, DQN, seed) for market in seeds for seed in models)
    rows = _load_metrics(run, split)
    _check(set(rows) == expected_keys and manifest.get("episode_count") == len(expected_keys), "metrics do not cover the complete paired episode grid")
    summary = _object(run / "summary.json")

    episodes = []
    used_keys = set()
    with (run / "episodes.jsonl").open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
                _check(isinstance(record, dict) and record.get("environment_version") == ENVIRONMENT_VERSION
                       and record.get("schema_version") == SCHEMA_VERSION and record.get("code_revision") == manifest["code_revision"]
                       and record.get("config") == environment, "foreign episode identity or environment")
                seed, controller = record.get("seed"), record.get("controller_id")
                model = record.get("model_id")
                _check(type(seed) is int and seed in markets and record.get("input_id") == markets[seed].input_id,
                       "episode has a foreign market input")
                _check((controller == DQN and model in seed_by_model) or (controller in BASELINE_IDS and model is None),
                       "episode has a foreign controller or model")
                learning_seed = seed_by_model.get(model)
                key = seed, controller, learning_seed
                _check(key in expected_keys and key not in used_keys, "duplicate or foreign episode")
                days = _episode_days(record, markets[seed], config)
                _check(rows[key] == {**_episode_metrics(record), "learning_seed": learning_seed, "model_id": model},
                       "episode ledger does not reconcile with saved metrics")
                used_keys.add(key)
                episodes.append({
                    "seed": seed, "input_id": record["input_id"], "controller_id": controller, "model_id": model,
                    "learning_seed": learning_seed, "initial_net_worth_cents": record["initial_net_worth_cents"],
                    "final_net_worth_cents": record["final_net_worth_cents"], "days": days,
                })
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"episodes.jsonl line {line_number}: {error}") from error
    _check(used_keys == expected_keys, "episodes.jsonl is missing a paired episode")
    return {
        "format": FORMAT, "schema_version": SCHEMA_VERSION, "environment_version": ENVIRONMENT_VERSION,
        "run": {"code_revision": manifest["code_revision"], "split": split, "scenario": scenario,
                "primary_baseline": manifest["primary_baseline"], "config": environment},
        "episodes": episodes, "evaluation": _evaluation(summary, settings, manifest, rows),
        "training": None if training is None else _training_curves(training, settings, manifest),
    }


def export_browser(run: Path, output: Path, training: Path | None = None) -> dict:
    """Publish a new browser JSON only after all source records have reconciled."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output file already exists: {output}")
    bundle = _bundle(run, training)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent, prefix=".browser-export-") as temporary:
        staged = Path(temporary) / "bundle.json"
        with staged.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(bundle, stream, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
        if os.name == "nt":
            staged.rename(output)
        else:
            os.link(staged, output)
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="saved Phase 3 or Phase 5 run directory")
    parser.add_argument("--output", type=Path, required=True, help="new browser bundle JSON path")
    parser.add_argument("--training", type=Path, help="matching Phase 4 directory with validation ranking")
    args = parser.parse_args()
    try:
        bundle = export_browser(args.run, args.output, args.training)
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(f"Wrote {len(bundle['episodes'])} research episodes to {args.output}")


if __name__ == "__main__":
    main()
