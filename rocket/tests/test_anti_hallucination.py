"""
Stage 5 — Anti-Hallucination Tests.

Tests for output validation:
- Slot derivation from input
- App name validation
- URL validation
- Search query validation
- Hallucination enforcement
"""

import pytest
from typing import Dict, Any


class TestHallucinationDetection:
    """Tests for detecting hallucinated outputs."""
    
    def test_valid_output_passes(self):
        """Valid output should pass validation."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    def test_invalid_intent_fails(self):
        """Invalid intent should fail."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "INVALID_INTENT",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_invented_app_fails(self):
        """Invented app name should fail."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "invented_app_xyz"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is False
    
    def test_known_app_passes(self):
        """Known app should pass even if not in input."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open browser"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},  # Chrome is a known app
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True


class TestAppSlotValidation:
    """Tests for app slot validation."""
    
    def test_app_in_input_valid(self):
        """App from input should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open firefox browser"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "firefox"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_known_browser_valid(self):
        """Known browsers should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        known_browsers = ["chrome", "firefox", "edge", "safari", "brave"]
        
        for browser in known_browsers:
            output = {
                "intent": "OPEN_APP",
                "slots": {"app": browser},
                "confidence": 0.9
            }
            
            result = check_hallucination("open browser", output)
            assert result.valid is True, f"{browser} should be valid"
    
    def test_known_apps_valid(self):
        """Known apps should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        known_apps = ["vscode", "notepad", "calculator", "spotify"]
        
        for app in known_apps:
            output = {
                "intent": "OPEN_APP",
                "slots": {"app": app},
                "confidence": 0.9
            }
            
            result = check_hallucination("open app", output)
            assert result.valid is True, f"{app} should be valid"


class TestUrlSlotValidation:
    """Tests for URL slot validation."""
    
    def test_url_in_input_valid(self):
        """URL mentioned in input should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open https://github.com"
        output = {
            "intent": "OPEN_URL",
            "slots": {"url": "https://github.com"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_domain_in_input_valid(self):
        """Domain mentioned in input should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "go to google"
        output = {
            "intent": "OPEN_URL",
            "slots": {"url": "https://google.com"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_invented_url_fails(self):
        """Invented URL should fail."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open google"
        output = {
            "intent": "OPEN_URL",
            "slots": {"url": "https://randomsite123.com"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is False


class TestSearchSlotValidation:
    """Tests for search query validation."""
    
    def test_search_from_input_valid(self):
        """Search query from input should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "search python tutorials"
        output = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "python tutorials"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_cleaned_search_valid(self):
        """Cleaned search query should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "search for python tutorials please"
        output = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "python tutorials"},  # Command words removed
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True


class TestClickTargetValidation:
    """Tests for click target validation."""
    
    def test_target_from_input_valid(self):
        """Click target from input should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "click on the play button"
        output = {
            "intent": "CLICK_ELEMENT",
            "slots": {"target": "play button"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_common_target_valid(self):
        """Common targets should be valid."""
        from agent.core.anti_hallucination import check_hallucination
        
        common_targets = ["search bar", "first result", "submit"]
        
        for target in common_targets:
            output = {
                "intent": "CLICK_ELEMENT",
                "slots": {"target": target},
                "confidence": 0.9
            }
            
            result = check_hallucination("click something", output)
            assert result.valid is True, f"{target} should be valid"


class TestMultiStepValidation:
    """Tests for multi-step intent validation."""
    
    def test_valid_multi_step_passes(self):
        """Valid multi-step should pass."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome and search youtube"
        output = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
                {"intent": "SEARCH_WEB", "slots": {"query": "youtube"}}
            ],
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is True
    
    def test_invalid_step_fails(self):
        """Multi-step with invalid step should fail."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
                {"intent": "OPEN_APP", "slots": {"app": "invented_app"}}
            ],
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.valid is False


class TestEnforceAntiHallucination:
    """Tests for enforcement function."""
    
    def test_valid_output_unchanged(self):
        """Valid output should remain unchanged."""
        from agent.core.anti_hallucination import enforce_anti_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = enforce_anti_hallucination(input_text, output)
        
        assert result["intent"] == "OPEN_APP"
        assert result["slots"]["app"] == "chrome"
    
    def test_invalid_output_becomes_unknown(self):
        """Invalid output should become UNKNOWN."""
        from agent.core.anti_hallucination import enforce_anti_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "INVALID_INTENT",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = enforce_anti_hallucination(input_text, output)
        
        assert result["intent"] == "UNKNOWN"
        assert result["confidence"] == 0.0
        assert "anti_hallucination_triggered" in result.get("reason", "")


class TestConfidenceScoring:
    """Tests for validation confidence scoring."""
    
    def test_valid_output_high_confidence(self):
        """Valid output should have high confidence."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        output = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output)
        
        assert result.confidence >= 0.9
    
    def test_warnings_reduce_confidence(self):
        """Warnings should reduce confidence."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "search"
        output = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "something completely different"},
            "confidence": 0.9
        }
        
        result = check_hallucination(input_text, output, strict=False)
        
        # May have warnings but still valid
        if result.warnings:
            assert result.confidence < 1.0


class TestKnownApps:
    """Tests for known apps list."""
    
    def test_known_apps_contains_browsers(self):
        """Known apps should contain browsers."""
        from agent.core.anti_hallucination import KNOWN_APPS
        
        browsers = ["chrome", "firefox", "edge", "safari", "brave"]
        for browser in browsers:
            assert browser in KNOWN_APPS
    
    def test_known_apps_contains_dev_tools(self):
        """Known apps should contain dev tools."""
        from agent.core.anti_hallucination import KNOWN_APPS
        
        dev_tools = ["vscode", "notepad", "terminal"]
        for tool in dev_tools:
            assert tool in KNOWN_APPS
    
    def test_known_apps_contains_utilities(self):
        """Known apps should contain utilities."""
        from agent.core.anti_hallucination import KNOWN_APPS
        
        utilities = ["calculator", "calendar", "settings"]
        for utility in utilities:
            assert utility in KNOWN_APPS
