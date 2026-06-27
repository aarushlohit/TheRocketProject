---
name: playwright
description: 'Test web applications using Playwright — browser automation, E2E testing, component testing, visual regression, and debugging. Use when: Playwright, browser test, E2E test, web automation, browser automation, end-to-end test, visual regression test.'
---

# Playwright

Browser automation and testing with Playwright.

## Setup

```bash
npm init playwright@latest
# Or install manually:
npm install @playwright/test
npx playwright install
```

## Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('User Login', () => {
  test('should log in with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'correct-password');
    await page.click('[data-testid="submit"]');
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="welcome"]')).toContainText('Welcome');
  });
});
```

## Best Practices

- Use `data-testid` attributes for selectors — never rely on CSS classes or text content.
- Test user flows, not implementation details.
- Use `page.waitForURL()`, `page.waitForResponse()`, `page.waitForSelector()` over fixed timeouts.
- Run tests in CI with `npx playwright test --ci`.
- Use `--project=chromium` for faster local runs, all browsers in CI.
- Visual regression: `await expect(page).toHaveScreenshot()`.
- Component testing (React/Vue/Svelte): use `@playwright/experimental-ct-*`.
