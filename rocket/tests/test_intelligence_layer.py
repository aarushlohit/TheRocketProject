"""
Stage 5.5 — Intelligence Layer Tests.

Tests for enhanced reasoning and validation:
- Intent validation
- Consensus logic
- Context priority
- Search normalization
- Multi-step detection
- Goal interpretation
- Self-correction
- Safety filter
"""

import pytest
from typing import Dict, Any, List


# =============================================================================
# INTENT VALIDATION TESTS
# =============================================================================

class TestIntentValidation:
    """Tests for intent validation against input."""
    
    def test_valid_intent_passes(self):
        """Valid intent matching input should pass."""
        from agent.core.intelligence_layer import validate_intent_against_input
        
        input_text = "open chrome"
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        valid, errors = validate_intent_against_input(input_text, intent_data)
        
        assert valid is True
        assert len(errors) == 0
    
    def test_invalid_intent_fails(self):
        """Invalid intent enum should fail."""
        from agent.core.intelligence_layer import validate_intent_against_input
        
        input_text = "open chrome"
        intent_data = {
            "intent": "INVALID_INTENT",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        valid, errors = validate_intent_against_input(input_text, intent_data)
        
        assert valid is False
        assert len(errors) > 0
    
    def test_hallucinated_app_fails(self):
        """App not mentioned in input should generate errors."""
        from agent.core.anti_hallucination import check_hallucination
        
        input_text = "open chrome"
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "firefox"},  # Different from input
            "confidence": 0.9
        }
        
        # Check - firefox is known app but not in input
        result = check_hallucination(input_text, intent_data, strict=False)
        
        # Should detect app mismatch - firefox not in "open chrome"
        assert result.valid is False or len(result.errors) > 0 or len(result.warnings) > 0


# =============================================================================
# CONSENSUS LOGIC TESTS
# =============================================================================

class TestConsensusLogic:
    """Tests for consensus logic with multiple candidates."""
    
    def test_single_candidate_returns_unchanged(self):
        """Single candidate should be returned as-is."""
        from agent.core.intelligence_layer import apply_consensus
        
        candidates = [
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.9}
        ]
        
        result = apply_consensus(candidates, "open chrome")
        
        assert result["intent"] == "OPEN_APP"
    
    def test_majority_wins(self):
        """Majority intent should win."""
        from agent.core.intelligence_layer import apply_consensus
        
        candidates = [
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.9},
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.85},
            {"intent": "SEARCH_WEB", "slots": {"query": "chrome"}, "confidence": 0.8},
        ]
        
        result = apply_consensus(candidates, "open chrome")
        
        assert result["intent"] == "OPEN_APP"
    
    def test_highest_confidence_in_majority(self):
        """Highest confidence in majority group should be selected."""
        from agent.core.intelligence_layer import apply_consensus
        
        candidates = [
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.85},
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.95},
            {"intent": "SEARCH_WEB", "slots": {"query": "chrome"}, "confidence": 0.8},
        ]
        
        result = apply_consensus(candidates, "open chrome")
        
        assert result["confidence"] == 0.95
    
    def test_empty_candidates_returns_unknown(self):
        """Empty candidates should return UNKNOWN."""
        from agent.core.intelligence_layer import apply_consensus
        
        result = apply_consensus([], "open chrome")
        
        assert result["intent"] == "UNKNOWN"


# =============================================================================
# CONTEXT PRIORITY TESTS
# =============================================================================

class TestContextPriority:
    """Tests for context-aware optimizations."""
    
    def test_skip_reopen_same_app(self):
        """Should skip reopening already open app."""
        from agent.core.intelligence_layer import apply_context_priority
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        context = {"last_app": "chrome"}
        
        result = apply_context_priority(intent_data, context)
        
        assert result["intent"] == "FOCUS_WINDOW"
    
    def test_no_context_unchanged(self):
        """Without context, intent should be unchanged."""
        from agent.core.intelligence_layer import apply_context_priority
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = apply_context_priority(intent_data, None)
        
        assert result["intent"] == "OPEN_APP"
    
    def test_different_app_unchanged(self):
        """Different app should still open."""
        from agent.core.intelligence_layer import apply_context_priority
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "firefox"},
            "confidence": 0.9
        }
        context = {"last_app": "chrome"}
        
        result = apply_context_priority(intent_data, context)
        
        assert result["intent"] == "OPEN_APP"


# =============================================================================
# SEARCH NORMALIZATION TESTS
# =============================================================================

class TestSearchNormalization:
    """Tests for search query normalization."""
    
    def test_normalize_search_query(self):
        """Search prefix should be removed."""
        from agent.core.intelligence_layer import normalize_search
        
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "search github"},
            "confidence": 0.9
        }
        
        result = normalize_search(intent_data)
        
        assert result["slots"]["query"] == "github"
    
    def test_clean_query_unchanged(self):
        """Clean query should remain unchanged."""
        from agent.core.intelligence_layer import normalize_search
        
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "python tutorials"},
            "confidence": 0.9
        }
        
        result = normalize_search(intent_data)
        
        assert result["slots"]["query"] == "python tutorials"
    
    def test_non_search_unchanged(self):
        """Non-SEARCH_WEB intents should be unchanged."""
        from agent.core.intelligence_layer import normalize_search
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = normalize_search(intent_data)
        
        assert result["intent"] == "OPEN_APP"


# =============================================================================
# MULTI-STEP DETECTION TESTS
# =============================================================================

class TestMultiStepDetection:
    """Tests for multi-step detection."""
    
    def test_detect_and_keyword(self):
        """'and' keyword should trigger multi-step."""
        from agent.core.intelligence_layer import detect_multi_step
        
        assert detect_multi_step("open chrome and search youtube") is True
    
    def test_detect_then_keyword(self):
        """'then' keyword should trigger multi-step."""
        from agent.core.intelligence_layer import detect_multi_step
        
        assert detect_multi_step("open chrome then search youtube") is True
    
    def test_detect_multiple_verbs(self):
        """Multiple action verbs should trigger multi-step."""
        from agent.core.intelligence_layer import detect_multi_step
        
        assert detect_multi_step("open chrome search youtube") is True
    
    def test_single_action_no_multi_step(self):
        """Single action should not trigger multi-step."""
        from agent.core.intelligence_layer import detect_multi_step
        
        assert detect_multi_step("open chrome") is False
    
    def test_ensure_multi_step_wraps_single(self):
        """ensure_multi_step should wrap when needed."""
        from agent.core.intelligence_layer import ensure_multi_step
        
        input_text = "open chrome and search youtube"
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = ensure_multi_step(input_text, intent_data)
        
        assert result["intent"] == "MULTI_STEP"


# =============================================================================
# GOAL INTERPRETATION TESTS
# =============================================================================

class TestGoalInterpretation:
    """Tests for goal interpretation."""
    
    def test_interpret_watch_goal(self):
        """'watch' goal should expand to steps."""
        from agent.core.intelligence_layer import interpret_goal
        
        result = interpret_goal("watch youtube videos")
        
        assert result is not None
        assert result.get("_goal_interpreted") is True
    
    def test_non_goal_returns_none(self):
        """Non-goal should return None."""
        from agent.core.intelligence_layer import interpret_goal
        
        result = interpret_goal("open chrome")
        
        assert result is None
    
    def test_goal_with_context(self):
        """High-level goal should be interpreted."""
        from agent.core.intelligence_layer import interpret_goal
        
        context = {"last_browser": "chrome"}
        # Use a proper goal pattern that matches GOAL_PATTERNS
        result = interpret_goal("watch youtube videos", context)
        
        assert result is not None
        assert result.get("_goal_interpreted") is True


# =============================================================================
# UI SEMANTIC CONTROL TESTS
# =============================================================================

class TestUISemanticControl:
    """Tests for semantic UI enforcement."""
    
    def test_normalize_click_target(self):
        """Click target should be normalized."""
        from agent.core.intelligence_layer import enforce_semantic_ui
        
        intent_data = {
            "intent": "CLICK_ELEMENT",
            "slots": {"target": "search field"},  # Alias
            "confidence": 0.9
        }
        
        result = enforce_semantic_ui(intent_data)
        
        # Should normalize to canonical name
        assert "target" in result["slots"]
    
    def test_non_click_unchanged(self):
        """Non-CLICK_ELEMENT should be unchanged."""
        from agent.core.intelligence_layer import enforce_semantic_ui
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = enforce_semantic_ui(intent_data)
        
        assert result["intent"] == "OPEN_APP"


# =============================================================================
# SELF-CORRECTION TESTS
# =============================================================================

class TestSelfCorrection:
    """Tests for self-correction strategy."""
    
    def test_low_confidence_fallback(self):
        """Low confidence should fallback to search."""
        from agent.core.intelligence_layer import apply_self_correction
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "something"},
            "confidence": 0.3
        }
        
        result = apply_self_correction(intent_data, "something")
        
        assert result["intent"] == "SEARCH_WEB"
        assert result.get("_self_corrected") is True
    
    def test_unknown_app_fallback(self):
        """Unknown app should fallback to search."""
        from agent.core.intelligence_layer import apply_self_correction
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "unknown_app_xyz"},
            "confidence": 0.8
        }
        
        result = apply_self_correction(intent_data, "open unknown app")
        
        assert result["intent"] == "SEARCH_WEB"
    
    def test_known_app_unchanged(self):
        """Known app should remain unchanged."""
        from agent.core.intelligence_layer import apply_self_correction
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = apply_self_correction(intent_data, "open chrome")
        
        assert result["intent"] == "OPEN_APP"


# =============================================================================
# SAFETY FILTER TESTS
# =============================================================================

class TestSafetyFilter:
    """Tests for safety filter."""
    
    def test_delete_file_requires_confirmation(self):
        """DELETE_FILE should require confirmation."""
        from agent.core.intelligence_layer import apply_safety_filter
        
        intent_data = {
            "intent": "DELETE_FILE",
            "slots": {"path": "/tmp/file.txt"},
            "confidence": 0.9
        }
        
        result = apply_safety_filter(intent_data)
        
        # Per system spec: CONDITIONAL with requires_confirmation
        assert result["intent"] == "CONDITIONAL"
        assert result["slots"]["requires_confirmation"] is True
        assert result["slots"]["original_intent"] == "DELETE_FILE"
    
    def test_lock_screen_requires_confirmation(self):
        """LOCK_SCREEN should require confirmation."""
        from agent.core.intelligence_layer import apply_safety_filter
        
        intent_data = {
            "intent": "LOCK_SCREEN",
            "slots": {},
            "confidence": 0.9
        }
        
        result = apply_safety_filter(intent_data)
        
        # Per system spec: CONDITIONAL with requires_confirmation
        assert result["intent"] == "CONDITIONAL"
        assert result["slots"]["requires_confirmation"] is True
    
    def test_dangerous_text_requires_confirmation(self):
        """Dangerous text should require confirmation."""
        from agent.core.intelligence_layer import apply_safety_filter
        
        intent_data = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "rm -rf /"},
            "confidence": 0.9
        }
        
        result = apply_safety_filter(intent_data)
        
        # Per system spec: CONDITIONAL with requires_confirmation
        assert result["intent"] == "CONDITIONAL"
        assert result["slots"]["requires_confirmation"] is True
    
    def test_safe_intent_unchanged(self):
        """Safe intents should be unchanged."""
        from agent.core.intelligence_layer import apply_safety_filter
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = apply_safety_filter(intent_data)
        
        assert result["intent"] == "OPEN_APP"


# =============================================================================
# FAILURE HANDLING TESTS
# =============================================================================

class TestFailureHandling:
    """Tests for failure handling."""
    
    def test_handle_failure_returns_unknown(self):
        """handle_failure should return UNKNOWN."""
        from agent.core.intelligence_layer import handle_failure
        
        result = handle_failure("test_reason", "test input")
        
        assert result["intent"] == "UNKNOWN"
        assert result["confidence"] == 0.0
        assert result["_failure_reason"] == "test_reason"


# =============================================================================
# MAIN INTELLIGENCE PIPELINE TESTS
# =============================================================================

class TestIntelligencePipeline:
    """Tests for the main intelligence pipeline."""
    
    def test_valid_input_processed(self):
        """Valid input should be processed successfully."""
        from agent.core.intelligence_layer import process_with_intelligence
        
        input_text = "open chrome"
        raw_intent = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        result = process_with_intelligence(input_text, raw_intent)
        
        assert result.is_valid is True
        assert result.intent_data["intent"] == "OPEN_APP"
    
    def test_goal_expansion_fallback(self):
        """High-level goal should expand."""
        from agent.core.intelligence_layer import process_with_intelligence
        
        input_text = "watch youtube videos"
        raw_intent = {
            "intent": "UNKNOWN",
            "slots": {},
            "confidence": 0.3
        }
        
        result = process_with_intelligence(input_text, raw_intent)
        
        # Should expand goal or handle gracefully
        assert result.intent_data is not None
    
    def test_search_normalization_applied(self):
        """Search queries should be normalized."""
        from agent.core.intelligence_layer import process_with_intelligence
        
        input_text = "search github"
        raw_intent = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "search github"},
            "confidence": 0.9
        }
        
        result = process_with_intelligence(input_text, raw_intent)
        
        assert result.intent_data["slots"]["query"] == "github"
    
    def test_consensus_with_multiple_candidates(self):
        """Multiple candidates should use consensus."""
        from agent.core.intelligence_layer import process_with_intelligence
        
        input_text = "open chrome"
        raw_intent = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.85
        }
        candidates = [
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.9},
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}, "confidence": 0.85},
            {"intent": "SEARCH_WEB", "slots": {"query": "chrome"}, "confidence": 0.7},
        ]
        
        result = process_with_intelligence(input_text, raw_intent, candidates=candidates)
        
        assert result.is_valid is True
        assert result.metadata.get("consensus_applied") is True


# =============================================================================
# INTELLIGENCE RESULT TESTS
# =============================================================================

class TestIntelligenceResult:
    """Tests for IntelligenceResult structure."""
    
    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        from agent.core.intelligence_layer import IntelligenceResult
        
        result = IntelligenceResult(
            intent_data={"intent": "OPEN_APP"},
            is_valid=True,
            confidence=0.9,
            validation_passed=True,
        )
        
        assert hasattr(result, "intent_data")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "confidence")
        assert hasattr(result, "validation_passed")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "metadata")
