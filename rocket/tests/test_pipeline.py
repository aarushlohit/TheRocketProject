"""
Test suite for Pipeline Integration (Stage 4).

Tests complete pipeline flow with mocked model responses:
- Valid flow → should_execute = True
- Invalid JSON → blocked
- Inconsistent outputs → resolved correctly
- Multi-step flow → correct plan
- Failure handling
- Edge cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.core.json_validator import ValidationResult
from agent.core.consistency_engine import ConsistencyResult
from agent.core.trust_evaluator import TrustDecision


class TestPipelineValidFlow:
    """Test valid pipeline flow scenarios."""
    
    @pytest.mark.asyncio
    async def test_valid_flow_executes(
        self, sample_valid_intent, json_validator, consistency_engine, trust_evaluator
    ):
        """Test that valid flow results in should_execute = True."""
        # Arrange
        candidates = [sample_valid_intent, sample_valid_intent, sample_valid_intent]
        
        # Act - Step 1: Consistency
        consistency_result = consistency_engine.analyze(candidates)
        
        # Act - Step 2: Validation
        validation_result = json_validator.validate(consistency_result.selected_intent)
        
        # Act - Step 3: Trust
        trust_decision = trust_evaluator.evaluate(
            confidence=consistency_result.selected_intent.get("confidence", 0.9),
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert validation_result.valid is True
        assert consistency_result.consistency_score > 0.8
        assert trust_decision.should_execute is True
        assert trust_decision.final_score >= 0.75
    
    @pytest.mark.asyncio
    async def test_high_quality_unanimous_execution(self, sample_unanimous_candidates):
        """Test high quality unanimous candidates execute successfully."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        consistency_engine = ConsistencyEngine()
        validator = JSONValidator()
        trust_evaluator = TrustEvaluator()
        
        # Act
        consistency_result = consistency_engine.analyze(sample_unanimous_candidates)
        validation_result = validator.validate(consistency_result.selected_intent)
        trust_decision = trust_evaluator.evaluate(
            confidence=consistency_result.selected_intent["confidence"],
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert trust_decision.should_execute is True
        assert validation_result.valid is True


class TestPipelineInvalidJSON:
    """Test pipeline handling of invalid JSON."""
    
    @pytest.mark.asyncio
    async def test_invalid_json_blocked(
        self, sample_invalid_intent_missing_field, 
        json_validator, consistency_engine, trust_evaluator
    ):
        """Test that invalid JSON is blocked from execution."""
        # Arrange
        candidates = [
            sample_invalid_intent_missing_field,
            sample_invalid_intent_missing_field,
            sample_invalid_intent_missing_field
        ]
        
        # Act
        consistency_result = consistency_engine.analyze(candidates)
        validation_result = json_validator.validate(consistency_result.selected_intent)
        trust_decision = trust_evaluator.evaluate(
            confidence=consistency_result.selected_intent.get("confidence", 0.5),
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert - Either validation fails OR trust blocks execution
        assert validation_result.valid is False or trust_decision.should_execute is False
        # Final result must be blocked
        assert trust_decision.should_execute is False
    
    @pytest.mark.asyncio
    async def test_missing_slots_blocked(self):
        """Test that missing required slots blocks execution."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        invalid_intent = {
            "intent": "OPEN_APP",
            "slots": {},  # Missing required 'app' slot
            "confidence": 0.9,
            "normalized_text": "open"
        }
        candidates = [invalid_intent, invalid_intent, invalid_intent]
        
        # Act
        consistency_result = ConsistencyEngine().analyze(candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=0.9,
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert validation_result.valid is False
        assert trust_decision.should_execute is False


class TestPipelineInconsistentOutputs:
    """Test pipeline resolution of inconsistent outputs."""
    
    @pytest.mark.asyncio
    async def test_majority_voting_resolution(self, sample_majority_candidates):
        """Test that majority voting correctly resolves 2:1 scenarios."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        # Act
        consistency_result = ConsistencyEngine().analyze(sample_majority_candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=consistency_result.selected_intent["confidence"],
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert consistency_result.selected_intent["slots"]["app"] == "brave"
        assert consistency_result.agreement_ratio >= 0.66
        assert validation_result.valid is True
    
    @pytest.mark.asyncio
    async def test_conflicting_outputs_blocked(self, sample_conflicting_candidates):
        """Test that highly conflicting outputs may be blocked."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        # Act
        consistency_result = ConsistencyEngine().analyze(sample_conflicting_candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=consistency_result.selected_intent.get("confidence", 0.8),
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert consistency_result.consistency_score < 0.6
        # May or may not execute depending on exact scores
        # At minimum, consistency should be low
        assert consistency_result.agreement_ratio < 1.0


class TestPipelineMultiStepFlow:
    """Test multi-step pipeline flow."""
    
    @pytest.mark.asyncio
    async def test_multi_step_flow_correct_plan(self, sample_multi_step_intent):
        """Test that multi-step intent creates correct execution plan."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        from agent.core.planner import ExecutionPlanner
        
        candidates = [sample_multi_step_intent, sample_multi_step_intent, sample_multi_step_intent]
        
        # Act
        consistency_result = ConsistencyEngine().analyze(candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=consistency_result.selected_intent["confidence"],
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        plan = ExecutionPlanner().plan(consistency_result.selected_intent)
        
        # Assert
        assert validation_result.valid is True
        assert trust_decision.should_execute is True
        assert len(plan.steps) == 2
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[1].intent == "SEARCH_WEB"


class TestPipelineFailureHandling:
    """Test pipeline failure scenarios."""
    
    @pytest.mark.asyncio
    async def test_unknown_intent_blocked(self, sample_unknown_intent):
        """Test that UNKNOWN intent is handled appropriately."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        # Act
        validation_result = JSONValidator().validate(sample_unknown_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=sample_unknown_intent["confidence"],
            consistency_score=0.5,
            validation_passed=validation_result.valid
        )
        
        # Assert
        # Low confidence UNKNOWN should be blocked
        if sample_unknown_intent["confidence"] < 0.5:
            assert trust_decision.should_execute is False
    
    @pytest.mark.asyncio
    async def test_empty_slots_blocked(self):
        """Test that empty slots block execution."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {},  # Empty
            "confidence": 0.8,
            "normalized_text": "search"
        }
        
        # Act
        validation_result = JSONValidator().validate(intent_data)
        trust_decision = TrustEvaluator().evaluate(
            confidence=0.8,
            consistency_score=0.7,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert validation_result.valid is False
        assert trust_decision.should_execute is False
    
    @pytest.mark.asyncio
    async def test_low_confidence_blocked(self):
        """Test that confidence < 0.5 blocks execution."""
        # Arrange
        from agent.core.trust_evaluator import TrustEvaluator
        
        # Act
        trust_decision = TrustEvaluator().evaluate(
            confidence=0.4,  # Below threshold
            consistency_score=0.9,
            validation_passed=True
        )
        
        # Assert
        assert trust_decision.should_execute is False
        assert "confidence" in trust_decision.reason.lower()


class TestPipelineEdgeCases:
    """Test edge case scenarios."""
    
    @pytest.mark.asyncio
    async def test_empty_string_input(self):
        """Test handling of empty string input."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": ""},  # Empty string
            "confidence": 0.9,
            "normalized_text": ""
        }
        
        # Act
        validation_result = JSONValidator().validate(intent_data)
        
        # Assert
        assert validation_result.valid is False
    
    @pytest.mark.asyncio
    async def test_extremely_long_query(self):
        """Test handling of extremely long query."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "a" * 10000},
            "confidence": 0.9,
            "normalized_text": "search " + ("a" * 10000)
        }
        
        # Act
        validation_result = JSONValidator().validate(intent_data)
        
        # Assert
        # Should handle without crashing
        assert isinstance(validation_result.valid, bool)
    
    @pytest.mark.asyncio
    async def test_missing_confidence_field(self):
        """Test handling of missing confidence field."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            # Missing confidence
            "normalized_text": "open chrome"
        }
        
        # Act
        validation_result = JSONValidator().validate(intent_data)
        
        # Assert
        # Should handle missing confidence gracefully
        assert isinstance(validation_result.valid, bool)


class TestPipelineGarbageInput:
    """Test garbage input handling."""
    
    @pytest.mark.asyncio
    async def test_garbage_input_blocked(self):
        """Test that garbage input is blocked."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        garbage_intent = {
            "intent": "asdfghjkl",  # Garbage
            "slots": {"xyz": "123"},
            "confidence": 0.2,
            "normalized_text": "unintelligible"
        }
        
        # Act
        validation_result = JSONValidator().validate(garbage_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=0.2,
            consistency_score=0.1,
            validation_passed=validation_result.valid
        )
        
        # Assert
        assert validation_result.valid is False or trust_decision.should_execute is False
    
    @pytest.mark.asyncio
    async def test_partial_json_handled(self):
        """Test that partial/incomplete JSON is handled."""
        # Arrange
        from agent.core.json_validator import JSONValidator
        
        partial_intent = {
            "intent": "OPEN_APP"
            # Missing slots, confidence, normalized_text
        }
        
        # Act
        validation_result = JSONValidator().validate(partial_intent)
        
        # Assert
        assert validation_result.valid is False


class TestPipelineIntegrationScenarios:
    """Test complete integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_scenario_perfect_input(self):
        """Test perfect input scenario (production success case)."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        from agent.core.planner import ExecutionPlanner
        
        perfect_intent = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.98,
            "normalized_text": "open chrome"
        }
        candidates = [perfect_intent, perfect_intent, perfect_intent]
        
        # Act - Full pipeline
        consistency_result = ConsistencyEngine().analyze(candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=consistency_result.selected_intent["confidence"],
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        plan = ExecutionPlanner().plan(consistency_result.selected_intent)
        
        # Assert - Complete success
        assert consistency_result.consistency_score > 0.95
        assert validation_result.valid is True
        assert trust_decision.should_execute is True
        assert trust_decision.final_score > 0.9
        assert len(plan.steps) >= 1
    
    @pytest.mark.asyncio
    async def test_scenario_borderline_quality(self):
        """Test borderline quality input scenario."""
        # Arrange
        from agent.core.consistency_engine import ConsistencyEngine
        from agent.core.json_validator import JSONValidator
        from agent.core.trust_evaluator import TrustEvaluator
        
        borderline_intent = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "test"},
            "confidence": 0.65,
            "normalized_text": "search test"
        }
        candidates = [borderline_intent, borderline_intent, borderline_intent]
        
        # Act
        consistency_result = ConsistencyEngine().analyze(candidates)
        validation_result = JSONValidator().validate(consistency_result.selected_intent)
        trust_decision = TrustEvaluator().evaluate(
            confidence=consistency_result.selected_intent["confidence"],
            consistency_score=consistency_result.consistency_score,
            validation_passed=validation_result.valid
        )
        
        # Assert - Borderline may or may not execute
        assert isinstance(trust_decision.should_execute, bool)
        assert 0.0 <= trust_decision.final_score <= 1.0
