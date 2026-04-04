"""
Test suite for Consistency Engine (Stage 4).

Tests:
- Unanimous agreement → select with high consistency
- Majority voting (2 vs 1) → select majority
- Conflicting outputs → resolve correctly
- Confidence weighting → prefer higher confidence
- Edge cases (single candidate, empty list)
"""

import pytest
from agent.core.consistency_engine import (
    ConsistencyEngine,
    ConsistencyResult,
    analyze_consistency,
    MIN_CONSISTENCY_SCORE
)


class TestConsistencyEngineUnanimous:
    """Test unanimous agreement scenarios."""
    
    def test_unanimous_agreement_high_consistency(
        self, consistency_engine, sample_unanimous_candidates
    ):
        """Test that unanimous agreement results in high consistency score."""
        # Arrange
        candidates = sample_unanimous_candidates
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.consistency_score > 0.8
        assert result.agreement_ratio == 1.0
        assert result.selected_intent["intent"] == "OPEN_APP"
        assert result.selected_intent["slots"]["app"] == "chrome"
    
    def test_unanimous_selects_highest_confidence(self, consistency_engine):
        """Test that unanimous agreement selects candidate with highest confidence."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.75,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.95,  # Highest
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.80,
                "normalized_text": "open chrome"
            },
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.selected_intent["confidence"] == 0.95


class TestConsistencyEngineMajorityVoting:
    """Test majority voting scenarios."""
    
    def test_majority_voting_two_vs_one(
        self, consistency_engine, sample_majority_candidates
    ):
        """Test that 2:1 majority correctly selects the majority intent."""
        # Arrange
        candidates = sample_majority_candidates
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.selected_intent["slots"]["app"] == "brave"
        assert result.agreement_ratio >= 0.66
        assert "brave" in str(result.voting_breakdown).lower()
    
    def test_majority_with_higher_confidence_minority(self, consistency_engine):
        """Test that majority wins even if minority has higher confidence."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.85,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.80,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "firefox"},
                "confidence": 0.95,  # Higher confidence but minority
                "normalized_text": "open firefox"
            },
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.selected_intent["slots"]["app"] == "chrome"


class TestConsistencyEngineConflicting:
    """Test conflicting outputs scenarios."""
    
    def test_conflicting_intents_selects_highest_confidence(
        self, consistency_engine, sample_conflicting_candidates
    ):
        """Test that complete disagreement selects highest confidence."""
        # Arrange
        candidates = sample_conflicting_candidates
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.consistency_score < 0.6
        assert result.agreement_ratio < 0.5
        # Should select highest confidence (chrome at 0.8)
        assert result.selected_intent["intent"] == "OPEN_APP"
    
    def test_conflicting_low_consistency_score(self, consistency_engine):
        """Test that conflicting outputs result in low consistency score."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.8,
                "normalized_text": "open chrome"
            },
            {
                "intent": "SEARCH_WEB",
                "slots": {"query": "websites"},
                "confidence": 0.75,
                "normalized_text": "search websites"
            },
            {
                "intent": "TYPE_TEXT",
                "slots": {"text": "hello"},
                "confidence": 0.7,
                "normalized_text": "type hello"
            },
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.consistency_score < MIN_CONSISTENCY_SCORE


class TestConsistencyEngineConfidenceWeighting:
    """Test confidence weighting scenarios."""
    
    def test_confidence_weighting_in_score(self, consistency_engine):
        """Test that higher average confidence increases final score."""
        # Arrange
        high_conf_candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.95,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.93,
                "normalized_text": "open chrome"
            },
        ]
        
        low_conf_candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.65,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.60,
                "normalized_text": "open chrome"
            },
        ]
        
        # Act
        high_result = consistency_engine.analyze(high_conf_candidates)
        low_result = consistency_engine.analyze(low_conf_candidates)
        
        # Assert
        assert high_result.consistency_score > low_result.consistency_score


class TestConsistencyEngineEdgeCases:
    """Test edge cases."""
    
    def test_single_candidate(self, consistency_engine):
        """Test handling of single candidate."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.9,
                "normalized_text": "open chrome"
            }
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.selected_intent["intent"] == "OPEN_APP"
        assert result.agreement_ratio == 1.0
    
    def test_empty_candidate_list(self, consistency_engine):
        """Test handling of empty candidate list."""
        # Arrange
        candidates = []
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert - Implementation handles gracefully, returns result with no valid candidates
        assert isinstance(result, ConsistencyResult)
        assert result.consistency_score == 0.0
    
    def test_candidates_with_missing_fields(self, consistency_engine):
        """Test handling of candidates with missing required fields."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "confidence": 0.9,
                # Missing slots
            },
            {
                "slots": {"app": "chrome"},
                "confidence": 0.85,
                # Missing intent
            },
        ]
        
        # Act & Assert
        # Should either handle gracefully or raise appropriate error
        try:
            result = consistency_engine.analyze(candidates)
            assert isinstance(result, ConsistencyResult)
        except (ValueError, KeyError):
            pass  # Expected behavior


class TestConsistencyEngineSignatureMatching:
    """Test signature-based grouping."""
    
    def test_signature_matches_same_intent_and_slots(self, consistency_engine):
        """Test that identical intent+slots are grouped together."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.9,
                "normalized_text": "open chrome browser"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.85,
                "normalized_text": "open chrome"  # Different text, same intent
            },
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.agreement_ratio == 1.0
    
    def test_signature_distinguishes_different_slots(self, consistency_engine):
        """Test that different slot values create different signatures."""
        # Arrange
        candidates = [
            {
                "intent": "OPEN_APP",
                "slots": {"app": "chrome"},
                "confidence": 0.9,
                "normalized_text": "open chrome"
            },
            {
                "intent": "OPEN_APP",
                "slots": {"app": "firefox"},  # Different app
                "confidence": 0.85,
                "normalized_text": "open firefox"
            },
        ]
        
        # Act
        result = consistency_engine.analyze(candidates)
        
        # Assert
        assert result.agreement_ratio < 1.0


class TestConsistencyResultStructure:
    """Test ConsistencyResult dataclass structure."""
    
    def test_consistency_result_has_required_fields(
        self, consistency_engine, sample_unanimous_candidates
    ):
        """Test that ConsistencyResult contains all required fields."""
        # Arrange & Act
        result = consistency_engine.analyze(sample_unanimous_candidates)
        
        # Assert
        assert hasattr(result, 'selected_intent')
        assert hasattr(result, 'consistency_score')
        assert hasattr(result, 'agreement_ratio')
        assert isinstance(result.selected_intent, dict)
        assert isinstance(result.consistency_score, float)
        assert isinstance(result.agreement_ratio, float)
    
    def test_agreement_ratio_bounds(
        self, consistency_engine, sample_unanimous_candidates
    ):
        """Test that agreement_ratio is between 0 and 1."""
        # Arrange & Act
        result = consistency_engine.analyze(sample_unanimous_candidates)
        
        # Assert
        assert 0.0 <= result.agreement_ratio <= 1.0
    
    def test_consistency_score_bounds(
        self, consistency_engine, sample_unanimous_candidates
    ):
        """Test that consistency_score is between 0 and 1."""
        # Arrange & Act
        result = consistency_engine.analyze(sample_unanimous_candidates)
        
        # Assert
        assert 0.0 <= result.consistency_score <= 1.0


class TestAnalyzeConsistencyFunction:
    """Test standalone analyze_consistency function."""
    
    def test_standalone_function(self, sample_unanimous_candidates):
        """Test standalone analyze_consistency function."""
        # Arrange & Act
        result = analyze_consistency(sample_unanimous_candidates)
        
        # Assert
        assert isinstance(result, ConsistencyResult)
        assert result.selected_intent["intent"] == "OPEN_APP"
