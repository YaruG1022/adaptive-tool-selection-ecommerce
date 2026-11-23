import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from little_signal_shop.environment import Action, generate_market
from little_signal_shop.experiments.baseline_comparison import run_comparison
from little_signal_shop.experiments.evaluate_dqn import _evaluate_scenario
from little_signal_shop.experiments.export_browser import export_browser
from little_signal_shop.experiments.protocol import DEFAULT_CONFIG, load_protocol


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class BrowserExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = TemporaryDirectory(prefix="lss-browser-export-source-")
        cls.addClassCleanup(work.cleanup)
        root = Path(work.name)
        cls.protocol = _read(DEFAULT_CONFIG)
        cls.protocol["environment"]["days"] = 2
        cls.protocol["seeds"] = {"train": [11], "validation": [21, 22], "held_out": [31, 32], "learning": [41, 42]}
        cls.protocol["analysis"]["bootstrap_replicates"] = 13
        cls.protocol_file = root / "protocol.json"
        _write(cls.protocol_file, cls.protocol)
        cls.validation = root / "validation"
        run_comparison(cls.protocol_file, cls.validation)

    def setUp(self):
        work = TemporaryDirectory(prefix="lss-browser-export-test-")
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)

    def _changed_archive(self):
        return Path(shutil.copytree(self.validation, self.root / "modified"))

    def test_exports_source_settlements_tools_and_terminal_opening_values(self):
        output = self.root / "browser.json"
        saved = export_browser(self.validation, output)
        self.assertEqual(_read(output), saved)
        self.assertEqual(set(saved), {"format", "schema_version", "environment_version", "run", "episodes", "evaluation", "training"})
        self.assertEqual(saved["run"]["split"], "validation")
        self.assertEqual(saved["run"]["scenario"], "primary")
        self.assertEqual(len(saved["episodes"]), 6)
        self.assertIsNone(saved["evaluation"])
        self.assertIsNone(saved["training"])

        records = [json.loads(line) for line in (self.validation / "episodes.jsonl").read_text(encoding="utf-8").splitlines()]
        record = next(row for row in records if row["controller_id"] == "fixed_order" and row["seed"] == 21)
        episode = next(row for row in saved["episodes"] if row["controller_id"] == "fixed_order" and row["seed"] == 21)
        day, terminal = episode["days"]
        self.assertIsNone(episode["model_id"])
        self.assertIsNone(episode["learning_seed"])
        self.assertEqual([day["settlement"], terminal["settlement"]], record["transitions"][-1]["settlements"])
        self.assertEqual(day["opening_cash_cents"], 10_000)
        self.assertEqual(day["opening_net_worth_cents"], 12_500)
        self.assertEqual([(tool["id"], tool["start_minute"], tool["end_minute"], tool["fee_cents"]) for tool in day["tools"]],
                         [("market_report", 540, 570, 100), ("forecast", 570, 630, 200)])
        self.assertEqual(day["stop_minute"], 630)
        self.assertEqual([day["demand"], terminal["demand"]], record["analysis_only"]["daily_demand"])
        self.assertEqual(terminal["opening_cash_cents"], day["settlement"]["cash_cents"])
        self.assertEqual(terminal["opening_net_worth_cents"], day["settlement"]["net_worth_cents"])
        self.assertEqual([terminal["public_today"], terminal["public_tomorrow"], terminal["stop_minute"], terminal["tools"]],
                         [None, None, None, []])

    def test_rejects_foreign_input_and_leaves_no_output(self):
        archive = self._changed_archive()
        inputs = _read(archive / "market_inputs.json")
        inputs["markets"][0]["input_id"] = "0" * 64
        _write(archive / "market_inputs.json", inputs)
        output = self.root / "browser.json"
        with self.assertRaisesRegex(ValueError, "foreign input ID"):
            export_browser(archive, output)
        self.assertFalse(output.exists())

    def test_rejects_missing_market_and_missing_input_file(self):
        archive = self._changed_archive()
        input_path = archive / "market_inputs.json"
        inputs = _read(input_path)
        inputs["markets"].pop()
        _write(input_path, inputs)
        output = self.root / "browser.json"
        with self.assertRaisesRegex(ValueError, "missing registered market inputs"):
            export_browser(archive, output)
        input_path.unlink()
        with self.assertRaises(FileNotFoundError):
            export_browser(archive, output)
        self.assertFalse(output.exists())

    def test_rejects_corrupt_settlement_and_missing_paired_episode(self):
        archive = self._changed_archive()
        source = archive / "episodes.jsonl"
        lines = source.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[0])
        record["transitions"][-1]["settlements"][0]["cash_cents"] += 1
        source.write_text("\n".join([json.dumps(record), *lines[1:]]) + "\n", encoding="utf-8")
        output = self.root / "browser.json"
        with self.assertRaisesRegex(ValueError, "settlement does not reconcile"):
            export_browser(archive, output)
        source.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing a paired episode"):
            export_browser(archive, output)
        self.assertFalse(output.exists())

    def test_refuses_to_overwrite_an_existing_output(self):
        output = self.root / "browser.json"
        output.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_browser(self.validation, output)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    def test_exports_archived_contrast_and_matching_validation_curves(self):
        _, config = load_protocol(self.protocol_file)
        markets = tuple(generate_market(config, seed) for seed in self.protocol["seeds"]["held_out"])
        seeds = self.protocol["seeds"]["learning"]
        checksums = {str(seed): f"{seed:064x}" for seed in seeds}
        selection = {
            "primary_baseline": "no_tools", "candidate_id": "toy", "checkpoint_episode": 2,
            "learning_seeds": seeds, "validation_mean_final_net_worth_cents": 16_000,
            "checkpoints": {seed: {"path": f"seed-{seed}.pt", "sha256": digest} for seed, digest in checksums.items()},
        }

        def choose(observation):
            return Action.FORECAST if Action.FORECAST in observation.legal_actions else Action.STOP

        learned = {seed: (f"toy:seed-{seed}:episode-2:sha256:{checksums[str(seed)]}", choose) for seed in seeds}
        held_out = self.root / "held-out"
        summary = _evaluate_scenario(held_out, self.protocol, config, markets, selection, learned,
                                     ("toy-revision", None, "source-hash"), {"id": "primary", "version": "1"})
        training = self.root / "training"
        training.mkdir()
        _write(training / "selection.json", selection)
        _write(training / "protocol.json", self.protocol)
        _write(training / "validation_ranking.json", {"ranking": [
            {"candidate_id": "toy", "checkpoint_episode": episode, "validation_episode_count": 4,
             "validation_total_final_net_worth_cents": score * 4, "validation_mean_final_net_worth_cents": score}
            for episode, score in ((2, 16_000), (1, 15_000))
        ]})
        saved = export_browser(held_out, self.root / "held-out.json", training)
        self.assertEqual(len(saved["episodes"]), 10)
        self.assertEqual(saved["evaluation"], {
            "reference_id": "no_tools", "mean_delta_cents": summary["primary_contrast"]["mean_delta"],
            "confidence_level": summary["primary_contrast"]["confidence_level"],
            "confidence_interval_cents": summary["primary_contrast"]["confidence_interval"],
        })
        self.assertEqual(saved["training"], {
            "selected_candidate": "toy", "selected_episode": 2, "learning_seeds": seeds,
            "series": [{"candidate_id": "toy", "points": [
                {"episode": 1, "mean_final_net_worth_cents": 15_000}, {"episode": 2, "mean_final_net_worth_cents": 16_000},
            ]}],
        })
        selection["checkpoints"]["41"]["sha256"] = "f" * 64
        _write(training / "selection.json", selection)
        with self.assertRaisesRegex(ValueError, "foreign checkpoint"):
            export_browser(held_out, self.root / "rejected.json", training)


if __name__ == "__main__":
    unittest.main()
