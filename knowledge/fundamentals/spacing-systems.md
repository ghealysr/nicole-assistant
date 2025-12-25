<!-- category: fundamentals -->
<!-- keywords: spacing, 8-point grid, touch targets, wcag, container queries, logical properties, clamp, gap, flexbox, grid -->

# Modern Spacing & Layout Systems (2025-2026)

## The 8-point grid dominates production design

**The 8-point grid system is the universal spacing standard** adopted by Apple, Google, and virtually every major design system in 2025. This system uses multiples of 8px (8, 16, 24, 32, 40, 48, 56, 64) for all margins, paddings, and dimensions, with 4px available for fine-tuning.

Why 8 works: most screen sizes divide evenly by 8 on at least one axis, 8px scales cleanly at @2x and @3x resolutions, and developers using rem units (16px base) integrate naturally with 8pt multiples. For $2-5K client websites, this means faster design decisions, consistent visual rhythm, and fewer revision cycles.

### Tailwind's spacing scale alignment

Tailwind uses a **4px base unit** (0.25rem), which aligns perfectly with the 8-point grid:

| Class | Value | 8pt Grid |
|-------|-------|----------|
| p-2 | 8px (0.5rem) | ✓ |
| p-4 | 16px (1rem) | ✓ |
| p-6 | 24px (1.5rem) | ✓ |
| p-8 | 32px (2rem) | ✓ |
| p-10 | 40px (2.5rem) | ✓ |
| p-12 | 48px (3rem) | ✓ |
| p-16 | 64px (4rem) | ✓ |
| p-20 | 80px (5rem) | ✓ |
| p-24 | 96px (6rem) | ✓ |

**Use even Tailwind values (2, 4, 6, 8, 12, 16, 24)** to stay on the 8pt grid. Odd values (3, 5, 7) provide 4pt granularity for fine adjustments.

---

## Tailwind v4 spacing configuration

Tailwind v4 uses the `@theme` directive for custom spacing scales:

```css
@import "tailwindcss";

@theme {
  --spacing-xs: 0.25rem;    /* 4px */
  --spacing-sm: 0.5rem;     /* 8px */
  --spacing-md: 1rem;       /* 16px */
  --spacing-lg: 1.5rem;     /* 24px */
  --spacing-xl: 2rem;       /* 32px */
  --spacing-2xl: 3rem;      /* 48px */
  --spacing-3xl: 4rem;      /* 64px */
  
  /* Section spacing */
  --spacing-section: 5rem;  /* 80px */
  --spacing-hero: 6rem;     /* 96px */
}
```

### CSS custom properties for dynamic spacing

```css
:root {
  --space-unit: 8px;
  
  --space-xs: calc(var(--space-unit) * 0.5);    /* 4px */
  --space-sm: var(--space-unit);                 /* 8px */
  --space-md: calc(var(--space-unit) * 2);       /* 16px */
  --space-lg: calc(var(--space-unit) * 3);       /* 24px */
  --space-xl: calc(var(--space-unit) * 4);       /* 32px */
  --space-2xl: calc(var(--space-unit) * 6);      /* 48px */
  --space-3xl: calc(var(--space-unit) * 8);      /* 64px */
  
  /* Responsive container padding */
  --container-padding: clamp(var(--space-md), 5vw, var(--space-xl));
}
```

---

## Touch target requirements (WCAG 2.2)

Touch target sizing is now a **legal accessibility requirement** under WCAG 2.2 and the European Accessibility Act.

### Minimum sizes

| Standard | Minimum Size | Notes |
|----------|--------------|-------|
| WCAG 2.2 Level AA | **24×24px** | With spacing if undersized |
| WCAG 2.2 Level AAA | **44×44px** | Best practice target |
| Apple iOS HIG | **44×44pt** | Recommended standard |
| Android Material | **48×48dp** | With 8dp spacing between |

**The MIT Touch Lab study found** the average adult fingertip is 16-20mm wide (~45-57px). Target **48-50px** for comfortable touch interactions.

### Spacing between touch targets

- **Minimum**: 8px between clickable elements
- **Recommended**: 12-24px for mobile interfaces
- **WCAG 2.2 rule**: If a target is smaller than 24px, surrounding spacing must prevent a 24px diameter circle from intersecting adjacent targets

```css
/* Touch-friendly button spacing */
.button-group {
  display: flex;
  gap: 12px; /* Minimum 8px, 12px recommended */
}

.button {
  min-height: 44px;
  min-width: 44px;
  padding: 12px 24px;
}
```

---

## CSS layout features browser support (December 2025)

All modern CSS spacing features are now production-ready with 92%+ support:

| Feature | Global Support | Chrome | Firefox | Safari |
|---------|----------------|--------|---------|--------|
| Container Queries | **93.92%** | 106+ | 110+ | 16.0+ |
| Container Query Units | **93.92%** | 106+ | 110+ | 16.0+ |
| CSS Logical Properties | **93.27%** | 89+ | 66+ | 15+ |
| Flexbox Gap | **92.39%** | 84+ | 63+ | 14.1+ |
| CSS Nesting | **91.97%** | 120+ | 117+ | 17.2+ |
| clamp()/min()/max() | **92.52%** | 79+ | 75+ | 13.1+ |

### Container queries for component-level spacing

```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

.card {
  padding: 16px;
  gap: 12px;
}

@container card (min-width: 400px) {
  .card {
    padding: 24px;
    gap: 16px;
  }
}

@container card (min-width: 600px) {
  .card {
    padding: 32px;
    gap: 24px;
  }
}

/* Container query units for fluid spacing */
.card {
  padding: clamp(16px, 4cqi, 32px);
  font-size: clamp(1rem, 2cqi + 0.5rem, 1.5rem);
}
```

### CSS logical properties for internationalization

Logical properties automatically adapt for RTL languages and vertical writing modes:

```css
/* Instead of physical properties */
margin-left: 1rem;
margin-right: 2rem;
padding-top: 1rem;
padding-bottom: 1rem;

/* Use logical properties */
margin-inline-start: 1rem;
margin-inline-end: 2rem;
padding-block: 1rem;

/* Shorthand */
margin-inline: 1rem 2rem;  /* start end */
padding-block: 1rem 2rem;  /* start end */
```

---

## Responsive spacing with clamp()

Fluid spacing eliminates breakpoint-specific values while maintaining control over minimum and maximum bounds:

```css
:root {
  /* Fluid spacing scale */
  --space-sm: clamp(0.5rem, 1vw + 0.25rem, 1rem);
  --space-md: clamp(1rem, 2vw + 0.5rem, 2rem);
  --space-lg: clamp(1.5rem, 3vw + 0.75rem, 3rem);
  --space-xl: clamp(2rem, 4vw + 1rem, 4rem);
  
  /* Container padding that scales with viewport */
  --container-padding: clamp(1rem, 5vw, 4rem);
}

.section {
  padding-block: var(--space-xl);
  padding-inline: var(--container-padding);
}
```

**Accessibility warning**: Never use viewport units alone for font sizing—combine with rem to preserve zoom functionality:

```css
/* Bad - breaks WCAG 1.4.4 (text resize) */
font-size: 4vw;

/* Good - respects user preferences */
font-size: clamp(1rem, calc(0.5rem + 2vw), 2rem);
```

---

## Component spacing patterns

### Card spacing

```css
/* Small cards (thumbnails, compact lists) */
.card-sm {
  padding: 12px;
  gap: 8px;
}

/* Standard cards */
.card-md {
  padding: 16px;
  gap: 12px;
}

/* Large cards (features, testimonials) */
.card-lg {
  padding: 24px;
  gap: 16px;
}

/* Hero cards */
.card-xl {
  padding: 32px;
  gap: 24px;
}

/* Card grid spacing */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px; /* Use gap, not margins */
}
```

### Form spacing

**The Gestalt proximity principle**: Internal spacing (within groups) should be **less than** external spacing (between groups).

```css
/* Form field group */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px; /* Label to input: tight */
}

/* Between form groups */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 20px; /* Between fields: spacious */
}

/* Form sections */
.form-section {
  margin-block-end: 32px;
  padding-block-end: 32px;
  border-bottom: 1px solid var(--border);
}

/* Form actions */
.form-actions {
  display: flex;
  gap: 12px;
  margin-block-start: 24px;
}
```

### Button spacing

**Horizontal padding should be 2-3× vertical padding** for natural reading flow:

```css
/* Standard button */
.btn {
  padding: 8px 16px;  /* 1:2 ratio */
  min-height: 40px;
  min-width: 80px;
}

/* Large button */
.btn-lg {
  padding: 12px 32px; /* 1:2.67 ratio */
  min-height: 48px;
}

/* Compact button */
.btn-sm {
  padding: 6px 12px;  /* 1:2 ratio */
  min-height: 32px;
}

/* Button groups */
.btn-group {
  display: flex;
  gap: 8px;
}
```

### Navigation spacing

```css
/* Horizontal navigation */
.nav-horizontal {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 64px; /* Standard nav height */
  padding-inline: 16px;
}

.nav-link {
  padding: 8px 12px;
  min-height: 44px; /* Touch target */
  display: flex;
  align-items: center;
}

/* Vertical navigation */
.nav-vertical {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px;
}

.nav-vertical .nav-link {
  padding: 12px 16px;
  min-height: 44px;
}
```

---

## Vertical rhythm systems

Consistent vertical rhythm creates visual harmony. Use line-height-based spacing multiples:

```css
:root {
  --baseline: 8px;
  --line-height-body: 1.5; /* 24px at 16px font */
  --line-height-heading: 1.25;
}

body {
  font-size: 16px;
  line-height: var(--line-height-body);
}

/* Typography spacing */
h1, h2, h3, h4, h5, h6 {
  line-height: var(--line-height-heading);
  margin-block-start: 1.5em;
  margin-block-end: 0.5em;
}

p {
  margin-block-end: 1em;
}

/* Lists */
ul, ol {
  margin-block: 1em;
  padding-inline-start: 1.5em;
}

li {
  margin-block-end: 0.5em;
}
```

### Section spacing

```css
/* Standard section */
.section {
  padding-block: 64px; /* 80px on desktop */
}

/* Compact section */
.section-sm {
  padding-block: 48px;
}

/* Hero section */
.section-hero {
  padding-block: 96px;
}

/* Responsive section spacing */
.section-responsive {
  padding-block: clamp(48px, 8vw, 96px);
}
```

---

## Design systems spacing comparison

Major design systems converge on similar spacing scales:

| System | Base Unit | Scale |
|--------|-----------|-------|
| Tailwind CSS | 4px | 4, 8, 12, 16, 20, 24, 32, 40, 48, 64... |
| Radix Themes | 4px | 4, 8, 12, 16, 24, 32, 40, 48, 64 |
| Material Design 3 | 4dp | 4, 8, 12, 16, 24, 32, 48, 64 |
| Chakra UI | 4px | 4, 8, 12, 16, 20, 24, 32, 40, 48... |
| shadcn/ui | 4px (Tailwind) | Uses Tailwind defaults |

### Radix Themes spacing tokens

```css
var(--space-1);  /* 4px */
var(--space-2);  /* 8px */
var(--space-3);  /* 12px */
var(--space-4);  /* 16px */
var(--space-5);  /* 24px */
var(--space-6);  /* 32px */
var(--space-7);  /* 40px */
var(--space-8);  /* 48px */
var(--space-9);  /* 64px */
```

---

## Gap vs margin strategies

Modern layouts should prefer `gap` over margins for spacing between items:

| Approach | Pros | Cons |
|----------|------|------|
| **gap** | Clean, no negative margins, works with wrapping, single property | Can't create asymmetric spacing between specific items |
| **margins** | Fine-grained per-item control | Complex with wrapping, requires negative margins for grids |

```css
/* Modern pattern: gap for items, padding for container */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-lg);       /* Between cards */
  padding: var(--space-xl);   /* Container edges */
}

/* Flex spacing */
.flex-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
```

---

## Performance considerations

### CSS custom properties performance

1. **Scope variables appropriately**: Root-level changes trigger recalculation for all children
2. **Use `setProperty()` for JavaScript updates**: Slightly faster than inline styles
3. **calc() with variables is performant**: No measurable difference vs direct values

```css
/* Efficient: scoped override */
.compact-section {
  --card-padding: var(--space-sm); /* Only affects children */
}

/* Less efficient: frequent root changes */
document.documentElement.style.setProperty('--spacing', '24px');
```

### Layout shift prevention

Reserve space for dynamic content to prevent CLS (Cumulative Layout Shift):

```css
/* Fixed aspect ratio containers */
.video-container {
  aspect-ratio: 16 / 9;
}

/* Minimum heights for loading states */
.card-skeleton {
  min-height: 200px;
}

/* Image dimensions */
img {
  max-width: 100%;
  height: auto;
  aspect-ratio: attr(width) / attr(height);
}
```

---

## Accessibility requirements summary

| Requirement | Value | WCAG Reference |
|-------------|-------|----------------|
| Touch target minimum | 24×24px | SC 2.5.8 (AA) |
| Touch target recommended | 44×44px | SC 2.5.5 (AAA) |
| Line height minimum | 1.5× font size | SC 1.4.12 |
| Paragraph spacing | 2× font size | SC 1.4.12 |
| Focus indicator | Not cropped by overflow | SC 2.4.11 |
| Target spacing | No 24px circle overlap | SC 2.5.8 |

```css
/* Accessibility-compliant typography spacing */
body {
  line-height: 1.5;
}

p + p {
  margin-block-start: 1.5em; /* ~2× font size */
}

/* Ensure focus indicators aren't clipped */
.card {
  overflow: visible; /* Or use inset focus rings */
}

.interactive:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}
```

---

## Dos and don'ts

**DO:**
- Use the 8-point grid (multiples of 8px) for all spacing
- Target 44×44px minimum for touch targets
- Use `gap` for flex/grid item spacing
- Apply `clamp()` for fluid responsive spacing
- Keep internal spacing tighter than external (Gestalt proximity)
- Use logical properties (`margin-inline`, `padding-block`) for i18n

**DON'T:**
- Use odd pixel values (7px, 13px, 19px) that break the grid
- Create touch targets smaller than 24×24px
- Use margins for grid/flex item spacing (use gap)
- Apply `vw` units alone for font sizing (breaks zoom)
- Set `overflow: hidden` on parents of focus-ring elements
- Mix spacing scales inconsistently across components

---

## Quick reference: Common spacing values

| Use Case | Mobile | Desktop |
|----------|--------|---------|
| Container padding | 16px | 24-32px |
| Card padding | 16px | 24px |
| Button padding | 8px 16px | 12px 24px |
| Form field gap | 16-20px | 20-24px |
| Label to input | 4-6px | 4-8px |
| Section padding | 48-64px | 80-96px |
| Grid gap | 16px | 24px |
| Nav item padding | 8-12px | 12-16px |
| Touch target min | 44px | 44px |

