"""NLU Parser - parses voice text into intents."""

import re
from typing import Optional

from agent.core.context import ExecutionContext
from agent.core.exceptions import AmbiguousIntentError
from agent.core.intent import Intent
from agent.nlu.gesture_recognizer import GestureRecognizer
from agent.utils.logger import get_logger


logger = get_logger(__name__)


class NLUEngine:
    """Natural Language Understanding for intent parsing."""

    def __init__(self, platform):
        """Initialize NLU engine.
        
        Args:
            platform: Platform adapter (for context)
        """
        self.platform = platform
        self.gesture_recognizer = GestureRecognizer()
        self._init_patterns()

    def _init_patterns(self) -> None:
        """Initialize intent patterns."""
        # Patterns: action -> list of regex patterns
        self.patterns = {
            "OPEN_APP": [
                r"^(?:open|launch|start)\s+(\w+)$",
            ],
            "TYPE_TEXT": [
                r"^(?:type|write|input)\s+(.+)$",
            ],
            "PRESS_KEYS": [
                r"^(?:press|hit|do|execute)\s+(.+)$",
            ],
            "OPEN_URL": [
                r"^(?:go\s+to|open|visit)\s+([a-zA-Z0-9\.\-]+(?:\.[a-zA-Z]{2,})?)$",
            ],
            "SCROLL": [
                r"^scroll\s+(up|down|left|right)(?:\s+(\d+))?$",
            ],
        }

    def parse(
        self, text: str, context: Optional[ExecutionContext] = None
    ) -> Intent:
        """Parse voice text into intent.
        
        Args:
            text: Transcribed voice text
            context: Execution context for disambiguation
            
        Returns:
            Parsed intent
        """
        text = text.lower().strip()
        logger.debug(f"Parsing: '{text}'")

        # Try to match against registered patterns
        for action, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.match(pattern, text)
                if match:
                    parameters = self._extract_parameters(action, match, text)
                    intent = Intent(
                        action=action,
                        parameters=parameters,
                        confidence=0.95,  # Rule-based match
                        context=context,
                    )
                    logger.info(f"Matched intent: {intent}")
                    return intent

        # If no match, return ambiguous/clarification intent
        logger.warning(f"No intent match for: '{text}'")
        return Intent(
            action="CLARIFY",
            parameters={"text": text},
            confidence=0.3,
        )

    def recognize_gesture(self, strokes: list) -> Intent:
        """Recognize drawn gesture into intent.
        
        Args:
            strokes: List of stroke data
            
        Returns:
            Intent for gesture
        """
        gesture = self.gesture_recognizer.recognize(strokes)
        logger.info(f"Recognized gesture: {gesture}")

        gesture_to_action = {
            "scroll_up": "SCROLL",
            "scroll_down": "SCROLL",
            "scroll_left": "SCROLL",
            "scroll_right": "SCROLL",
            "go_back": "NAVIGATE",
            "go_forward": "NAVIGATE",
            "select_all": "SELECT_TEXT",
            "undo": "PRESS_KEYS",
            "redo": "PRESS_KEYS",
        }

        action = gesture_to_action.get(gesture, "UNKNOWN_GESTURE")
        parameters = self._gesture_parameters(gesture)

        return Intent(
            action=action,
            parameters=parameters,
            confidence=0.85,
        )

    def _extract_parameters(self, action: str, match, text: str) -> dict:
        """Extract parameters from matched pattern.
        
        Args:
            action: Action name
            match: Regex match object
            text: Original text
            
        Returns:
            Parameters dict
        """
        groups = match.groups()

        if action == "OPEN_APP":
            return {"app": groups[0]}
        elif action == "TYPE_TEXT":
            return {"text": groups[0]}
        elif action == "PRESS_KEYS":
            # Parse key combination
            keys_str = groups[0].lower()
            keys = [k.strip() for k in keys_str.split("+")]
            return {"keys": keys}
        elif action == "OPEN_URL":
            url = groups[0]
            # Add protocol if missing
            if not url.startswith("http"):
                url = "https://" + url
            return {"url": url}
        elif action == "SCROLL":
            direction = groups[0]
            amount = int(groups[1]) if len(groups) > 1 and groups[1] else 3
            return {"direction": direction, "amount": amount}

        return {}

    def _gesture_parameters(self, gesture: str) -> dict:
        """Generate parameters for gesture-based intent.
        
        Args:
            gesture: Gesture name
            
        Returns:
            Parameters dict
        """
        if gesture.startswith("scroll_"):
            direction = gesture.split("_")[1]
            return {"direction": direction, "amount": 3}
        elif gesture in ("undo", "redo"):
            key = "ctrl+z" if gesture == "undo" else "ctrl+y"
            return {"keys": key.split("+")}

        return {"gesture": gesture}
