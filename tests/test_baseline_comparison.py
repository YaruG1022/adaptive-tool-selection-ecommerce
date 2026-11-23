import csv
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from little_signal_shop.environment import EnvironmentConfig


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_IDS = ("no_tools", "fixed_order", "uncertainty_threshold")
PAIRS = (
    ("fixed_order", "no_tools"),
    ("uncertainty_threshold", "no_tools"),
    ("uncertainty_threshold", "fixed_order"),
)
SCIENCE_OUTPUTS = (
    "config.json",
    "market_inputs.json",
    "episodes.jsonl",
    "metrics.csv",
    "paired_differences.csv",
    "summary.json",
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class BaselineComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.config_path = self.workspace / "config.json"
        self.config = {
            "protocol_version": "1",
            "environment_version": "1",
            "market_model_version": "lss-market-v1",
            "environment": asdict(EnvironmentConfig(days=3)),
            "seeds": {
                "train": [101, 102],
                "validation": [202, 203, 204],
                "held_out": [303, 304],
                "learning": [404, 405],
            },
            "selection": {
                "baseline_candidates": 1,
                "dqn_configurations_max": 4,
                "training_episodes_max": 500,
                "validation_checkpoints_max": 10,
            },
            "analysis": {
                "bootstrap_seed": 8801,
                "bootstrap_replicates": 10_000,
                "confidence_level": 0.95,
            },
        }
        self.write_config()

    def write_config(self):
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")

    def run_cli(self, output, *, inputs=None, success=True):
        command = [
            sys.executable,
            "-B",
            "-m",
            "little_signal_shop.experiments.baseline_comparison",
            "--config",
            str(self.config_path),
            "--output",
            str(output),
        ]
        if inputs is not None:
            command.extend(("--inputs", str(inputs)))
        environment = dict(os.environ, PYTHONPATH=str(REPO_ROOT / "research" / "src"))
        result = subprocess.run(
            command, cwd=REPO_ROOT, env=environment, capture_output=True, text=True, timeout=30
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_validation_episodes_metrics_and_pairs_reconcile(self):
        output = self.workspace / "run"
        self.run_cli(output)
        self.assertEqual(
            {child.name for child in output.iterdir()},
            {*SCIENCE_OUTPUTS, "manifest.json"},
        )
        self.assertEqual(read_json(output / "config.json"), self.config)

        validation = self.config["seeds"]["validation"]
        manifest = read_json(output / "manifest.json")
        self.assertEqual(manifest["split"], "validation")
        self.assertCountEqual(manifest["market_seeds"], validation)
        self.assertEqual(manifest["episode_count"], len(validation) * len(CONTROLLER_IDS))
        self.assertRegex(manifest["source_sha256"], r"^[a-f0-9]{64}$")
        inputs = read_json(output / "market_inputs.json")
        self.assertEqual(inputs["split"], "validation")
        self.assertEqual(inputs["environment_version"], "1")
        self.assertEqual(inputs["market_model_version"], "lss-market-v1")
        self.assertCountEqual([entry["seed"] for entry in inputs["markets"]], validation)
        markets = {entry["seed"]: entry for entry in inputs["markets"]}

        record_lines = (output / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in record_lines]
        expected_episode_keys = [
            (seed, controller) for seed in validation for controller in CONTROLLER_IDS
        ]
        self.assertCountEqual(
            [(record["seed"], record["controller_id"]) for record in records],
            expected_episode_keys,
        )
        metrics = read_csv(output / "metrics.csv")
        self.assertCountEqual(
            [(int(row["market_seed"]), row["controller_id"]) for row in metrics],
            expected_episode_keys,
        )
        metric_by_key = {(int(row["market_seed"]), row["controller_id"]): row for row in metrics}

        for record in records:
            key = (record["seed"], record["controller_id"])
            with self.subTest(seed=key[0], controller=key[1]):
                market = markets[key[0]]
                row = metric_by_key[key]
                self.assertEqual(record["input_id"], market["input_id"])
                self.assertEqual(row["input_id"], market["input_id"])
                self.assertEqual(record["code_revision"], manifest["code_revision"])
                self.assertEqual(
                    record["analysis_only"]["daily_demand"],
                    [day["demand"] for day in market["days"]],
                )
                transitions = record["transitions"]
                receipts = [day for step in transitions for day in step["settlements"]]
                self.assertEqual([day["day"] for day in receipts], [1, 2, 3])
                expected = {
                    "final_net_worth_cents": record["final_net_worth_cents"],
                    "total_reward_cents": (
                        record["final_net_worth_cents"] - record["initial_net_worth_cents"]
                    ),
                    "tool_fees_cents": sum(step["fee_cents"] for step in transitions),
                    "tool_calls": sum(step["action"] != "stop" for step in transitions),
                    "sold_units": sum(day["sold_units"] for day in receipts),
                    "unfilled_units": sum(day["unfilled_units"] for day in receipts),
                    "remaining_units": receipts[-1]["closing_stock"],
                }
                self.assertEqual(
                    {name: int(row[name]) for name in expected},
                    expected,
                )
                if key[1] == "no_tools":
                    self.assertEqual(int(row["tool_calls"]), 0)

        paired = read_csv(output / "paired_differences.csv")
        self.assertCountEqual(
            [(int(row["market_seed"]), row["controller_id"], row["reference_id"]) for row in paired],
            [(seed, controller, reference) for seed in validation for controller, reference in PAIRS],
        )
        provided_deltas = (
            "final_net_worth_cents",
            "tool_fees_cents",
            "tool_calls",
            "sold_units",
            "unfilled_units",
            "remaining_units",
        )
        for row in paired:
            seed = int(row["market_seed"])
            current = metric_by_key[seed, row["controller_id"]]
            reference = metric_by_key[seed, row["reference_id"]]
            self.assertEqual(row["input_id"], markets[seed]["input_id"])
            for metric in provided_deltas:
                self.assertEqual(
                    int(row[f"delta_{metric}"]), int(current[metric]) - int(reference[metric])
                )

        summary = read_json(output / "summary.json")
        self.assertEqual(summary["split"], "validation")
        self.assertEqual(summary["market_count"], len(validation))
        net_worth_totals = {
            controller: sum(
                int(metric_by_key[seed, controller]["final_net_worth_cents"])
                for seed in validation
            )
            for controller in CONTROLLER_IDS
        }
        expected_primary = max(CONTROLLER_IDS, key=net_worth_totals.__getitem__)
        self.assertEqual(summary["primary_baseline"], expected_primary)
        self.assertEqual(manifest["primary_baseline"], expected_primary)
        self.assertEqual(set(summary["by_controller"]), set(CONTROLLER_IDS))
        for controller, total in net_worth_totals.items():
            aggregate = summary["by_controller"][controller]
            self.assertEqual(aggregate["market_count"], len(validation))
            self.assertEqual(aggregate["mean_final_net_worth_cents"], total / len(validation))
        self.assertCountEqual(
            [(row["controller_id"], row["reference_id"]) for row in summary["paired_differences"]],
            PAIRS,
        )
        for row in summary["paired_differences"]:
            total_difference = (
                net_worth_totals[row["controller_id"]] - net_worth_totals[row["reference_id"]]
            )
            self.assertEqual(row["market_count"], len(validation))
            self.assertEqual(row["mean_delta_final_net_worth_cents"], total_difference / len(validation))

    def test_replay_from_saved_inputs_reproduces_scientific_outputs(self):
        original = self.workspace / "original"
        replay = self.workspace / "replay"
        self.run_cli(original)
        self.run_cli(replay, inputs=original / "market_inputs.json")
        for filename in SCIENCE_OUTPUTS:
            with self.subTest(filename=filename):
                self.assertEqual((original / filename).read_bytes(), (replay / filename).read_bytes())

    def test_existing_output_is_never_overwritten(self):
        output = self.workspace / "present"
        output.mkdir()
        existing = output / "summary.json"
        existing.write_bytes(b"preserve this result")
        self.run_cli(output, success=False)
        self.assertEqual(existing.read_bytes(), b"preserve this result")
        self.assertEqual(list(output.iterdir()), [existing])

    def test_modified_saved_market_rows_are_rejected(self):
        original = self.workspace / "original"
        self.run_cli(original)
        modified = read_json(original / "market_inputs.json")
        modified["markets"][0]["days"][0]["demand"] += 1
        bad_inputs = self.workspace / "edited.json"
        bad_inputs.write_text(json.dumps(modified), encoding="utf-8")
        result = self.run_cli(self.workspace / "invalid", inputs=bad_inputs, success=False)
        self.assertIn("input_id fingerprint", result.stderr)

    def test_overlapping_validation_and_held_out_seeds_are_rejected(self):
        self.config["seeds"]["held_out"][0] = self.config["seeds"]["validation"][0]
        self.write_config()
        result = self.run_cli(self.workspace / "invalid", success=False)
        self.assertIn("disjoint", result.stderr)


if __name__ == "__main__":
    unittest.main()
