"""Custom exceptions for Rocket Agent."""


class RocketException(Exception):
    """Base exception for all Rocket errors."""

    pass


class SkillError(RocketException):
    """Error related to skills."""

    pass


class SkillNotFoundError(SkillError):
    """Requested skill not found."""

    pass


class SkillExecutionError(SkillError):
    """Skill execution failed."""

    pass


class SkillValidationError(SkillError):
    """Skill parameters invalid."""

    pass


class PlatformError(RocketException):
    """Error related to platform adapter."""

    pass


class NLUError(RocketException):
    """Error in NLU/intent parsing."""

    pass


class IntentError(NLUError):
    """Intent parse/validation failed."""

    pass


class AmbiguousIntentError(NLUError):
    """Intent is ambiguous, needs clarification."""

    pass


class ConnectionError(RocketException):
    """WebSocket or network connection error."""

    pass


class ConfigurationError(RocketException):
    """Configuration loading/validation error."""

    pass


class TimeoutError(RocketException):
    """Operation timed out."""

    pass
