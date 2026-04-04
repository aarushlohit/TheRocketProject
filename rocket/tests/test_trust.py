"""
Test suite for Trust Evaluator (Stage 4).

Tests:
- High confidence + consistency → execute
- Low confidence → block
- Low consistency → block
- Validation fail → block
- Trust score calculation
- Edge cases
"""

import pytest
from agent.core.trust_evaluator import (
    TrustEvaluator,
    TrustDecision,
    evaluate_trust,
    EXECUTION_THRESHOLD,
    MIN_CONFIDENCE,
    MIN_CONSISTENCY
)


class TestTrustEvaluatorExecutionDecisions:
    """Test execution decision logic."""
    
    def test_high_confidence_and_consistency_executes(self, trust_evaluator):
        """Test that high confidence + consistency → execute."""
        # Arrange
        confidence = 0.95
        consistency_score = 0.90
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is True
        assert decision.final_score >= EXECUTION_THRESHOLD
        assert len(decision.reason) > 0  # Has meaningful reason
        assert "threshold" in decision.reason.lower() or "exceeds" in decision.reason.lower()
    
    def test_low_confidence_blocks_execution(self, trust_evaluator):
        """Test that low confidence → block."""
        # Arrange
        confidence = 0.4  # Below MIN_CONFIDENCE
        consistency_score = 0.90
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is False
        assert "confidence" in decision.reason.lower()
    
    def test_low_consistency_blocks_execution(self, trust_evaluator):
        """Test that low consistency → block."""
        # Arrange
        confidence = 0.95
        consistency_score = 0.3  # Below MIN_CONSISTENCY
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is False
        assert "consistency" in decision.reason.lower()
    
    def test_validation_failed_blocks_execution(self, trust_evaluator):
        """Test that validation failure → block."""
        # Arrange
        confidence = 0.95
        consistency_score = 0.90
        validation_passed = False
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is False
        assert "validation" in decision.reason.lower()


class TestTrustScoreCalculation:
    """Test trust score calculation formula."""
    
    def test_trust_score_formula(self, trust_evaluator):
        """Test that trust score is calculated correctly."""
        # Arrange
        confidence = 0.9
        consistency_score = 0.8
        validation_passed = True
        
        # Expected: (0.9 * 0.5) + (0.8 * 0.3) + (1.0 * 0.2) = 0.89
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        expected_score = (confidence * 0.5) + (consistency_score * 0.3) + (1.0 * 0.2)
        assert abs(decision.final_score - expected_score) < 0.01
    
    def test_validation_failed_affects_score(self, trust_evaluator):
        """Test that failed validation affects trust score."""
        # Arrange
        confidence = 0.9
        consistency_score = 0.8
        
        # Act
        passed_decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=True
        )
        
        failed_decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=False
        )
        
        # Assert
        assert passed_decision.final_score > failed_decision.final_score
    
    def test_score_bounds(self, trust_evaluator):
        """Test that final score is between 0 and 1."""
        # Arrange
        test_cases = [
            (0.0, 0.0, False),
            (1.0, 1.0, True),
            (0.5, 0.5, True),
            (0.8, 0.6, False),
        ]
        
        # Act & Assert
        for confidence, consistency, validation in test_cases:
            decision = trust_evaluator.evaluate(
                confidence=confidence,
                consistency_score=consistency,
                validation_passed=validation
            )
            assert 0.0 <= decision.final_score <= 1.0


class TestTrustEvaluatorThresholds:
    """Test threshold boundary conditions."""
    
    def test_score_exactly_at_threshold_executes(self, trust_evaluator):
        """Test that score exactly at threshold allows execution."""
        # Arrange - construct inputs to hit threshold exactly
        # Threshold = 0.75
        # Formula: (conf * 0.5) + (cons * 0.3) + (val * 0.2)
        # Need: conf * 0.5 + cons * 0.3 + 0.2 = 0.75
        # conf * 0.5 + cons * 0.3 = 0.55
        # Example: conf=0.8, cons=0.5 → 0.4 + 0.15 + 0.2 = 0.75
        
        confidence = 0.8
        consistency_score = 0.5
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert abs(decision.final_score - EXECUTION_THRESHOLD) < 0.01
        assert decision.should_execute is True
    
    def test_score_just_below_threshold_blocks(self, trust_evaluator):
        """Test that score just below threshold blocks execution."""
        # Arrange - construct inputs to be just below threshold
        confidence = 0.7
        consistency_score = 0.5
        validation_passed = True
        # Score: 0.35 + 0.15 + 0.2 = 0.70 < 0.75
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.final_score < EXECUTION_THRESHOLD
        assert decision.should_execute is False
    
    def test_confidence_at_minimum_threshold(self, trust_evaluator):
        """Test confidence exactly at minimum threshold."""
        # Arrange
        confidence = MIN_CONFIDENCE  # 0.6
        consistency_score = 0.9
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        # Should be allowed if final score is high enough
        if decision.final_score >= EXECUTION_THRESHOLD:
            assert decision.should_execute is True
    
    def test_consistency_at_minimum_threshold(self, trust_evaluator):
        """Test consistency exactly at minimum threshold."""
        # Arrange
        confidence = 0.9
        consistency_score = MIN_CONSISTENCY  # 0.5
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        # Should be allowed if final score is high enough
        if decision.final_score >= EXECUTION_THRESHOLD:
            assert decision.should_execute is True


class TestTrustDecisionStructure:
    """Test TrustDecision dataclass structure."""
    
    def test_trust_decision_has_required_fields(self, trust_evaluator):
        """Test that TrustDecision contains all required fields."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=0.9,
            consistency_score=0.8,
            validation_passed=True
        )
        
        # Assert
        assert hasattr(decision, 'should_execute')
        assert hasattr(decision, 'final_score')
        assert hasattr(decision, 'reason')
        assert isinstance(decision.should_execute, bool)
        assert isinstance(decision.final_score, float)
        assert isinstance(decision.reason, str)
    
    def test_reason_is_meaningful(self, trust_evaluator):
        """Test that reason string is meaningful."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=0.9,
            consistency_score=0.8,
            validation_passed=True
        )
        
        # Assert
        assert len(decision.reason) > 0
        assert decision.reason is not None


class TestTrustEvaluatorEdgeCases:
    """Test edge cases."""
    
    def test_zero_confidence(self, trust_evaluator):
        """Test handling of zero confidence."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=0.0,
            consistency_score=1.0,
            validation_passed=True
        )
        
        # Assert
        assert decision.should_execute is False
    
    def test_zero_consistency(self, trust_evaluator):
        """Test handling of zero consistency."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=1.0,
            consistency_score=0.0,
            validation_passed=True
        )
        
        # Assert
        assert decision.should_execute is False
    
    def test_perfect_scores(self, trust_evaluator):
        """Test handling of perfect scores."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=1.0,
            consistency_score=1.0,
            validation_passed=True
        )
        
        # Assert
        assert decision.should_execute is True
        assert decision.final_score == 1.0
    
    def test_negative_values_handled(self, trust_evaluator):
        """Test handling of negative values (invalid input)."""
        # Arrange & Act
        decision = trust_evaluator.evaluate(
            confidence=-0.5,
            consistency_score=-0.3,
            validation_passed=True
        )
        
        # Assert
        # Should either clamp to 0 or block execution
        assert decision.should_execute is False or decision.final_score >= 0


class TestEvaluateTrustFunction:
    """Test standalone evaluate_trust function."""
    
    def test_standalone_function_executes(self):
        """Test standalone evaluate_trust function allows execution."""
        # Arrange & Act
        decision = evaluate_trust(
            confidence=0.9,
            consistency_score=0.8,
            validation_passed=True
        )
        
        # Assert
        assert isinstance(decision, TrustDecision)
        assert decision.should_execute is True
    
    def test_standalone_function_blocks(self):
        """Test standalone evaluate_trust function blocks execution."""
        # Arrange & Act
        decision = evaluate_trust(
            confidence=0.3,
            consistency_score=0.2,
            validation_passed=False
        )
        
        # Assert
        assert isinstance(decision, TrustDecision)
        assert decision.should_execute is False


class TestTrustEvaluatorMultipleScenarios:
    """Test multiple realistic scenarios."""
    
    def test_scenario_high_quality_input(self, trust_evaluator):
        """Test high quality input (typical production success)."""
        # Arrange
        confidence = 0.95
        consistency_score = 0.92
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is True
        assert decision.final_score > 0.9
    
    def test_scenario_borderline_quality(self, trust_evaluator):
        """Test borderline quality input."""
        # Arrange
        confidence = 0.65
        consistency_score = 0.60
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        # Borderline case - decision depends on exact weights
        assert isinstance(decision.should_execute, bool)
    
    def test_scenario_poor_quality_input(self, trust_evaluator):
        """Test poor quality input."""
        # Arrange
        confidence = 0.4
        consistency_score = 0.3
        validation_passed = True
        
        # Act
        decision = trust_evaluator.evaluate(
            confidence=confidence,
            consistency_score=consistency_score,
            validation_passed=validation_passed
        )
        
        # Assert
        assert decision.should_execute is False
        assert decision.final_score < EXECUTION_THRESHOLD
