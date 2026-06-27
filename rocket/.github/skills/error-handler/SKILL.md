---
name: error-handler
description: 'Design robust error handling strategies for applications — typed errors, graceful degradation, retry logic, and observability. Use when: error handling, exception handling, error recovery, fault tolerance, graceful degradation, retry logic, circuit breaker.'
---

# Error Handler

Design error handling that makes failures visible, debuggable, and recoverable.

## Principles

1. **Errors are data** — model them as types, not strings. Use enums, sealed classes, or Result types.
2. **Fail fast at boundaries** — validate inputs early, catch surprises close to the source.
3. **Never swallow errors** — every caught exception must be logged, wrapped, or re-raised.
4. **Degrade gracefully** — a failing feature should never take down the whole app.

## Error Handling Patterns

### 1. Typed Errors (Preferred)

```python
class OrderError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)

class OrderNotFoundError(OrderError): ...
class InsufficientInventoryError(OrderError): ...
```

### 2. Result Type (Functional)

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Ok(Generic[T]):
    value: T

@dataclass
class Err(Generic[E]):
    error: E

Result = Ok[T] | Err[E]
```

### 3. Retry with Exponential Backoff

```python
import time
from functools import wraps

def retry(max_attempts=3, base_delay=1, max_delay=30):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_error = e
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
            raise last_error
        return wrapper
    return decorator
```

## Observability

- Log errors with: error type, message, stack trace, correlation ID, and relevant context.
- Use structured logging (JSON) — not `print()`.
- Track error rates and types in monitoring (Datadog, Grafana, Sentry).
- Alert on error rate spikes, not individual errors.
