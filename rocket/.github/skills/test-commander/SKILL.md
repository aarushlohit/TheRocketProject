---
name: test-commander
description: 'Generate unit, integration, E2E, and visual regression tests following the Testing Trophy methodology (80% integration, 10% unit, 10% E2E). Use when: write tests, unit test, integration test, E2E test, test coverage, Vitest, Jest, Playwright test, Testing Library, MSW, mock API, visual regression, test setup.'
---

# Test Commander

Tests that catch real bugs. Following the Testing Trophy (Kent C. Dodds): 80% integration, 10% unit, 10% E2E.

## Testing Strategy

```
        /\
       /E2E\        ← 2-3 critical flows
      /------\
     / Visual \     ← Visual regression on key components
    /----------\
   /Integration\    ← 80% of tests. Components + API + store.
  /--------------\
 /     Unit       \ ← Pure logic. Utils, helpers, formatters.
/------------------\
```

## 1. Unit Tests (10%)

- Pure functions, utilities, formatters, data transformations.
- No mocks needed — test inputs and outputs.
- Fast and deterministic.

## 2. Integration Tests (80%)

- Components with their dependencies (API, store, router).
- Mock external services (HTTP, database) at the boundary.
- Use MSW for API mocking, Testing Library for DOM queries.
- Test user flows, not implementation details.

## 3. E2E Tests (10%)

- Critical user journeys only (signup, checkout, core workflow).
- Use Playwright or Cypress.
- Run against a real/staged backend.

## 4. Visual Regression

- Use Chromatic, Percy, or Playwright screenshot tests.
- Test key components and pages at different viewports.
- Set a baseline and review every diff.

## Patterns

- **Test factories**: use Faker to generate realistic test data.
- **Arrange-Act-Assert**: structure every test with clear sections.
- **Test behavior, not implementation**: don't test private methods or internal state.
- **One assertion per test** (or a logical group of related assertions).
