from __future__ import annotations

import unittest

from agent.runtime.recovery import (
    BROWSER_IN_USE,
    LOST_SESSION,
    PLAYWRIGHT_BUSY,
    TIMEOUT,
    TOOL_EXCEPTION,
    UNKNOWN,
    VERIFIER_FAILED,
    RecoveryEngine,
    RecoveryStrategy,
    classify_failure,
    recovery_plan,
)


class ClassifyTests(unittest.TestCase):
    def test_classifies_known_reasons(self) -> None:
        self.assertEqual(classify_failure("OpenCode timed out after 600 seconds"), TIMEOUT)
        self.assertEqual(classify_failure("Playwright already in use"), PLAYWRIGHT_BUSY)
        self.assertEqual(classify_failure("Chrome already in use by another process"), BROWSER_IN_USE)
        self.assertEqual(classify_failure("Traceback: tool failed with exception"), TOOL_EXCEPTION)
        self.assertEqual(classify_failure("session expired, no session id"), LOST_SESSION)
        self.assertEqual(classify_failure("Rocket could not verify the desktop"), VERIFIER_FAILED)

    def test_unknown_default(self) -> None:
        self.assertEqual(classify_failure("something weird happened"), UNKNOWN)

    def test_empty_message_is_unknown(self) -> None:
        self.assertEqual(classify_failure(""), UNKNOWN)


class PlanTests(unittest.TestCase):
    def test_ask_user_is_always_last(self) -> None:
        for reason in (TIMEOUT, PLAYWRIGHT_BUSY, BROWSER_IN_USE, TOOL_EXCEPTION, LOST_SESSION, VERIFIER_FAILED, UNKNOWN):
            plan = recovery_plan(reason)
            self.assertEqual(plan[-1], RecoveryStrategy.ASK_USER)
            self.assertEqual([s for s in plan if s is RecoveryStrategy.ASK_USER], [RecoveryStrategy.ASK_USER])

    def test_playwright_busy_reconnects_first(self) -> None:
        self.assertEqual(recovery_plan(PLAYWRIGHT_BUSY)[0], RecoveryStrategy.RECONNECT_PLAYWRIGHT)

    def test_browser_in_use_reuses_first(self) -> None:
        self.assertEqual(recovery_plan(BROWSER_IN_USE)[0], RecoveryStrategy.REUSE_BROWSER)

    def test_lost_session_reuses_session_first(self) -> None:
        self.assertEqual(recovery_plan(LOST_SESSION)[0], RecoveryStrategy.REUSE_SESSION)


class EngineTests(unittest.TestCase):
    def test_never_asks_user_first(self) -> None:
        engine = RecoveryEngine()
        engine.begin("Playwright already in use")
        first = engine.next_strategy()
        self.assertNotEqual(first, RecoveryStrategy.ASK_USER)
        self.assertEqual(first, RecoveryStrategy.RECONNECT_PLAYWRIGHT)

    def test_progresses_through_plan_then_asks_user(self) -> None:
        engine = RecoveryEngine(max_attempts=10)
        engine.begin("Chrome already in use")
        seen = []
        for _ in range(5):
            seen.append(engine.next_strategy())
        # browser_in_use has 3 real strategies, then ASK_USER thereafter.
        self.assertEqual(seen[0], RecoveryStrategy.REUSE_BROWSER)
        self.assertEqual(seen[1], RecoveryStrategy.RESTORE_BROWSER)
        self.assertEqual(seen[2], RecoveryStrategy.RECONNECT_PLAYWRIGHT)
        self.assertEqual(seen[3], RecoveryStrategy.ASK_USER)
        self.assertEqual(seen[4], RecoveryStrategy.ASK_USER)

    def test_attempt_budget_forces_ask_user(self) -> None:
        engine = RecoveryEngine(max_attempts=2)
        engine.begin("Traceback exception")  # tool_exception has 4 real strategies
        engine.next_strategy()
        engine.next_strategy()
        third = engine.next_strategy()  # exceeds budget
        self.assertEqual(third, RecoveryStrategy.ASK_USER)

    def test_metrics_tracked(self) -> None:
        engine = RecoveryEngine()
        engine.begin("timed out")
        engine.next_strategy()
        engine.next_strategy()
        engine.record_success()
        metrics = engine.metrics
        self.assertEqual(metrics.recovery_reason, TIMEOUT)
        self.assertEqual(metrics.attempts, 2)
        self.assertEqual(metrics.recovery_count, 2)
        self.assertTrue(metrics.recovery_success)
        self.assertEqual(len(metrics.history), 2)

    def test_should_ask_user_flag(self) -> None:
        engine = RecoveryEngine(max_attempts=1)
        engine.begin("unknown boom")
        engine.next_strategy()  # retry
        engine.next_strategy()  # over budget -> ask user
        self.assertTrue(engine.should_ask_user())

    def test_metrics_serializable(self) -> None:
        engine = RecoveryEngine()
        engine.begin("playwright already in use")
        engine.next_strategy()
        data = engine.metrics.to_dict()
        self.assertEqual(data["recovery_reason"], PLAYWRIGHT_BUSY)
        self.assertIn("history", data)


if __name__ == "__main__":
    unittest.main()
