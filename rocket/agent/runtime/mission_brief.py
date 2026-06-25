"""Human mission brief, window policy, and cleanup policy for OpenCode.

OpenCode and the phone must never receive raw mission JSON. This module turns a
compiled mission dict into the blind-first brief Rocket speaks and acts on:

    MISSION
    Search cats
    CONTEXT
    YouTube is open
    GOAL
    Search inside YouTube
    DONE WHEN
    Search results are visible inside YouTube

It also derives the window policy (reuse, foreground, maximize, no duplicate)
and the cleanup policy (persistent apps stay open, one-shot utilities close).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.runtime.browser_state import (
    SUPPORTED_SITES,
    _app_label,
    _site_display_name,
    parse_mission,
    task_display_text,
)

# Apps/sites that should stay open for reuse after the goal is achieved.
PERSISTENT_CONTEXTS = {
    "chrome",
    "edge",
    "vscode",
    "whatsapp",
    "spotify",
    *SUPPORTED_SITES.values(),
}

# Phrases that force an app to stay open regardless of defaults.
_KEEP_OPEN_PHRASES = ("keep open", "leave open", "do not close", "don't close", "stay open")


@dataclass(frozen=True)
class WindowPolicy:
    """How Rocket must treat the target window."""

    reuse_existing: bool = True
    focus: bool = True
    foreground: bool = True
    maximize: bool = True
    allow_minimized: bool = False
    allow_duplicate: bool = False

    def describe(self, target: str) -> str:
        return (
            f"Reuse the existing {target} if it is already open; restore, focus, bring it to the "
            "foreground, and maximize it. Never open a duplicate. Never work in a minimized or hidden window."
        )


def window_policy(mission: dict[str, Any] | None) -> WindowPolicy:
    """Return the window policy for a mission (currently uniform and strict)."""

    del mission
    return WindowPolicy()


def cleanup_policy(mission: dict[str, Any] | None) -> str:
    """Return ``"persistent"`` (keep open) or ``"temporary"`` (close after).

    Defaults to ``"persistent"`` so Rocket never closes something unexpectedly.
    Only one-shot utilities (e.g. a Calculator opened just to compute) are
    classified as temporary.
    """

    if not isinstance(mission, dict):
        return "persistent"
    intent = str(mission.get("intent", "")).upper()
    context = str(mission.get("context", "")).strip().lower()
    display = task_display_text_from_mission(mission).lower()

    if any(phrase in display for phrase in _KEEP_OPEN_PHRASES):
        return "persistent"
    if context in PERSISTENT_CONTEXTS:
        return "persistent"
    if intent == "CALCULATE":
        return "temporary"
    if context in {"calculator", "notepad"} and any(
        word in display for word in ("calculate", "calc", "temporary", "quick", "weather", "clipboard")
    ):
        return "temporary"
    return "persistent"


def task_display_text_from_mission(mission: dict[str, Any]) -> str:
    """Human display text for a mission dict (no JSON)."""

    from agent.runtime.browser_state import mission_to_task

    return task_display_text(mission_to_task(mission))


def _target_label(mission: dict[str, Any]) -> str:
    context = str(mission.get("context", "")).strip().lower()
    if context in SUPPORTED_SITES.values():
        return f"{_site_display_name(context)} in Chrome"
    if context in {"chrome", "edge"}:
        return _app_label(context)
    if context and context != "browser":
        return _app_label(context)
    return "Chrome"


def _context_line(mission: dict[str, Any]) -> str:
    context = str(mission.get("context", "")).strip().lower()
    state = mission.get("browser_state") if isinstance(mission.get("browser_state"), dict) else {}
    browser_open = bool(state.get("browser_open"))
    current_site = str(state.get("current_site", "")).lower()

    if context in SUPPORTED_SITES.values():
        if browser_open and current_site == context:
            return f"{_site_display_name(context)} is already open"
        return f"Target site is {_site_display_name(context)}"
    if context in {"chrome", "edge"}:
        return f"{_app_label(context)} is the active browser"
    if context and context != "browser":
        return f"Target app is {_app_label(context)}"
    if browser_open and current_site:
        return f"Chrome is open on {_site_display_name(current_site)}"
    if browser_open:
        return "Chrome is open"
    return "No relevant app is open yet"


def _goal_line(mission: dict[str, Any]) -> str:
    intent = str(mission.get("intent", "")).upper()
    context = str(mission.get("context", "")).strip().lower()
    mission_text = str(mission.get("mission", "")).strip()
    if intent == "SEARCH" and context in SUPPORTED_SITES.values():
        return f"Search inside {_site_display_name(context)}"
    return mission_text or task_display_text_from_mission(mission)


_DONE_WHEN_PHRASES = {
    "search_results_visible": "Search results are visible",
    "video_or_media_playing": "The video or media is playing",
    "video_or_media_paused": "The video or media is paused",
    "page_visible": "The page is visible",
    "tab_count_increased": "A new tab is open",
    "new_tab_focused": "The new tab is focused",
    "previous_tab_focused": "The previous tab is focused",
    "requested_tab_focused": "The requested tab is focused",
    "tab_closed": "The tab is closed",
    "calculator_visible": "Calculator is visible",
    "calculator_result_visible": "The calculator result is visible",
    "message_sent_visible": "The sent message is visible in the conversation",
    "installer_or_store_page_visible": "The install source is open",
    "requested_app_or_game_identified": "The requested app is identified",
}


def _done_when_line(mission: dict[str, Any]) -> str:
    criteria = mission.get("success_criteria")
    phrases: list[str] = []
    if isinstance(criteria, list):
        for token in criteria:
            key = str(token).strip()
            if not key:
                continue
            phrase = _DONE_WHEN_PHRASES.get(key)
            if phrase is None:
                if key.endswith("_search_completed"):
                    phrase = "The search has completed"
                elif key.endswith("_visible"):
                    phrase = f"{key[:-len('_visible')].replace('_', ' ').strip().capitalize()} is visible"
                elif key.endswith("_open"):
                    phrase = f"{key[:-len('_open')].replace('_', ' ').strip().capitalize()} is open"
                elif key.endswith("_process_running"):
                    phrase = f"{key[:-len('_process_running')].replace('_', ' ').strip().capitalize()} is running"
                else:
                    phrase = key.replace("_", " ").strip().capitalize()
            if phrase and phrase not in phrases:
                phrases.append(phrase)
    if not phrases:
        return "The Rocket verifier confirms the goal in observable reality"
    return ". ".join(phrases)


def build_mission_brief(task_or_mission: str | dict[str, Any]) -> str:
    """Return the blind-first MISSION/CONTEXT/GOAL/DONE WHEN brief.

    Accepts either a mission task string (JSON) or a parsed mission dict. Never
    emits JSON.
    """

    if isinstance(task_or_mission, dict):
        mission: dict[str, Any] | None = task_or_mission
        display = task_display_text_from_mission(task_or_mission)
    else:
        mission = parse_mission(task_or_mission)
        display = task_display_text(task_or_mission)

    if mission is None:
        return (
            "MISSION\n"
            f"{display}\n"
            "CONTEXT\n"
            "No relevant app is open yet\n"
            "GOAL\n"
            f"{display}\n"
            "DONE WHEN\n"
            "The Rocket verifier confirms the goal in observable reality"
        )

    policy = window_policy(mission)
    target = _target_label(mission)
    after_goal = (
        f"Keep {target} open for reuse."
        if cleanup_policy(mission) == "persistent"
        else f"Close {target} once the verified result is reported."
    )
    return (
        "MISSION\n"
        f"{display}\n"
        "CONTEXT\n"
        f"{_context_line(mission)}\n"
        "GOAL\n"
        f"{_goal_line(mission)}\n"
        "DONE WHEN\n"
        f"{_done_when_line(mission)}\n"
        "WINDOW POLICY\n"
        f"{policy.describe(target)}\n"
        "AFTER GOAL\n"
        f"{after_goal}"
    )
