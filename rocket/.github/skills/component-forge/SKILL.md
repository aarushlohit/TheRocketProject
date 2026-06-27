---
name: component-forge
description: 'Build production-grade UI components with all states (loading, empty, error, success, idle), TypeScript strict, WCAG 2.2 accessibility, and compound component patterns. Use when: create component, build component, React component, Vue component, Svelte component, UI component, button component, modal component, form component, accessible component, component library.'
---

# Component Forge

Build components that survive every state, at every screen size, under every edge case.

## Component States

Every component must handle all applicable states:

| State | Description |
|-------|-------------|
| **Idle** | Default appearance with no interaction |
| **Loading** | Show a spinner/skeleton while data fetches |
| **Empty** | Graceful display when there's no data |
| **Error** | Friendly error message with retry option |
| **Success** | Confirmation of successful action |
| **Disabled** | Grayed out, non-interactive |
| **Focus** | Visible focus ring for keyboard navigation |
| **Active** | Currently being interacted with |

## Component Design Patterns

### Compound Components

```tsx
<Select>
  <Select.Label>Country</Select.Label>
  <Select.Trigger>
    <Select.Value placeholder="Choose..." />
  </Select.Trigger>
  <Select.Options>
    <Select.Option value="us">United States</Select.Option>
    <Select.Option value="ca">Canada</Select.Option>
  </Select.Options>
</Select>
```

### Polymorphic Components

Allow `as` prop to render as different HTML elements while maintaining type safety.

### Controlled & Uncontrolled

Support both controlled (state managed by parent) and uncontrolled (internal state) usage.

## Accessibility (WCAG 2.2)

- All interactive elements must be keyboard accessible.
- Use proper ARIA roles, states, and properties.
- Ensure focus order follows visual order.
- Support `prefers-reduced-motion` for animations.
- Maintain 4.5:1 contrast ratio for text.
- Test with screen readers (VoiceOver, NVDA, JAWS).
