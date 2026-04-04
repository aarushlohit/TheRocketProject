"""
Stage 5 — Goal Expander Tests.

Tests for goal-based execution:
- High-level goal detection
- Goal type identification
- Goal expansion to multi-step
- Search query normalization
- Compound input splitting
"""

import pytest


class TestGoalDetection:
    """Tests for detecting high-level goals."""
    
    def test_detect_watch_goal(self):
        """Detect 'watch' goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("watch cat videos") is True
        assert is_high_level_goal("watch youtube") is True
        assert is_high_level_goal("watch a movie") is True
    
    def test_detect_play_goal(self):
        """Detect 'play' goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("play some music") is True
        assert is_high_level_goal("play spotify") is True
        assert is_high_level_goal("listen to songs") is True
    
    def test_detect_search_goal(self):
        """Detect 'search/find' goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("find python tutorials") is True
        assert is_high_level_goal("look for recipes") is True
        assert is_high_level_goal("search for documentation") is True
    
    def test_detect_check_goal(self):
        """Detect 'check' goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("check email") is True
        assert is_high_level_goal("check the news") is True
    
    def test_detect_browse_goal(self):
        """Detect 'browse/goto' goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("browse reddit") is True
        assert is_high_level_goal("go to youtube") is True
        assert is_high_level_goal("visit github") is True
    
    def test_not_goal_direct_command(self):
        """Direct commands should not be detected as goals."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("open chrome") is False
        assert is_high_level_goal("type hello") is False
        assert is_high_level_goal("click button") is False
    
    def test_not_goal_empty(self):
        """Empty input should not be a goal."""
        from agent.core.goal_expander import is_high_level_goal
        
        assert is_high_level_goal("") is False
        assert is_high_level_goal(None) is False


class TestGoalTypeDetection:
    """Tests for identifying goal type."""
    
    def test_detect_goal_type_watch(self):
        """Identify watch goal type."""
        from agent.core.goal_expander import detect_goal_type
        
        result = detect_goal_type("watch cat videos")
        assert result is not None
        assert result[0] == "watch"
        assert result[1] == "cat videos"
    
    def test_detect_goal_type_play(self):
        """Identify play goal type."""
        from agent.core.goal_expander import detect_goal_type
        
        result = detect_goal_type("play music")
        assert result is not None
        assert result[0] == "play"
        assert result[1] == "music"
    
    def test_detect_goal_type_search(self):
        """Identify search goal type."""
        from agent.core.goal_expander import detect_goal_type
        
        result = detect_goal_type("find python tutorials")
        assert result is not None
        assert result[0] == "search"
        assert result[1] == "python tutorials"
    
    def test_detect_goal_type_goto(self):
        """Identify goto goal type."""
        from agent.core.goal_expander import detect_goal_type
        
        result = detect_goal_type("go to youtube")
        assert result is not None
        assert result[0] == "goto"
        assert result[1] == "youtube"
    
    def test_detect_goal_type_none(self):
        """Non-goal should return None."""
        from agent.core.goal_expander import detect_goal_type
        
        result = detect_goal_type("open chrome")
        assert result is None


class TestGoalExpansion:
    """Tests for expanding goals to multi-step plans."""
    
    def test_expand_watch_youtube_goal(self):
        """Expand 'watch youtube videos' goal."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("watch youtube videos")
        
        assert result.is_goal is True
        assert result.goal_type == "watch"
        assert len(result.steps) >= 2
        
        # Should include OPEN_APP or OPEN_URL
        intents = [s["intent"] for s in result.steps]
        assert "OPEN_APP" in intents or "OPEN_URL" in intents
    
    def test_expand_check_email_goal(self):
        """Expand 'check email' goal."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("check email")
        
        assert result.is_goal is True
        assert len(result.steps) >= 2
        
        # Should include gmail URL
        has_gmail = any(
            "gmail" in str(s.get("slots", {})).lower()
            for s in result.steps
        )
        assert has_gmail
    
    def test_expand_search_goal(self):
        """Expand 'find python tutorials' goal."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("find python tutorials")
        
        assert result.is_goal is True
        assert len(result.steps) >= 1
        
        intents = [s["intent"] for s in result.steps]
        assert "SEARCH_WEB" in intents
    
    def test_expand_with_context(self):
        """Expand goal with browser context."""
        from agent.core.goal_expander import expand_goal
        
        context = {"last_browser": "chrome"}
        result = expand_goal("search something", context)
        
        assert result.is_goal is True
        assert len(result.steps) >= 1
        
        # With browser open, should not add OPEN_APP
        intents = [s["intent"] for s in result.steps]
        # First intent should be SEARCH_WEB if browser is open
        if len(intents) == 1:
            assert intents[0] == "SEARCH_WEB"
    
    def test_expand_non_goal_returns_empty(self):
        """Non-goal should return empty expansion."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("open chrome")
        
        assert result.is_goal is False
        assert len(result.steps) == 0


class TestSearchNormalization:
    """Tests for search query normalization."""
    
    def test_normalize_removes_search_prefix(self):
        """Remove 'search' prefix."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("search github") == "github"
        assert normalize_search_query("search for python") == "python"
    
    def test_normalize_removes_find_prefix(self):
        """Remove 'find' prefix."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("find tutorials") == "tutorials"
    
    def test_normalize_removes_look_for(self):
        """Remove 'look for' prefix."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("look for recipes") == "recipes"
    
    def test_normalize_removes_google(self):
        """Remove 'google' prefix."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("google machine learning") == "machine learning"
    
    def test_normalize_keeps_clean_query(self):
        """Clean queries should remain unchanged."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("python tutorials") == "python tutorials"
    
    def test_normalize_empty(self):
        """Empty input should return empty."""
        from agent.core.goal_expander import normalize_search_query
        
        assert normalize_search_query("") == ""


class TestMultiStepDetection:
    """Tests for detecting multi-step commands."""
    
    def test_detect_and_keyword(self):
        """Detect 'and' keyword."""
        from agent.core.goal_expander import contains_multiple_actions
        
        assert contains_multiple_actions("open chrome and search youtube") is True
    
    def test_detect_then_keyword(self):
        """Detect 'then' keyword."""
        from agent.core.goal_expander import contains_multiple_actions
        
        assert contains_multiple_actions("open chrome then search youtube") is True
    
    def test_detect_after_that_keyword(self):
        """Detect 'after that' keyword."""
        from agent.core.goal_expander import contains_multiple_actions
        
        assert contains_multiple_actions("open chrome after that search youtube") is True
    
    def test_detect_single_action(self):
        """Single action should return False."""
        from agent.core.goal_expander import contains_multiple_actions
        
        assert contains_multiple_actions("open chrome") is False
        assert contains_multiple_actions("search youtube") is False


class TestCompoundInputSplitting:
    """Tests for splitting compound inputs."""
    
    def test_split_by_and(self):
        """Split by 'and' keyword."""
        from agent.core.goal_expander import split_compound_input
        
        result = split_compound_input("open chrome and search youtube")
        
        assert len(result) == 2
        assert result[0] == "open chrome"
        assert result[1] == "search youtube"
    
    def test_split_by_then(self):
        """Split by 'then' keyword."""
        from agent.core.goal_expander import split_compound_input
        
        result = split_compound_input("open chrome then search youtube")
        
        assert len(result) == 2
    
    def test_split_single_action(self):
        """Single action should return single item list."""
        from agent.core.goal_expander import split_compound_input
        
        result = split_compound_input("open chrome")
        
        assert len(result) == 1
        assert result[0] == "open chrome"


class TestGoalExpansionResult:
    """Tests for GoalExpansionResult structure."""
    
    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("watch youtube")
        
        assert hasattr(result, "is_goal")
        assert hasattr(result, "goal_type")
        assert hasattr(result, "extracted_subject")
        assert hasattr(result, "steps")
        assert hasattr(result, "confidence")
    
    def test_result_metadata(self):
        """Result should include metadata."""
        from agent.core.goal_expander import expand_goal
        
        result = expand_goal("watch youtube", {"preferred_browser": "firefox"})
        
        assert "preferred_browser" in result.metadata


class TestKeywordToSiteMapping:
    """Tests for keyword to site mapping."""
    
    def test_youtube_mapping(self):
        """YouTube should map to youtube.com."""
        from agent.core.goal_expander import KEYWORD_TO_SITE
        
        assert KEYWORD_TO_SITE.get("youtube") == "youtube.com"
    
    def test_email_mapping(self):
        """Email should map to gmail.com."""
        from agent.core.goal_expander import KEYWORD_TO_SITE
        
        assert KEYWORD_TO_SITE.get("email") == "gmail.com"
    
    def test_music_mapping(self):
        """Music should map to spotify.com."""
        from agent.core.goal_expander import KEYWORD_TO_SITE
        
        assert KEYWORD_TO_SITE.get("music") == "spotify.com"
