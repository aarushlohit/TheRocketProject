import asyncio
import json

from agent.platform.linux import LinuxAdapter
from agent.utils import dependency_check


def test_linux_adapter_detects_hyprland(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "session")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)

    adapter = LinuxAdapter()

    assert adapter.env == "hyprland"


def test_close_app_uses_hyprctl_on_hyprland(monkeypatch):
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "session")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr(dependency_check, "HAS_HYPRCTL", True)

    adapter = LinuxAdapter()
    commands = []

    def fake_run_command(command, check=True):
        commands.append(command)
        if command == ["hyprctl", "-j", "clients"]:
            class Result:
                stdout = json.dumps(
                    [
                        {"class": "google-chrome-stable", "address": "0x123"},
                    ]
                )

            return Result()

        class Result:
            stdout = ""
            returncode = 0

        return Result()

    monkeypatch.setattr(adapter, "_run_command", fake_run_command)

    asyncio.run(adapter.close_app(app_name="chrome"))

    assert commands[0] == ["hyprctl", "-j", "clients"]
    assert commands[1] == [
        "hyprctl",
        "dispatch",
        "closewindow",
        "address:0x123",
    ]


def test_screenshot_uses_grim_on_wayland(monkeypatch, tmp_path):
    monkeypatch.delenv("HYPRLAND_INSTANCE_SIGNATURE", raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr(dependency_check, "HAS_GRIM", True)

    adapter = LinuxAdapter()
    commands = []

    def fake_run_command(command, check=True):
        commands.append(command)
        target = command[-1]
        if target.endswith(".png"):
            tmp_path.joinpath("out.png").write_bytes(b"grim")

        class Result:
            stdout = ""
            returncode = 0

        return Result()

    monkeypatch.setattr(adapter, "_run_command", fake_run_command)

    path = asyncio.run(adapter.screenshot(tmp_path))

    assert commands[0][0] == "grim"
    assert path.suffix == ".png"
