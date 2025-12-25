<!-- category: qa -->
<!-- keywords: accessibility, wcag, a11y, aria, keyboard, screen-reader, contrast -->

# WCAG 2.2 Accessibility Review Standards

## Quick Reference: Critical Checkpoints

### WCAG 2.2 Level AA Requirements

| Criterion | Requirement | Test Method |
|-----------|-------------|-------------|
| 1.1.1 Non-text Content | All images have alt text | Inspect `<img>` tags |
| 1.4.3 Contrast | 4.5:1 normal, 3:1 large text | Chrome DevTools |
| 2.1.1 Keyboard | All functionality via keyboard | Tab through page |
| 2.4.7 Focus Visible | Visible focus indicators | Tab and observe |
| 2.5.8 Target Size | 24×24px minimum (NEW in 2.2) | Measure touch targets |
| 4.1.2 Name, Role, Value | ARIA attributes correct | axe-core scan |

---

## 1. Semantic HTML Requirements

### MUST Use Semantic Elements

```tsx
// ❌ WRONG - div soup
<div class="header">
  <div class="nav">
    <div class="link">Home</div>
  </div>
</div>

// ✅ CORRECT - semantic HTML
<header>
  <nav aria-label="Main navigation">
    <a href="/">Home</a>
  </nav>
</header>
```

### Required Semantic Structure

- `<header>` - Page/section header
- `<nav>` - Navigation blocks (with aria-label if multiple)
- `<main>` - One per page, main content
- `<section>` - Thematic grouping (with heading)
- `<article>` - Self-contained content
- `<aside>` - Complementary content
- `<footer>` - Footer content

### Heading Hierarchy

```tsx
// ❌ WRONG - skipped levels
<h1>Page Title</h1>
<h3>Section</h3>  // Skipped h2!

// ✅ CORRECT - sequential
<h1>Page Title</h1>
<h2>Section</h2>
<h3>Subsection</h3>
```

---

## 2. Color Contrast Requirements

### Minimum Ratios (WCAG 2.2 AA)

| Text Type | Minimum Ratio | Example |
|-----------|---------------|---------|
| Normal text (<18px, or <14px bold) | 4.5:1 | #767676 on white |
| Large text (≥18px, or ≥14px bold) | 3:1 | #949494 on white |
| UI components & graphics | 3:1 | Borders, icons |
| Focus indicators | 3:1 | Outline color |

### Testing in Chrome DevTools

1. Right-click element → Inspect
2. In Styles panel, click color swatch
3. Look for contrast ratio display
4. ⚠️ if below minimum, ✅ if passing

### OKLCH Contrast Calculation

```css
/* Use OKLCH for perceptually accurate contrast */
:root {
  --text-primary: oklch(20% 0 0);      /* L=20%, very dark */
  --text-secondary: oklch(45% 0 0);    /* L=45%, medium */
  --background: oklch(98% 0 0);        /* L=98%, near white */
}

/* Contrast ratio ≈ (L_light + 0.05) / (L_dark + 0.05) */
/* 98% vs 20% ≈ (0.98 + 0.05) / (0.20 + 0.05) = 4.12:1 */
```

---

## 3. Keyboard Navigation

### Required Keyboard Interactions

| Element | Enter | Space | Escape | Arrows |
|---------|-------|-------|--------|--------|
| Link | Activate | - | - | - |
| Button | Activate | Activate | - | - |
| Checkbox | - | Toggle | - | - |
| Radio | - | Select | - | Navigate |
| Select | Open | Open | Close | Navigate |
| Dialog | - | - | Close | - |
| Menu | - | - | Close | Navigate |
| Tabs | - | - | - | Switch tab |

### Focus Management

```tsx
// ✅ Proper focus trapping in modal
import { FocusTrap } from '@radix-ui/react-focus-trap';

<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <FocusTrap>
    <DialogContent>
      {/* Focus trapped here */}
      <button autoFocus>First focusable</button>
    </DialogContent>
  </FocusTrap>
</Dialog>
```

### Focus Indicator Requirements

```css
/* ❌ WRONG - removed focus outline */
*:focus {
  outline: none;
}

/* ✅ CORRECT - visible custom focus */
*:focus-visible {
  outline: 2px solid var(--focus-color);
  outline-offset: 2px;
}

/* Focus must have 3:1 contrast against adjacent colors */
```

---

## 4. Touch Target Sizing (NEW in WCAG 2.2)

### Minimum Sizes

| Platform | Minimum | Recommended |
|----------|---------|-------------|
| WCAG 2.2 AA | 24×24px | 44×44px |
| iOS Human Interface | 44×44pt | 44×44pt |
| Material Design | 48×48dp | 48×48dp |

### Implementation

```tsx
// ✅ Proper touch target
<Button className="min-h-[44px] min-w-[44px] px-4 py-2">
  Click me
</Button>

// ✅ Icon button with adequate target
<button 
  className="p-3 -m-3" // Visual is smaller, touch area is 44px
  aria-label="Close"
>
  <XIcon className="h-5 w-5" />
</button>
```

---

## 5. ARIA Attributes

### When to Use ARIA

1. **First Rule**: Don't use ARIA if native HTML works
2. **Second Rule**: Don't change native semantics
3. **Third Rule**: All interactive ARIA must be keyboard accessible
4. **Fourth Rule**: Don't hide focusable elements
5. **Fifth Rule**: Interactive elements need accessible names

### Common ARIA Patterns

```tsx
// Expandable section
<button 
  aria-expanded={isOpen}
  aria-controls="section-content"
>
  Toggle Section
</button>
<div id="section-content" hidden={!isOpen}>
  Content
</div>

// Live region for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>

// Loading state
<button aria-busy={isLoading} disabled={isLoading}>
  {isLoading ? "Loading..." : "Submit"}
</button>

// Tab panel
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected={activeTab === 0} aria-controls="panel-0">
    General
  </button>
</div>
<div role="tabpanel" id="panel-0" aria-labelledby="tab-0">
  Panel content
</div>
```

---

## 6. Form Accessibility

### Required Form Elements

```tsx
// ✅ Properly labeled form
<form aria-labelledby="form-title">
  <h2 id="form-title">Contact Form</h2>
  
  <div>
    <label htmlFor="email">Email address</label>
    <input 
      id="email"
      type="email"
      aria-required="true"
      aria-describedby="email-hint email-error"
    />
    <p id="email-hint" className="text-sm text-muted">
      We'll never share your email
    </p>
    {error && (
      <p id="email-error" className="text-sm text-red-500" role="alert">
        {error}
      </p>
    )}
  </div>
</form>
```

### Error Handling

- Use `role="alert"` or `aria-live="assertive"` for errors
- Associate errors with inputs via `aria-describedby`
- Provide clear, actionable error messages
- Focus first error field on submit failure

---

## 7. Image Accessibility

### Alt Text Patterns

```tsx
// Informative image - describe content
<Image 
  src="/team-photo.jpg" 
  alt="AlphaWave team celebrating product launch, March 2024"
/>

// Decorative image - empty alt
<Image 
  src="/decorative-swoosh.svg" 
  alt=""
  aria-hidden="true"
/>

// Functional image (button/link) - describe action
<button aria-label="Close dialog">
  <Image src="/close-icon.svg" alt="" aria-hidden="true" />
</button>

// Complex image - use figure/figcaption or aria-describedby
<figure>
  <Image src="/chart.png" alt="Q4 revenue growth chart" aria-describedby="chart-desc" />
  <figcaption id="chart-desc">
    Chart showing 45% revenue increase from October to December 2024
  </figcaption>
</figure>
```

---

## 8. Motion & Animation

### prefers-reduced-motion (REQUIRED)

```css
/* Always respect user preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

```tsx
// React hook for reduced motion
import { useReducedMotion } from 'framer-motion';

function AnimatedComponent() {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      animate={{ x: 100 }}
      transition={{ 
        duration: shouldReduceMotion ? 0 : 0.5 
      }}
    />
  );
}
```

---

## 9. QA Checklist

### Automated Testing (axe-core)

```bash
npm install @axe-core/react axe-core

# In development
import React from 'react';
import ReactDOM from 'react-dom';
import axe from '@axe-core/react';

axe(React, ReactDOM, 1000);
```

### Manual Testing Checklist

- [ ] Tab through entire page - logical order?
- [ ] Every interactive element focusable?
- [ ] Focus visible on all elements?
- [ ] Escape closes modals/dropdowns?
- [ ] Screen reader announces content correctly?
- [ ] Zoom to 200% - content still usable?
- [ ] Color contrast passing (check DevTools)?
- [ ] Touch targets ≥44×44px on mobile?
- [ ] No keyboard traps?
- [ ] Form errors announced and focusable?

### Common Failures

| Issue | Impact | Fix |
|-------|--------|-----|
| Missing alt text | Blind users can't understand images | Add descriptive alt |
| Low contrast | Hard to read for low vision | Increase contrast ratio |
| No focus indicator | Keyboard users lost | Add visible focus styles |
| Small touch targets | Mobile users can't tap | Increase to 44×44px |
| Keyboard trap | Can't escape element | Add Escape handler |
| Auto-playing video | Disorienting | Add controls, pause option |

---

## 10. Screen Reader Testing

### Quick VoiceOver Test (Mac)

1. Cmd+F5 to enable VoiceOver
2. Use Tab to navigate
3. Listen for: headings, links, buttons, form labels
4. Check: images announced with alt text
5. Check: dynamic content updates announced
6. Cmd+F5 to disable

### NVDA Test (Windows)

1. Download NVDA (free)
2. Same navigation pattern
3. Check same criteria
4. Note any differences from VoiceOver

---

## Summary: Pass/Fail Criteria

### MUST PASS (Block deployment)

- ✅ All images have alt text (or alt="" for decorative)
- ✅ Color contrast ≥4.5:1 for normal text
- ✅ All functionality keyboard accessible
- ✅ Visible focus indicators
- ✅ Touch targets ≥24×24px
- ✅ Forms have labels
- ✅ Errors announced to screen readers
- ✅ prefers-reduced-motion respected

### SHOULD PASS (Fix before next release)

- ⚠️ Skip links for main content
- ⚠️ Touch targets ≥44×44px
- ⚠️ Landmark regions used
- ⚠️ Heading hierarchy correct

