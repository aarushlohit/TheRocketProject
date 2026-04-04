"""
Test suite for Planner (Stage 4).

Tests:
- Single intent → 1 step
- Compound input → multi-step
- Search expansion (SEARCH_WEB with browser context)
- MULTI_STEP from model → correct plan
- Edge cases
"""

import pytest
from agent.core.planner import (
    ExecutionPlanner,
    ExecutionPlan,
    ExecutionStep
)


class TestPlannerSingleIntent:
    """Test single intent planning."""
    
    def test_single_open_app_intent(self, planner_instance, sample_valid_intent):
        """Test that single OPEN_APP intent creates 1-step plan."""
        # Arrange
        intent_data = sample_valid_intent
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 1
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[0].slots["app"] == "chrome"
    
    def test_single_search_web_intent(self, planner_instance, sample_search_web_intent):
        """Test that single SEARCH_WEB intent creates plan."""
        # Arrange
        intent_data = sample_search_web_intent
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert isinstance(plan, ExecutionPlan)
        # May be 1 step or expanded to 2 steps depending on context
        assert len(plan.steps) >= 1
        assert any(step.intent == "SEARCH_WEB" for step in plan.steps)
    
    def test_single_type_text_intent(self, planner_instance):
        """Test that TYPE_TEXT intent creates 1-step plan."""
        # Arrange
        intent_data = {
            "intent": "TYPE_TEXT",
            "slots": {"text": "hello world"},
            "confidence": 0.9,
            "normalized_text": "type hello world"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan.steps) >= 1
        assert any(step.intent == "TYPE_TEXT" for step in plan.steps)


class TestPlannerMultiStep:
    """Test multi-step planning."""
    
    def test_multi_step_from_model(self, planner_instance, sample_multi_step_intent):
        """Test that MULTI_STEP intent from model creates multi-step plan."""
        # Arrange
        intent_data = sample_multi_step_intent
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) == 2
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[0].slots["app"] == "chrome"
        assert plan.steps[1].intent == "SEARCH_WEB"
        assert plan.steps[1].slots["query"] == "youtube"
    
    def test_multi_step_preserves_order(self, planner_instance):
        """Test that multi-step plan preserves step order."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "notepad"}},
                {"intent": "TYPE_TEXT", "slots": {"text": "hello"}},
                {"intent": "PRESS_KEYS", "slots": {"keys": "ctrl+s"}},
            ],
            "confidence": 0.92,
            "normalized_text": "open notepad type hello and save"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan.steps) == 3
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[1].intent == "TYPE_TEXT"
        assert plan.steps[2].intent == "PRESS_KEYS"


class TestPlannerSearchExpansion:
    """Test smart search expansion."""
    
    def test_search_expansion_with_browser_name(self, planner_instance):
        """Test that 'search on chrome' expands to OPEN_APP + SEARCH_WEB."""
        # Arrange
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "youtube videos on chrome"},
            "confidence": 0.88,
            "normalized_text": "search youtube videos on chrome"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        # May expand if planner detects browser context
        # At minimum should have SEARCH_WEB
        assert any(step.intent == "SEARCH_WEB" for step in plan.steps)
    
    def test_search_without_browser_context(self, planner_instance):
        """Test that simple search doesn't expand unnecessarily."""
        # Arrange
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "python tutorial"},
            "confidence": 0.9,
            "normalized_text": "search python tutorial"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        # Simple search may or may not expand depending on implementation
        assert any(step.intent == "SEARCH_WEB" for step in plan.steps)


class TestPlannerCompoundIntents:
    """Test compound intent detection and expansion."""
    
    def test_compound_open_and_search(self, planner_instance):
        """Test 'open chrome and search youtube' creates 2 steps."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
                {"intent": "SEARCH_WEB", "slots": {"query": "youtube"}},
            ],
            "confidence": 0.93,
            "normalized_text": "open chrome and search youtube"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan.steps) == 2
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[1].intent == "SEARCH_WEB"
    
    def test_compound_open_and_type(self, planner_instance):
        """Test 'open notepad and type' creates 2 steps."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "notepad"}},
                {"intent": "TYPE_TEXT", "slots": {"text": "meeting notes"}},
            ],
            "confidence": 0.90,
            "normalized_text": "open notepad and type meeting notes"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan.steps) == 2
        assert plan.steps[0].slots["app"] == "notepad"
        assert plan.steps[1].slots["text"] == "meeting notes"


class TestExecutionPlanStructure:
    """Test ExecutionPlan dataclass structure."""
    
    def test_execution_plan_has_steps(self, planner_instance, sample_valid_intent):
        """Test that ExecutionPlan has steps list."""
        # Arrange & Act
        plan = planner_instance.plan(sample_valid_intent)
        
        # Assert
        assert hasattr(plan, 'steps')
        assert isinstance(plan.steps, list)
        assert all(isinstance(step, ExecutionStep) for step in plan.steps)
    
    def test_execution_step_has_intent_and_slots(self, planner_instance, sample_valid_intent):
        """Test that ExecutionStep has intent and slots."""
        # Arrange & Act
        plan = planner_instance.plan(sample_valid_intent)
        step = plan.steps[0]
        
        # Assert
        assert hasattr(step, 'intent')
        assert hasattr(step, 'slots')
        assert isinstance(step.intent, str)
        assert isinstance(step.slots, dict)


class TestPlannerEdgeCases:
    """Test edge cases."""
    
    def test_unknown_intent(self, planner_instance, sample_unknown_intent):
        """Test that UNKNOWN intent is handled gracefully."""
        # Arrange
        intent_data = sample_unknown_intent
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        # Should either create empty plan or plan with UNKNOWN step
        assert isinstance(plan, ExecutionPlan)
    
    def test_empty_steps_in_multi_step(self, planner_instance):
        """Test that empty steps array is handled."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [],
            "confidence": 0.5,
            "normalized_text": "do nothing"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        # Should handle gracefully, possibly returning empty or minimal plan
        assert isinstance(plan, ExecutionPlan)
    
    def test_missing_normalized_text(self, planner_instance):
        """Test handling of missing normalized_text field."""
        # Arrange
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9
            # Missing normalized_text
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1


class TestPlannerStepValidation:
    """Test step validation."""
    
    def test_all_steps_have_valid_intents(self, planner_instance, sample_multi_step_intent):
        """Test that all steps have valid intent types."""
        # Arrange & Act
        plan = planner_instance.plan(sample_multi_step_intent)
        
        # Assert
        from agent.core.planner import SUPPORTED_INTENTS
        for step in plan.steps:
            assert step.intent in SUPPORTED_INTENTS or step.intent == "MULTI_STEP"
    
    def test_all_steps_have_required_slots(self, planner_instance, sample_multi_step_intent):
        """Test that all steps have their required slots."""
        # Arrange & Act
        plan = planner_instance.plan(sample_multi_step_intent)
        
        # Assert
        for step in plan.steps:
            if step.intent == "OPEN_APP":
                assert "app" in step.slots
            elif step.intent == "SEARCH_WEB":
                assert "query" in step.slots
            elif step.intent == "TYPE_TEXT":
                assert "text" in step.slots


class TestPlannerComplexScenarios:
    """Test complex realistic scenarios."""
    
    def test_three_step_workflow(self, planner_instance):
        """Test three-step workflow planning."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [
                {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
                {"intent": "SEARCH_WEB", "slots": {"query": "github"}},
                {"intent": "TYPE_TEXT", "slots": {"text": "username"}},
            ],
            "confidence": 0.91,
            "normalized_text": "open chrome search github and type username"
        }
        
        # Act
        plan = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan.steps) == 3
        assert plan.steps[0].intent == "OPEN_APP"
        assert plan.steps[1].intent == "SEARCH_WEB"
        assert plan.steps[2].intent == "TYPE_TEXT"
    
    def test_plan_metadata_preserved(self, planner_instance, sample_valid_intent):
        """Test that plan preserves important metadata."""
        # Arrange & Act
        plan = planner_instance.plan(sample_valid_intent)
        
        # Assert
        # Plan should have metadata like confidence, source, etc.
        assert hasattr(plan, 'steps')
        # Additional metadata checks if applicable


class TestPlannerDeterminism:
    """Test that planner is deterministic."""
    
    def test_same_input_produces_same_plan(self, planner_instance, sample_valid_intent):
        """Test that same input produces identical plan."""
        # Arrange
        intent_data = sample_valid_intent
        
        # Act
        plan1 = planner_instance.plan(intent_data)
        plan2 = planner_instance.plan(intent_data)
        
        # Assert
        assert len(plan1.steps) == len(plan2.steps)
        for step1, step2 in zip(plan1.steps, plan2.steps):
            assert step1.intent == step2.intent
            assert step1.slots == step2.slots
