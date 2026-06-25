"""Installer missions with UAC awareness and reality-based completion.

Installation is proven only by the program's binary existing on disk (via the
Slice 1 :class:`InstallVerifier`). Opening a website, the Microsoft Store, or an
installer is never accepted as proof.

When Windows shows a UAC prompt, Rocket detects it, announces it, pauses, waits
for approval, and then resumes. Rocket never reports completion while admin
approval is still pending.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

from agent.runtime.verifier import (
    INSTALL_TARGETS,
    InstallVerifier,
    RealityProbe,
    Verdict,
    WindowsRealityProbe,
)

ADMIN_REQUIRED_SPEECH = "Administrator permission required. Please approve."
ADMIN_WAITING_SPEECH = "Waiting for administrator approval."
ADMIN_APPROVED_SPEECH = "Administrator approval received. Continuing."
ADMIN_TIMEOUT_SPEECH = "Administrator approval was not given in time. The installation is not complete."


@dataclass(frozen=True)
class InstallStatus:
    app: str
    installed: bool
    awaiting_admin: bool
    spoken: str
    verdict: Verdict
    admin_result: str  # "not_required" | "approved" | "timeout"


class UacProbe:
    """Observes whether a UAC consent prompt is active. Override for tests."""

    def uac_active(self) -> bool | None:
        return None


class WindowsUacProbe(UacProbe):
    """Detect the UAC consent prompt via the consent.exe process."""

    def uac_active(self) -> bool | None:
        try:
            completed = subprocess.run(
                ["tasklist", "/fi", "imagename eq consent.exe", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        return "consent.exe" in (completed.stdout or "").lower()


def install_key_from_mission(mission: dict[str, Any] | str) -> str:
    """Resolve an install target key from a mission dict or free text."""

    if isinstance(mission, dict):
        text = f"{mission.get('mission', '')} {mission.get('context', '')}"
    else:
        text = str(mission)
    lower = text.lower()
    aliases = {
        "vscode": ("vscode", "vs code", "visual studio code"),
        "git": ("git",),
        "vlc": ("vlc",),
        "python": ("python",),
    }
    for key, needles in aliases.items():
        if any(needle in lower for needle in needles):
            return key
    return ""


class InstallMissionVerifier:
    """Confirms an install mission against reality (disk binary only)."""

    name = "InstallMissionVerifier"

    def __init__(self, reality_probe: RealityProbe | None = None) -> None:
        self._install = InstallVerifier(reality_probe or WindowsRealityProbe())

    def verify(self, app_key: str) -> Verdict:
        verdict = self._install.verify(app_key)
        return Verdict(self.name, verdict.passed, verdict.reality, verdict.evidence)

    def verify_mission(self, mission: dict[str, Any] | str) -> Verdict:
        return self.verify(install_key_from_mission(mission))


class InstallMissionRunner:
    """Orchestrates UAC handling and reality verification for installs."""

    def __init__(
        self,
        reality_probe: RealityProbe | None = None,
        *,
        uac_probe: UacProbe | None = None,
        speak: Callable[[str], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        poll_interval: float = 1.0,
        timeout: float = 180.0,
    ) -> None:
        self.verifier = InstallMissionVerifier(reality_probe)
        self.uac = uac_probe or WindowsUacProbe()
        self._speak = speak or (lambda _message: None)
        self._sleep = sleep
        self._clock = clock
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.spoken: list[str] = []

    def announce(self, message: str) -> None:
        self.spoken.append(message)
        self._speak(message)

    def wait_for_admin(self) -> str:
        """Pause for a UAC prompt. Returns the admin result."""

        active = self.uac.uac_active()
        if active is not True:
            # None (unknown) or False both mean no prompt to wait on right now.
            return "not_required"
        self.announce(ADMIN_REQUIRED_SPEECH)
        deadline = self._clock() + self.timeout
        announced_wait = False
        while self._clock() < deadline:
            if not announced_wait:
                self.announce(ADMIN_WAITING_SPEECH)
                announced_wait = True
            self._sleep(self.poll_interval)
            if self.uac.uac_active() is not True:
                self.announce(ADMIN_APPROVED_SPEECH)
                return "approved"
        self.announce(ADMIN_TIMEOUT_SPEECH)
        return "timeout"

    def run(self, app_key: str) -> InstallStatus:
        """Handle pending UAC, then verify the install against reality."""

        label = INSTALL_TARGETS[app_key].label if app_key in INSTALL_TARGETS else (app_key or "the program")
        admin_result = self.wait_for_admin()
        if admin_result == "timeout":
            verdict = Verdict(
                InstallMissionVerifier.name,
                False,
                f"{label} is not installed; administrator approval is still pending.",
            )
            return InstallStatus(
                app=app_key,
                installed=False,
                awaiting_admin=True,
                spoken=verdict.reality,
                verdict=verdict,
                admin_result=admin_result,
            )

        verdict = self.verifier.verify(app_key)
        self.announce(verdict.spoken)
        return InstallStatus(
            app=app_key,
            installed=verdict.passed,
            awaiting_admin=False,
            spoken=verdict.spoken,
            verdict=verdict,
            admin_result=admin_result,
        )

    def run_mission(self, mission: dict[str, Any] | str) -> InstallStatus:
        return self.run(install_key_from_mission(mission))
