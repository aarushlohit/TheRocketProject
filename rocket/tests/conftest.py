"""
Pytest fixtures for Stage 4 test suite.

Provides reusable test fixtures for:
- Mock model responses
- Sample intent data
- Pipeline instances
- Planner instances
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def pytest_configure(config):
    """Register local markers used by the suite."""
    config.addinivalue_line("markers", "asyncio: run test in an event loop")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Run async tests without requiring pytest-asyncio."""
    test_function = pyfuncitem.obj

    if not asyncio.iscoroutinefunction(test_function):
        return None

    kwargs = {
        arg_name: pyfuncitem.funcargs[arg_name]
        for arg_name in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(test_function(**kwargs))
    return True


# =============================================================================
# FIXTURES - SAMPLE DATA
# =============================================================================

@pytest.fixture
def sample_valid_intent() -> Dict[str, Any]:
    """Valid intent JSON for testing."""
    return {
        "intent": "OPEN_APP",
        "slots": {"app": "chrome"},
        "confidence": 0.9,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def sample_invalid_intent_missing_field() -> Dict[str, Any]:
    """Invalid intent JSON - missing intent field."""
    return {
        "slots": {"app": "chrome"},
        "confidence": 0.9,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def sample_invalid_intent_wrong_type() -> Dict[str, Any]:
    """Invalid intent JSON - wrong intent type."""
    return {
        "intent": "INVALID_INTENT",
        "slots": {"app": "chrome"},
        "confidence": 0.9,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def sample_invalid_intent_missing_slots() -> Dict[str, Any]:
    """Invalid intent JSON - missing required slots."""
    return {
        "intent": "OPEN_APP",
        "slots": {},
        "confidence": 0.9,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def sample_low_confidence_intent() -> Dict[str, Any]:
    """Intent with low confidence."""
    return {
        "intent": "OPEN_APP",
        "slots": {"app": "chrome"},
        "confidence": 0.5,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def sample_multi_step_intent() -> Dict[str, Any]:
    """Multi-step intent JSON."""
    return {
        "intent": "MULTI_STEP",
        "steps": [
            {"intent": "OPEN_APP", "slots": {"app": "chrome"}},
            {"intent": "SEARCH_WEB", "slots": {"query": "youtube"}},
        ],
        "confidence": 0.95,
        "normalized_text": "open chrome and search youtube"
    }


@pytest.fixture
def sample_search_web_intent() -> Dict[str, Any]:
    """Search web intent."""
    return {
        "intent": "SEARCH_WEB",
        "slots": {"query": "python tutorial"},
        "confidence": 0.88,
        "normalized_text": "search python tutorial"
    }


@pytest.fixture
def sample_unknown_intent() -> Dict[str, Any]:
    """Unknown intent."""
    return {
        "intent": "UNKNOWN",
        "slots": {},
        "confidence": 0.3,
        "normalized_text": "unintelligible scribble"
    }


# =============================================================================
# FIXTURES - CONSISTENCY ENGINE DATA
# =============================================================================

@pytest.fixture
def sample_unanimous_candidates() -> List[Dict[str, Any]]:
    """Three candidates with unanimous agreement."""
    return [
        {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.9,
            "normalized_text": "open chrome",
            "variant": "original"
        },
        {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.85,
            "normalized_text": "open chrome",
            "variant": "rotated_90"
        },
        {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.88,
            "normalized_text": "open chrome",
            "variant": "rotated_270"
        },
    ]


@pytest.fixture
def sample_majority_candidates() -> List[Dict[str, Any]]:
    """Three candidates with 2:1 majority."""
    return [
        {
            "intent": "OPEN_APP",
            "slots": {"app": "brave"},
            "confidence": 0.9,
            "normalized_text": "open brave",
            "variant": "original"
        },
        {
            "intent": "OPEN_APP",
            "slots": {"app": "brave"},
            "confidence": 0.85,
            "normalized_text": "open brave",
            "variant": "rotated_90"
        },
        {
            "intent": "OPEN_APP",
            "slots": {"app": "naver"},
            "confidence": 0.7,
            "normalized_text": "open naver",
            "variant": "rotated_270"
        },
    ]


@pytest.fixture
def sample_conflicting_candidates() -> List[Dict[str, Any]]:
    """Three candidates with complete disagreement."""
    return [
        {
            "intent": "OPEN_APP",
            "slots": {"app": "chrome"},
            "confidence": 0.8,
            "normalized_text": "open chrome",
            "variant": "original"
        },
        {
            "intent": "SEARCH_WEB",
            "slots": {"query": "chrome"},
            "confidence": 0.75,
            "normalized_text": "search chrome",
            "variant": "rotated_90"
        },
        {
            "intent": "TYPE_TEXT",
            "slots": {"text": "chrome"},
            "confidence": 0.7,
            "normalized_text": "type chrome",
            "variant": "rotated_270"
        },
    ]


# =============================================================================
# FIXTURES - MOCKED INSTANCES
# =============================================================================

@pytest.fixture
def mock_model_response_valid() -> Dict[str, Any]:
    """Mock valid model response."""
    return {
        "intent": "OPEN_APP",
        "slots": {"app": "chrome"},
        "confidence": 0.9,
        "normalized_text": "open chrome"
    }


@pytest.fixture
def mock_model_response_invalid_json() -> str:
    """Mock invalid JSON response."""
    return "This is not valid JSON {intent: OPEN_APP"


@pytest.fixture
def mock_model_response_malformed() -> str:
    """Mock malformed JSON response."""
    return '{"intent": "OPEN_APP", "slots": {"app": "chrome"'


@pytest.fixture
def mock_gemini_api():
    """Mock Gemini API calls."""
    with patch("agent.core.hardened_pipeline.call_gemini_with_retry") as mock:
        async def async_return(image_url, api_key):
            return (
                {
                    "intent": "OPEN_APP",
                    "slots": {"app": "chrome"},
                    "confidence": 0.9,
                    "normalized_text": "open chrome"
                },
                None
            )
        mock.side_effect = async_return
        yield mock


@pytest.fixture
def mock_qwen_api():
    """Mock Qwen API calls."""
    with patch("agent.core.hardened_pipeline.call_qwen_with_retry") as mock:
        async def async_return(image_url, api_key):
            return (
                {
                    "intent": "OPEN_APP",
                    "slots": {"app": "chrome"},
                    "confidence": 0.85,
                    "normalized_text": "open chrome"
                },
                None
            )
        mock.side_effect = async_return
        yield mock


# =============================================================================
# FIXTURES - COMPONENT INSTANCES
# =============================================================================

@pytest.fixture
def json_validator():
    """JSONValidator instance."""
    from agent.core.json_validator import JSONValidator
    return JSONValidator()


@pytest.fixture
def consistency_engine():
    """ConsistencyEngine instance."""
    from agent.core.consistency_engine import ConsistencyEngine
    return ConsistencyEngine()


@pytest.fixture
def trust_evaluator():
    """TrustEvaluator instance."""
    from agent.core.trust_evaluator import TrustEvaluator
    return TrustEvaluator()


@pytest.fixture
def planner_instance():
    """Planner instance."""
    from agent.core.planner import ExecutionPlanner
    return ExecutionPlanner()


# =============================================================================
# EVENT LOOP SETUP
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
