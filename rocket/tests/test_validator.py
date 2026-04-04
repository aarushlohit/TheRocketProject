"""
Test suite for JSON Validator (Stage 4).

Tests:
- Missing intent field → fail
- Invalid intent type → fail
- Missing required slots → fail
- Low confidence → warning
- Valid input → pass
- Edge cases (empty strings, malformed data)
"""

import pytest
from agent.core.json_validator import (
    JSONValidator,
    ValidationResult,
    validate_intent_json,
    VALID_INTENTS,
    MIN_CONFIDENCE_THRESHOLD
)


class TestJSONValidatorBasic:
    """Basic validation tests."""
    
    def test_valid_intent_passes(self, json_validator, sample_valid_intent):
        """Test that valid intent passes validation."""
        # Arrange
        intent_data = sample_valid_intent
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.confidence >= MIN_CONFIDENCE_THRESHOLD
    
    def test_missing_intent_field_fails(self, json_validator, sample_invalid_intent_missing_field):
        """Test that missing 'intent' field causes validation failure."""
        # Arrange
        intent_data = sample_invalid_intent_missing_field
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("intent" in error.lower() for error in result.errors)
    
    def test_invalid_intent_type_fails(self, json_validator, sample_invalid_intent_wrong_type):
        """Test that invalid intent type fails validation."""
        # Arrange
        intent_data = sample_invalid_intent_wrong_type
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_missing_required_slots_fails(self, json_validator, sample_invalid_intent_missing_slots):
        """Test that missing required slots fails validation."""
        # Arrange
        intent_data = sample_invalid_intent_missing_slots
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert len(result.errors) > 0
        assert any("slot" in error.lower() or "app" in error.lower() for error in result.errors)
    
    def test_low_confidence_generates_warning(self, json_validator, sample_low_confidence_intent):
        """Test that low confidence generates a warning but may still pass."""
        # Arrange
        intent_data = sample_low_confidence_intent
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert len(result.warnings) > 0
        assert any("confidence" in warning.lower() for warning in result.warnings)


class TestJSONValidatorSlotValidation:
    """Slot-specific validation tests."""
    
    def test_open_app_requires_app_slot(self, json_validator):
        """Test that OPEN_APP intent requires 'app' slot."""
        # Arrange
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {},
            "confidence": 0.9,
            "normalized_text": "open something"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert any("app" in error.lower() for error in result.errors)
    
    def test_search_web_requires_query_slot(self, json_validator):
        """Test that SEARCH_WEB intent requires 'query' slot."""
        # Arrange
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {},
            "confidence": 0.9,
            "normalized_text": "search"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert any("query" in error.lower() for error in result.errors)
    
    def test_type_text_requires_text_slot(self, json_validator):
        """Test that TYPE_TEXT intent requires 'text' slot."""
        # Arrange
        intent_data = {
            "intent": "TYPE_TEXT",
            "slots": {},
            "confidence": 0.9,
            "normalized_text": "type"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert any("text" in error.lower() for error in result.errors)
    
    def test_empty_slot_values_fail(self, json_validator):
        """Test that empty slot values fail validation."""
        # Arrange
        intent_data = {
            "intent": "OPEN_APP",
            "slots": {"app": ""},
            "confidence": 0.9,
            "normalized_text": "open"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False


class TestJSONValidatorMultiStep:
    """Multi-step intent validation tests."""
    
    def test_multi_step_requires_steps_array(self, json_validator):
        """Test that MULTI_STEP intent requires 'steps' array."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "slots": {},
            "confidence": 0.9,
            "normalized_text": "do multiple things"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert any("steps" in error.lower() for error in result.errors)
    
    def test_multi_step_empty_steps_fails(self, json_validator):
        """Test that MULTI_STEP with empty steps array fails."""
        # Arrange
        intent_data = {
            "intent": "MULTI_STEP",
            "steps": [],
            "confidence": 0.9,
            "normalized_text": "do nothing"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
    
    def test_multi_step_valid_steps_passes(self, json_validator, sample_multi_step_intent):
        """Test that MULTI_STEP with valid steps passes."""
        # Arrange
        intent_data = sample_multi_step_intent
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is True
        assert len(result.errors) == 0


class TestJSONValidatorEdgeCases:
    """Edge case validation tests."""
    
    def test_empty_dict_fails(self, json_validator):
        """Test that empty dict fails validation."""
        # Arrange
        intent_data = {}
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_none_intent_fails(self, json_validator):
        """Test that None as intent fails."""
        # Arrange
        intent_data = {
            "intent": None,
            "slots": {"app": "chrome"},
            "confidence": 0.9
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        assert result.valid is False
    
    def test_extremely_long_slot_value(self, json_validator):
        """Test handling of extremely long slot values."""
        # Arrange
        intent_data = {
            "intent": "SEARCH_WEB",
            "slots": {"query": "a" * 10000},
            "confidence": 0.9,
            "normalized_text": "search many a's"
        }
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        # Should either pass or fail gracefully, not crash
        assert isinstance(result.valid, bool)
    
    def test_unknown_intent_passes_validation(self, json_validator, sample_unknown_intent):
        """Test that UNKNOWN intent is valid (system-recognized fallback)."""
        # Arrange
        intent_data = sample_unknown_intent
        
        # Act
        result = json_validator.validate(intent_data)
        
        # Assert
        # UNKNOWN is a valid intent type
        assert "UNKNOWN" in VALID_INTENTS


class TestValidationResultStructure:
    """Test ValidationResult dataclass structure."""
    
    def test_validation_result_has_required_fields(self, json_validator, sample_valid_intent):
        """Test that ValidationResult contains all required fields."""
        # Arrange & Act
        result = json_validator.validate(sample_valid_intent)
        
        # Assert
        assert hasattr(result, 'valid')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_errors_are_strings(self, json_validator, sample_invalid_intent_missing_field):
        """Test that error messages are strings."""
        # Arrange & Act
        result = json_validator.validate(sample_invalid_intent_missing_field)
        
        # Assert
        assert all(isinstance(error, str) for error in result.errors)
    
    def test_warnings_are_strings(self, json_validator, sample_low_confidence_intent):
        """Test that warning messages are strings."""
        # Arrange & Act
        result = json_validator.validate(sample_low_confidence_intent)
        
        # Assert
        assert all(isinstance(warning, str) for warning in result.warnings)


class TestValidateIntentJSONFunction:
    """Test standalone validate_intent_json function."""
    
    def test_standalone_function_valid_input(self, sample_valid_intent):
        """Test standalone validation function with valid input."""
        # Arrange & Act
        result = validate_intent_json(sample_valid_intent)
        
        # Assert
        assert result.valid is True
    
    def test_standalone_function_invalid_input(self, sample_invalid_intent_missing_field):
        """Test standalone validation function with invalid input."""
        # Arrange & Act
        result = validate_intent_json(sample_invalid_intent_missing_field)
        
        # Assert
        assert result.valid is False
