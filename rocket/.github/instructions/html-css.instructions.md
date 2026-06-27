---
description: 'Use when writing HTML, CSS, or building web frontends. Covers semantic HTML, modern CSS, responsive design, and accessibility standards.'
applyTo: "**/*.{html,css,scss}"
---

# HTML & CSS Conventions

## HTML
- Use semantic HTML elements (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`).
- Every form input must have an associated `<label>`.
- Use `alt` attributes on all images.
- Maintain a logical heading hierarchy (h1 → h2 → h3, never skip levels).

## CSS
- Use CSS Custom Properties (variables) for colors, spacing, and typography.
- Prefer Container Queries over Media Queries for component-level responsiveness.
- Use `clamp()` for fluid typography and spacing.
- Avoid `!important` — use specificity instead.
- Use logical properties (`margin-inline`, `padding-block`) for better RTL support.

## Accessibility
- All interactive elements need visible focus styles.
- Color is never the only indicator of state.
- Touch targets: minimum 44x44px.
- Support `prefers-reduced-motion`.
- Test with keyboard navigation (Tab, Enter, Escape, Arrow keys).
