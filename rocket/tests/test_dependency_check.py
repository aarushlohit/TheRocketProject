import asyncio

from agent.utils import dependency_check


def test_is_arch_linux_variants():
    assert dependency_check._is_arch_linux("arch") is True
    assert dependency_check._is_arch_linux("manjaro") is True
    assert dependency_check._is_arch_linux("ubuntu") is False


def test_check_and_prepare_dependencies_sets_flags(monkeypatch):
    async def fake_check_dependency(**kwargs):
        return {
            "xdg-open": True,
            "wmctrl": False,
            "scrot": True,
        }[kwargs["command"]]

    monkeypatch.setattr(dependency_check, "detect_environment", lambda: ("linux", "arch"))
    monkeypatch.setattr(dependency_check, "_check_dependency", fake_check_dependency)

    asyncio.run(dependency_check.check_and_prepare_dependencies())

    assert dependency_check.HAS_XDG_OPEN is True
    assert dependency_check.HAS_WMCTRL is False
    assert dependency_check.HAS_SCROT is True
