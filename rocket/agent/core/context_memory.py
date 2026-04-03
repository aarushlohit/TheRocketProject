"""
Stage 3 — Context Memory Module.

Stores execution context for session awareness:
- Last app opened
- Last query
- Last action
- Session history
- User preferences
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CONTEXT ENTRY
# =============================================================================

@dataclass
class ContextEntry:
    """A single context memory entry."""
    
    timestamp: datetime
    action_type: str  # Intent type executed
    action_data: Dict[str, Any]  # Slots and parameters
    result: str  # success, failed, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type,
            "action_data": self.action_data,
            "result": self.result,
            "metadata": self.metadata,
        }


# =============================================================================
# CONTEXT MEMORY CLASS
# =============================================================================

class ContextMemory:
    """
    Session context memory for intelligent execution.
    
    Features:
    - Thread-safe operation
    - Limited history (sliding window)
    - Quick access to last actions
    - App state tracking
    - User preference learning
    
    Use Cases:
    - "search youtube" → reuse last opened browser
    - "type hello" → use last focused app
    - Track user preferences (preferred browser, etc.)
    """
    
    MAX_HISTORY = 50
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Current state
        self.last_app_opened: Optional[str] = None
        self.last_browser_opened: Optional[str] = None
        self.last_query: Optional[str] = None
        self.last_url: Optional[str] = None
        self.last_text_typed: Optional[str] = None
        self.last_intent: Optional[str] = None
        
        # History
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        
        # Session metadata
        self.session_start: datetime = datetime.now()
        self.action_count: int = 0
        
        # User preferences (learned over time)
        self.preferred_browser: Optional[str] = None
        self.app_frequencies: Dict[str, int] = {}
        
        # Current execution context
        self.current_plan_id: Optional[str] = None
        self.current_step_index: int = 0
        
        print(f"[CONTEXT MEMORY] Initialized at {self.session_start}")
    
    def record_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Record an executed action.
        
        Args:
            action_type: Intent type (OPEN_APP, SEARCH_WEB, etc.)
            action_data: Slots/parameters
            result: Execution result (success, failed)
            metadata: Additional metadata
        """
        with self._lock:
            entry = ContextEntry(
                timestamp=datetime.now(),
                action_type=action_type,
                action_data=action_data,
                result=result,
                metadata=metadata or {},
            )
            
            self._history.append(entry)
            self.action_count += 1
            self.last_intent = action_type
            
            # Update state based on action type
            self._update_state(action_type, action_data, result)
            
            print(f"\n========== [CONTEXT MEMORY UPDATE] ==========")
            print(f"[ACTION] {action_type}")
            print(f"[DATA] {action_data}")
            print(f"[RESULT] {result}")
            print(f"[TOTAL ACTIONS] {self.action_count}")
            
            logger.debug(f"[CONTEXT] Recorded: {action_type} ({result})")
    
    def _update_state(self, action_type: str, data: Dict[str, Any], result: str):
        """Update internal state based on action."""
        if result != "success":
            return  # Only update state for successful actions
        
        if action_type == "OPEN_APP":
            app = data.get("app", "")
            self.last_app_opened = app
            
            # Track browser specifically
            browsers = ["chrome", "firefox", "edge", "safari", "brave", "opera"]
            if any(b in app.lower() for b in browsers):
                self.last_browser_opened = app
                self.preferred_browser = app
            
            # Track app frequency
            self.app_frequencies[app] = self.app_frequencies.get(app, 0) + 1
        
        elif action_type == "SEARCH_WEB":
            self.last_query = data.get("query", "")
        
        elif action_type == "OPEN_URL":
            self.last_url = data.get("url", "")
        
        elif action_type == "TYPE_TEXT":
            self.last_text_typed = data.get("text", "")
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get current context for execution.
        
        Returns dict with:
        - last_app: Last opened app
        - last_browser: Last opened browser
        - last_query: Last search query
        - preferred_browser: User's preferred browser
        - recent_history: Last 5 actions
        """
        with self._lock:
            recent = list(self._history)[-5:]
            
            return {
                "last_app": self.last_app_opened,
                "last_browser": self.last_browser_opened,
                "last_query": self.last_query,
                "last_url": self.last_url,
                "last_text": self.last_text_typed,
                "last_intent": self.last_intent,
                "preferred_browser": self.preferred_browser or "chrome",
                "session_duration": (datetime.now() - self.session_start).total_seconds(),
                "action_count": self.action_count,
                "recent_history": [e.to_dict() for e in recent],
            }
    
    def get_last_action(self) -> Optional[ContextEntry]:
        """Get the most recent action."""
        with self._lock:
            return self._history[-1] if self._history else None
    
    def get_last_successful_app(self) -> Optional[str]:
        """Get the last successfully opened app."""
        with self._lock:
            for entry in reversed(self._history):
                if entry.action_type == "OPEN_APP" and entry.result == "success":
                    return entry.action_data.get("app")
            return None
    
    def get_last_browser(self) -> Optional[str]:
        """Get the last opened browser (for SEARCH_WEB context)."""
        with self._lock:
            return self.last_browser_opened or self.preferred_browser or "chrome"
    
    def get_most_used_apps(self, limit: int = 5) -> List[tuple]:
        """Get most frequently used apps."""
        with self._lock:
            sorted_apps = sorted(
                self.app_frequencies.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            return sorted_apps[:limit]
    
    def clear_session(self):
        """Clear session context (for new session)."""
        with self._lock:
            self._history.clear()
            self.last_app_opened = None
            self.last_browser_opened = None
            self.last_query = None
            self.last_url = None
            self.last_text_typed = None
            self.last_intent = None
            self.session_start = datetime.now()
            self.action_count = 0
            # Keep preferences
            
            print("[CONTEXT MEMORY] Session cleared")
    
    def should_reuse_browser(self, intent_type: str) -> bool:
        """
        Determine if we should reuse last browser for this intent.
        
        Returns True if:
        - Intent is SEARCH_WEB
        - A browser was recently opened
        - Within reasonable time window
        """
        if intent_type != "SEARCH_WEB":
            return False
        
        with self._lock:
            if not self.last_browser_opened:
                return False
            
            # Check if browser was opened recently
            for entry in reversed(self._history):
                if entry.action_type == "OPEN_APP":
                    time_diff = (datetime.now() - entry.timestamp).total_seconds()
                    # If browser was opened within last 30 seconds, reuse it
                    if time_diff < 30:
                        return True
                    break
            
            return False
    
    def enrich_intent(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich intent with context information.
        
        For example:
        - SEARCH_WEB without browser → add last browser context
        - TYPE_TEXT without target → use last focused app
        """
        enriched = intent_data.copy()
        intent_type = enriched.get("intent", "")
        
        with self._lock:
            # Add context metadata
            enriched["_context"] = {
                "last_app": self.last_app_opened,
                "last_browser": self.last_browser_opened,
                "action_count": self.action_count,
            }
            
            # Specific enrichments
            if intent_type == "SEARCH_WEB":
                if self.should_reuse_browser(intent_type):
                    enriched["_context"]["reuse_browser"] = True
                    enriched["_context"]["target_browser"] = self.last_browser_opened
            
            elif intent_type == "TYPE_TEXT":
                if self.last_app_opened:
                    enriched["_context"]["target_app"] = self.last_app_opened
        
        return enriched


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_context_memory_instance: Optional[ContextMemory] = None
_context_lock = threading.Lock()


def get_context_memory() -> ContextMemory:
    """Get singleton ContextMemory instance."""
    global _context_memory_instance
    
    with _context_lock:
        if _context_memory_instance is None:
            _context_memory_instance = ContextMemory()
        return _context_memory_instance


def reset_context_memory():
    """Reset the context memory singleton."""
    global _context_memory_instance
    
    with _context_lock:
        if _context_memory_instance:
            _context_memory_instance.clear_session()
        _context_memory_instance = None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ContextEntry",
    "ContextMemory",
    "get_context_memory",
    "reset_context_memory",
]
