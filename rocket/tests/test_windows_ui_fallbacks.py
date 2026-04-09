import asyncio

from agent.platform import save_file_control
from agent.platform.windows import WindowsAdapter


def test_save_file_via_os_prefers_ui(monkeypatch):
    monkeypatch.setattr(save_file_control.sys, "platform", "win32")
    captured = {}

    def fake_save_file_ui(app_name, filename):
        captured["call"] = (app_name, filename)
        return {"status": "success", "app": app_name, "filename": filename, "method": "ui"}

    monkeypatch.setattr(save_file_control, "save_file_ui", fake_save_file_ui)

    result = save_file_control.save_file_via_os("notepad", "test.txt")

    assert captured["call"] == ("notepad", "test.txt")
    assert result["method"] == "ui"


def test_save_file_via_os_falls_back_to_keyboard(monkeypatch):
    monkeypatch.setattr(save_file_control.sys, "platform", "win32")
    monkeypatch.setattr(save_file_control, "save_file_ui", lambda app_name, filename: (_ for _ in ()).throw(RuntimeError("ui failed")))
    monkeypatch.setattr(save_file_control, "focus_app", lambda app_name: True)
    monkeypatch.setattr(save_file_control, "safe_hotkey", lambda *keys: None)
    monkeypatch.setattr(save_file_control, "safe_write", lambda text: None)
    monkeypatch.setattr(save_file_control, "safe_press", lambda key: None)
    monkeypatch.setattr(save_file_control.time, "sleep", lambda _: None)

    result = save_file_control.save_file_via_os("notepad", "test.txt")

    assert result["status"] == "success"
    assert result["method"] == "keyboard_fallback"


def test_windows_adapter_minimize_prefers_ui(monkeypatch):
    adapter = WindowsAdapter()
    captured = {}

    def fake_minimize_ui(app_name):
        captured["app"] = app_name
        return {"status": "success", "method": "ui"}

    monkeypatch.setattr("agent.platform.windows.minimize_app_ui", fake_minimize_ui)

    result = asyncio.run(adapter.minimize(app_name="notepad"))

    assert captured["app"] == "notepad"
    assert result["status"] == "success"


def test_windows_adapter_maximize_falls_back_to_win32(monkeypatch):
    adapter = WindowsAdapter()

    def fail_ui(app_name):
        raise RuntimeError("uia attach failed")

    monkeypatch.setattr("agent.platform.windows.maximize_app_ui", fail_ui)
    monkeypatch.setattr("agent.platform.windows.maximize_window", lambda app_name: 1)

    result = asyncio.run(adapter.maximize(app_name="notepad"))

    assert result["status"] == "success"
    assert result["method"] == "win32"


def test_windows_adapter_close_falls_back_to_win32(monkeypatch):
    adapter = WindowsAdapter()

    def fail_ui(app_name):
        raise RuntimeError("uia attach failed")

    monkeypatch.setattr("agent.platform.windows.close_app_ui", fail_ui)
    monkeypatch.setattr("agent.platform.windows.close_window", lambda app_name: 1)

    result = asyncio.run(adapter.close_app(app_name="notepad"))

    assert result["status"] == "success"
    assert result["method"] == "win32"
