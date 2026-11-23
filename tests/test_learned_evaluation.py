import csv
from dataclasses import replace
from hashlib import sha256
from importlib.util import find_spec
import json
from math import isfinite
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from little_signal_shop.environment import Action, EnvironmentConfig, ShopEnvironment, generate_market
from little_signal_shop.experiments.baseline_comparison import run_comparison
from little_signal_shop.experiments.protocol import DEFAULT_CONFIG, load_protocol


REPO_ROOT = Path(__file__).resolve().parents[1]
DQN_CONFIG = REPO_ROOT / "research" / "configs" / "dqn-v1.json"
TRAIN_SEEDS = [101, 102]
VALIDATION_SEEDS = [202, 203]
HELD_OUT_SEEDS = [303, 304]
LEARNING_SEEDS = [404, 405]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class EnvironmentRecordingTests(unittest.TestCase):
    def test_disabling_recording_preserves_decisions_and_rewards(self):
        config = EnvironmentConfig(days=4)
        market = generate_market(config, seed=17)
        recording = ShopEnvironment(config)
        unrecorded = ShopEnvironment(config, record_transitions=False)
        observation = recording.reset(market)
        self.assertEqual(observation, unrecorded.reset(market))
        while observation is not None:
            action = (
                Action.FORECAST if Action.FORECAST in observation.legal_actions else Action.STOP
            )
            result = recording.step(action)
            self.assertEqual(result, unrecorded.step(action))
            observation = result.observation
        recording.episode_record("test-source", "test-controller")
        with self.assertRaises(RuntimeError):
            unrecorded.episode_record("test-source", "test-controller")


@unittest.skipIf(find_spec("torch") is None, "PyTorch is required for learned-controller tests")
class LearnedMathTests(unittest.TestCase):
    def test_bootstrap_resamples_both_axes_and_interpolates_percentiles(self):
        from little_signal_shop.experiments.evaluate_dqn import paired_bootstrap

        differences = [[15, -1], [7, 29]]
        interval = paired_bootstrap(differences, seed=2, replicates=7, confidence_level=0.80)
        # The sorted resample means are -1, 7, 11, 12.5, 14, 15, and 18.
        # An 80% interval interpolates at indices 0.6 and 5.4.
        self.assertAlmostEqual(interval[0], 3.8)
        self.assertAlmostEqual(interval[1], 16.2)
        self.assertEqual(
            interval,
            paired_bootstrap(differences, seed=2, replicates=7, confidence_level=0.80),
        )

    def test_bootstrap_preserves_a_constant_signed_difference(self):
        from little_signal_shop.experiments.evaluate_dqn import paired_bootstrap

        interval = paired_bootstrap(
            [[-4, -4, -4], [-4, -4, -4]], seed=8801, replicates=50, confidence_level=0.95
        )
        self.assertEqual(interval, (-4, -4))

    def test_target_values_mask_illegal_actions_and_zero_terminal_bootstraps(self):
        import torch

        from little_signal_shop.controllers.dqn import masked_bootstrap

        values = torch.tensor([
            [10.0, -4.0, 8.0], [10.0, 9.0, 8.0], [-3.0, 20.0, 15.0], [0.0, 3.0, 2.0],
        ])
        legal = torch.tensor([
            [False, True, False], [True, True, True], [True, False, True], [False, False, False],
        ])
        terminated = torch.tensor([False, True, False, True])
        self.assertEqual(masked_bootstrap(values, legal, terminated).tolist(), [-4.0, 0.0, 15.0, 0.0])

    def test_greedy_selection_ignores_the_highest_scoring_illegal_action(self):
        import torch

        from little_signal_shop.controllers.dqn import greedy_actions

        class FixedScores(torch.nn.Module):
            def forward(self, features):
                return torch.tensor([[1.0, 50.0, 2.0]]).expand(len(features), -1)

        config = EnvironmentConfig(days=3, market_report_minutes=91)
        decision = ShopEnvironment(config).reset(generate_market(config, seed=17))
        self.assertEqual(decision.legal_actions, (Action.STOP, Action.FORECAST))
        self.assertEqual(greedy_actions(FixedScores(), [decision], config), [Action.FORECAST])

    def test_training_configuration_enforces_candidate_episode_and_checkpoint_quotas(self):
        from little_signal_shop.experiments.train_dqn import load_training_config

        settings = read_json(DQN_CONFIG)
        settings["episodes"] = 2
        settings["checkpoint_episodes"] = [1, 2]
        settings["epsilon_decay_episodes"] = 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "training.json"
            write_json(path, settings)
            self.assertEqual(load_training_config(path, read_json(DEFAULT_CONFIG)), settings)
            for lowered_limit in (
                "dqn_configurations_max", "training_episodes_max", "validation_checkpoints_max",
            ):
                with self.subTest(quota=lowered_limit):
                    protocol = read_json(DEFAULT_CONFIG)
                    protocol["selection"][lowered_limit] = 1
                    with self.assertRaises(ValueError):
                        load_training_config(path, protocol)


@unittest.skipIf(find_spec("torch") is None, "PyTorch is required for learned-controller tests")
class LearnedEvaluationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.workspace = Path(directory.name)
        cls.protocol_path = cls.workspace / "protocol.json"
        protocol = read_json(DEFAULT_CONFIG)
        protocol["environment"]["days"] = 3
        protocol["seeds"] = {
            "train": TRAIN_SEEDS,
            "validation": VALIDATION_SEEDS,
            "held_out": HELD_OUT_SEEDS,
            "learning": LEARNING_SEEDS,
        }
        protocol["analysis"]["bootstrap_replicates"] = 100
        write_json(cls.protocol_path, protocol)
        _, cls.environment_config = load_protocol(cls.protocol_path)

        baseline = cls.workspace / "baseline"
        run_comparison(cls.protocol_path, baseline)
        cls.baseline_summary = read_json(baseline / "summary.json")
        training_config = cls.workspace / "training-config.json"
        settings = read_json(DQN_CONFIG)
        settings["episodes"] = 2
        settings["checkpoint_episodes"] = [1, 2]
        settings["candidates"] = settings["candidates"][:1]
        settings["batch_size"] = 2
        settings["learning_starts"] = 2
        settings["train_every_steps"] = 1
        settings["target_update_steps"] = 2
        settings["epsilon_decay_episodes"] = 1
        write_json(training_config, settings)
        cls.training = cls.workspace / "training"
        result = subprocess.run(
            [
                sys.executable, "-B", "-m", "little_signal_shop.experiments.train_dqn",
                "--protocol", str(cls.protocol_path), "--config", str(training_config),
                "--validation-inputs", str(baseline / "market_inputs.json"),
                "--baseline-summary", str(baseline / "summary.json"),
                "--output", str(cls.training), "--workers", "1",
            ],
            cwd=REPO_ROOT,
            env=dict(os.environ, PYTHONPATH=str(REPO_ROOT / "research" / "src")),
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.selection = read_json(cls.training / "selection.json")

    def test_reloaded_greedy_checkpoints_obey_the_legal_action_list(self):
        from little_signal_shop.controllers.dqn import load_controller

        validation_path = self.training / "validation_metrics.jsonl"
        validation_rows = [
            json.loads(line) for line in validation_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertCountEqual(
            [(row["checkpoint_episode"], row["learning_seed"], row["market_seed"])
             for row in validation_rows],
            [(checkpoint, learning, market) for checkpoint in [1, 2]
             for learning in LEARNING_SEEDS for market in VALIDATION_SEEDS],
        )
        net_worth_totals = [sum(
            row["final_net_worth_cents"] for row in validation_rows
            if row["checkpoint_episode"] == checkpoint
        ) for checkpoint in [1, 2]]
        self.assertEqual(self.selection["checkpoint_episode"], net_worth_totals.index(max(net_worth_totals)) + 1)
        self.assertEqual(self.selection["primary_baseline"], self.baseline_summary["primary_baseline"])
        self.assertEqual(self.selection["learning_seeds"], LEARNING_SEEDS)
        self.assertEqual(set(self.selection["checkpoints"]), {str(seed) for seed in LEARNING_SEEDS})
        self.assertIn(self.selection["checkpoint_episode"], [1, 2])
        observation = ShopEnvironment(self.environment_config).reset(
            generate_market(self.environment_config, VALIDATION_SEEDS[0])
        )
        for seed, entry in self.selection["checkpoints"].items():
            checkpoint = self.training / entry["path"]
            self.assertEqual(sha256(checkpoint.read_bytes()).hexdigest(), entry["sha256"])
            controller = load_controller(checkpoint, self.environment_config)
            log_path = checkpoint.parent / "training_log.jsonl"
            log_rows = [
                json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["episode"] for row in log_rows], [1, 2])
            self.assertCountEqual([row["market_seed"] for row in log_rows], TRAIN_SEEDS)
            self.assertGreater(sum(row["optimizer_steps"] for row in log_rows), 0)
            for row in log_rows:
                if row["optimizer_steps"]:
                    self.assertTrue(isfinite(row["mean_loss"]))
            for available_action in Action:
                with self.subTest(seed=seed, available_action=available_action):
                    restricted = replace(observation, legal_actions=(available_action,))
                    self.assertIs(controller(restricted), available_action)

    def test_held_out_receipts_pair_by_market_and_learning_seed(self):
        from little_signal_shop.experiments.evaluate_dqn import run_evaluation

        output = self.workspace / "evaluation"
        run_evaluation(self.training, output, self.protocol_path)
        markets = read_json(output / "market_inputs.json")
        self.assertEqual(markets["split"], "held_out")
        self.assertEqual([market["seed"] for market in markets["markets"]], HELD_OUT_SEEDS)
        input_ids = {market["seed"]: market["input_id"] for market in markets["markets"]}
        rows = read_csv(output / "metrics.csv")
        self.assertEqual(len(rows), len(HELD_OUT_SEEDS) * (3 + len(LEARNING_SEEDS)))
        for row in rows:
            self.assertEqual(row["input_id"], input_ids[int(row["market_seed"])])
        net_worth = {
            (int(row["market_seed"]), row["controller_id"], row["learning_seed"]):
            int(row["final_net_worth_cents"])
            for row in rows
        }
        self.assertEqual(len(net_worth), len(rows))
        primary = self.selection["primary_baseline"]
        paired = read_csv(output / "paired_differences.csv")
        primary_rows = [row for row in paired if row["reference_id"] == primary]
        self.assertCountEqual(
            [(int(row["market_seed"]), int(row["learning_seed"])) for row in primary_rows],
            [(market, learning) for market in HELD_OUT_SEEDS for learning in LEARNING_SEEDS],
        )
        deltas = []
        for row in primary_rows:
            market = int(row["market_seed"])
            self.assertEqual(row["input_id"], input_ids[market])
            difference = (
                net_worth[market, "dqn", row["learning_seed"]] - net_worth[market, primary, ""]
            )
            self.assertEqual(int(row["delta_final_net_worth_cents"]), difference)
            deltas.append(difference)
        contrast = read_json(output / "summary.json")["primary_contrast"]
        self.assertEqual(contrast["mean_delta"], sum(deltas) / len(deltas))
        self.assertEqual(contrast["reference_id"], primary)
        low, high = contrast["confidence_interval"]
        self.assertLessEqual(min(deltas), low)
        self.assertLessEqual(low, high)
        self.assertLessEqual(high, max(deltas))

        replay = self.workspace / "replay"
        run_evaluation(self.training, replay, self.protocol_path, output / "market_inputs.json")
        for artifact in ("episodes.jsonl", "metrics.csv", "paired_differences.csv", "summary.json"):
            with self.subTest(artifact=artifact):
                self.assertEqual((replay / artifact).read_bytes(), (output / artifact).read_bytes())

    def test_evaluation_rejects_modified_checkpoint_bytes(self):
        from little_signal_shop.experiments.evaluate_dqn import run_evaluation

        training = self.workspace / "modified-training"
        shutil.copytree(self.training, training)
        entry = self.selection["checkpoints"][str(LEARNING_SEEDS[0])]
        checkpoint = training / entry["path"]
        checkpoint.write_bytes(checkpoint.read_bytes() + b"modified")
        output = self.workspace / "rejected"
        with self.assertRaisesRegex(ValueError, "SHA-256|hash"):
            run_evaluation(training, output, self.protocol_path)
        self.assertFalse(output.exists())

    def test_sensitivity_scenarios_keep_models_fixed_and_change_only_declared_inputs(self):
        from little_signal_shop.experiments.evaluate_dqn import run_evaluation

        output = self.workspace / "scenarios"
        run_evaluation(self.training, output, self.protocol_path, sensitivity=True)
        settings = read_json(output / "config.json")
        main_markets = read_json(output / "market_inputs.json")["markets"]
        model_hashes = read_json(output / "manifest.json")["checkpoint_sha256_by_learning_seed"]
        scenarios = {
            "forecast_noise_1": {"forecast_noise": 1},
            "forecast_noise_4": {"forecast_noise": 4},
            "regime_switch_010": {"regime_switch_probability": 0.10},
            "regime_switch_035": {"regime_switch_probability": 0.35},
            "tool_fees_half": {"tool_fee_multiplier": 0.5},
            "tool_fees_double": {"tool_fee_multiplier": 2},
        }
        sensitivity = output / "sensitivity"
        self.assertEqual(set(read_json(sensitivity / "summary.json")), set(scenarios))
        for name, changes in scenarios.items():
            with self.subTest(scenario=name):
                folder = sensitivity / name
                manifest = read_json(folder / "manifest.json")
                self.assertEqual(manifest["checkpoint_sha256_by_learning_seed"], model_hashes)
                self.assertEqual(manifest["scenario"], {"id": name, "version": "1", **changes})
                scenario_environment = read_json(folder / "config.json")["environment"]
                scenario_markets = read_json(folder / "market_inputs.json")["markets"]
                self.assertEqual([market["seed"] for market in scenario_markets], HELD_OUT_SEEDS)
                expected_environment = settings["environment"].copy()
                if "tool_fee_multiplier" in changes:
                    for fee in ("market_report_fee_cents", "forecast_fee_cents"):
                        expected_environment[fee] = int(expected_environment[fee] * changes["tool_fee_multiplier"])
                    self.assertEqual(scenario_markets, main_markets)
                elif "forecast_noise" in changes:
                    for main, variant in zip(main_markets, scenario_markets, strict=True):
                        for day, (before, after) in enumerate(zip(main["days"], variant["days"], strict=True)):
                            self.assertEqual(
                                {key: before[key] for key in before if key != "forecast"},
                                {key: after[key] for key in after if key != "forecast"},
                            )
                            if day + 1 < len(variant["days"]):
                                demand = variant["days"][day + 1]["demand"]
                                self.assertLessEqual(abs(after["forecast"] - demand), changes["forecast_noise"])
                self.assertEqual(scenario_environment, expected_environment)

    def test_evaluation_rejects_relabeling_a_checkpoint_under_another_seed(self):
        from little_signal_shop.experiments.evaluate_dqn import run_evaluation

        training = self.workspace / "relabeled-training"
        shutil.copytree(self.training, training)
        selection_path = training / "selection.json"
        relabeled = read_json(selection_path)
        checkpoints = relabeled["checkpoints"]
        checkpoints[str(LEARNING_SEEDS[0])] = checkpoints[str(LEARNING_SEEDS[1])]
        write_json(selection_path, relabeled)
        output = self.workspace / "relabeled-output"
        with self.assertRaisesRegex(ValueError, "checkpoint.*identity"):
            run_evaluation(training, output, self.protocol_path)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
