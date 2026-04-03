"""
Stage 3 — Intent Refiner Module.

Normalizes and fixes intents before execution:
- App name normalization
- Spelling correction
- Noise removal
- Query cleanup
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# APP NAME ALIASES AND CORRECTIONS
# =============================================================================

APP_ALIASES: Dict[str, str] = {
    # Browser aliases
    "chrom": "chrome",
    "crome": "chrome",
    "googlechrome": "chrome",
    "google": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "chromium": "chrome",
    
    "firefoz": "firefox",
    "firfox": "firefox",
    "mozilla": "firefox",
    "mozilla firefox": "firefox",
    
    "edge": "msedge",
    "microsoft edge": "msedge",
    "ms edge": "msedge",
    
    # Code editors
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "visualstudiocode": "code",
    "vsode": "code",
    "vscod": "code",
    
    "notepad++": "notepad++",
    "notepadpp": "notepad++",
    "npp": "notepad++",
    
    "sublim": "sublime",
    "sublimetext": "sublime",
    "sublime text": "sublime",
    
    # System apps
    "calulator": "calculator",
    "calc": "calculator",
    "calculater": "calculator",
    "calcuator": "calculator",
    
    "cmd": "terminal",
    "command prompt": "terminal",
    "command": "terminal",
    "powershell": "terminal",
    "ps": "terminal",
    "wt": "terminal",
    "windows terminal": "terminal",
    "konsole": "terminal",
    "gnome-terminal": "terminal",
    "xterm": "terminal",
    
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "finder": "explorer",
    "nautilus": "explorer",
    
    # Media
    "spotfy": "spotify",
    "sptofy": "spotify",
    
    "vlc media player": "vlc",
    "vlc player": "vlc",
    
    "youtube": "youtube",
    "yt": "youtube",
    
    # Communication
    "discrd": "discord",
    "dicord": "discord",
    
    "slck": "slack",
    "slak": "slack",
    
    "teams": "teams",
    "microsoft teams": "teams",
    "ms teams": "teams",
    
    "zom": "zoom",
    "zoon": "zoom",
    
    # Productivity
    "word": "winword",
    "microsoft word": "winword",
    "ms word": "winword",
    
    "excel": "excel",
    "microsoft excel": "excel",
    "ms excel": "excel",
    
    "powerpoint": "powerpnt",
    "ppt": "powerpnt",
    "microsoft powerpoint": "powerpnt",
    
    "outlook": "outlook",
    "microsoft outlook": "outlook",
    
    # Games
    "stean": "steam",
    "steaam": "steam",
}

# Common spelling corrections for general words
SPELLING_CORRECTIONS: Dict[str, str] = {
    "serch": "search",
    "searh": "search",
    "seach": "search",
    "srch": "search",
    
    "opne": "open",
    "oepn": "open",
    "oen": "open",
    
    "lanch": "launch",
    "launc": "launch",
    "lunche": "launch",
    
    "tpye": "type",
    "tyep": "type",
    "typw": "type",
    
    "youube": "youtube",
    "yotube": "youtube",
    "youtub": "youtube",
    "utube": "youtube",
}

# Noise patterns to remove
NOISE_PATTERNS = [
    r"^please\s+",
    r"^can you\s+",
    r"^could you\s+",
    r"^i want to\s+",
    r"^i need to\s+",
    r"\s+for me$",
    r"\s+please$",
    r"\s+now$",
    r"\s+quickly$",
]


# =============================================================================
# INTENT REFINER CLASS
# =============================================================================

class IntentRefiner:
    """
    Refines and normalizes intents before execution.
    
    Features:
    - App name normalization with fuzzy matching
    - Spelling correction
    - Noise word removal
    - Query cleanup
    """
    
    def __init__(self):
        self.app_aliases = APP_ALIASES.copy()
        self.spelling_corrections = SPELLING_CORRECTIONS.copy()
        self.noise_patterns = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]
    
    def refine(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refine intent data.
        
        Args:
            intent_data: Raw intent JSON from model
            
        Returns:
            Refined intent JSON
        """
        if not intent_data:
            return intent_data
        
        refined = intent_data.copy()
        intent_type = refined.get("intent", "")
        slots = refined.get("slots", {})
        
        print(f"\n========== [INTENT REFINER] ==========")
        print(f"[ORIGINAL INTENT] {intent_type}")
        print(f"[ORIGINAL SLOTS] {slots}")
        
        # Refine based on intent type
        if intent_type == "OPEN_APP":
            slots = self._refine_open_app(slots)
        elif intent_type == "SEARCH_WEB":
            slots = self._refine_search_web(slots)
        elif intent_type == "TYPE_TEXT":
            slots = self._refine_type_text(slots)
        elif intent_type == "OPEN_URL":
            slots = self._refine_open_url(slots)
        
        # Also refine normalized_text if present
        if "normalized_text" in refined:
            refined["normalized_text"] = self._clean_noise(refined["normalized_text"])
        
        refined["slots"] = slots
        refined["_refined"] = True
        
        print(f"[REFINED SLOTS] {slots}")
        logger.info(f"[REFINER] {intent_type}: {intent_data.get('slots')} → {slots}")
        
        return refined
    
    def _refine_open_app(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Refine OPEN_APP slots."""
        app = slots.get("app", "")
        if not app:
            return slots
        
        refined_slots = slots.copy()
        original_app = app
        
        # Normalize: lowercase, strip whitespace
        app = app.lower().strip()
        
        # Remove noise words
        app = self._clean_noise(app)
        
        # Check aliases
        if app in self.app_aliases:
            app = self.app_aliases[app]
            print(f"[APP ALIAS] {original_app} → {app}")
        else:
            # Try fuzzy matching for misspellings
            corrected = self._fuzzy_match_app(app)
            if corrected != app:
                print(f"[APP CORRECTION] {app} → {corrected}")
                app = corrected
        
        refined_slots["app"] = app
        refined_slots["_original_app"] = original_app
        
        return refined_slots
    
    def _refine_search_web(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Refine SEARCH_WEB slots."""
        query = slots.get("query", "")
        if not query:
            return slots
        
        refined_slots = slots.copy()
        original_query = query
        
        # Clean noise
        query = self._clean_noise(query)
        
        # Fix common spelling errors
        for wrong, correct in self.spelling_corrections.items():
            if wrong in query.lower():
                query = re.sub(re.escape(wrong), correct, query, flags=re.IGNORECASE)
        
        refined_slots["query"] = query.strip()
        refined_slots["_original_query"] = original_query
        
        return refined_slots
    
    def _refine_type_text(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Refine TYPE_TEXT slots."""
        text = slots.get("text", "")
        if not text:
            return slots
        
        refined_slots = slots.copy()
        
        # Don't modify the actual text content too much
        # Just normalize whitespace
        refined_slots["text"] = " ".join(text.split())
        
        return refined_slots
    
    def _refine_open_url(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Refine OPEN_URL slots."""
        url = slots.get("url", "")
        if not url:
            return slots
        
        refined_slots = slots.copy()
        
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Common URL fixes
        url = url.replace(" ", "")
        
        refined_slots["url"] = url
        
        return refined_slots
    
    def _clean_noise(self, text: str) -> str:
        """Remove noise patterns from text."""
        cleaned = text
        for pattern in self.noise_patterns:
            cleaned = pattern.sub("", cleaned)
        return cleaned.strip()
    
    def _fuzzy_match_app(self, app: str) -> str:
        """
        Try to fuzzy match app name against known aliases.
        
        Uses simple edit distance heuristics.
        """
        if len(app) < 3:
            return app
        
        best_match = app
        best_score = 0.0
        
        for alias, canonical in self.app_aliases.items():
            # Skip exact matches (already handled)
            if alias == app:
                return canonical
            
            # Calculate similarity score
            score = self._similarity(app, alias)
            
            if score > best_score and score >= 0.75:  # 75% threshold
                best_score = score
                best_match = canonical
        
        return best_match
    
    def _similarity(self, s1: str, s2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Uses simple character overlap ratio.
        """
        if not s1 or not s2:
            return 0.0
        
        # Character overlap
        set1 = set(s1.lower())
        set2 = set(s2.lower())
        overlap = len(set1 & set2)
        total = max(len(set1), len(set2))
        
        # Length penalty
        len_ratio = min(len(s1), len(s2)) / max(len(s1), len(s2))
        
        # Prefix bonus
        prefix_match = 0
        for i in range(min(len(s1), len(s2))):
            if s1[i].lower() == s2[i].lower():
                prefix_match += 1
            else:
                break
        prefix_bonus = prefix_match / max(len(s1), len(s2)) * 0.5
        
        return (overlap / total) * len_ratio + prefix_bonus
    
    def add_alias(self, alias: str, canonical: str):
        """Add a new app alias."""
        self.app_aliases[alias.lower()] = canonical.lower()
    
    def add_correction(self, wrong: str, correct: str):
        """Add a new spelling correction."""
        self.spelling_corrections[wrong.lower()] = correct.lower()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_refiner_instance: Optional[IntentRefiner] = None


def get_intent_refiner() -> IntentRefiner:
    """Get singleton IntentRefiner instance."""
    global _refiner_instance
    if _refiner_instance is None:
        _refiner_instance = IntentRefiner()
    return _refiner_instance


def refine_intent(intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to refine an intent.
    
    Args:
        intent_data: Raw intent JSON
        
    Returns:
        Refined intent JSON
    """
    return get_intent_refiner().refine(intent_data)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "IntentRefiner",
    "get_intent_refiner",
    "refine_intent",
    "APP_ALIASES",
    "SPELLING_CORRECTIONS",
]
