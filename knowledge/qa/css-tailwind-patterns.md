<!-- category: qa -->
<!-- keywords: css, tailwind, styling, responsive, dark-mode, animations -->

# CSS & Tailwind v4 QA Standards

## Tailwind v4 Changes to Watch For

| v3 Syntax | v4 Syntax | Notes |
|-----------|-----------|-------|
| `tailwind.config.js` | `@theme` in CSS | Config in CSS now |
| `text-gray-900` | `text-gray-900` or OKLCH | OKLCH colors available |
| `darkMode: 'class'` | CSS `@variant` | Native cascade layers |
| `@apply` | Still works | But prefer direct classes |

---

## 1. Responsive Design Patterns

### Mobile-First Approach (Required)

```tsx
// ✅ CORRECT - mobile first
<div className="p-4 md:p-6 lg:p-8">
  <h1 className="text-2xl md:text-3xl lg:text-4xl">Title</h1>
</div>

// 🔴 WRONG - desktop first (overriding down)
<div className="p-8 sm:p-6 xs:p-4"> {/* ❌ Backwards */}
```

### Breakpoint Reference

| Breakpoint | Width | Use Case |
|------------|-------|----------|
| (default) | 0-639px | Mobile phones |
| `sm:` | 640px+ | Large phones |
| `md:` | 768px+ | Tablets |
| `lg:` | 1024px+ | Laptops |
| `xl:` | 1280px+ | Desktops |
| `2xl:` | 1536px+ | Large screens |

### Container Queries (v4)

```tsx
// ✅ Component-level responsive design
<div className="@container">
  <div className="@md:flex @md:gap-4">
    <aside className="@md:w-1/3">Sidebar</aside>
    <main className="@md:w-2/3">Content</main>
  </div>
</div>
```

---

## 2. Color System

### OKLCH in Tailwind v4

```css
/* @theme directive in CSS (v4) */
@theme {
  --color-primary: oklch(65% 0.25 260);
  --color-primary-foreground: oklch(98% 0 0);
  --color-destructive: oklch(55% 0.22 25);
}
```

### Dark Mode Implementation

```tsx
// ✅ Proper dark mode with CSS variables
<div className="bg-background text-foreground">
  <button className="bg-primary text-primary-foreground hover:bg-primary/90">
    Click
  </button>
</div>

// CSS setup
@layer base {
  :root {
    --background: oklch(98% 0 0);
    --foreground: oklch(15% 0 0);
    --primary: oklch(55% 0.2 260);
  }
  
  .dark {
    --background: oklch(10% 0 0);
    --foreground: oklch(95% 0 0);
    --primary: oklch(70% 0.25 260);
  }
}
```

### Color Contrast Requirements

```tsx
// ✅ Check contrast programmatically
function hasAdequateContrast(l1: number, l2: number): boolean {
  const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  return ratio >= 4.5; // WCAG AA for normal text
}
```

---

## 3. Spacing & Layout

### 8-Point Grid System

```tsx
// ✅ Use spacing scale consistently
<div className="space-y-4"> {/* 16px - good */}
  <Card className="p-4 md:p-6"> {/* 16px / 24px */}
    <h2 className="mb-2">Title</h2> {/* 8px */}
    <p className="text-muted-foreground">Content</p>
  </Card>
</div>

// 🔴 AVOID arbitrary values when possible
<div className="p-[13px]"> {/* ❌ Not on grid */}
```

### Spacing Scale Reference

| Class | Size | Use Case |
|-------|------|----------|
| `gap-1` | 4px | Tight inline elements |
| `gap-2` | 8px | Related elements |
| `gap-4` | 16px | Standard spacing |
| `gap-6` | 24px | Section padding |
| `gap-8` | 32px | Major sections |
| `gap-12` | 48px | Page sections |
| `gap-16` | 64px | Hero margins |

### Flexbox Patterns

```tsx
// ✅ Common flex patterns
// Center everything
<div className="flex items-center justify-center min-h-screen">

// Space between with center
<header className="flex items-center justify-between px-4 h-16">

// Flex column with auto-spacing
<nav className="flex flex-col gap-2">

// Flex wrap grid alternative
<div className="flex flex-wrap gap-4">
  {items.map(item => (
    <div key={item.id} className="flex-1 min-w-[280px] max-w-[400px]">
```

### Grid Patterns

```tsx
// ✅ Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

// ✅ Auto-fit responsive
<div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-6">

// ✅ Bento grid
<div className="grid grid-cols-4 grid-rows-3 gap-4">
  <div className="col-span-2 row-span-2">Large</div>
  <div className="col-span-2">Wide</div>
  <div>Small 1</div>
  <div>Small 2</div>
</div>
```

---

## 4. Typography

### Font Size Scale

```tsx
// ✅ Semantic text classes
<h1 className="text-4xl font-bold tracking-tight">Page Title</h1>
<h2 className="text-2xl font-semibold">Section</h2>
<h3 className="text-xl font-medium">Subsection</h3>
<p className="text-base leading-7">Body text</p>
<small className="text-sm text-muted-foreground">Caption</small>
```

### Fluid Typography

```css
/* ✅ Responsive font sizes with clamp */
@layer base {
  h1 {
    font-size: clamp(2rem, 5vw, 4rem);
    line-height: 1.1;
  }
  
  h2 {
    font-size: clamp(1.5rem, 4vw, 2.5rem);
    line-height: 1.2;
  }
}
```

### Text Readability

```tsx
// ✅ Optimal reading width
<article className="prose max-w-prose mx-auto">
  {/* max-w-prose = 65ch, optimal reading width */}
</article>

// ✅ Proper line height for body text
<p className="leading-7 text-base"> {/* 1.75 line-height for body */}
```

---

## 5. Animation & Transitions

### Safe Animations

```tsx
// ✅ Use transform and opacity (GPU accelerated)
<div className="transition-transform hover:scale-105">

// ✅ Smooth transitions
<button className="transition-colors duration-150 hover:bg-primary/90">

// 🔴 AVOID animating layout properties
<div className="hover:w-[200px]"> {/* ❌ Causes layout shift */}
```

### Reduced Motion

```tsx
// ✅ Always respect user preference
<div className="motion-safe:animate-fade-in motion-reduce:animate-none">

// CSS version
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Tailwind Animation Classes

```tsx
// Built-in animations
<div className="animate-spin">Spinner</div>
<div className="animate-pulse">Loading</div>
<div className="animate-bounce">Attention</div>
<div className="animate-ping">Notification</div>

// Custom animations
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}
```

---

## 6. Component Patterns

### Button Variants

```tsx
// ✅ shadcn-style button variants
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
```

### Card Pattern

```tsx
// ✅ Consistent card structure
<div className="rounded-lg border bg-card text-card-foreground shadow-sm">
  <div className="p-6 pt-0 flex flex-col space-y-1.5">
    <h3 className="text-2xl font-semibold leading-none tracking-tight">
      Card Title
    </h3>
    <p className="text-sm text-muted-foreground">
      Card description
    </p>
  </div>
  <div className="p-6 pt-0">
    {/* Content */}
  </div>
  <div className="flex items-center p-6 pt-0">
    {/* Footer */}
  </div>
</div>
```

---

## 7. Common CSS Issues

### Z-Index Management

```css
/* ✅ Z-index scale */
:root {
  --z-dropdown: 50;
  --z-sticky: 100;
  --z-fixed: 200;
  --z-modal-backdrop: 300;
  --z-modal: 400;
  --z-popover: 500;
  --z-tooltip: 600;
  --z-toast: 700;
}
```

### Overflow Issues

```tsx
// 🔴 COMMON BUG - horizontal scroll on mobile
<div className="w-screen"> {/* ❌ Causes horizontal overflow */}

// ✅ FIX - use 100% or viewport-relative
<div className="w-full">

// ✅ Prevent child overflow
<main className="overflow-x-hidden">
```

### Specificity Issues

```css
/* 🔴 BAD - too specific */
div.container > section.hero > h1.title {
  font-size: 3rem;
}

/* ✅ GOOD - low specificity with Tailwind */
.hero-title {
  @apply text-5xl font-bold;
}

/* ✅ BEST - utility classes directly */
<h1 className="text-5xl font-bold">
```

---

## 8. Tailwind Anti-Patterns

### Class Soup Prevention

```tsx
// 🔴 BAD - class soup, hard to read
<div className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 border border-gray-200 dark:border-gray-800">

// ✅ GOOD - extract to component or use cva
<Card className="hover:shadow-lg transition-shadow">
```

### Avoid @apply Overuse

```css
/* 🔴 BAD - defeats purpose of Tailwind */
.btn {
  @apply flex items-center justify-center px-4 py-2 rounded-md bg-primary text-white font-medium hover:bg-primary-dark;
}

/* ✅ GOOD - use @apply sparingly for true reusability */
.prose-custom {
  @apply prose prose-lg dark:prose-invert;
}
```

### Don't Mix Tailwind with Inline Styles

```tsx
// 🔴 BAD - mixed approach
<div className="p-4" style={{ backgroundColor: '#f0f0f0' }}>

// ✅ GOOD - pick one
<div className="p-4 bg-gray-100">
// or
<div style={{ padding: '1rem', backgroundColor: '#f0f0f0' }}>
```

---

## 9. Testing CSS

### Visual Regression Testing

```tsx
// Playwright visual test
test('hero section matches snapshot', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.hero')).toHaveScreenshot('hero.png');
});
```

### Responsive Testing Checklist

- [ ] 320px (iPhone SE)
- [ ] 375px (iPhone 12)
- [ ] 390px (iPhone 14)
- [ ] 768px (iPad)
- [ ] 1024px (iPad Pro)
- [ ] 1280px (Laptop)
- [ ] 1920px (Desktop)

### Dark Mode Testing

- [ ] All text readable in dark mode
- [ ] Images don't blind user in dark mode
- [ ] Borders visible in both modes
- [ ] Focus states visible in both modes
- [ ] Hover states work in both modes

---

## 10. QA Checklist

### Layout Review

- [ ] Mobile-first responsive design
- [ ] No horizontal scrolling on mobile
- [ ] Consistent spacing (8-point grid)
- [ ] Content doesn't touch screen edges
- [ ] Cards/containers have consistent padding

### Typography Review

- [ ] Heading hierarchy (h1 → h2 → h3)
- [ ] Body text readable (16px+)
- [ ] Line height adequate (1.5-1.75)
- [ ] Max reading width ~65ch
- [ ] No orphaned words in headings

### Color Review

- [ ] Contrast ratios pass WCAG AA
- [ ] Dark mode fully implemented
- [ ] Colors consistent across components
- [ ] No color-only information

### Animation Review

- [ ] prefers-reduced-motion respected
- [ ] Animations use transform/opacity
- [ ] No layout-shifting animations
- [ ] Transitions smooth (150-300ms)

