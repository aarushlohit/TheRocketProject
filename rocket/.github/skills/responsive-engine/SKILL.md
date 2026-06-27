---
name: responsive-engine
description: 'Design multi-device layouts with Container Queries, clamp() fluid typography, :has() selector, subgrid, and modern CSS units. Use when: responsive design, responsive layout, mobile layout, container queries, fluid typography, clamp, mobile responsive, responsive grid, multi-device, subgrid.'
---

# Responsive Engine

Layouts that work at every screen size without breakpoint spaghetti.

## Core Principle

Responsive design is about containers, not viewports. Use Container Queries first, media queries only for global layout shifts and form factor detection.

## Container Queries (preferred over media queries)

```css
.card-grid {
  container-type: inline-size;
  container-name: card-grid;
}

@container card-grid (min-width: 600px) {
  .card {
    display: grid;
    grid-template-columns: 200px 1fr;
  }
}
```

## Fluid Typography with clamp()

```css
/* Heading: scales from 1.5rem (320px) to 3rem (1200px) */
h1 {
  font-size: clamp(1.5rem, 1rem + 2vw, 3rem);
}

/* Better: using a formula */
:root {
  --fluid-min: 320px;
  --fluid-max: 1200px;
}
h1 {
  font-size: clamp(
    1.5rem,
    1.5rem + (3 - 1.5) * ((100vw - 320px) / (1200 - 320)),
    3rem
  );
}
```

## Modern CSS Layout

- Use `:has()` for parent-aware styling: `.card:has(img) { grid-template-rows: auto 1fr; }`
- Use `subgrid` for aligned nested grids: `grid-template-rows: subgrid;`
- Use `dvh`/`svh`/`lvh` for dynamic viewport heights.
- Use `gap` on flexbox and grid containers instead of margins.

## Responsive Strategy

1. **Mobile-first** — base styles are mobile, add complexity with `min-width` queries.
2. **Container Queries** — for component-level responsiveness.
3. **Media Queries** — only for global layout (sidebar, header, footer).
4. **Test** — at 320px, 768px, 1024px, 1440px, and actual device widths.
