"""Browser session state and mission compilation helpers for Rocket."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_SITES = {
    "youtube": "youtube.com",
    "spotify": "spotify.com",
    "gmail": "gmail.com",
    "github": "github.com",
    "google": "google.com",
    "reddit": "reddit.com",
}


@dataclass
class BrowserState:
    current_browser: str = "chrome"
    current_site: str = ""
    current_tab: int = 1
    previous_tab: int | None = None
    search_query: str = ""
    video_playing: bool = False
    browser_open: bool = False
    tabs: list[dict[str, Any]] = field(default_factory=lambda: [{"index": 1, "site": "", "title": ""}])
    history: list[str] = field(default_factory=list)
    last_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "BrowserState":
        if not isinstance(value, dict):
            return cls()
        state = cls()
        data = asdict(state)
        data.update({key: value.get(key, fallback) for key, fallback in data.items()})
        if not isinstance(data.get("tabs"), list) or not data["tabs"]:
            data["tabs"] = [{"index": 1, "site": "", "title": ""}]
        if not isinstance(data.get("history"), list):
            data["history"] = []
        return cls(**data)


def compile_browser_mission(user_task: str, state: BrowserState) -> dict[str, Any]:
    """Compile one conversational browser task into mission JSON."""

    task = " ".join(user_task.strip().split())
    lower = task.lower()
    intent = _intent(lower)
    app = _target_desktop_app(lower)
    if intent == "CALCULATE":
        app = "calculator"
    explicit_site = _target_site(lower)
    target_site = explicit_site or _context_site_for(intent, lower, state)
    context = app or target_site or "browser"
    query = _query_for(intent, task, target_site)
    mission = _mission_text(intent, task, target_site, query, state, app)
    criteria = _success_criteria(intent, target_site, app)
    instructions = _instructions(intent, target_site, state, app)
    next_state = predict_browser_state(state, user_task)
    return {
        "intent": intent,
        "context": context,
        "mission": mission,
        "complexity": _complexity(intent),
        "estimated_steps": _estimated_steps(intent),
        "success_criteria": criteria,
        "instructions": instructions,
        "browser_state": state.to_dict(),
        "predicted_browser_state": next_state.to_dict(),
        "verifier": _verifier(intent, target_site),
        "recovery": [
            "Attempt 1: reuse the active browser window.",
            "Attempt 2: reuse or refocus the current tab.",
            "Attempt 3: repeat the site-specific action once.",
            "Attempt 4: stop and report that user help is required.",
        ],
    }


def predict_browser_state(state: BrowserState, task: str) -> BrowserState:
    next_state = BrowserState.from_dict(state.to_dict())
    lower = task.lower()
    explicit_site = _target_site(lower)
    site = explicit_site
    intent = _intent(lower)
    if not explicit_site and not _context_is_compatible(intent, lower, state.current_site):
        site = ""
    if intent == "CLOSE_BROWSER":
        reset = BrowserState()
        reset.last_action = task
        reset.history = [*state.history, task][-20:]
        return reset
    if "chrome" in lower or site or intent in {"SEARCH", "OPEN_TAB", "CLOSE_TAB", "SWITCH_TAB", "RETURN_TAB", "REFRESH", "BACK", "FORWARD"}:
        next_state.browser_open = True
        next_state.current_browser = "chrome"
    if site:
        next_state.current_site = site
        _set_current_tab_site(next_state, site)
    if intent == "SEARCH":
        next_state.search_query = _query_for(intent, task, site or next_state.current_site)
    if intent == "PLAY":
        next_state.video_playing = True
    if intent == "PAUSE":
        next_state.video_playing = False
    if intent == "RESUME":
        next_state.video_playing = True
    if intent == "OPEN_TAB":
        next_state.previous_tab = next_state.current_tab
        next_state.current_tab = max([tab.get("index", 1) for tab in next_state.tabs] or [1]) + 1
        next_state.tabs.append({"index": next_state.current_tab, "site": site or "", "title": ""})
        if site:
            next_state.current_site = site
    if intent == "CLOSE_TAB" and len(next_state.tabs) > 1:
        next_state.tabs = [tab for tab in next_state.tabs if tab.get("index") != next_state.current_tab]
        next_state.current_tab = next_state.previous_tab or next_state.tabs[-1].get("index", 1)
        next_state.current_site = _tab_site(next_state, next_state.current_tab)
    if intent == "RETURN_TAB" and next_state.previous_tab:
        current = next_state.current_tab
        next_state.current_tab = next_state.previous_tab
        next_state.previous_tab = current
        next_state.current_site = _tab_site(next_state, next_state.current_tab)
    next_state.last_action = task
    next_state.history = [*next_state.history, task][-20:]
    return next_state


def mission_to_task(mission: dict[str, Any]) -> str:
    return json.dumps(mission, ensure_ascii=True, separators=(",", ":"))


def parse_mission(task: str) -> dict[str, Any] | None:
    try:
        value = json.loads(task)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) and "mission" in value else None


def task_display_text(task: str) -> str:
    """Return the human-facing task text while keeping mission JSON private."""

    mission = parse_mission(task)
    if mission is None:
        return _clean_display(task)
    intent = str(mission.get("intent", "")).upper()
    context = str(mission.get("context", "")).strip().lower()
    mission_text = str(mission.get("mission", "")).strip()
    if intent == "OPEN_APP" and context:
        return f"Open {_app_label(context)}"
    if intent == "CALCULATE":
        return _clean_display(mission_text or task)
    if intent == "SEND_MESSAGE":
        return _clean_display(mission_text or task)
    if intent == "SEARCH":
        predicted = mission.get("predicted_browser_state")
        query = str(predicted.get("search_query", "")).strip() if isinstance(predicted, dict) else ""
        query = query or _query_for("SEARCH", mission_text, context)
        if query and context in SUPPORTED_SITES.values():
            return f"Search {query} on {_site_display_name(context)}"
        if query:
            return f"Search {query}"
    if intent == "OPEN" and context in SUPPORTED_SITES.values():
        return f"Open {_site_display_name(context)}"
    if intent == "INSTALL":
        return re.sub(
            r"\s+using\s+Microsoft\s+Store\s+or\s+the\s+official\s+safe\s+source\b",
            "",
            mission_text,
            flags=re.IGNORECASE,
        ).strip(" .")
    return _clean_display(mission_text or task)


def _clean_display(value: str) -> str:
    return " ".join(value.strip().strip(".").split())


def _intent(lower: str) -> str:
    checks = (
        ("INSTALL", r"\b(install|download|setup)\b|\bget\b.*\b(app|game|software|program|extension)\b"),
        ("SEND_MESSAGE", r"\b(send|message|text|reply)\b.*\b(whatsapp|gmail|telegram|group|chat)\b|\b(whatsapp|gmail|telegram)\b.*\b(send|message|text|reply)\b"),
        ("CALCULATE", r"\b(calc|calculator|calculate)\b.*(?:\d|\bplus\b|\bminus\b|\btimes\b|\bdivided\b|[+\-*/=])|(?:\d|\bplus\b|\bminus\b|\btimes\b|\bdivided\b|[+\-*/=]).*\b(calc|calculator|calculate)\b"),
        ("OPEN_APP", r"\b(open|launch|start|run)\b.*\b(whatsapp|settings|windows settings|chrome|edge|vscode|visual studio code|file explorer|explorer|notepad|calculator|calc|terminal|cmd|powershell)\b"),
        ("OPEN_TAB", r"\b(open|new)\s+(a\s+)?new\s+tab\b"),
        ("CLOSE_TAB", r"\bclose\s+(current\s+)?tab\b"),
        ("RETURN_TAB", r"\b(return|switch back|go back)\s+to\s+(youtube|previous tab|last tab)\b"),
        ("SWITCH_TAB", r"\bswitch\s+(tab|to)\b"),
        ("SEARCH", r"\b(search|find|look up)\b"),
        ("PLAY", r"\b(play|start)\b"),
        ("PAUSE", r"\bpause\b"),
        ("RESUME", r"\b(resume|continue)\b"),
        ("VOLUME_UP", r"\b(increase|raise|turn up).*\bvolume\b"),
        ("VOLUME_DOWN", r"\b(decrease|lower|turn down).*\bvolume\b"),
        ("MUTE", r"\bmute\b"),
        ("UNMUTE", r"\bunmute\b"),
        ("LIKE", r"\blike\b"),
        ("SUBSCRIBE", r"\bsubscribe\b"),
        ("COMMENTS", r"\bcomments?\b"),
        ("SCROLL", r"\bscroll\b"),
        ("BACK", r"\bgo back\b"),
        ("FORWARD", r"\bgo forward\b"),
        ("REFRESH", r"\b(refresh|reload)\b"),
        ("BOOKMARK", r"\bbookmark\b"),
        ("HISTORY", r"\bhistory\b"),
        ("DOWNLOADS", r"\bdownloads?\b"),
        ("CLOSE_BROWSER", r"\bclose\s+(chrome|browser|edge|all tabs)\b"),
        ("OPEN", r"\b(open|go to|navigate|visit|launch)\b"),
    )
    for intent, pattern in checks:
        if re.search(pattern, lower):
            return intent
    return "BROWSER_ACTION"


def _target_site(lower: str) -> str:
    for name, domain in SUPPORTED_SITES.items():
        if name in lower:
            return domain
    return ""


def context_is_compatible_task(task: str, context: str, intent: str | None = None) -> bool:
    """Return whether a model-provided context should be trusted for this task."""

    lower = task.lower()
    return _context_is_compatible(intent or _intent(lower), lower, context)


def strip_incompatible_context(task: str, context: str) -> str:
    """Remove a hallucinated site suffix like "on YouTube youtube.com" from unrelated tasks."""

    cleaned = task.strip(" .")
    for name in _context_names(context):
        cleaned = re.sub(rf"\b(on|in|inside|within)\s+{re.escape(name)}\b", "", cleaned, flags=re.IGNORECASE).strip(" .")
        cleaned = re.sub(rf"\b{re.escape(name)}\b$", "", cleaned, flags=re.IGNORECASE).strip(" .")
    return cleaned or task.strip(" .")


def _context_site_for(intent: str, lower: str, state: BrowserState) -> str:
    if _context_is_compatible(intent, lower, state.current_site):
        return state.current_site
    return ""


def _context_is_compatible(intent: str, lower: str, context: str) -> bool:
    if not context:
        return False
    if _looks_like_context_breaking_task(lower):
        return False
    return intent in {
        "SEARCH",
        "PLAY",
        "PAUSE",
        "RESUME",
        "VOLUME_UP",
        "VOLUME_DOWN",
        "MUTE",
        "UNMUTE",
        "LIKE",
        "SUBSCRIBE",
        "COMMENTS",
        "SCROLL",
        "BACK",
        "FORWARD",
        "REFRESH",
    }


def _looks_like_context_breaking_task(lower: str) -> bool:
    if re.search(r"\b(install|download|setup)\b|\bget\b.*\b(app|game|software|program|extension)\b", lower):
        return True
    if re.search(r"\b(open|launch|start|run)\b.*\b(settings|whatsapp|chrome|edge|vscode|visual studio code|file explorer|explorer|notepad|calculator|calc|terminal|cmd|powershell)\b", lower):
        return True
    if re.search(r"\b(create|save|delete|rename|move|copy|paste|edit|write)\b.*\b(file|folder|document|note|desktop|workspace)\b", lower):
        return True
    return False


def _query_for(intent: str, task: str, site: str) -> str:
    if intent != "SEARCH":
        return ""
    cleaned = re.sub(r"^(search|find|look up)\s+", "", task, flags=re.IGNORECASE).strip(" .")
    site_names = [*SUPPORTED_SITES.keys()]
    if site:
        site_names.extend(_site_aliases(site))
    for name in site_names:
        cleaned = re.sub(rf"\b(on|in|inside|within)\s+{re.escape(name)}\b", "", cleaned, flags=re.IGNORECASE).strip(" .")
        cleaned = re.sub(rf"\b{re.escape(name)}\s+(search|results)\b", "", cleaned, flags=re.IGNORECASE).strip(" .")
    return cleaned


def _mission_text(intent: str, task: str, site: str, query: str, state: BrowserState, app: str = "") -> str:
    if intent == "OPEN_APP" and app:
        return f"Open installed {_app_label(app)} application"
    if intent == "CALCULATE":
        expression = _calculator_expression(task)
        result = _safe_arithmetic_result(expression)
        if result:
            return f"Calculate {expression} in Calculator and verify the result is {result}"
        return f"Calculate {expression or task} in Calculator"
    if intent == "SEND_MESSAGE":
        target_app = _app_label(app) if app else _site_display_name(site) if site else "messaging app"
        return f"{_clean_send_message_task(task)} using {target_app}"
    if intent == "INSTALL":
        return f"{_clean_install_task(task)} using Microsoft Store or the official safe source"
    if intent == "SEARCH" and site:
        return f"Search {query or task} inside {site}"
    if intent == "OPEN" and site:
        return f"Open {site} in the active browser"
    if intent == "OPEN_TAB":
        return "Open a new browser tab"
    if intent == "RETURN_TAB":
        return "Return to the previous browser tab"
    if intent == "PLAY":
        return "Play the requested media/result in the current site context"
    if intent in {"PAUSE", "RESUME", "VOLUME_UP", "VOLUME_DOWN", "MUTE", "UNMUTE"}:
        return f"{task} in the current {state.current_site or 'browser'} context"
    return task


def _success_criteria(intent: str, site: str, app: str = "") -> list[str]:
    if intent == "OPEN_APP" and app:
        return [f"{app}_visible", f"{app}_process_running"]
    if intent == "CALCULATE":
        expression = _calculator_expression("")
        return ["calculator_visible", "calculator_expression_entered", "calculator_result_visible"]
    if intent == "SEND_MESSAGE":
        app_key = app or (site.split(".", 1)[0] if site else "messaging_app")
        return [f"{app_key}_visible", "recipient_or_chat_selected", "message_sent_visible"]
    site_key = site.split(".", 1)[0] if site else "browser"
    mapping = {
        "SEARCH": [f"{site_key}_search_completed", "search_results_visible"],
        "PLAY": ["video_or_media_playing"],
        "PAUSE": ["video_or_media_paused"],
        "RESUME": ["video_or_media_playing"],
        "OPEN_TAB": ["tab_count_increased", "new_tab_focused"],
        "CLOSE_TAB": ["tab_closed", "previous_or_adjacent_tab_focused"],
        "RETURN_TAB": ["previous_tab_focused"],
        "SWITCH_TAB": ["requested_tab_focused"],
        "OPEN": [f"{site_key}_open", "page_visible"],
        "INSTALL": ["installer_or_store_page_visible", "requested_app_or_game_identified"],
    }
    return mapping.get(intent, ["browser_action_verified"])


def _instructions(intent: str, site: str, state: BrowserState, app: str = "") -> list[str]:
    instructions = [
        "Reuse active browser",
        "Reuse current tab unless mission explicitly requires a new tab",
        "Do not perform Google Search unless context is google.com or mission says Google",
        "Verify using browser URL/title/page state before final status",
    ]
    if intent == "OPEN_APP" and app:
        return [
            f"Open installed {_app_label(app)} application",
            "Do not search the web",
            "Do not use the current browser context",
            f"Verify {_app_label(app)} process or window is visible",
        ]
    if intent == "CALCULATE":
        return [
            "Use installed Windows Calculator",
            "If Calculator is already open, focus and reuse the existing window",
            "Do not open a duplicate Calculator window unless no usable Calculator exists",
            "Enter the requested arithmetic expression exactly",
            "Verify the final displayed result visually or through accessibility state",
            "Do not report success merely because Calculator opened",
            "After the verified result is reported, the runtime may close Calculator unless the user asked to keep it open",
        ]
    if intent == "SEND_MESSAGE":
        target = _app_label(app) if app else _site_display_name(site) if site else "the messaging app"
        return [
            f"Use {target}; if it is already open, focus and reuse the existing window",
            "Do not open duplicate app windows unless no usable window exists",
            "Locate the exact recipient or group named by the user",
            "Type the exact message text requested by the user without rewriting it",
            "Before sending, verify the recipient/chat and message text are correct",
            "Send only when recipient/chat and message are unambiguous",
            "Verify the sent message is visible in the conversation",
            "Close only temporary popups/dialogs after sending; do not close the main app unless the user asked to close it",
        ]
    if site:
        instructions.append(f"Perform the action inside {site}")
    if intent == "INSTALL":
        instructions.extend(
            [
                "This is an install/download task, not a YouTube or media-site task",
                "Do not search inside the current site unless the user explicitly asks for that site",
                "Prefer Microsoft Store for games/apps on Windows; otherwise use the official vendor source",
                "Verify the requested app or game name before starting install/download",
            ]
        )
    if intent == "SEARCH" and site:
        instructions.append(f"Search inside {site}, not from the browser address bar as a generic web search")
    if state.current_site and _context_is_compatible(intent, "", state.current_site):
        instructions.append(f"Current site is {state.current_site}; preserve this context unless the mission changes site")
    return instructions


def _verifier(intent: str, site: str) -> str:
    if intent == "CALCULATE":
        return "CalculatorVerifier"
    if intent == "SEND_MESSAGE":
        return "MessagingVerifier"
    if intent == "OPEN_APP":
        return "DesktopAppVerifier"
    if site == "youtube.com":
        return "YouTubeVerifier"
    if site == "spotify.com":
        return "SpotifyVerifier"
    if site == "gmail.com":
        return "GmailVerifier"
    if intent in {"OPEN_TAB", "CLOSE_TAB", "SWITCH_TAB", "RETURN_TAB"}:
        return "TabVerifier"
    if intent == "INSTALL":
        return "InstallVerifier"
    return "BrowserVerifier"


def _complexity(intent: str) -> str:
    if intent == "INSTALL":
        return "MEDIUM"
    return "LOW" if intent in {"SEARCH", "OPEN", "OPEN_APP", "PLAY", "PAUSE", "RESUME", "OPEN_TAB", "RETURN_TAB"} else "MEDIUM"


def _estimated_steps(intent: str) -> int:
    return {
        "SEARCH": 2,
        "OPEN": 2,
        "OPEN_APP": 2,
        "CALCULATE": 3,
        "PLAY": 2,
        "PAUSE": 1,
        "RESUME": 1,
        "OPEN_TAB": 1,
        "RETURN_TAB": 1,
        "INSTALL": 4,
    }.get(intent, 3)


def _set_current_tab_site(state: BrowserState, site: str) -> None:
    for tab in state.tabs:
        if tab.get("index") == state.current_tab:
            tab["site"] = site
            return
    state.tabs.append({"index": state.current_tab, "site": site, "title": ""})


def _tab_site(state: BrowserState, index: int) -> str:
    for tab in state.tabs:
        if tab.get("index") == index:
            return str(tab.get("site", ""))
    return ""


def _site_aliases(site: str) -> list[str]:
    aliases = {
        "youtube.com": ["youtube", "you tube"],
        "spotify.com": ["spotify"],
        "gmail.com": ["gmail", "google mail"],
        "github.com": ["github", "git hub"],
        "google.com": ["google"],
        "reddit.com": ["reddit"],
    }
    return aliases.get(site, [site.split(".", 1)[0]])


def _site_display_name(site: str) -> str:
    names = {
        "youtube.com": "YouTube",
        "spotify.com": "Spotify",
        "gmail.com": "Gmail",
        "github.com": "GitHub",
        "google.com": "Google",
        "reddit.com": "Reddit",
    }
    return names.get(site, site)


def _clean_install_task(task: str) -> str:
    return strip_incompatible_context(task, "")


def _clean_send_message_task(task: str) -> str:
    cleaned = _clean_display(task)
    open_first = re.search(
        r"^(?:open\s+whats\s*app\s+and\s+)?(?:in\s+)?(.+?)\s+(?:send\s+(?:message|msg)|message|text)\s+(.+)$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if open_first:
        recipient = _clean_display(open_first.group(1))
        body = _clean_display(open_first.group(2))
        return f"Send message {body} to {recipient}"
    send_first = re.search(
        r"^send\s+(?:message\s+|msg\s+)?(.+?)\s+to\s+(.+?)(?:\s+(?:in|on|using)\s+whats\s*app)?$",
        cleaned,
        flags=re.IGNORECASE,
    )
    if send_first:
        body = _clean_display(send_first.group(1))
        recipient = _clean_display(send_first.group(2))
        return f"Send message {body} to {recipient}"
    return cleaned


def _calculator_expression(task: str) -> str:
    cleaned = _clean_display(task).lower()
    cleaned = re.sub(r"\b(open|launch|start|run)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(calculator|calc|calculate|type|enter|and|in|using)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("plus", "+")
    cleaned = cleaned.replace("minus", "-")
    cleaned = cleaned.replace("times", "*")
    cleaned = cleaned.replace("multiplied by", "*")
    cleaned = cleaned.replace("divided by", "/")
    cleaned = cleaned.replace("x", "*")
    match = re.search(r"(\d+(?:\.\d+)?(?:\s*[+\-*/]\s*\d+(?:\.\d+)?)+)", cleaned)
    if not match:
        return ""
    return re.sub(r"\s+", "", match.group(1))


def _safe_arithmetic_result(expression: str) -> str:
    if not expression or not re.fullmatch(r"\d+(?:\.\d+)?(?:[+\-*/]\d+(?:\.\d+)?)+", expression):
        return ""
    try:
        value = eval(expression, {"__builtins__": {}}, {})  # noqa: S307 - validated arithmetic only.
    except Exception:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _context_names(context: str) -> list[str]:
    names = [*SUPPORTED_SITES.keys(), *SUPPORTED_SITES.values(), "you tube", "google mail", "git hub"]
    if context:
        names.extend([context, *_site_aliases(context)])
    return sorted(set(names), key=len, reverse=True)


def _target_desktop_app(lower: str) -> str:
    app_patterns = (
        ("whatsapp", r"\bwhats\s*app\b|\bwhatsapp\b"),
        ("settings", r"\bwindows settings\b|\bsettings\b"),
        ("chrome", r"\bgoogle chrome\b|\bchrome\b"),
        ("edge", r"\bmicrosoft edge\b|\bedge\b"),
        ("vscode", r"\bvisual studio code\b|\bvs\s*code\b|\bvscode\b"),
        ("explorer", r"\bfile explorer\b|\bexplorer\b"),
        ("notepad", r"\bnotepad\b"),
        ("calculator", r"\bcalculator\b|\bcalc\b"),
        ("terminal", r"\bterminal\b|\bcmd\b|\bpowershell\b"),
    )
    for app, pattern in app_patterns:
        if re.search(pattern, lower):
            return app
    return ""


def _app_label(app: str) -> str:
    return {
        "whatsapp": "WhatsApp",
        "settings": "Windows Settings",
        "chrome": "Chrome",
        "edge": "Microsoft Edge",
        "vscode": "VSCode",
        "explorer": "File Explorer",
        "notepad": "Notepad",
        "calculator": "Calculator",
        "terminal": "Terminal",
    }.get(app, app)
