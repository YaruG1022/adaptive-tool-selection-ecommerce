"""Load the frozen experiment settings and versioned development market inputs."""

from dataclasses import asdict, fields
import json
from pathlib import Path

from ..environment import DayInput, EnvironmentConfig, MarketInputs, generate_market

PROTOCOL_VERSION = "1"
ENVIRONMENT_VERSION = "1"
MARKET_MODEL_VERSION = "lss-market-v1"
DEVELOPMENT_SPLIT = "validation"
DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "baselines-v1.json"


def _require_fields(data: object, names: set[str], label: str) -> None:
    if not isinstance(data, dict) or set(data) != names:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(names))}")


def load_protocol(path: Path) -> tuple[dict, EnvironmentConfig]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    _require_fields(protocol, {
        "protocol_version", "environment_version", "market_model_version", "environment",
        "seeds", "selection", "analysis",
    }, "protocol")
    if (protocol["protocol_version"], protocol["environment_version"],
            protocol["market_model_version"]) != (
        PROTOCOL_VERSION, ENVIRONMENT_VERSION, MARKET_MODEL_VERSION,
    ):
        raise ValueError("unsupported protocol, environment, or market model version")

    environment = protocol["environment"]
    _require_fields(environment, {field.name for field in fields(EnvironmentConfig)}, "environment")
    config = EnvironmentConfig(**environment)
    seeds = protocol["seeds"]
    _require_fields(seeds, {"train", DEVELOPMENT_SPLIT, "held_out", "learning"}, "seed splits")
    used_seeds: set[int] = set()
    for split, values in seeds.items():
        if not isinstance(values, list) or not values or any(
            type(seed) is not int or seed < 0 for seed in values
        ):
            raise ValueError(f"{split} seeds must be a nonempty list of nonnegative integers")
        if len(set(values)) != len(values) or used_seeds.intersection(values):
            raise ValueError("all lists must contain unique seeds and be disjoint")
        used_seeds.update(values)

    selection = protocol["selection"]
    _require_fields(selection, {
        "baseline_candidates", "dqn_configurations_max", "training_episodes_max",
        "validation_checkpoints_max",
    }, "selection")
    if any(type(value) is not int or value < 1 for value in selection.values()):
        raise ValueError("selection budgets must be positive integers")
    if selection["baseline_candidates"] != 1:
        raise ValueError("the v1 comparison uses one predeclared rule per baseline")

    analysis = protocol["analysis"]
    _require_fields(analysis, {"bootstrap_seed", "bootstrap_replicates", "confidence_level"}, "analysis")
    if type(analysis["bootstrap_seed"]) is not int or analysis["bootstrap_seed"] < 0:
        raise ValueError("bootstrap_seed must be a nonnegative integer")
    if type(analysis["bootstrap_replicates"]) is not int or analysis["bootstrap_replicates"] < 1:
        raise ValueError("bootstrap_replicates must be a positive integer")
    if type(analysis["confidence_level"]) not in (int, float) or not 0 < analysis["confidence_level"] < 1:
        raise ValueError("confidence_level must be strictly between zero and one")
    return protocol, config


def market_bundle(markets: tuple[MarketInputs, ...]) -> dict:
    return {
        "environment_version": ENVIRONMENT_VERSION,
        "market_model_version": MARKET_MODEL_VERSION,
        "split": DEVELOPMENT_SPLIT,
        "markets": [
            {"seed": market.seed, "input_id": market.input_id,
             "days": [asdict(day) for day in market.days]}
            for market in markets
        ],
    }


def validation_markets(
    protocol: dict, config: EnvironmentConfig, input_path: Path | None
) -> tuple[MarketInputs, ...]:
    seeds = protocol["seeds"][DEVELOPMENT_SPLIT]
    if input_path is None:
        return tuple(generate_market(config, seed) for seed in seeds)

    saved = json.loads(input_path.read_text(encoding="utf-8"))
    _require_fields(saved, {"environment_version", "market_model_version", "split", "markets"}, "market inputs")
    if (saved["environment_version"], saved["market_model_version"], saved["split"]) != (
        ENVIRONMENT_VERSION, MARKET_MODEL_VERSION, DEVELOPMENT_SPLIT,
    ):
        raise ValueError("market inputs must use the frozen versions and validation split")
    if not isinstance(saved["markets"], list):
        raise ValueError("markets must be a list")

    by_seed = {}
    for row in saved["markets"]:
        _require_fields(row, {"seed", "input_id", "days"}, "market")
        seed = row["seed"]
        if type(seed) is not int or seed not in seeds or seed in by_seed:
            raise ValueError("saved markets must contain each configured validation seed exactly once")
        if not isinstance(row["days"], list) or len(row["days"]) != config.days:
            raise ValueError(f"market {seed} must contain {config.days} day rows")
        day_fields = {field.name for field in fields(DayInput)}
        for day in row["days"]:
            _require_fields(day, day_fields, f"day in market {seed}")
        market = MarketInputs(tuple(DayInput(**day) for day in row["days"]), seed=seed)
        if row["input_id"] != market.input_id:
            raise ValueError(f"market {seed} does not match its input_id fingerprint")
        by_seed[seed] = market
    if set(by_seed) != set(seeds):
        raise ValueError("saved markets must contain each configured validation seed exactly once")
    return tuple(by_seed[seed] for seed in seeds)
