---
name: aesthetic-web
description: 'Apply professional, premium UI/UX design standards when building or styling web interfaces. Use when: make it look better, make it beautiful, design system, UI design, web design, visual design, premium design, styling, interface design, typography, color palette.'
---

# Aesthetic Web Design

Professional, premium design standards for web interfaces.

## Register Distinction

Every design task is either **Brand** or **Product**:

| Register | Scope | Bar |
|----------|-------|-----|
| **Brand** | Marketing, landing pages, portfolios, long-form content. Design IS the product. | Distinctiveness — must stand out from competitors. Full creative range. |
| **Product** | App UI, admin, dashboards, developer tools. Design SERVES the product. | Earned familiarity — users of Linear, Stripe, Vercel should trust it. Restrained. Clean. Fast. |

## Visual Hierarchy

1. **Size** — most important element gets the most visual weight.
2. **Whitespace** — use generous spacing around key elements.
3. **Color** — use accent color sparingly for interactive elements and key information.
4. **Typography** — use weight and size contrast between headings and body.

## Design Standards

- **Colors**: max 3 colors (primary, neutral, accent). Use semantic colors (success, warning, error) consistently.
- **Borders**: use subtle borders (1px, low contrast). Soften with border-radius (6-12px for cards, 4-8px for inputs).
- **Shadows**: use `box-shadow` sparingly. One elevation level for cards, one for modals/dropdowns.
- **Gradients**: subtle, single-hue gradients only. Never mix multiple saturated colors.
- **Icons**: use a consistent icon set (Lucide, Phosphor, Heroicons). Keep stroke weight uniform.
- **Dark mode**: reduce chroma by 30-50% for neutrals. Use 3-4 surface levels (base, raised, overlay, modal).

## Accessibility

- All interactive elements must have focus styles.
- Color is never the only indicator of state.
- Touch targets: minimum 44x44px.
- Support reduced motion: `@media (prefers-reduced-motion: reduce)`.
