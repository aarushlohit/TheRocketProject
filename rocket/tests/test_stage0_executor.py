import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.core.intent import Intent
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

    async def open_url(self, url: str) -> None:
        self.calls.append(("open_url", url))

    async def screenshot(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / "shot.png"
        screenshot_path.write_bytes(b"png")
        self.calls.append(("screenshot", str(output_dir)))
        return screenshot_path


def test_executor_routes_open_app():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(platform=platform, artifacts_dir=Path(temp_dir))

        result = asyncio.run(
            executor.execute(
                Intent(action="OPEN_APP", parameters={"app": "chrome"}, confidence=0.95)
            )
        )

        assert platform.calls == [("open_app", "chrome")]
        assert result.status == "success"
        assert result.message == "Opened Chrome"


def test_executor_routes_screenshot():
    with TemporaryDirectory() as temp_dir:
        platform = FakePlatform()
        executor = ActionExecutor(platform=platform, artifacts_dir=Path(temp_dir))

        result = asyncio.run(
            executor.execute(
                Intent(action="SCREENSHOT", parameters={}, confidence=0.95)
            )
        )

        assert platform.calls == [("screenshot", temp_dir)]
        assert result.status == "success"
        assert result.data["screenshot_path"].endswith("shot.png")
