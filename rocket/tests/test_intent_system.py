"""
Stage 5 — Intent System Tests.

Tests for expanded 38-intent system covering:
- App control intents
- Browser control intents
- Input control intents
- System control intents
- File system intents
- UI/Vision intents
- Advanced intents
"""

import pytest
from typing import Dict, Any


# =============================================================================
# INTENT SYSTEM TESTS
# =============================================================================

class TestIntentSystem:
    """Tests for the intent system module."""
    
    def test_all_intents_count(self):
        """Verify we have 38 intents total."""
        from agent.core.intent_system import VALID_INTENTS
        
        # 6 + 8 + 7 + 6 + 5 + 3 + 3 = 38
        assert len(VALID_INTENTS) == 38
    
    def test_app_control_intents(self):
        """Verify app control intents."""
        from agent.core.intent_system import APP_CONTROL_INTENTS
        
        expected = {"OPEN_APP", "CLOSE_APP", "MINIMIZE_APP", "MAXIMIZE_APP", "SWITCH_APP", "FOCUS_WINDOW"}
        assert APP_CONTROL_INTENTS == expected
        assert len(APP_CONTROL_INTENTS) == 6
    
    def test_browser_control_intents(self):
        """Verify browser control intents."""
        from agent.core.intent_system import BROWSER_CONTROL_INTENTS
        
        expected = {"OPEN_URL", "SEARCH_WEB", "NEW_TAB", "CLOSE_TAB", "SWITCH_TAB", "REFRESH_PAGE", "SCROLL_UP", "SCROLL_DOWN"}
        assert BROWSER_CONTROL_INTENTS == expected
        assert len(BROWSER_CONTROL_INTENTS) == 8
    
    def test_input_control_intents(self):
        """Verify input control intents."""
        from agent.core.intent_system import INPUT_CONTROL_INTENTS
        
        expected = {"TYPE_TEXT", "CLEAR_TEXT", "SELECT_TEXT", "COPY", "PASTE", "CUT", "PRESS_KEYS"}
        assert INPUT_CONTROL_INTENTS == expected
        assert len(INPUT_CONTROL_INTENTS) == 7
    
    def test_system_control_intents(self):
        """Verify system control intents."""
        from agent.core.intent_system import SYSTEM_CONTROL_INTENTS
        
        expected = {"LOCK_SCREEN", "VOLUME_UP", "VOLUME_DOWN", "MUTE", "BRIGHTNESS_UP", "BRIGHTNESS_DOWN"}
        assert SYSTEM_CONTROL_INTENTS == expected
        assert len(SYSTEM_CONTROL_INTENTS) == 6
    
    def test_file_system_intents(self):
        """Verify file system intents."""
        from agent.core.intent_system import FILE_SYSTEM_INTENTS
        
        expected = {"OPEN_FILE", "DELETE_FILE", "CREATE_FILE", "MOVE_FILE", "RENAME_FILE"}
        assert FILE_SYSTEM_INTENTS == expected
        assert len(FILE_SYSTEM_INTENTS) == 5
    
    def test_ui_vision_intents(self):
        """Verify UI/vision intents."""
        from agent.core.intent_system import UI_VISION_INTENTS
        
        expected = {"CLICK_ELEMENT", "SCROLL", "WAIT"}
        assert UI_VISION_INTENTS == expected
        assert len(UI_VISION_INTENTS) == 3
    
    def test_advanced_intents(self):
        """Verify advanced intents."""
        from agent.core.intent_system import ADVANCED_INTENTS
        
        expected = {"MULTI_STEP", "CONDITIONAL", "UNKNOWN"}
        assert ADVANCED_INTENTS == expected
        assert len(ADVANCED_INTENTS) == 3
    
    def test_is_valid_intent_returns_true_for_valid(self):
        """Valid intents should return True."""
        from agent.core.intent_system import is_valid_intent
        
        valid_intents = ["OPEN_APP", "SEARCH_WEB", "CLICK_ELEMENT", "VOLUME_UP"]
        for intent in valid_intents:
            assert is_valid_intent(intent) is True
    
    def test_is_valid_intent_returns_false_for_invalid(self):
        """Invalid intents should return False."""
        from agent.core.intent_system import is_valid_intent
        
        invalid_intents = ["INVALID", "OPEN", "HACK_SYSTEM", ""]
        for intent in invalid_intents:
            assert is_valid_intent(intent) is False
    
    def test_is_dangerous_intent(self):
        """Test dangerous intent detection."""
        from agent.core.intent_system import is_dangerous_intent
        
        assert is_dangerous_intent("DELETE_FILE") is True
        assert is_dangerous_intent("LOCK_SCREEN") is True
        assert is_dangerous_intent("OPEN_APP") is False
        assert is_dangerous_intent("SEARCH_WEB") is False
    
    def test_is_system_intent(self):
        """Test system intent detection."""
        from agent.core.intent_system import is_system_intent
        
        assert is_system_intent("VOLUME_UP") is True
        assert is_system_intent("MUTE") is True
        assert is_system_intent("BRIGHTNESS_DOWN") is True
        assert is_system_intent("OPEN_APP") is False
    
    def test_validate_slots_open_app(self):
        """OPEN_APP requires 'app' slot."""
        from agent.core.intent_system import validate_slots
        
        valid, missing = validate_slots("OPEN_APP", {"app": "chrome"})
        assert valid is True
        assert missing == []
        
        valid, missing = validate_slots("OPEN_APP", {})
        assert valid is False
        assert "app" in missing
    
    def test_validate_slots_search_web(self):
        """SEARCH_WEB requires 'query' slot."""
        from agent.core.intent_system import validate_slots
        
        valid, missing = validate_slots("SEARCH_WEB", {"query": "test"})
        assert valid is True
        
        valid, missing = validate_slots("SEARCH_WEB", {})
        assert valid is False
        assert "query" in missing
    
    def test_validate_slots_click_element(self):
        """CLICK_ELEMENT requires 'target' slot."""
        from agent.core.intent_system import validate_slots
        
        valid, missing = validate_slots("CLICK_ELEMENT", {"target": "play button"})
        assert valid is True
        
        valid, missing = validate_slots("CLICK_ELEMENT", {})
        assert valid is False
        assert "target" in missing
    
    def test_validate_slots_no_required(self):
        """Intents without required slots should pass."""
        from agent.core.intent_system import validate_slots
        
        valid, missing = validate_slots("VOLUME_UP", {})
        assert valid is True
        assert missing == []
        
        valid, missing = validate_slots("NEW_TAB", {})
        assert valid is True
    
    def test_get_intent_info(self):
        """Test intent info retrieval."""
        from agent.core.intent_system import get_intent_info
        
        info = get_intent_info("OPEN_APP")
        assert info["valid"] is True
        assert info["intent"] == "OPEN_APP"
        assert "app" in info["required_slots"]
        assert info["is_dangerous"] is False
    
    def test_get_intent_info_invalid(self):
        """Test invalid intent info retrieval."""
        from agent.core.intent_system import get_intent_info
        
        info = get_intent_info("INVALID_INTENT")
        assert info["valid"] is False
    
    def test_suggest_intent_open_keywords(self):
        """Test intent suggestion for open commands."""
        from agent.core.intent_system import suggest_intent
        
        suggestions = suggest_intent("open chrome")
        assert "OPEN_APP" in suggestions
    
    def test_suggest_intent_search_keywords(self):
        """Test intent suggestion for search commands."""
        from agent.core.intent_system import suggest_intent
        
        suggestions = suggest_intent("search for python tutorials")
        assert "SEARCH_WEB" in suggestions
    
    def test_suggest_intent_click_keywords(self):
        """Test intent suggestion for click commands."""
        from agent.core.intent_system import suggest_intent
        
        suggestions = suggest_intent("click on the button")
        assert "CLICK_ELEMENT" in suggestions
    
    def test_suggest_intent_multi_step(self):
        """Test intent suggestion for multi-step commands."""
        from agent.core.intent_system import suggest_intent
        
        suggestions = suggest_intent("open chrome and then search youtube")
        assert "MULTI_STEP" in suggestions


class TestIntentCategoryMapping:
    """Tests for intent category mapping."""
    
    def test_get_intent_category_app_control(self):
        """Test app control category."""
        from agent.core.intent_system import get_intent_category, IntentCategory
        
        assert get_intent_category("OPEN_APP") == IntentCategory.APP_CONTROL
        assert get_intent_category("CLOSE_APP") == IntentCategory.APP_CONTROL
    
    def test_get_intent_category_browser(self):
        """Test browser category."""
        from agent.core.intent_system import get_intent_category, IntentCategory
        
        assert get_intent_category("SEARCH_WEB") == IntentCategory.BROWSER_CONTROL
        assert get_intent_category("NEW_TAB") == IntentCategory.BROWSER_CONTROL
    
    def test_get_intent_category_ui_vision(self):
        """Test UI/vision category."""
        from agent.core.intent_system import get_intent_category, IntentCategory
        
        assert get_intent_category("CLICK_ELEMENT") == IntentCategory.UI_VISION
        assert get_intent_category("WAIT") == IntentCategory.UI_VISION
    
    def test_get_intent_category_invalid(self):
        """Invalid intent should return None."""
        from agent.core.intent_system import get_intent_category
        
        assert get_intent_category("INVALID") is None
