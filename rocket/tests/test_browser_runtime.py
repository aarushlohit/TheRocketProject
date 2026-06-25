from __future__ import annotations

import unittest

from agent.runtime.browser_runtime import (
    BrowserController,
    BrowserRuntime,
    BrowserWindow,
    get_browser_runtime,
    reset_browser_runtime,
)


class FakeController(BrowserController):
    """Simulated Windows browser with controllable state and call counts."""

    def __init__(self, *, existing: BrowserWindow | None = None, launchable: bool = True) -> None:
        self.window = existing
        self.launchable = launchable
        self.launch_count = 0
        self.close_count = 0
        self.next_handle = 1000

    def find_window(self):
        return self.window

    def launch(self, profile_path):
        self.launch_count += 1
        if not self.launchable:
            return None
        self.next_handle += 1
        self.window = BrowserWindow(pid=4242, handle=self.next_handle, title="New Tab - Google Chrome")
        return self.window

    def query(self, handle):
        if self.window and self.window.handle == handle:
            return self.window
        return None

    def set_foreground(self, handle):
        if self.window and self.window.handle == handle:
            self._update(is_foreground=True)
            return True
        return False

    def maximize(self, handle):
        if self.window and self.window.handle == handle:
            self._update(is_maximized=True, is_minimized=False)
            return True
        return False

    def restore(self, handle):
        if self.window and self.window.handle == handle:
            self._update(is_minimized=False)
            return True
        return False

    def close(self, pid):
        self.close_count += 1
        self.window = None
        return True

    def _update(self, **changes):
        data = {
            "pid": self.window.pid,
            "handle": self.window.handle,
            "title": self.window.title,
            "is_minimized": self.window.is_minimized,
            "is_foreground": self.window.is_foreground,
            "is_maximized": self.window.is_maximized,
            "bounds": self.window.bounds,
        }
        data.update(changes)
        self.window = BrowserWindow(**data)


class ReuseTests(unittest.TestCase):
    def test_reuse_existing_browser_adopts_state(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200, title="YouTube - Google Chrome"))
        runtime = BrowserRuntime(controller)
        self.assertTrue(runtime.reuse_browser())
        self.assertEqual(runtime.state.browser_pid, 10)
        self.assertEqual(runtime.state.window_handle, 200)

    def test_reuse_returns_false_when_none(self) -> None:
        runtime = BrowserRuntime(FakeController(existing=None))
        self.assertFalse(runtime.reuse_browser())

    def test_ensure_browser_reuses_without_launching(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200))
        runtime = BrowserRuntime(controller)
        self.assertTrue(runtime.ensure_browser())
        self.assertEqual(controller.launch_count, 0)

    def test_ensure_browser_launches_only_when_absent(self) -> None:
        controller = FakeController(existing=None)
        runtime = BrowserRuntime(controller)
        self.assertTrue(runtime.ensure_browser())
        self.assertEqual(controller.launch_count, 1)

    def test_ensure_browser_never_duplicates(self) -> None:
        controller = FakeController(existing=None)
        runtime = BrowserRuntime(controller)
        runtime.ensure_browser()
        runtime.ensure_browser()
        runtime.ensure_browser()
        self.assertEqual(controller.launch_count, 1)


class WindowPolicyTests(unittest.TestCase):
    def test_minimized_chrome_is_restored(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200, is_minimized=True))
        runtime = BrowserRuntime(controller)
        runtime.reuse_browser()
        self.assertTrue(runtime.ensure_not_minimized())
        self.assertFalse(controller.window.is_minimized)

    def test_chrome_behind_vscode_is_brought_foreground(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200, is_foreground=False))
        runtime = BrowserRuntime(controller)
        runtime.reuse_browser()
        self.assertTrue(runtime.ensure_foreground())
        self.assertTrue(runtime.state.is_foreground)
        self.assertGreater(runtime.state.last_focus_time, 0)

    def test_ensure_maximized(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200, is_maximized=False))
        runtime = BrowserRuntime(controller)
        runtime.reuse_browser()
        self.assertTrue(runtime.ensure_maximized())
        self.assertTrue(runtime.state.is_maximized)

    def test_ensure_visible_focused_full_sequence(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200, is_minimized=True, is_foreground=False, is_maximized=False))
        runtime = BrowserRuntime(controller)
        self.assertTrue(runtime.ensure_visible_focused())
        self.assertFalse(controller.window.is_minimized)
        self.assertTrue(controller.window.is_foreground)
        self.assertTrue(controller.window.is_maximized)

    def test_foreground_fails_safely_when_no_browser(self) -> None:
        runtime = BrowserRuntime(FakeController(existing=None, launchable=False))
        self.assertFalse(runtime.ensure_foreground())


class PlaywrightOwnershipTests(unittest.TestCase):
    def test_playwright_connect_requires_running_browser(self) -> None:
        runtime = BrowserRuntime(FakeController(existing=None, launchable=False))
        self.assertFalse(runtime.connect_playwright())

    def test_playwright_connect_is_idempotent(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200))
        runtime = BrowserRuntime(controller)
        runtime.reuse_browser()
        self.assertTrue(runtime.connect_playwright())
        self.assertTrue(runtime.connect_playwright())
        self.assertTrue(runtime.state.playwright_connected)


class CleanupTests(unittest.TestCase):
    def test_cleanup_closes_and_resets(self) -> None:
        controller = FakeController(existing=BrowserWindow(pid=10, handle=200))
        runtime = BrowserRuntime(controller, profile_path="C:/profile")
        runtime.reuse_browser()
        self.assertTrue(runtime.cleanup_browser())
        self.assertEqual(controller.close_count, 1)
        self.assertIsNone(runtime.state.browser_pid)
        self.assertFalse(runtime.state.playwright_connected)
        # profile is preserved across cleanup for the next reuse
        self.assertEqual(runtime.state.profile_path, "C:/profile")


class SingletonTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_browser_runtime()

    def tearDown(self) -> None:
        reset_browser_runtime()

    def test_singleton_is_shared(self) -> None:
        first = get_browser_runtime(FakeController(existing=None))
        second = get_browser_runtime()
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
