"""Gesture recognizer - recognizes drawn gestures."""

import math
from typing import List, Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


class GestureRecognizer:
    """Recognizes drawn gestures from touch coordinates."""

    def __init__(self):
        """Initialize recognizer."""
        self.strokes = []

    def recognize(self, strokes: List[dict]) -> str:
        """Recognize drawn gesture.
        
        Args:
            strokes: List of stroke data with points
            
        Returns:
            Gesture name (e.g., 'scroll_up', 'circle')
        """
        if not strokes:
            return "unknown"

        # For MVP Phase 0: simple direction detection
        # Get overall direction based on start and end points
        gesture = self._detect_simple_gesture(strokes)
        logger.debug(f"Recognized gesture: {gesture}")
        return gesture

    def _detect_simple_gesture(self, strokes: List[dict]) -> str:
        """Detect gesture based on overall direction.
        
        Args:
            strokes: Stroke data
            
        Returns:
            Gesture name
        """
        if not strokes:
            return "unknown"

        # Get first and last points
        first_stroke = strokes[0]
        last_stroke = strokes[-1]

        if not first_stroke.get("points") or not last_stroke.get("points"):
            return "unknown"

        start_point = first_stroke["points"][0]
        end_point = last_stroke["points"][-1]

        start_x = start_point.get("x", 0)
        start_y = start_point.get("y", 0)
        end_x = end_point.get("x", 0)
        end_y = end_point.get("y", 0)

        # Calculate delta
        dx = end_x - start_x
        dy = end_y - start_y

        # Determine direction
        if abs(dy) > abs(dx):
            # Vertical motion
            if dy < -30:  # Threshold: 30 pixels upward
                return "scroll_up"
            elif dy > 30:  # Threshold: 30 pixels downward
                return "scroll_down"
        else:
            # Horizontal motion
            if dx < -30:  # Leftward
                return "go_back"
            elif dx > 30:  # Rightward
                return "go_forward"

        return "unknown"
