"""Rocket reality verifier suite.

Rocket never trusts words. After OpenCode reports a task done, the verifier
inspects the real operating system and only then decides whether the goal was
truly achieved.

Design for zero false positives:

* Every verifier is split into a :class:`RealityProbe` (observes the OS, easily
  injected/mocked) and a pure evaluation that turns observed facts into a
  :class:`Verdict`.
* Observation is tri-state. A probe returns ``True``/``False`` for a confirmed
  fact, or ``None`` when reality could not be observed. ``None`` never passes.
  Opening Settings, a Store page, or a website is *not* evidence that a radio is
  on or that an app is installed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class Verdict:
    """Outcome of a single reality check."""

    verifier: str
    passed: bool
    reality: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def spoken(self) -> str:
        """Blind-first, natural-language statement of observed reality."""

        return self.reality


@dataclass(frozen=True)
class WindowInfo:
    title: str
    is_visible: bool = True
    is_foreground: bool = False
    is_maximized: bool = False
    is_minimized: bool = False


def _confirmed(observed: bool | None) -> bool:
    """Only an explicit ``True`` counts as confirmed reality."""

    return observed is True


# ---------------------------------------------------------------------------
# Install target registry (anti-false-positive core for installs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstallTarget:
    label: str
    executables: tuple[str, ...]
    search_paths: tuple[str, ...] = ()


def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


INSTALL_TARGETS: dict[str, InstallTarget] = {
    "vscode": InstallTarget(
        label="VSCode",
        executables=("Code.exe",),
        search_paths=(
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ),
    ),
    "git": InstallTarget(
        label="Git",
        executables=("git.exe",),
        search_paths=(
            r"%PROGRAMFILES%\Git\cmd\git.exe",
            r"%PROGRAMFILES%\Git\bin\git.exe",
        ),
    ),
    "vlc": InstallTarget(
        label="VLC",
        executables=("vlc.exe",),
        search_paths=(
            r"%PROGRAMFILES%\VideoLAN\VLC\vlc.exe",
            r"%PROGRAMFILES(X86)%\VideoLAN\VLC\vlc.exe",
        ),
    ),
    "python": InstallTarget(
        label="Python",
        executables=("python.exe",),
        search_paths=(
            r"%LOCALAPPDATA%\Programs\Python",
        ),
    ),
}

# Common app -> process names for desktop/process verification.
APP_PROCESSES: dict[str, tuple[str, ...]] = {
    "calculator": ("calculatorapp.exe", "calc.exe", "applicationframehost.exe"),
    "whatsapp": ("whatsapp.exe",),
    "chrome": ("chrome.exe",),
    "edge": ("msedge.exe",),
    "vscode": ("code.exe",),
    "explorer": ("explorer.exe",),
    "notepad": ("notepad.exe", "notepad++.exe"),
    "spotify": ("spotify.exe",),
    "settings": ("systemsettings.exe", "applicationframehost.exe"),
    "terminal": ("windowsterminal.exe", "cmd.exe", "powershell.exe"),
}


# ---------------------------------------------------------------------------
# Reality probe
# ---------------------------------------------------------------------------


class RealityProbe:
    """Observes the real operating system. Override for tests.

    Every method returns observed facts, or ``None`` when reality could not be
    determined. ``None`` must never be treated as success.
    """

    def running_processes(self) -> set[str] | None:
        """Lower-cased set of running executable names, or ``None``."""

        return None

    def windows(self) -> list[WindowInfo] | None:
        return None

    def find_executable(self, executables: Sequence[str], search_paths: Sequence[str]) -> str | None:
        return None

    def path_exists(self, path: str) -> bool | None:
        return None

    def bluetooth_enabled(self) -> bool | None:
        return None

    def wifi_connected(self) -> bool | None:
        return None

    def browser_state(self) -> dict[str, Any] | None:
        return None

    def window_value(self, title_substring: str) -> str | None:
        return None


class WindowsRealityProbe(RealityProbe):
    """Best-effort Windows reality probe. Unknown observations return ``None``."""

    def running_processes(self) -> set[str] | None:
        try:
            completed = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        names: set[str] = set()
        for line in completed.stdout.splitlines():
            match = re.match(r'"([^"]+)"', line.strip())
            if match:
                names.add(match.group(1).strip().lower())
        return names or None

    def find_executable(self, executables: Sequence[str], search_paths: Sequence[str]) -> str | None:
        for name in executables:
            resolved = shutil.which(name)
            if resolved:
                return resolved
        for raw_path in search_paths:
            path = _expand(raw_path)
            if os.path.isfile(path):
                return path
            if os.path.isdir(path):
                for name in executables:
                    for root, _dirs, files in os.walk(path):
                        if name.lower() in {f.lower() for f in files}:
                            return os.path.join(root, name)
        return None

    def path_exists(self, path: str) -> bool | None:
        try:
            return os.path.exists(_expand(path))
        except Exception:
            return None

    def wifi_connected(self) -> bool | None:
        try:
            completed = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        for line in completed.stdout.splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("state"):
                return "connected" in stripped and "disconnected" not in stripped
        return False

    def bluetooth_enabled(self) -> bool | None:
        script = (
            "$ErrorActionPreference='Stop'; "
            "$d = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue; "
            "if ($null -eq $d) { Write-Output 'none'; exit 0 }; "
            "$radio = $d | Where-Object { $_.FriendlyName -match 'Radio|Adapter|Enumerator' } | Select-Object -First 1; "
            "if ($null -eq $radio) { $radio = $d | Select-Object -First 1 }; "
            "if ($radio.Status -eq 'OK') { Write-Output 'on' } else { Write-Output 'off' }"
        )
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
        except Exception:
            return None
        if completed.returncode != 0:
            return None
        out = completed.stdout.strip().lower()
        if out == "on":
            return True
        if out == "off":
            return False
        return None


# ---------------------------------------------------------------------------
# Verifiers
# ---------------------------------------------------------------------------


class ProcessVerifier:
    name = "ProcessVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(self, expected: Iterable[str], *, label: str | None = None) -> Verdict:
        wanted = {name.strip().lower() for name in expected if name and name.strip()}
        display = label or (", ".join(sorted(wanted)) or "the process")
        if not wanted:
            return Verdict(self.name, False, f"No process name was given to verify {display}.")
        running = self.probe.running_processes()
        if running is None:
            return Verdict(self.name, False, f"I could not read the process list, so I cannot confirm {display} is running.")
        matched = sorted(wanted & running)
        if matched:
            return Verdict(self.name, True, f"{display} is running.", {"matched": matched})
        return Verdict(self.name, False, f"{display} is not running.", {"expected": sorted(wanted)})


class WindowVerifier:
    name = "WindowVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(
        self,
        title_substring: str,
        *,
        require_foreground: bool = False,
        require_maximized: bool = False,
        forbid_minimized: bool = True,
    ) -> Verdict:
        needle = title_substring.strip().lower()
        windows = self.probe.windows()
        if windows is None:
            return Verdict(self.name, False, f"I could not inspect open windows, so I cannot confirm {title_substring} is visible.")
        matches = [w for w in windows if needle and needle in w.title.lower()]
        if not matches:
            return Verdict(self.name, False, f"No visible window matching {title_substring} was found.")
        window = matches[0]
        problems: list[str] = []
        if not window.is_visible:
            problems.append("not visible")
        if forbid_minimized and window.is_minimized:
            problems.append("minimized")
        if require_foreground and not window.is_foreground:
            problems.append("not in the foreground")
        if require_maximized and not window.is_maximized:
            problems.append("not maximized")
        if problems:
            return Verdict(self.name, False, f"{window.title} is {', '.join(problems)}.", {"title": window.title})
        return Verdict(self.name, True, f"{window.title} is visible.", {"title": window.title})


class BrowserVerifier:
    name = "BrowserVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(
        self,
        *,
        expected_site: str | None = None,
        expect_playing: bool | None = None,
        expected_query: str | None = None,
    ) -> Verdict:
        state = self.probe.browser_state()
        if state is None:
            return Verdict(self.name, False, "I could not read the browser state, so I cannot confirm the page.")
        if not state.get("browser_open"):
            return Verdict(self.name, False, "The browser is not open.", {"state": state})
        current_site = str(state.get("current_site", "")).lower()
        if expected_site and expected_site.lower() not in current_site:
            return Verdict(
                self.name,
                False,
                f"The browser is on {current_site or 'an unknown page'}, not {expected_site}.",
                {"current_site": current_site},
            )
        if expect_playing is not None and bool(state.get("video_playing")) != expect_playing:
            word = "playing" if expect_playing else "paused"
            return Verdict(self.name, False, f"Media is not {word}.", {"state": state})
        if expected_query:
            actual_query = str(state.get("search_query", "")).lower()
            if expected_query.lower() not in actual_query:
                return Verdict(self.name, False, f"The search for {expected_query} is not reflected on the page.", {"state": state})
        site_label = current_site or "the requested page"
        return Verdict(self.name, True, f"The browser is on {site_label} as expected.", {"state": state})


class FilesystemVerifier:
    name = "FilesystemVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(self, path: str, *, must_exist: bool = True) -> Verdict:
        if not path or not path.strip():
            return Verdict(self.name, False, "No path was given to verify.")
        exists = self.probe.path_exists(path)
        if exists is None:
            return Verdict(self.name, False, f"I could not check the filesystem for {path}.")
        if must_exist and exists:
            return Verdict(self.name, True, f"{path} exists.", {"path": path})
        if not must_exist and not exists:
            return Verdict(self.name, True, f"{path} no longer exists.", {"path": path})
        target = "exist" if must_exist else "be gone"
        return Verdict(self.name, False, f"{path} does not {target}.", {"path": path})


class InstallVerifier:
    """Confirms a program is truly installed by locating its binary on disk.

    Opening a website, the Microsoft Store, or an installer is never accepted as
    proof of installation.
    """

    name = "InstallVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(
        self,
        app_key: str,
        *,
        executables: Sequence[str] | None = None,
        search_paths: Sequence[str] | None = None,
        label: str | None = None,
    ) -> Verdict:
        key = (app_key or "").strip().lower()
        target = INSTALL_TARGETS.get(key)
        exes = tuple(executables) if executables else (target.executables if target else ())
        paths = tuple(search_paths) if search_paths else (target.search_paths if target else ())
        display = label or (target.label if target else app_key or "the program")
        if not exes:
            return Verdict(
                self.name,
                False,
                f"I do not know which executable proves {display} is installed, so I cannot confirm it.",
            )
        found = self.probe.find_executable(exes, paths)
        if found is None:
            return Verdict(
                self.name,
                False,
                f"{display} is not installed. I could not find {exes[0]} on disk.",
                {"executables": list(exes)},
            )
        return Verdict(self.name, True, f"{display} is installed.", {"path": found})


class BluetoothVerifier:
    name = "BluetoothVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(self, *, expected_enabled: bool = True) -> Verdict:
        state = self.probe.bluetooth_enabled()
        if state is None:
            return Verdict(self.name, False, "I could not read the Bluetooth radio state, so I cannot confirm it.")
        if state == expected_enabled:
            word = "on" if expected_enabled else "off"
            return Verdict(self.name, True, f"Bluetooth is {word}.", {"enabled": state})
        word = "still off" if expected_enabled else "still on"
        return Verdict(self.name, False, f"Bluetooth is {word}.", {"enabled": state})


class WifiVerifier:
    name = "WifiVerifier"

    def __init__(self, probe: RealityProbe) -> None:
        self.probe = probe

    def verify(self, *, expected_connected: bool = True) -> Verdict:
        state = self.probe.wifi_connected()
        if state is None:
            return Verdict(self.name, False, "I could not read the Wi-Fi state, so I cannot confirm it.")
        if state == expected_connected:
            word = "connected" if expected_connected else "disconnected"
            return Verdict(self.name, True, f"Wi-Fi is {word}.", {"connected": state})
        word = "not connected" if expected_connected else "still connected"
        return Verdict(self.name, False, f"Wi-Fi is {word}.", {"connected": state})


# ---------------------------------------------------------------------------
# Suite / mission dispatcher
# ---------------------------------------------------------------------------


class VerifierSuite:
    """Runs the reality verifier matching a compiled mission."""

    def __init__(self, probe: RealityProbe | None = None) -> None:
        self.probe = probe or WindowsRealityProbe()
        self.process = ProcessVerifier(self.probe)
        self.window = WindowVerifier(self.probe)
        self.browser = BrowserVerifier(self.probe)
        self.filesystem = FilesystemVerifier(self.probe)
        self.install = InstallVerifier(self.probe)
        self.bluetooth = BluetoothVerifier(self.probe)
        self.wifi = WifiVerifier(self.probe)

    def verify_mission(self, mission: dict[str, Any]) -> Verdict:
        """Dispatch a compiled mission to the correct reality verifier.

        Conservative by design: any mission we cannot map to a concrete reality
        check fails closed rather than reporting a false success.
        """

        if not isinstance(mission, dict):
            return Verdict("VerifierSuite", False, "There is no mission to verify.")
        intent = str(mission.get("intent", "")).upper()
        context = str(mission.get("context", "")).strip().lower()
        text = str(mission.get("mission", ""))
        lower = text.lower()

        if intent == "INSTALL" or "install" in lower:
            return self.install.verify(_install_key_from_text(lower))
        if "bluetooth" in lower:
            return self.bluetooth.verify(expected_enabled=not _is_disable(lower))
        if re.search(r"\bwi[\s-]?fi\b", lower):
            return self.wifi.verify(expected_connected=not _is_disable(lower))
        if intent in {"SEARCH", "PLAY", "PAUSE", "RESUME", "OPEN"} and context in {
            "youtube.com",
            "spotify.com",
            "gmail.com",
            "github.com",
            "google.com",
            "reddit.com",
            "browser",
        }:
            return self.browser.verify(
                expected_site=None if context == "browser" else context,
                expect_playing=_expected_playing(intent),
            )
        if intent == "OPEN_APP" and context in APP_PROCESSES:
            return self.process.verify(APP_PROCESSES[context], label=context)
        return Verdict("VerifierSuite", False, f"I cannot yet verify this goal in reality: {text or intent}.")


def _install_key_from_text(lower: str) -> str:
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


def _is_disable(lower: str) -> bool:
    return bool(re.search(r"\b(turn off|disable|switch off|deactivate)\b", lower))


def _expected_playing(intent: str) -> bool | None:
    if intent == "PLAY" or intent == "RESUME":
        return True
    if intent == "PAUSE":
        return False
    return None
