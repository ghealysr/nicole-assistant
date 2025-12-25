<!-- category: fundamentals -->
<!-- keywords: oklch, color, wcag, accessibility, contrast, tailwind v4, dark mode, semantic tokens, color blind, palette -->

# Modern Web Color Systems (2025-2026)

## OKLCH transforms web color management

**OKLCH is now the production standard for modern web color systems.** With **92.86% global browser support** as of December 2025, designers can confidently use this perceptually uniform color space that eliminates the inconsistencies that plagued RGB and HSL for decades. Tailwind CSS v4 (released January 2025) made OKLCH its default color format, signaling industry-wide adoption.

The shift to OKLCH solves three critical problems: colors with identical lightness values now appear equally bright across all hues, gradients no longer pass through muddy gray zones, and accessibility calculations become more predictable. For $2-5K client websites, this means easier palette creation, more reliable WCAG compliance, and future-proofed color systems.

### Browser support confirms production readiness

| Browser | OKLCH Support | Relative Color Syntax |
|---------|---------------|----------------------|
| Chrome | 111+ (March 2023) | 122+ |
| Firefox | 113+ (May 2023) | 128+ |
| Safari | 15.4+ (March 2022) | 18.0+ |
| Edge | 111+ (March 2023) | 122+ |
| Safari iOS | 15.4+ | 18.0+ |
| **Global Coverage** | **92.86%** | **85.85%** |

The only browsers lacking support are Internet Explorer (deprecated), UC Browser for Android, KaiOS, and QQ Browser—none relevant for modern client projects.

---

## OKLCH syntax and value ranges

OKLCH uses three intuitive parameters: **Lightness** (0-100%), **Chroma** (saturation intensity, typically 0-0.4), and **Hue** (0-360 degrees on the color wheel).

```css
/* Basic syntax */
oklch(L C H)
oklch(L C H / alpha)

/* Production examples */
oklch(70% 0.15 240)           /* Soft blue */
oklch(63% 0.26 29)            /* Vibrant red */
oklch(87% 0.20 95)            /* Yellow */
oklch(60% 0.2 280 / 75%)      /* Purple at 75% opacity */

/* Quick reference values */
oklch(0% 0 0)                 /* Black */
oklch(50% 0 0)                /* Mid gray */
oklch(100% 0 0)               /* White */
```

**Critical hue angles to memorize:** Red ≈ 20-29°, Yellow ≈ 90-95°, Green ≈ 140-150°, Blue ≈ 220-264°, Purple ≈ 280-320°, Magenta ≈ 0° (not red like HSL).

### Relative color syntax enables dynamic theming

```css
/* Adjust existing colors without JavaScript */
:root {
  --base-color: oklch(65% 0.15 240);
}

.lighter {
  background: oklch(from var(--base-color) calc(l + 0.15) c h);
}

.darker {
  background: oklch(from var(--base-color) calc(l - 0.15) c h);
}

.desaturated {
  background: oklch(from var(--base-color) l calc(c * 0.5) h);
}
```

---

## Tailwind v4 color configuration

Tailwind CSS v4 (stable since January 22, 2025) revolutionized color configuration with CSS-first configuration using the `@theme` directive. No more `tailwind.config.js` for colors—everything lives in your CSS.

### Defining custom colors

```css
@import "tailwindcss";

@theme {
  --color-brand-50: oklch(0.99 0 0);
  --color-brand-100: oklch(0.98 0.04 113);
  --color-brand-200: oklch(0.94 0.11 115);
  --color-brand-300: oklch(0.92 0.19 114);
  --color-brand-400: oklch(0.84 0.18 117);
  --color-brand-500: oklch(0.72 0.15 120);
  --color-brand-600: oklch(0.53 0.12 118);
  --color-brand-700: oklch(0.45 0.10 120);
  --color-brand-800: oklch(0.35 0.08 120);
  --color-brand-900: oklch(0.25 0.06 120);
  --color-brand-950: oklch(0.15 0.04 120);
}
```

This automatically generates utilities: `bg-brand-500`, `text-brand-100`, `border-brand-300`, etc.

### Semantic color system (shadcn/ui pattern)

The shadcn/ui approach has become the industry standard for semantic color naming:

```css
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --border: oklch(1 0 0 / 10%);
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
}
```

**The `@theme inline` keyword** is essential when referencing CSS variables—it ensures values resolve correctly for dynamic theming.

### Adding state colors

```css
:root {
  --success: oklch(0.72 0.22 149);
  --success-foreground: oklch(0.98 0.02 155);
  --warning: oklch(0.84 0.16 84);
  --warning-foreground: oklch(0.28 0.07 46);
  --error: oklch(0.58 0.25 27);
  --error-foreground: oklch(0.97 0.01 17);
  --info: oklch(0.69 0.17 237);
  --info-foreground: oklch(0.97 0.01 237);
}

@theme inline {
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-error: var(--error);
  --color-error-foreground: var(--error-foreground);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
}
```

---

## WCAG 2.2 accessibility requirements

WCAG 2.2 became a W3C Recommendation on October 5, 2023, and the European Accessibility Act (EAA) became applicable June 28, 2025—making these requirements legally binding for many projects.

### Contrast ratios (Level AA)

| Element | Minimum Ratio | Notes |
|---------|---------------|-------|
| Normal text (<18pt/24px) | **4.5:1** | Most body copy |
| Large text (≥18pt or ≥14pt bold) | **3:1** | Headlines, buttons |
| UI components | **3:1** | Borders, icons, focus rings |
| Non-text elements | **3:1** | Charts, infographics |

**Level AAA** (enhanced): 7:1 for normal text, 4.5:1 for large text.

### Why OKLCH improves accessibility

Colors with the **same L (lightness) value** in OKLCH have **consistent perceived brightness**, making contrast calculations more reliable. A blue at `oklch(65% 0.15 240)` and a yellow at `oklch(65% 0.20 95)` will have nearly identical contrast against white—unlike HSL where "equal" lightness produces vastly different perceived brightness.

### APCA: The future of contrast (not yet required)

APCA (Accessible Perceptual Contrast Algorithm) is the candidate contrast method for WCAG 3.0 but is **not yet an official standard**. Key differences:

- **Polarity-sensitive**: Light text on dark backgrounds calculates differently than dark on light
- **Better dark mode handling**: WCAG 2.x overstates contrast for dark colors
- **Lc values**: Uses -108 to +106 scale instead of ratios (Lc 60 ≈ old 4.5:1)

**Current recommendation**: Meet WCAG 2.2 requirements for compliance; use APCA for enhanced accuracy in testing.

---

## Color-blind safe design

**8% of males have some form of color vision deficiency**—primarily deuteranopia and protanopia (red-green confusion). Designing for accessibility means never relying on color alone.

### Color combinations to avoid

- Green + Red (most critical)
- Green + Brown, Blue + Purple
- Light green + Yellow
- Red + Black (protanopia issue)
- Blue + Gray, Green + Gray

### Design patterns that work

1. **Add icons or patterns** alongside color-coded elements
2. **Underline links** rather than color-only differentiation  
3. **Use text labels** for error states: "Required field" not just red asterisks
4. **Test in grayscale** to verify luminance contrast works
5. **Vary brightness and tone**, not just hue

---

## Production fallback strategies

For the ~7% without OKLCH support, implement graceful degradation:

```css
/* Cascade fallback (simplest) */
.button {
  background-color: #4a90e2;              /* Fallback */
  background-color: oklch(65% 0.15 240);  /* Modern browsers */
}

/* Feature query fallback */
:root {
  --brand-primary: rgb(4, 140, 44);
}

@supports (color: oklch(0% 0 0)) {
  :root {
    --brand-primary: oklch(55% 0.23 146);
  }
}

.button {
  background-color: var(--brand-primary);
}
```

---

## Color tools for production (December 2025)

### OKLCH-specific tools

| Tool | URL | Best For |
|------|-----|----------|
| oklch.com | oklch.com | Primary OKLCH picker, education |
| oklch.fyi | oklch.fyi | Palette generation with CSS export |
| Harmonizer | harmonizer.evilmartians.com | APCA-compliant palette creation |

### Palette generators

| Tool | URL | Key Feature |
|------|-----|-------------|
| Realtime Colors | realtimecolors.com | Live website visualization |
| Coolors | coolors.co | Rapid palette exploration |
| Huemint | huemint.com | AI-powered context-aware palettes |
| Leonardo (Adobe) | leonardocolor.io | Contrast-based generation |

### Accessibility checkers

| Tool | URL | Best For |
|------|-----|----------|
| WebAIM Contrast | webaim.org/resources/contrastchecker | Quick ratio checking |
| Stark | getstark.co | Figma integration, APCA support |
| Color Oracle | colororacle.org | Desktop-wide colorblind simulation |
| axe DevTools | deque.com/axe | Automated scanning, CI/CD |

### Figma plugins for OKLCH

- **OkColor**: Full OKLCH picker with APCA checking
- **Harmonizer**: Evil Martians' accessible palette generator
- **OKLCH Color Ramp**: Perceptually uniform scale creation
- **Polychrom**: Real-time APCA contrast analysis

**Important**: Figma does NOT natively support OKLCH in its color picker. Use these plugins as workarounds.

---

## Quick reference: Semantic color tokens

Modern color systems follow the **background/foreground pairing pattern**:

```
--primary              → Main brand/action color
--primary-foreground   → Text on primary
--secondary            → Supporting color
--secondary-foreground → Text on secondary
--muted                → Subtle backgrounds
--muted-foreground     → De-emphasized text
--accent               → Highlights, interactive states
--accent-foreground    → Text on accent
--destructive          → Error/danger states
--background           → Page background
--foreground           → Default text
--border               → Borders and dividers
--input                → Form field backgrounds
--ring                 → Focus rings
```

---

## Dos and don'ts

**DO:**
- Use OKLCH for all new projects (92%+ support)
- Define semantic color tokens, not raw values
- Test all interactive states for contrast compliance
- Include foreground color for every background color
- Use `@theme inline` when referencing CSS variables

**DON'T:**
- Assume HSL hue values transfer to OKLCH (they don't)
- Use color alone to convey information
- Skip dark mode contrast verification (light mode contrast ≠ dark mode)
- Forget that 100% chroma in OKLCH equals 0.4, not 1
- Use APCA-only without WCAG 2.2 backup (not yet standard)

