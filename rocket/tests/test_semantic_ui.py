"""
Stage 5 — Semantic UI Tests.

Tests for semantic UI interaction system:
- Target normalization
- Click action parsing
- Target extraction from text
- Scroll direction parsing
"""

import pytest


class TestSemanticTargets:
    """Tests for semantic target validation and normalization."""
    
    def test_valid_targets_count(self):
        """Verify we have a good number of semantic targets."""
        from agent.core.semantic_ui import VALID_TARGETS
        
        assert len(VALID_TARGETS) >= 20
    
    def test_navigation_targets_exist(self):
        """Verify navigation targets exist."""
        from agent.core.semantic_ui import VALID_TARGETS
        
        expected = ["search bar", "address bar", "back button", "forward button"]
        for target in expected:
            assert target in VALID_TARGETS
    
    def test_action_targets_exist(self):
        """Verify action targets exist."""
        from agent.core.semantic_ui import VALID_TARGETS
        
        expected = ["play button", "pause button", "submit button", "login button"]
        for target in expected:
            assert target in VALID_TARGETS
    
    def test_form_targets_exist(self):
        """Verify form targets exist."""
        from agent.core.semantic_ui import VALID_TARGETS
        
        expected = ["text field", "password field", "dropdown", "checkbox"]
        for target in expected:
            assert target in VALID_TARGETS
    
    def test_result_targets_exist(self):
        """Verify result targets exist."""
        from agent.core.semantic_ui import VALID_TARGETS
        
        expected = ["first result", "second result", "third result"]
        for target in expected:
            assert target in VALID_TARGETS


class TestTargetNormalization:
    """Tests for target normalization."""
    
    def test_normalize_direct_match(self):
        """Direct matches should normalize correctly."""
        from agent.core.semantic_ui import normalize_target
        
        assert normalize_target("search bar") == "search bar"
        assert normalize_target("play button") == "play button"
    
    def test_normalize_alias_match(self):
        """Aliases should normalize to canonical name."""
        from agent.core.semantic_ui import normalize_target
        
        # "search field" → "search bar"
        result = normalize_target("search field")
        assert result == "search bar"
        
        # "url bar" → "address bar"
        result = normalize_target("url bar")
        assert result == "address bar"
    
    def test_normalize_case_insensitive(self):
        """Normalization should be case-insensitive."""
        from agent.core.semantic_ui import normalize_target
        
        assert normalize_target("Search Bar") == "search bar"
        assert normalize_target("PLAY BUTTON") == "play button"
    
    def test_normalize_with_extra_spaces(self):
        """Handle extra whitespace."""
        from agent.core.semantic_ui import normalize_target
        
        result = normalize_target("  search bar  ")
        assert result == "search bar"
    
    def test_normalize_unknown_target(self):
        """Unknown targets should return as-is."""
        from agent.core.semantic_ui import normalize_target
        
        result = normalize_target("custom element")
        assert result == "custom element"
    
    def test_normalize_empty_returns_none(self):
        """Empty string should return None."""
        from agent.core.semantic_ui import normalize_target
        
        assert normalize_target("") is None
        assert normalize_target(None) is None


class TestClickActions:
    """Tests for click action parsing."""
    
    def test_normalize_click_action_default(self):
        """Default action should be click."""
        from agent.core.semantic_ui import normalize_click_action, ClickAction
        
        assert normalize_click_action("") == ClickAction.CLICK
        assert normalize_click_action(None) == ClickAction.CLICK
    
    def test_normalize_click_action_valid(self):
        """Valid actions should normalize correctly."""
        from agent.core.semantic_ui import normalize_click_action, ClickAction
        
        assert normalize_click_action("click") == ClickAction.CLICK
        assert normalize_click_action("double_click") == ClickAction.DOUBLE_CLICK
        assert normalize_click_action("right_click") == ClickAction.RIGHT_CLICK
    
    def test_normalize_click_action_aliases(self):
        """Action aliases should normalize correctly."""
        from agent.core.semantic_ui import normalize_click_action, ClickAction
        
        assert normalize_click_action("double") == ClickAction.DOUBLE_CLICK
        assert normalize_click_action("right") == ClickAction.RIGHT_CLICK
        assert normalize_click_action("dblclick") == ClickAction.DOUBLE_CLICK


class TestTargetExtraction:
    """Tests for extracting targets from natural language."""
    
    def test_extract_from_click_command(self):
        """Extract target from click commands."""
        from agent.core.semantic_ui import extract_target_from_text
        
        result = extract_target_from_text("click on the play button")
        assert result == "play button"
    
    def test_extract_from_tap_command(self):
        """Extract target from tap commands."""
        from agent.core.semantic_ui import extract_target_from_text
        
        result = extract_target_from_text("tap the search bar")
        assert result == "search bar"
    
    def test_extract_first_result(self):
        """Extract 'first result' target."""
        from agent.core.semantic_ui import extract_target_from_text
        
        result = extract_target_from_text("click on the first result")
        assert result == "first result"
    
    def test_extract_returns_none_for_empty(self):
        """Empty input should return None."""
        from agent.core.semantic_ui import extract_target_from_text
        
        assert extract_target_from_text("") is None
        assert extract_target_from_text(None) is None


class TestScrollDirection:
    """Tests for scroll direction parsing."""
    
    def test_parse_scroll_up(self):
        """Parse scroll up direction."""
        from agent.core.semantic_ui import parse_scroll_direction, ScrollDirection
        
        assert parse_scroll_direction("scroll up") == ScrollDirection.UP
        assert parse_scroll_direction("go up") == ScrollDirection.UP
    
    def test_parse_scroll_down(self):
        """Parse scroll down direction."""
        from agent.core.semantic_ui import parse_scroll_direction, ScrollDirection
        
        assert parse_scroll_direction("scroll down") == ScrollDirection.DOWN
        assert parse_scroll_direction("go down") == ScrollDirection.DOWN
    
    def test_parse_scroll_default(self):
        """Default scroll direction should be down."""
        from agent.core.semantic_ui import parse_scroll_direction, ScrollDirection
        
        assert parse_scroll_direction("scroll") == ScrollDirection.DOWN
        assert parse_scroll_direction("") == ScrollDirection.DOWN


class TestBuildClickIntent:
    """Tests for building click intents."""
    
    def test_build_basic_click(self):
        """Build basic click intent."""
        from agent.core.semantic_ui import build_click_intent
        
        result = build_click_intent("play button")
        
        assert result["intent"] == "CLICK_ELEMENT"
        assert result["slots"]["target"] == "play button"
        assert result["slots"]["action"] == "click"
        assert result["confidence"] == 0.9
    
    def test_build_double_click(self):
        """Build double-click intent."""
        from agent.core.semantic_ui import build_click_intent
        
        result = build_click_intent("file icon", action="double_click")
        
        assert result["slots"]["action"] == "double_click"
    
    def test_build_with_custom_confidence(self):
        """Build click with custom confidence."""
        from agent.core.semantic_ui import build_click_intent
        
        result = build_click_intent("button", confidence=0.75)
        
        assert result["confidence"] == 0.75


class TestTargetCategories:
    """Tests for target category retrieval."""
    
    def test_get_targets_by_category_navigation(self):
        """Get navigation targets."""
        from agent.core.semantic_ui import get_targets_by_category
        
        targets = get_targets_by_category("navigation")
        assert len(targets) > 0
        
        names = [t.name for t in targets]
        assert "search bar" in names
        assert "back button" in names
    
    def test_get_targets_by_category_action(self):
        """Get action targets."""
        from agent.core.semantic_ui import get_targets_by_category
        
        targets = get_targets_by_category("action")
        assert len(targets) > 0
        
        names = [t.name for t in targets]
        assert "play button" in names
        assert "submit button" in names
    
    def test_get_targets_by_category_form(self):
        """Get form targets."""
        from agent.core.semantic_ui import get_targets_by_category
        
        targets = get_targets_by_category("form")
        assert len(targets) > 0
        
        names = [t.name for t in targets]
        assert "text field" in names


class TestTargetInfo:
    """Tests for getting target information."""
    
    def test_get_target_info_valid(self):
        """Get info for valid target."""
        from agent.core.semantic_ui import get_target_info
        
        info = get_target_info("search bar")
        
        assert info is not None
        assert info.name == "search bar"
        assert info.category == "navigation"
    
    def test_get_target_info_via_alias(self):
        """Get info via alias."""
        from agent.core.semantic_ui import get_target_info
        
        info = get_target_info("search field")
        
        assert info is not None
        assert info.name == "search bar"
    
    def test_get_target_info_invalid(self):
        """Invalid target returns None."""
        from agent.core.semantic_ui import get_target_info
        
        info = get_target_info("nonexistent target")
        
        assert info is None


class TestValidSemanticTarget:
    """Tests for semantic target validation."""
    
    def test_is_valid_semantic_target_true(self):
        """Valid targets should return True."""
        from agent.core.semantic_ui import is_valid_semantic_target
        
        assert is_valid_semantic_target("search bar") is True
        assert is_valid_semantic_target("play button") is True
        assert is_valid_semantic_target("first result") is True
    
    def test_is_valid_semantic_target_via_alias(self):
        """Aliases should also be valid."""
        from agent.core.semantic_ui import is_valid_semantic_target
        
        assert is_valid_semantic_target("search field") is True
        assert is_valid_semantic_target("url bar") is True
    
    def test_is_valid_semantic_target_false(self):
        """Invalid targets should return False."""
        from agent.core.semantic_ui import is_valid_semantic_target
        
        assert is_valid_semantic_target("") is False
        assert is_valid_semantic_target(None) is False
