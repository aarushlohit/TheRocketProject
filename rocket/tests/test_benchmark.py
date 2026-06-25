from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent.runtime.benchmark import (
    CATEGORIES,
    ExecOutcome,
    generate_default_suite,
    run_benchmark,
)


class SuiteTests(unittest.TestCase):
    def test_suite_has_350_tasks_in_correct_proportions(self) -> None:
        suite = generate_default_suite()
        self.assertEqual(len(suite), 350)
        counts = {category: 0 for category in CATEGORIES}
        for task in suite:
            counts[task.category] += 1
        self.assertEqual(counts["browser"], 100)
        self.assertEqual(counts["desktop"], 100)
        self.assertEqual(counts["install"], 50)
        self.assertEqual(counts["accessibility"], 50)
        self.assertEqual(counts["reading"], 50)

    def test_tasks_cover_all_blind_modalities(self) -> None:
        suite = generate_default_suite()
        modalities = {task.modality for task in suite}
        self.assertEqual(modalities, {"voice", "braille", "drawing", "text"})

    def test_task_ids_unique(self) -> None:
        suite = generate_default_suite()
        ids = [task.id for task in suite]
        self.assertEqual(len(ids), len(set(ids)))


class HonestRunTests(unittest.TestCase):
    def test_capable_executor_has_zero_false_positives(self) -> None:
        report = run_benchmark()
        overall = report.overall()
        self.assertEqual(overall["total"], 350)
        # A genuinely capable executor that achieves reality has no false positives.
        self.assertEqual(overall["false_positives"], 0)
        self.assertEqual(report.mode, "simulated")

    def test_report_writes_benchmark_json(self) -> None:
        report = run_benchmark()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = report.write(Path(tmp) / "benchmark.json")
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("overall", data)
            self.assertIn("by_category", data)
            self.assertEqual(data["targets"], {"success_rate": 0.95, "false_positives": 0})
            self.assertIn("by_modality", data)

    def test_recovery_metrics_are_recorded(self) -> None:
        report = run_benchmark()
        self.assertGreater(report.overall()["recovered"], 0)


class FalsePositiveDetectionTests(unittest.TestCase):
    """The harness must catch a lying executor (reports success, reality fails)."""

    def test_lying_executor_is_flagged(self) -> None:
        def lying_executor(task) -> ExecOutcome:
            # Claims success but provides empty reality (nothing actually happened).
            return ExecOutcome(reported_success=True, reality={}, message="done")

        report = run_benchmark(executor=lying_executor, mode="adversarial")
        overall = report.overall()
        # Every verifiable task is now a false positive; reading (unverifiable) is not.
        self.assertEqual(overall["false_positives"], overall["verifiable_tasks"])
        self.assertGreater(overall["false_positives"], 0)
        self.assertEqual(report.mode, "adversarial")

    def test_failing_executor_has_no_false_positives(self) -> None:
        def honest_failure(task) -> ExecOutcome:
            # Reports failure honestly -> never a false positive.
            return ExecOutcome(reported_success=False, reality={}, message="could not verify")

        report = run_benchmark(executor=honest_failure)
        self.assertEqual(report.overall()["false_positives"], 0)


if __name__ == "__main__":
    unittest.main()
