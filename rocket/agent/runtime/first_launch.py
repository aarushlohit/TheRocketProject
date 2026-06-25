"""First-launch onboarding, encrypted preferences, and bundled-component load.

Runs exactly once. It collects accessibility/behaviour preferences (encrypted
via the DPAPI-backed memory and vault), detects the components already bundled
in the repository (skills, plugins, MCP servers, Shokunin powers, memory), and
records load markers so subsequent launches start instantly.

Rocket never stores passwords. Credentials are referenced only by mode and by
non-secret reference names.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent.runtime.memory import RocketMemory
from agent.runtime.vault import RocketVault

CREDENTIAL_MODES = {"already_configured", "import_references", "skip"}
CLEANUP_PREFERENCES = {"auto", "keep_open", "close"}

_PREFERENCES_KEY = "onboarding_preferences"
_MARKERS_KEY = "bootstrap_markers"
_COMPONENTS_KEY = "bundled_components"

# Components Rocket wants registered when present in the bundle.
REQUIRED_REGISTRATIONS = (
    "playwright",
    "windows",
    "shokunin",
    "github",
    "filesystem",
    "accessibility_skills",
)


@dataclass(frozen=True)
class OnboardingPreferences:
    name: str = ""
    preferred_name: str = ""
    language: str = "en"
    timezone: str = ""
    screen_reader: str = ""
    speech_rate: str = "normal"
    speech_verbosity: str = "normal"
    browser: str = "chrome"
    editor: str = "code"
    music_app: str = ""
    cleanup_preference: str = "auto"
    reuse_browser: bool = True
    credential_mode: str = "already_configured"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "OnboardingPreferences":
        if not isinstance(value, dict):
            return cls()
        defaults = asdict(cls())
        merged = {key: value.get(key, default) for key, default in defaults.items()}
        merged["credential_mode"] = (
            str(merged["credential_mode"]).strip().lower()
            if str(merged["credential_mode"]).strip().lower() in CREDENTIAL_MODES
            else "already_configured"
        )
        if str(merged["cleanup_preference"]).strip().lower() not in CLEANUP_PREFERENCES:
            merged["cleanup_preference"] = "auto"
        merged["reuse_browser"] = bool(merged["reuse_browser"])
        return cls(**merged)


@dataclass
class BootstrapMarkers:
    bootstrap_completed: bool = False
    skills_loaded: bool = False
    plugins_loaded: bool = False
    memory_loaded: bool = False
    mcp_loaded: bool = False
    vault_initialized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "BootstrapMarkers":
        if not isinstance(value, dict):
            return cls()
        defaults = asdict(cls())
        return cls(**{key: bool(value.get(key, default)) for key, default in defaults.items()})


@dataclass
class BundledComponents:
    skills: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    shokunin: list[str] = field(default_factory=list)
    memory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _list_subdirs(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(child.name for child in path.iterdir() if child.is_dir() and not child.name.startswith("."))


def _read_opencode_mcp(opencode_json: Path) -> list[str]:
    if not opencode_json.is_file():
        return []
    try:
        config = json.loads(opencode_json.read_text(encoding="utf-8"))
    except Exception:
        return []
    mcp = config.get("mcp") if isinstance(config, dict) else None
    if not isinstance(mcp, dict):
        return []
    enabled: list[str] = []
    for name, spec in mcp.items():
        if isinstance(spec, dict) and spec.get("enabled", True):
            enabled.append(str(name))
    return sorted(enabled)


def detect_bundled_components(workspace_root: Path) -> BundledComponents:
    """Scan the repository for already-bundled components. No downloads."""

    opencode_dir = workspace_root / ".opencode"
    skills = _list_subdirs(opencode_dir / "skills")
    plugins = _list_subdirs(opencode_dir / "plugin") + _list_subdirs(opencode_dir / "plugins")
    mcp_servers = _read_opencode_mcp(workspace_root / "opencode.json")
    shokunin = _list_subdirs(workspace_root / "shokunin-opencode-powers")
    memory = any("memory" in name for name in mcp_servers) or (workspace_root / "data").is_dir()
    return BundledComponents(
        skills=skills,
        plugins=plugins,
        mcp_servers=mcp_servers,
        shokunin=shokunin,
        memory=memory,
    )


def registration_status(components: BundledComponents) -> dict[str, bool]:
    """Report which required components are present to be registered."""

    mcp = {name.lower() for name in components.mcp_servers}
    skills = {name.lower() for name in components.skills}
    return {
        "playwright": any("playwright" in name for name in mcp),
        "windows": any("windows" in name for name in mcp),
        "shokunin": bool(components.shokunin) or any("shokunin" in name for name in mcp),
        "github": any("github" in name or "google" in name for name in mcp),
        "filesystem": any("filesystem" in name for name in mcp),
        "accessibility_skills": any("accessib" in name for name in skills),
    }


@dataclass
class BootstrapResult:
    ran: bool
    already_complete: bool
    markers: BootstrapMarkers
    components: BundledComponents
    registrations: dict[str, bool]
    preferences: OnboardingPreferences


class FirstLaunchBootstrap:
    """Runs onboarding + component load exactly once, with a reset option."""

    def __init__(
        self,
        data_dir: Path,
        workspace_root: Path,
        memory: RocketMemory | None = None,
        vault: RocketVault | None = None,
    ) -> None:
        phase2 = data_dir / "phase2"
        self.workspace_root = workspace_root
        self.memory = memory or RocketMemory(phase2)
        self.vault = vault or RocketVault(phase2)

    # -- state --------------------------------------------------------------

    def is_complete(self) -> bool:
        return self.markers().bootstrap_completed

    def markers(self) -> BootstrapMarkers:
        return BootstrapMarkers.from_dict(self.memory.get(_MARKERS_KEY))

    def load_preferences(self) -> OnboardingPreferences:
        return OnboardingPreferences.from_dict(self.memory.get(_PREFERENCES_KEY))

    def save_preferences(self, preferences: OnboardingPreferences) -> None:
        # Stored through DPAPI-backed memory; contains no passwords.
        self.memory.set(_PREFERENCES_KEY, preferences.to_dict())

    def save_credential_reference(self, name: str, reference: str) -> bool:
        """Store a non-secret credential *reference* (never a password)."""

        if not name.strip() or not reference.strip():
            return False
        if _looks_like_password(name):
            return False
        self.vault.set_secret(f"ref:{name.strip()}", reference.strip())
        return True

    # -- run / reset --------------------------------------------------------

    def run(
        self,
        preferences: OnboardingPreferences | None = None,
        *,
        force: bool = False,
    ) -> BootstrapResult:
        if self.is_complete() and not force:
            components = BundledComponents(**(self.memory.get(_COMPONENTS_KEY) or {}))
            return BootstrapResult(
                ran=False,
                already_complete=True,
                markers=self.markers(),
                components=components,
                registrations=registration_status(components),
                preferences=self.load_preferences(),
            )

        if preferences is not None:
            self.save_preferences(preferences)

        # Initialise the vault (writes the encrypted store if absent).
        self.vault.set_secret("vault:initialized", "1")

        components = detect_bundled_components(self.workspace_root)
        self.memory.set(_COMPONENTS_KEY, components.to_dict())

        markers = BootstrapMarkers(
            bootstrap_completed=True,
            skills_loaded=bool(components.skills),
            plugins_loaded=bool(components.plugins),
            memory_loaded=bool(components.memory),
            mcp_loaded=bool(components.mcp_servers),
            vault_initialized=self.vault.get_secret("vault:initialized") == "1",
        )
        self.memory.set(_MARKERS_KEY, markers.to_dict())

        return BootstrapResult(
            ran=True,
            already_complete=False,
            markers=markers,
            components=components,
            registrations=registration_status(components),
            preferences=self.load_preferences(),
        )

    def reset(self) -> None:
        """Clear onboarding so the next launch runs first-launch again."""

        self.memory.set(_MARKERS_KEY, BootstrapMarkers().to_dict())
        self.memory.set(_PREFERENCES_KEY, OnboardingPreferences().to_dict())
        self.memory.set(_COMPONENTS_KEY, BundledComponents().to_dict())


def _looks_like_password(name: str) -> bool:
    lowered = name.strip().lower()
    return any(token in lowered for token in ("password", "passwd", "secret", "pwd"))
