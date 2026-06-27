---
description: 'Use when writing Python code, editing .py files, or working on Python backend. Covers type hints, dataclasses, pathlib, error handling, and project conventions.'
applyTo: "**/*.py"
---

# Python Coding Conventions

## Style & Types
- **Type hints** on all function signatures and public attributes.
- Use `pathlib.Path` over `os.path` for all file operations.
- Favor `dataclasses` over plain dicts for structured data.
- Use `enum.Enum` or `enum.StrEnum` for enumerated constants.
- Prefer `|` union syntax (`str | None`) over `Optional[str]`.

## Error Handling
- Define custom exception classes for domain errors.
- Use `Result[T, E]` pattern or typed exceptions — never silent `None` returns.
- Log errors with context via `structlog` or standard `logging`.

## Imports
- Group: standard library → third-party → local modules (alphabetical within groups).
- Use absolute imports within the project package.
- Avoid `from module import *`.

## Project-Specific
- Virtual env at `.venv/`. Run `python -m agent.main` to start.
- Tests live in `tests/` and use `pytest`.
- See `requirements.txt` for dependencies.
