"""Run all three baselines on the same saved validation market inputs."""

import argparse
import csv
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import platform
from statistics import mean
import subprocess
from tempfile import TemporaryDirectory

from ..controllers.baselines import BASELINE_IDS, make_baselines
from ..environment import ShopEnvironment
from .protocol import DEFAULT_CONFIG, DEVELOPMENT_SPLIT, load_protocol, market_bundle, validation_markets

METRIC_FIELDS = (
    "final_net_worth_cents", "tool_fees_cents", "tool_calls", "sold_units",
    "unfilled_units", "remaining_units",
)
PAIRS = tuple(combinations(BASELINE_IDS, 2))


def _source_revision() -> tuple[str, str | None, str]:
    source_root = Path(__file__).resolve().parents[1]
    source_files = [
        (path.relative_to(source_root).as_posix(), sha256(path.read_bytes()).hexdigest())
        for path in sorted(source_root.rglob("*.py"))
    ]
    source_hash = sha256(json.dumps(source_files, separators=(",", ":")).encode("utf-8")).hexdigest()
    try:
        git = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source_root, capture_output=True,
            text=True, check=False, timeout=5,
        )
        head = git.stdout.strip() if git.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        head = None
    revision = f"{head or 'source'}+sha256:{source_hash}"
    return revision, head, source_hash


def _episode_metrics(record: dict) -> dict:
    transitions = record["transitions"]
    settlements = [day for step in transitions for day in step["settlements"]]
    return {
        "market_seed": record["seed"],
        "input_id": record["input_id"],
        "controller_id": record["controller_id"],
        "total_reward_cents": sum(step["reward_cents"] for step in transitions),
        "final_net_worth_cents": record["final_net_worth_cents"],
        "tool_fees_cents": sum(step["fee_cents"] for step in transitions),
        "tool_calls": sum(step["action"] != "stop" for step in transitions),
        "sold_units": sum(day["sold_units"] for day in settlements),
        "unfilled_units": sum(day["unfilled_units"] for day in settlements),
        "remaining_units": settlements[-1]["closing_stock"],
    }


def _paired_rows(market_rows: dict[str, dict]) -> list[dict]:
    rows = []
    for reference_id, controller_id in PAIRS:
        reference = market_rows[reference_id]
        candidate = market_rows[controller_id]
        rows.append({
            "market_seed": candidate["market_seed"],
            "input_id": candidate["input_id"],
            "controller_id": controller_id,
            "reference_id": reference_id,
            **{f"delta_{field}": candidate[field] - reference[field] for field in METRIC_FIELDS},
        })
    return rows


def _summarize(rows: list[dict], pairs: list[dict], market_count: int) -> dict:
    by_controller = {}
    for controller_id in BASELINE_IDS:
        group = [row for row in rows if row["controller_id"] == controller_id]
        by_controller[controller_id] = {
            "market_count": len(group),
            **{f"mean_{field}": mean(row[field] for row in group) for field in METRIC_FIELDS},
        }
    primary = max(BASELINE_IDS, key=lambda key: by_controller[key]["mean_final_net_worth_cents"])

    pair_summaries = []
    for reference_id, controller_id in PAIRS:
        group = [
            row for row in pairs
            if row["controller_id"] == controller_id and row["reference_id"] == reference_id
        ]
        pair_summaries.append({
            "controller_id": controller_id,
            "reference_id": reference_id,
            "market_count": len(group),
            **{
                f"mean_delta_{field}": mean(row[f"delta_{field}"] for row in group)
                for field in METRIC_FIELDS
            },
        })
    return {
        "split": DEVELOPMENT_SPLIT,
        "market_count": market_count,
        "primary_baseline": primary,
        "by_controller": by_controller,
        "paired_differences": pair_summaries,
    }


def _write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(data, output, indent=2, allow_nan=False)
        output.write("\n")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_comparison(config_path: Path, output: Path, inputs: Path | None = None) -> dict:
    """Publish a complete development run in a new directory and return its summary."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output directory already exists: {output}")
    protocol, config = load_protocol(config_path)
    markets = validation_markets(protocol, config, inputs)
    controllers = make_baselines(config)
    source_revision, git_head, source_hash = _source_revision()
    rows = []
    pairs = []
    output.parent.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(dir=output.parent, prefix=".baseline-run-") as pending:
        staging = Path(pending) / "run"
        staging.mkdir()
        with (staging / "episodes.jsonl").open("w", encoding="utf-8", newline="\n") as records:
            environment = ShopEnvironment(config)
            for market in markets:
                market_rows = {}
                for controller_id, controller in controllers.items():
                    observation = environment.reset(market)
                    while observation is not None:
                        observation = environment.step(controller(observation)).observation
                    record = environment.episode_record(source_revision, controller_id)
                    json.dump(record, records, separators=(",", ":"), allow_nan=False)
                    records.write("\n")
                    metrics = _episode_metrics(record)
                    market_rows[controller_id] = metrics
                    rows.append(metrics)
                pairs.extend(_paired_rows(market_rows))

        summary = _summarize(rows, pairs, len(markets))
        _write_json(staging / "config.json", protocol)
        _write_json(staging / "market_inputs.json", market_bundle(markets))
        _write_csv(staging / "metrics.csv", rows)
        _write_csv(staging / "paired_differences.csv", pairs)
        _write_json(staging / "summary.json", summary)
        _write_json(staging / "manifest.json", {
            "protocol_version": protocol["protocol_version"],
            "environment_version": protocol["environment_version"],
            "market_model_version": protocol["market_model_version"],
            "episode_schema_version": "1",
            "code_revision": source_revision,
            "git_head": git_head,
            "source_sha256": source_hash,
            "python_version": platform.python_version(),
            "split": DEVELOPMENT_SPLIT,
            "market_seeds": protocol["seeds"][DEVELOPMENT_SPLIT],
            "market_count": len(markets),
            "episode_count": len(rows),
            "controller_ids": list(controllers),
            "market_input_source": "generated" if inputs is None else "saved",
            "primary_baseline": summary["primary_baseline"],
        })
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"output directory already exists: {output}")
        staging.rename(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="versioned protocol JSON")
    parser.add_argument("--output", type=Path, required=True, help="new results directory")
    parser.add_argument("--inputs", type=Path, help="replay a saved market_inputs.json bundle")
    args = parser.parse_args()
    try:
        summary = run_comparison(args.config, args.output, args.inputs)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Wrote {summary['market_count']} matched markets to {args.output}")
    print(f"Primary baseline: {summary['primary_baseline']}")


if __name__ == "__main__":
    main()
