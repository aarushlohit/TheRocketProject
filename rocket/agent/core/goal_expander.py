"""
Stage 5 — Goal Expander Module.

Converts high-level goals into executable multi-step plans.
Examples:
- "watch cat videos" → OPEN_APP + SEARCH_WEB + CLICK_ELEMENT
- "check email" → OPEN_APP + OPEN_URL
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# GOAL PATTERNS
# =============================================================================

GOAL_PATTERNS = [
    # Watch/View patterns
    (r"^watch\s+(.+)", "watch"),
    (r"^view\s+(.+)", "view"),
    (r"^see\s+(.+)", "view"),
    
    # Play patterns
    (r"^play\s+(.+)", "play"),
    (r"^listen\s+to\s+(.+)", "play"),
    
    # Search/Find patterns
    (r"^find\s+(.+)", "search"),
    (r"^look\s+for\s+(.+)", "search"),
    (r"^search\s+for\s+(.+)", "search"),
    (r"^search\s+(.+)", "search"),
    (r"^google\s+(.+)", "search"),
    
    # Check/Read patterns
    (r"^check\s+(.+)", "check"),
    (r"^read\s+(.+)", "read"),
    
    # Browse patterns
    (r"^browse\s+(.+)", "browse"),
    (r"^go\s+to\s+(.+)", "goto"),
    (r"^visit\s+(.+)", "goto"),
    
    # Download patterns
    (r"^download\s+(.+)", "download"),
    (r"^get\s+(.+)", "download"),
]


# =============================================================================
# KEYWORD TO SITE MAPPING
# =============================================================================

KEYWORD_TO_SITE = {
    # Video platforms
    "youtube": "youtube.com",
    "video": "youtube.com",
    "videos": "youtube.com",
    "movie": "youtube.com",
    "movies": "youtube.com",
    "netflix": "netflix.com",
    "twitch": "twitch.tv",
    
    # Music platforms
    "music": "spotify.com",
    "song": "spotify.com",
    "songs": "spotify.com",
    "spotify": "spotify.com",
    
    # Social media
    "twitter": "twitter.com",
    "x": "twitter.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
    "reddit": "reddit.com",
    
    # Email
    "email": "gmail.com",
    "mail": "gmail.com",
    "gmail": "gmail.com",
    "outlook": "outlook.com",
    
    # News
    "news": "news.google.com",
    
    # Shopping
    "amazon": "amazon.com",
    "shop": "amazon.com",
    "shopping": "amazon.com",
    
    # Work
    "github": "github.com",
    "docs": "docs.google.com",
    "drive": "drive.google.com",
    
    # Search
    "google": "google.com",
}


# =============================================================================
# GOAL RESULT
# =============================================================================

@dataclass
class GoalExpansionResult:
    """Result of goal expansion."""
    is_goal: bool
    goal_type: Optional[str]
    extracted_subject: Optional[str]
    steps: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# GOAL DETECTION
# =============================================================================

def is_high_level_goal(text: str) -> bool:
    """
    Detect if input is a high-level goal rather than a direct command.
    
    Goals: "watch videos", "check email", "play music"
    Commands: "open chrome", "search youtube", "type hello"
    """
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    for pattern, _ in GOAL_PATTERNS:
        if re.match(pattern, text_lower):
            return True
    
    return False


def detect_goal_type(text: str) -> Optional[tuple[str, str]]:
    """
    Detect goal type and extract subject.
    
    Returns: (goal_type, subject) or None
    """
    if not text:
        return None
    
    text_lower = text.lower().strip()
    
    for pattern, goal_type in GOAL_PATTERNS:
        match = re.match(pattern, text_lower)
        if match:
            subject = match.group(1).strip()
            return goal_type, subject
    
    return None


# =============================================================================
# GOAL EXPANSION
# =============================================================================

def expand_goal(
    text: str,
    context: Optional[Dict[str, Any]] = None,
) -> GoalExpansionResult:
    """
    Expand a high-level goal into executable steps.
    
    Args:
        text: Goal text
        context: Optional context (last_browser, etc.)
        
    Returns:
        GoalExpansionResult with steps
    """
    context = context or {}
    
    # Detect goal type
    detection = detect_goal_type(text)
    if not detection:
        return GoalExpansionResult(
            is_goal=False,
            goal_type=None,
            extracted_subject=None,
            steps=[],
            confidence=0.0,
        )
    
    goal_type, subject = detection
    steps = []
    
    # Check if browser is already open
    browser_open = bool(context.get("last_browser"))
    preferred_browser = context.get("preferred_browser", "chrome")
    
    # Expand based on goal type
    if goal_type == "watch":
        steps = _expand_watch_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "view":
        steps = _expand_view_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "play":
        steps = _expand_play_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "search":
        steps = _expand_search_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "check":
        steps = _expand_check_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "read":
        steps = _expand_read_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "browse":
        steps = _expand_browse_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "goto":
        steps = _expand_goto_goal(subject, browser_open, preferred_browser)
    
    elif goal_type == "download":
        steps = _expand_download_goal(subject, browser_open, preferred_browser)
    
    else:
        # Generic search fallback
        steps = _expand_search_goal(subject, browser_open, preferred_browser)
    
    return GoalExpansionResult(
        is_goal=True,
        goal_type=goal_type,
        extracted_subject=subject,
        steps=steps,
        confidence=0.9 if steps else 0.5,
        metadata={
            "browser_open": browser_open,
            "preferred_browser": preferred_browser,
        },
    )


# =============================================================================
# SPECIFIC GOAL EXPANDERS
# =============================================================================

def _expand_watch_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'watch X' goals."""
    steps = []
    
    # Step 1: Open browser if needed
    if not browser_open:
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": preferred_browser},
        })
    
    # Step 2: Determine target site
    target_site = _find_target_site(subject, default="youtube.com")
    
    # Step 3: Navigate to site or search
    if target_site:
        steps.append({
            "intent": "OPEN_URL",
            "slots": {"url": f"https://{target_site}"},
        })
        
        # Step 4: Search within site if subject has more than just site name
        search_query = _extract_search_query(subject)
        if search_query:
            steps.append({
                "intent": "TYPE_TEXT",
                "slots": {"text": search_query, "target": "search bar"},
            })
            steps.append({
                "intent": "PRESS_KEYS",
                "slots": {"keys": "enter"},
            })
            steps.append({
                "intent": "CLICK_ELEMENT",
                "slots": {"target": "first result"},
            })
    else:
        # Generic search
        steps.append({
            "intent": "SEARCH_WEB",
            "slots": {"query": subject},
        })
        steps.append({
            "intent": "CLICK_ELEMENT",
            "slots": {"target": "first result"},
        })
    
    return steps


def _expand_view_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'view X' goals."""
    # Similar to watch
    return _expand_watch_goal(subject, browser_open, preferred_browser)


def _expand_play_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'play X' goals."""
    steps = []
    
    # Check for music apps first
    if any(word in subject.lower() for word in ["music", "song", "spotify"]):
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": "spotify"},
        })
        
        search_query = _extract_search_query(subject)
        if search_query:
            steps.append({
                "intent": "CLICK_ELEMENT",
                "slots": {"target": "search bar"},
            })
            steps.append({
                "intent": "TYPE_TEXT",
                "slots": {"text": search_query},
            })
            steps.append({
                "intent": "PRESS_KEYS",
                "slots": {"keys": "enter"},
            })
            steps.append({
                "intent": "CLICK_ELEMENT",
                "slots": {"target": "first result"},
            })
        else:
            steps.append({
                "intent": "CLICK_ELEMENT",
                "slots": {"target": "play button"},
            })
    else:
        # Default to video
        return _expand_watch_goal(subject, browser_open, preferred_browser)
    
    return steps


def _expand_search_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'search/find X' goals."""
    steps = []
    
    if not browser_open:
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": preferred_browser},
        })
    
    steps.append({
        "intent": "SEARCH_WEB",
        "slots": {"query": subject},
    })
    
    return steps


def _expand_check_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'check X' goals (email, news, etc.)."""
    steps = []
    
    # Check for email
    if "email" in subject.lower() or "mail" in subject.lower():
        if not browser_open:
            steps.append({
                "intent": "OPEN_APP",
                "slots": {"app": preferred_browser},
            })
        steps.append({
            "intent": "OPEN_URL",
            "slots": {"url": "https://gmail.com"},
        })
        return steps
    
    # Check for news
    if "news" in subject.lower():
        if not browser_open:
            steps.append({
                "intent": "OPEN_APP",
                "slots": {"app": preferred_browser},
            })
        steps.append({
            "intent": "OPEN_URL",
            "slots": {"url": "https://news.google.com"},
        })
        return steps
    
    # Default to search
    return _expand_search_goal(subject, browser_open, preferred_browser)


def _expand_read_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'read X' goals."""
    # Similar to check
    return _expand_check_goal(subject, browser_open, preferred_browser)


def _expand_browse_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'browse X' goals."""
    steps = []
    
    if not browser_open:
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": preferred_browser},
        })
    
    # Find target site
    target_site = _find_target_site(subject)
    
    if target_site:
        steps.append({
            "intent": "OPEN_URL",
            "slots": {"url": f"https://{target_site}"},
        })
    else:
        steps.append({
            "intent": "SEARCH_WEB",
            "slots": {"query": subject},
        })
    
    return steps


def _expand_goto_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'go to X' / 'visit X' goals."""
    steps = []
    
    if not browser_open:
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": preferred_browser},
        })
    
    # Check if it's a URL
    if _is_url_like(subject):
        url = _normalize_url(subject)
        steps.append({
            "intent": "OPEN_URL",
            "slots": {"url": url},
        })
    else:
        # Find known site or search
        target_site = _find_target_site(subject)
        if target_site:
            steps.append({
                "intent": "OPEN_URL",
                "slots": {"url": f"https://{target_site}"},
            })
        else:
            steps.append({
                "intent": "SEARCH_WEB",
                "slots": {"query": subject},
            })
    
    return steps


def _expand_download_goal(
    subject: str,
    browser_open: bool,
    preferred_browser: str,
) -> List[Dict[str, Any]]:
    """Expand 'download X' goals."""
    steps = []
    
    if not browser_open:
        steps.append({
            "intent": "OPEN_APP",
            "slots": {"app": preferred_browser},
        })
    
    steps.append({
        "intent": "SEARCH_WEB",
        "slots": {"query": f"download {subject}"},
    })
    
    steps.append({
        "intent": "CLICK_ELEMENT",
        "slots": {"target": "first result"},
    })
    
    steps.append({
        "intent": "CLICK_ELEMENT",
        "slots": {"target": "download button"},
    })
    
    return steps


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _find_target_site(subject: str, default: Optional[str] = None) -> Optional[str]:
    """Find target site from keywords in subject."""
    subject_lower = subject.lower()
    
    for keyword, site in KEYWORD_TO_SITE.items():
        if keyword in subject_lower:
            return site
    
    return default


def _extract_search_query(subject: str) -> Optional[str]:
    """Extract search query from subject, removing site keywords."""
    subject_lower = subject.lower()
    
    # Remove site keywords
    query_parts = []
    words = subject.split()
    
    for word in words:
        if word.lower() not in KEYWORD_TO_SITE:
            query_parts.append(word)
    
    query = " ".join(query_parts).strip()
    return query if query else None


def _is_url_like(text: str) -> bool:
    """Check if text looks like a URL."""
    text_lower = text.lower()
    return (
        text_lower.startswith("http://") or
        text_lower.startswith("https://") or
        text_lower.startswith("www.") or
        ".com" in text_lower or
        ".org" in text_lower or
        ".net" in text_lower or
        ".io" in text_lower
    )


def _normalize_url(text: str) -> str:
    """Normalize text to a proper URL."""
    text = text.strip()
    
    if not text.startswith("http://") and not text.startswith("https://"):
        text = "https://" + text
    
    return text


# =============================================================================
# MULTI-STEP DETECTION
# =============================================================================

MULTI_STEP_KEYWORDS = [
    " and ",
    " then ",
    " after that ",
    " next ",
    " also ",
    ", then ",
]


def contains_multiple_actions(text: str) -> bool:
    """Detect if text contains multiple actions."""
    text_lower = text.lower()
    
    for keyword in MULTI_STEP_KEYWORDS:
        if keyword in text_lower:
            return True
    
    return False


def split_compound_input(text: str) -> List[str]:
    """Split compound input into individual actions."""
    text_lower = text.lower()
    
    # Try splitting by keywords
    for keyword in MULTI_STEP_KEYWORDS:
        if keyword in text_lower:
            parts = re.split(re.escape(keyword), text, flags=re.IGNORECASE)
            return [p.strip() for p in parts if p.strip()]
    
    return [text]


# =============================================================================
# SEARCH NORMALIZATION
# =============================================================================

SEARCH_COMMAND_WORDS = [
    "search for ",
    "search ",
    "find ",
    "look for ",
    "look up ",
    "google ",
    "bing ",
    "can you find ",
    "please search ",
    "i want to find ",
    "show me ",
]


def normalize_search_query(query: str) -> str:
    """
    Remove command words from search queries.
    
    "search github" → "github"
    "find youtube videos" → "youtube videos"
    """
    if not query:
        return query
    
    normalized = query.lower()
    
    for prefix in SEARCH_COMMAND_WORDS:
        if normalized.startswith(prefix):
            normalized = query[len(prefix):].strip()
            break
    
    return normalized or query


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Goal detection
    "is_high_level_goal",
    "detect_goal_type",
    
    # Goal expansion
    "expand_goal",
    "GoalExpansionResult",
    
    # Multi-step detection
    "contains_multiple_actions",
    "split_compound_input",
    
    # Search normalization
    "normalize_search_query",
    
    # Constants
    "GOAL_PATTERNS",
    "KEYWORD_TO_SITE",
    "SEARCH_COMMAND_WORDS",
]
