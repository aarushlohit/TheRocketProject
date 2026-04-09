import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.core.intent import Intent
import agent.stage0.executor as stage0_executor
from agent.stage0.executor import ActionExecutor


class FakePlatform:
    def __init__(self):
        self.calls = []

    async def open_app(self, app_name: str) -> None:
        self.calls.append(("open_app", app_name))

    async def type_text(self, text: str, delay: float = 0.05) -> None:
        self.calls.append(("type_text", text, delay))

    async def press_keys(self, keys: list) -> None:
        self.calls.append(("press_keys", tuple(keys)))

    async def click(self, x: int, y: int, button: str = "left") -> None:
        self.calls.append(("click", x, y, button))

    async def scroll(self, direction: str, amount: int = 3) -> None:
        self.calls.append(("scroll", direction, amount))

    async def get_focused_window(self) -> dict:
        return {}

    async def close_app(self, app_name: str | None = None, target: str = "focused") -> None:
        self.calls.append(("close_app", app_name, target))

    async def minimize(self, app_name: str | None = None, target: str = "focused") -> None:
        self.calls.append(("minimize", app_name, target))

    async def maximize(self, app_name: str | None = None, target: str = "focused") -> None:
        self.calls.append(("maximize", app_name, target))

    async def restore(self, app_name: str | None = None, target: str = "focused") -> None:
        self.calls.append(("restore", app_name, target))

    async def open_url(self, url: str) -> None:
        self.calls.append(("open_url", url))

    async def lock_screen(self) -> dict:
        self.calls.append(("lock_screen",))
        return {"status": "success"}

    async def screenshot(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / "shot.png"
        screenshot_path.write_bytes(b"png")
        self.calls.append(("screenshot", str(output_dir)))
        return screenshot_path


class FailingPlatform(FakePlatform):
    async def open_app(self, app_name: str) -> None:
        raise RuntimeError(f"could not launch {app_name}")


def test_executor_routes_open_app():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="linux",
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="OPEN_APP", parameters={"app": "chrome"}, confidence=0.95)
            )
        )

        assert platform.calls == [("open_app", "chrome")]
        assert result.status == "success"
        assert result.message == "Opened chrome"


def test_executor_routes_screenshot():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="SCREENSHOT", parameters={}, confidence=0.95)
            )
        )

        assert platform.calls == [("screenshot", temp_dir)]
        assert result.status == "success"
        assert result.data["screenshot_path"].endswith("shot.png")


def test_executor_returns_debug_in_dry_run_mode():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=True,
            platform_type="macos",
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="OPEN_APP", parameters={"app": "calculator"}, confidence=0.95)
            )
        )

        assert platform.calls == []
        assert result.status == "debug"
        assert result.message == "Dry run executed"
        assert result.data["intent"] == "OPEN_APP"
        assert result.data["slots"]["app"] == "calculator"


def test_executor_catches_platform_errors():
    with TemporaryDirectory() as temp_dir:
        platform = FailingPlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="OPEN_APP", parameters={"app": "calculator"}, confidence=0.95)
            )
        )

        assert result.status == "error"
        assert result.message == "could not launch calculator"


def test_executor_does_not_block_when_availability_checker_false():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: False,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="OPEN_APP", parameters={"app": "calculator"}, confidence=0.95)
            )
        )

        assert platform.calls == [("open_app", "calculator")]
        assert result.status == "success"
        assert result.message == "Opened calculator"


def test_executor_uses_dedicated_lock_screen():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="LOCK_SCREEN", parameters={}, confidence=0.95)
            )
        )

        assert platform.calls == [("lock_screen",)]
        assert result.status == "success"
        assert result.message == "Locking system"


def test_executor_routes_restore_app():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="RESTORE_APP", parameters={"app": "notepad"}, confidence=0.95)
            )
        )

        assert platform.calls == [("restore", "notepad", "focused")]
        assert result.status == "success"
        assert result.message == "Window restored"


def test_executor_routes_mute(monkeypatch):
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        called = {"mute": 0}

        monkeypatch.setattr(stage0_executor, "mute", lambda: called.__setitem__("mute", called["mute"] + 1))

        result = asyncio.run(
            executor.execute(
                Intent(action="MUTE", parameters={}, confidence=0.95)
            )
        )

        assert called["mute"] == 1
        assert platform.calls == []
        assert result.status == "success"
        assert result.message == "Muted"


def test_executor_routes_unmute(monkeypatch):
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        called = {"unmute": 0}

        monkeypatch.setattr(stage0_executor, "unmute", lambda: called.__setitem__("unmute", called["unmute"] + 1))

        result = asyncio.run(
            executor.execute(
                Intent(action="UNMUTE", parameters={}, confidence=0.95)
            )
        )

        assert called["unmute"] == 1
        assert platform.calls == []
        assert result.status == "success"
        assert result.message == "Unmuted"


def test_executor_routes_minimize_all(monkeypatch):
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        called = {"minimize_all": 0}

        monkeypatch.setattr(
            stage0_executor,
            "minimize_all_windows",
            lambda: called.__setitem__("minimize_all", called["minimize_all"] + 1),
        )

        result = asyncio.run(
            executor.execute(
                Intent(action="MINIMIZE_ALL", parameters={}, confidence=0.95)
            )
        )

        assert called["minimize_all"] == 1
        assert platform.calls == []
        assert result.status == "success"
        assert result.message == "All windows minimized"


def test_executor_routes_maximize_all(monkeypatch):
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(
            platform=platform,
            artifacts_dir=Path(temp_dir),
            debug_mode=False,
            platform_type="windows",
            availability_checker=lambda app, platform: True,
        )

        monkeypatch.setattr(stage0_executor, "maximize_all_windows", lambda: 3)

        result = asyncio.run(
            executor.execute(
                Intent(action="MAXIMIZE_ALL", parameters={}, confidence=0.95)
            )
        )

        assert platform.calls == []
        assert result.status == "success"
        assert result.message == "All windows maximized"
        assert result.data["affected_windows"] == 3
