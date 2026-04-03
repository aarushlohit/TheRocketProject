"""Circuit Breaker pattern for fault-tolerant model calls.

Prevents cascading failures by temporarily disabling failed models.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ModelHealth:
    """Track health state for a single model."""
    
    consecutive_fails: int = 0
    disabled_until: float = 0.0
    total_failures: int = 0
    total_successes: int = 0
    last_error: str = ""


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for model calls.
    
    Disables a model temporarily after consecutive failures.
    """
    
    # Config
    failure_threshold: int = 3  # Failures before disabling
    cooldown_seconds: float = 60.0  # Time to wait before retry
    
    # State
    models: Dict[str, ModelHealth] = field(default_factory=dict)
    
    def __post_init__(self):
        # Initialize known models
        self.models["gemini"] = ModelHealth()
        self.models["qwen"] = ModelHealth()
    
    def is_available(self, model: str) -> bool:
        """Check if model is available (not in cooldown)."""
        health = self.models.get(model, ModelHealth())
        
        if health.disabled_until > time.time():
            remaining = health.disabled_until - time.time()
            print(f"[CIRCUIT BREAKER] {model} disabled for {remaining:.1f}s more")
            return False
        
        return True
    
    def record_success(self, model: str) -> None:
        """Record successful model call."""
        health = self.models.get(model, ModelHealth())
        health.consecutive_fails = 0
        health.total_successes += 1
        self.models[model] = health
        print(f"[CIRCUIT BREAKER] {model} success (total: {health.total_successes})")
    
    def record_failure(self, model: str, error: str) -> bool:
        """
        Record failed model call.
        
        Returns True if model is now disabled.
        """
        health = self.models.get(model, ModelHealth())
        health.consecutive_fails += 1
        health.total_failures += 1
        health.last_error = error
        
        print(f"[CIRCUIT BREAKER] {model} failed ({health.consecutive_fails}/{self.failure_threshold})")
        
        # Check if we should disable
        if health.consecutive_fails >= self.failure_threshold:
            health.disabled_until = time.time() + self.cooldown_seconds
            print(f"[CIRCUIT BREAKER] ⚠️ {model} DISABLED for {self.cooldown_seconds}s")
            self.models[model] = health
            return True
        
        self.models[model] = health
        return False
    
    def get_status(self) -> dict:
        """Get current status of all models."""
        now = time.time()
        status = {}
        
        for name, health in self.models.items():
            is_disabled = health.disabled_until > now
            status[name] = {
                "available": not is_disabled,
                "consecutive_fails": health.consecutive_fails,
                "total_failures": health.total_failures,
                "total_successes": health.total_successes,
                "disabled_for": max(0, health.disabled_until - now) if is_disabled else 0,
                "last_error": health.last_error,
            }
        
        return status
    
    def reset(self, model: str = None) -> None:
        """Reset circuit breaker state."""
        if model:
            self.models[model] = ModelHealth()
        else:
            self.models = {
                "gemini": ModelHealth(),
                "qwen": ModelHealth(),
            }


# Global circuit breaker instance
CIRCUIT_BREAKER = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    """Get the global circuit breaker."""
    return CIRCUIT_BREAKER
