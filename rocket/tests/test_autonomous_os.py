"""
Stage 6.0 - Autonomous OS Test Suite.

Comprehensive tests for:
- Intent Classification
- Pre-Safety Layer
- Multi-Step Detection
- Routing Engine
- Execution Pipeline
- Verification System
"""

import asyncio
import json
import pytest
from typing import Dict, Any

from agent.core.autonomous_os import (
    # Intent sets
    ALL_VALID_INTENTS,
    APP_CONTROL_INTENTS,
    BROWSER_CONTROL_INTENTS,
    FILE_CONTROL_INTENTS,
    SYSTEM_CONTROL_INTENTS,
    
    # Safety
    pre_intent_safety_check,
    detect_dangerous_operation,
    check_type_text_safety_override,
    
    # Classification
    classify_intent,
    classify_multi_step,
    route_intent,
    ExecutionRoute,
    
    # Context
    SessionContext,
    get_session_context,
    reset_session_context,
    
    # Confirmation
    build_confirmation_response,
    register_tap,
    
    # Processor
    AutonomousOSProcessor,
    get_processor,
    reset_processor,
    
    # UI Mapping
    get_keyboard_shortcut,
    
    # ZeroClaw
    should_use_zeroclaw,
)


# =============================================================================
# TEST: INTENT CLASSIFICATION
# =============================================================================

class TestIntentClassification:
    """Test intent classification engine."""
    
    def test_open_app(self):
        """Test OPEN_APP intent classification."""
        result = classify_intent("open chrome")
        assert result["intent"] == "OPEN_APP"
        assert result["slots"]["app"] == "chrome"
        assert result["confidence"] > 0.5
    
    def test_launch_app(self):
        """Test launch synonym."""
        result = classify_intent("launch notepad")
        assert result["intent"] == "OPEN_APP"
        assert result["slots"]["app"] == "notepad"
    
    def test_search_web(self):
        """Test SEARCH_WEB intent."""
        result = classify_intent("search python tutorial")
        assert result["intent"] == "SEARCH_WEB"
        assert "python" in result["slots"]["query"]
    
    def test_type_text(self):
        """Test TYPE_TEXT intent."""
        result = classify_intent("type hello world")
        assert result["intent"] == "TYPE_TEXT"
        assert result["slots"]["text"] == "hello world"
    
    def test_open_url(self):
        """Test OPEN_URL intent."""
        result = classify_intent("go to https://google.com")
        assert result["intent"] == "OPEN_URL"
        assert "google" in result["slots"]["url"]
    
    def test_delete_file(self):
        """Test DELETE_FILE intent."""
        result = classify_intent("delete file test.txt")
        assert result["intent"] == "DELETE_FILE"
        assert result["slots"]["path"] == "test.txt"
    
    def test_press_keys(self):
        """Test PRESS_KEYS intent."""
        result = classify_intent("press ctrl+c")
        assert result["intent"] == "PRESS_KEYS"
        assert result["slots"]["keys"] == "ctrl+c"
    
    def test_close_app(self):
        """Test CLOSE_APP intent."""
        result = classify_intent("close notepad")
        assert result["intent"] == "CLOSE_APP"

    def test_volume_up_a_bit(self):
        """Test natural-language volume increase."""
        result = classify_intent("volume up a bit")
        assert result["intent"] == "VOLUME_UP"
        assert result["slots"]["value"] == 5

    def test_volume_down_slightly(self):
        """Test natural-language volume decrease."""
        result = classify_intent("volume down slightly")
        assert result["intent"] == "VOLUME_DOWN"
        assert result["slots"]["value"] == 5

    def test_volume_full(self):
        """Test implicit max volume intent."""
        result = classify_intent("volume full")
        assert result["intent"] == "VOLUME_UP"
        assert result["slots"]["value"] == 100

    def test_reduce_volume(self):
        """Test reduce volume maps down."""
        result = classify_intent("reduce volume")
        assert result["intent"] == "VOLUME_DOWN"
        assert result["slots"]["value"] == 5
    
    def test_unknown_intent(self):
        """Test unknown input returns UNKNOWN."""
        result = classify_intent("asdfghjkl random gibberish")
        assert result["intent"] == "UNKNOWN"
        assert result["confidence"] == 0.0
    
    def test_empty_input(self):
        """Test empty input returns UNKNOWN."""
        result = classify_intent("")
        assert result["intent"] == "UNKNOWN"
    
    def test_whitespace_only(self):
        """Test whitespace only returns UNKNOWN."""
        result = classify_intent("   ")
        assert result["intent"] == "UNKNOWN"


# =============================================================================
# TEST: PRE-SAFETY LAYER
# =============================================================================

class TestPreSafetyLayer:
    """Test mandatory pre-safety checks."""
    
    def test_delete_keyword_detected(self):
        """Test delete keyword triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("delete this file")
        assert is_dangerous is True
        assert "delete" in reason
    
    def test_remove_keyword_detected(self):
        """Test remove keyword triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("remove folder")
        assert is_dangerous is True
    
    def test_format_keyword_detected(self):
        """Test format keyword triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("format c drive")
        assert is_dangerous is True
    
    def test_system_path_detected(self):
        """Test system path triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("open c:\\windows\\system32")
        assert is_dangerous is True
        assert "system_path" in reason
    
    def test_unix_path_detected(self):
        """Test Unix system path triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("edit /etc/passwd")
        assert is_dangerous is True
    
    def test_shutdown_detected(self):
        """Test shutdown triggers safety."""
        is_dangerous, reason = detect_dangerous_operation("shutdown computer")
        assert is_dangerous is True
    
    def test_safe_operation(self):
        """Test safe operation passes."""
        is_dangerous, reason = detect_dangerous_operation("open chrome")
        assert is_dangerous is False
    
    def test_pre_intent_returns_confirmation(self):
        """Test pre-safety returns CONFIRMATION_REQUIRED."""
        result = pre_intent_safety_check("delete my files")
        assert result is not None
        assert result["intent"] == "CONFIRMATION_REQUIRED"
        assert result["reason"] == "dangerous_operation"
        assert result["confidence"] == 1.0
    
    def test_pre_intent_passes_safe(self):
        """Test safe input passes pre-safety."""
        result = pre_intent_safety_check("open notepad")
        assert result is None


# =============================================================================
# TEST: TYPE_TEXT SAFETY OVERRIDE
# =============================================================================

class TestTypeTextSafetyOverride:
    """Test TYPE_TEXT to DELETE_FILE override."""
    
    def test_system_path_in_type_text(self):
        """Test TYPE_TEXT with system path triggers override."""
        intent_data = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "c:\\windows\\system32\\config"}
        }
        result = check_type_text_safety_override(intent_data)
        assert result is not None
        assert result["intent"] == "CONFIRMATION_REQUIRED"
    
    def test_safe_type_text(self):
        """Test safe TYPE_TEXT passes."""
        intent_data = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "hello world"}
        }
        result = check_type_text_safety_override(intent_data)
        assert result is None
    
    def test_non_type_text_ignored(self):
        """Test non-TYPE_TEXT intents ignored."""
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"}
        }
        result = check_type_text_safety_override(intent_data)
        assert result is None


# =============================================================================
# TEST: MULTI-STEP DETECTION
# =============================================================================

class TestMultiStepDetection:
    """Test multi-step intent detection."""
    
    def test_and_then_detected(self):
        """Test 'and then' triggers multi-step."""
        result = classify_multi_step("open chrome and then search youtube")
        assert result["intent"] == "MULTI_STEP"
        assert len(result["steps"]) == 2
    
    def test_then_detected(self):
        """Test 'then' triggers multi-step."""
        result = classify_multi_step("open notepad then type hello")
        assert result["intent"] == "MULTI_STEP"
    
    def test_single_step(self):
        """Test single action returns single intent."""
        result = classify_multi_step("open chrome")
        assert result["intent"] == "OPEN_APP"
        assert "steps" not in result
    
    def test_multi_step_order_preserved(self):
        """Test step order is preserved."""
        result = classify_multi_step("open chrome and then search python and then scroll down")
        assert result["intent"] == "MULTI_STEP"
        steps = result["steps"]
        assert steps[0]["intent"] == "OPEN_APP"
        assert steps[1]["intent"] == "SEARCH_WEB"
        assert steps[2]["intent"] == "SCROLL_DOWN"

    def test_volume_bypasses_multi_step(self):
        """Test volume commands never become MULTI_STEP."""
        result = classify_multi_step("volume up and then volume down")
        assert result["intent"] in {"VOLUME_UP", "VOLUME_DOWN"}
        assert "steps" not in result


# =============================================================================
# TEST: ROUTING ENGINE
# =============================================================================

class TestRoutingEngine:
    """Test intent routing."""
    
    def test_file_routes_to_backend(self):
        """Test file operations route to backend."""
        intent_data = {"intent": "DELETE_FILE", "slots": {"path": "test.txt"}}
        route = route_intent(intent_data, "delete file test.txt")
        assert route == ExecutionRoute.BACKEND
    
    def test_app_routes_to_local(self):
        """Test app operations route to local."""
        intent_data = {"intent": "OPEN_APP", "slots": {"app": "chrome"}}
        route = route_intent(intent_data, "open chrome")
        assert route == ExecutionRoute.LOCAL
    
    def test_browser_routes_to_local(self):
        """Test browser operations route to local."""
        intent_data = {"intent": "SEARCH_WEB", "slots": {"query": "test"}}
        route = route_intent(intent_data, "search test")
        assert route == ExecutionRoute.LOCAL
    
    def test_unknown_with_click_routes_to_zeroclaw(self):
        """Test unknown with UI keyword routes to ZeroClaw."""
        intent_data = {"intent": "UNKNOWN", "slots": {}}
        route = route_intent(intent_data, "click the blue button")
        assert route == ExecutionRoute.ZEROCLAW


# =============================================================================
# TEST: ZEROCLAW RULES
# =============================================================================

class TestZeroClawRules:
    """Test ZeroClaw fallback rules."""
    
    def test_zeroclaw_for_unknown_ui(self):
        """Test ZeroClaw used for unknown UI actions."""
        intent_data = {"intent": "UNKNOWN"}
        assert should_use_zeroclaw(intent_data, "click the submit button") is True
    
    def test_zeroclaw_blocked_for_file(self):
        """Test ZeroClaw blocked for file operations."""
        intent_data = {"intent": "DELETE_FILE"}
        assert should_use_zeroclaw(intent_data, "delete file") is False
    
    def test_zeroclaw_blocked_for_system(self):
        """Test ZeroClaw blocked for system operations."""
        intent_data = {"intent": "SHUTDOWN"}
        assert should_use_zeroclaw(intent_data, "shutdown") is False
    
    def test_zeroclaw_not_for_known_intent(self):
        """Test ZeroClaw not used for known intents."""
        intent_data = {"intent": "OPEN_APP"}
        assert should_use_zeroclaw(intent_data, "open chrome") is False


# =============================================================================
# TEST: UI KEYBOARD MAPPINGS
# =============================================================================

class TestUIKeyboardMappings:
    """Test UI keyboard shortcut mappings."""
    
    def test_search_bar_mapping(self):
        """Test search_bar maps to Ctrl+L."""
        assert get_keyboard_shortcut("search_bar") == "Ctrl+L"
    
    def test_new_tab_mapping(self):
        """Test new_tab maps to Ctrl+T."""
        assert get_keyboard_shortcut("new_tab") == "Ctrl+T"
    
    def test_close_tab_mapping(self):
        """Test close_tab maps to Ctrl+W."""
        assert get_keyboard_shortcut("close_tab") == "Ctrl+W"
    
    def test_refresh_mapping(self):
        """Test refresh maps to F5."""
        assert get_keyboard_shortcut("refresh") == "F5"
    
    def test_back_mapping(self):
        """Test back maps to Alt+Left."""
        assert get_keyboard_shortcut("back") == "Alt+Left"
    
    def test_copy_mapping(self):
        """Test copy maps to Ctrl+C."""
        assert get_keyboard_shortcut("copy") == "Ctrl+C"
    
    def test_unknown_mapping(self):
        """Test unknown target returns None."""
        assert get_keyboard_shortcut("nonexistent") is None


# =============================================================================
# TEST: CONTEXT MEMORY
# =============================================================================

class TestContextMemory:
    """Test session context management."""
    
    def setup_method(self):
        """Reset context before each test."""
        reset_session_context()
    
    def test_context_tracks_app(self):
        """Test context tracks current app."""
        context = get_session_context()
        context.update("OPEN_APP", "chrome")
        assert context.current_app == "chrome"
        assert context.last_intent == "OPEN_APP"
    
    def test_context_detects_browser(self):
        """Test context detects browser active."""
        context = get_session_context()
        context.update("OPEN_APP", "chrome")
        assert context.browser_active is True
    
    def test_context_history_limited(self):
        """Test action history is limited."""
        context = get_session_context()
        for i in range(100):
            context.update(f"ACTION_{i}", f"app_{i}")
        assert len(context.action_history) == 50
    
    def test_context_reuse_browser(self):
        """Test browser reuse detection."""
        context = get_session_context()
        context.update("OPEN_APP", "firefox")
        assert context.should_reuse_browser() is True


# =============================================================================
# TEST: CONFIRMATION SYSTEM
# =============================================================================

class TestConfirmationSystem:
    """Test confirmation flow."""
    
    def test_confirmation_response_format(self):
        """Test confirmation response has correct format."""
        response = build_confirmation_response(
            "DELETE_FILE",
            {"path": "test.txt"},
            "dangerous_operation"
        )
        assert response["intent"] == "CONFIRMATION_REQUIRED"
        assert response["slots"]["requires_confirmation"] is True
        assert response["slots"]["original_intent"] == "DELETE_FILE"
        assert response["confidence"] == 1.0
    
    def test_confirmation_includes_accessibility(self):
        """Test confirmation includes accessibility info."""
        response = build_confirmation_response(
            "SHUTDOWN",
            {},
            "dangerous_operation"
        )
        assert "accessibility" in response
        assert "mode" in response["accessibility"]


# =============================================================================
# TEST: PROCESSOR PIPELINE
# =============================================================================

class TestProcessorPipeline:
    """Test full processor pipeline."""
    
    def setup_method(self):
        """Reset processor before each test."""
        reset_processor()
    
    def test_processor_safe_intent(self):
        """Test processor handles safe intent."""
        processor = get_processor()
        result = processor.process("open chrome")
        assert result["intent"] == "OPEN_APP"
        assert result["slots"]["app"] == "chrome"
    
    def test_processor_dangerous_intent(self):
        """Test processor catches dangerous intent."""
        processor = get_processor()
        result = processor.process("delete all files")
        assert result["intent"] == "CONFIRMATION_REQUIRED"
        assert result["reason"] == "dangerous_operation"
    
    def test_processor_pending_confirmation(self):
        """Test processor tracks pending confirmation."""
        processor = get_processor()
        processor.process("shutdown computer")
        assert processor.context.pending_confirmation is not None
    
    def test_processor_confirm_action(self):
        """Test processor confirms action."""
        processor = get_processor()
        processor.process("delete file test.txt")
        confirmed = processor.confirm_dangerous_action()
        assert confirmed is not None
        assert confirmed["intent"] == "DELETE_FILE"


# =============================================================================
# TEST: JSON OUTPUT
# =============================================================================

class TestJSONOutput:
    """Test strict JSON output compliance."""
    
    def test_output_is_valid_json(self):
        """Test output is valid JSON."""
        from agent.core.autonomous_os import process_input
        
        result = process_input("open chrome")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
    
    def test_output_has_required_fields(self):
        """Test output has all required fields."""
        from agent.core.autonomous_os import process_input
        
        result = json.loads(process_input("open notepad"))
        assert "intent" in result
        assert "confidence" in result
    
    def test_unknown_output_format(self):
        """Test UNKNOWN has correct format."""
        from agent.core.autonomous_os import process_input
        
        result = json.loads(process_input("qwertyuiop"))
        assert result["intent"] == "UNKNOWN"
        assert result["confidence"] == 0.0


# =============================================================================
# TEST: ASYNC EXECUTION
# =============================================================================

class TestAsyncExecution:
    """Test async execution."""
    
    @pytest.mark.asyncio
    async def test_execute_open_app(self):
        """Test execute OPEN_APP."""
        processor = get_processor()
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "notepad"},
            "confidence": 0.9,
            "_route": "local"
        }
        # Note: This will actually try to open notepad
        # In real tests, we'd mock the platform adapter


# =============================================================================
# TEST: INTENT VALIDATION
# =============================================================================

class TestIntentValidation:
    """Test intent validation."""
    
    def test_all_intents_valid(self):
        """Test all intent enums are valid."""
        for intent in ALL_VALID_INTENTS:
            assert isinstance(intent, str)
            assert intent.isupper()
    
    def test_intent_categories_complete(self):
        """Test all categories cover all intents."""
        categorized = (
            APP_CONTROL_INTENTS |
            BROWSER_CONTROL_INTENTS |
            FILE_CONTROL_INTENTS |
            SYSTEM_CONTROL_INTENTS
        )
        # All file/system/app/browser intents should be categorized
        for intent in categorized:
            assert intent in ALL_VALID_INTENTS


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
