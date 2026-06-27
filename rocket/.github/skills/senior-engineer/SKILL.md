---
name: senior-engineer
description: 'Apply senior software engineering standards when writing, editing, or refactoring code. Use when: senior engineer, production code, production-grade, write quality code, robust code, maintainable code, secure code, production quality.'
---

# Senior Engineer Coding

## Mindset

Write code for the next engineer who has to change it at 2am with no context. Clean code is risk management. Every production incident traces back to unclear, poorly structured, or hard-to-change code — not missing cleverness.

The standard: a teammate can safely change the code without fear, and explain what it does after a quick read.

## 1. Naming — Highest ROI Habit

Good names eliminate comments, prevent misunderstandings, and make refactoring safe.

- **Functions**: verb + noun (`getUserById`, `sendNotification`, `validateInput`). Avoid `processData`, `handleStuff`.
- **Booleans**: prefix with `is`, `has`, `can`, `should` (`isActive`, `hasPermission`, `canEdit`).
- **Classes/Entities**: noun phrases (`UserProfile`, `PaymentGateway`, `OrderRepository`).
- **Variables**: descriptive enough to stand alone — `userList` vs `list`. Use domain language (`invoice.total` not `invoice.x`).
- **Avoid abbreviations**: `idx` → `index`, `cfg` → `config`, `btn` → `button`. Clarity > brevity in names.

## 2. Function Design

- **Single responsibility**: each function does exactly one thing. If you need "and" in the name, split it.
- **Small by default**: if a function exceeds 20-30 lines, extract helper functions.
- **Predictable**: same inputs → same outputs (pure where possible). Minimize side effects.
- **Error states are part of the signature**: return `Optional[T]`, `Result[T, E]`, or throw typed exceptions. Never silently return `None`/`null` for errors.
- **Early returns**: validate inputs at the top, fail fast, then proceed with the happy path.

## 3. Error Handling

- Never trust external data — validate every input at the boundary.
- Every function should have a defined error state. If it can fail, the caller needs to know.
- Use typed errors, not generic ones. Prefer custom exception classes or result types.
- Log errors with context. Include enough info to debug without guessing.
- Fail gracefully — no crash should take down the entire process.

## 4. Code Organization

- Group related code together. Files should have one clear purpose.
- Keep nesting ≤ 3 levels deep. Extract conditions into well-named variables.
- Avoid flag arguments — split into two functions instead.
- Prefer early returns and guard clauses over deep if-else chains.
