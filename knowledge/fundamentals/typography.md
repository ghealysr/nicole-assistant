<!-- category: fundamentals -->
<!-- keywords: typography, fonts, type scale, line height, clamp, fluid typography, variable fonts, tailwind, wcag -->

# Modern Web Typography Best Practices

Fluid typography using CSS `clamp()` has become the standard for responsive type in 2025, eliminating the need for breakpoint-based font sizing. Combined with container queries for component-level responsiveness and Tailwind v4's new `@theme` directive, typography systems are now more maintainable and accessible than ever.

## Fluid Typography with CSS clamp()

The accessibility-safe formula includes a rem component to ensure browser zoom still works correctly—using `vw` alone fails WCAG requirements because text won't scale with zoom.

```css
/* Core syntax */
font-size: clamp(MIN, PREFERRED, MAX);

/* Production-ready formula (includes rem for zoom support) */
.fluid-text {
  font-size: clamp(1rem, 0.5rem + 2vw, 3rem);
}
```

**Production Type Scale (320px to 1240px viewport):**
```css
:root {
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --text-base: clamp(1rem, 0.925rem + 0.375vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.625vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.625rem);
  --text-2xl: clamp(1.5rem, 1.25rem + 1.25vw, 2rem);
  --text-3xl: clamp(1.875rem, 1.5rem + 1.875vw, 2.5rem);
  --text-4xl: clamp(2.25rem, 1.75rem + 2.5vw, 3.5rem);
  --text-5xl: clamp(3rem, 2rem + 5vw, 5rem);
}
```

## Container Query Typography

Container queries enable typography that responds to component width rather than viewport, essential for reusable components.

```css
.card-container {
  container-type: inline-size;
  container-name: card;
}

.card h2 {
  font-size: clamp(1.5rem, 4cqw, 3rem);
}

.card p {
  font-size: clamp(0.875rem, 2cqw, 1.125rem);
  line-height: 1.6;
}

@container (min-width: 600px) {
  .card-layout {
    display: grid;
    grid-template-columns: 200px 1fr;
  }
}
```

| Unit | Description |
|------|-------------|
| `cqw` | 1% of container width |
| `cqi` | 1% of container inline size |
| `cqb` | 1% of container block size |

## Recommended Type Scales

| Ratio | Name | Best For |
|-------|------|----------|
| 1.125 | Major Second | Dense UI, subtle hierarchy |
| **1.250** | **Major Third** | **Web apps (recommended)** |
| 1.333 | Perfect Fourth | Marketing, clear hierarchy |
| 1.500 | Perfect Fifth | Bold, dramatic layouts |

**Major Third Scale (1.25 ratio, base 16px):**
```css
:root {
  --text-xs: 0.64rem;    /* 10.24px */
  --text-sm: 0.8rem;     /* 12.8px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.25rem;    /* 20px */
  --text-xl: 1.563rem;   /* 25px */
  --text-2xl: 1.953rem;  /* 31.25px */
  --text-3xl: 2.441rem;  /* 39px */
  --text-4xl: 3.052rem;  /* 48.83px */
  --text-5xl: 3.815rem;  /* 61px */
}
```

## Font Loading with Next.js 15

```tsx
// app/fonts.ts
import { Inter, Plus_Jakarta_Sans } from 'next/font/google';

export const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jakarta',
});

// app/layout.tsx
import { inter, jakarta } from './fonts';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jakarta.variable}`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
```

| font-display | Behavior | Use Case |
|--------------|----------|----------|
| `swap` | Show fallback immediately, swap when loaded | **Recommended default** |
| `optional` | 100ms block, use fallback if not loaded | Performance-critical |
| `fallback` | 100ms block, 3s swap period | Balance |

## Top Variable Fonts (2024-2025)

| Font | Weight Range | Best For |
|------|--------------|----------|
| **Inter** | 100-900 | UI, body text, all-purpose |
| **Plus Jakarta Sans** | 200-800 | Modern UI, headings |
| **Geist** | 100-900 | Tech, developer tools |
| **DM Sans** | 100-1000 | Clean, geometric |
| **Outfit** | 100-900 | Modern, friendly |

**Font Pairing Examples:**
```css
/* Tech/SaaS */
--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
--font-display: 'Plus Jakarta Sans', sans-serif;

/* Developer Tools */
--font-sans: 'Geist', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

## Tailwind v4 @theme Configuration

```css
/* app/globals.css */
@import "tailwindcss";

@theme {
  --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif;
  --font-display: var(--font-jakarta), sans-serif;
  
  /* Fluid type scale */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --text-base: clamp(1rem, 0.925rem + 0.375vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.625vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1.1rem + 0.75vw, 1.625rem);
  --text-2xl: clamp(1.5rem, 1.25rem + 1.25vw, 2rem);
  --text-3xl: clamp(1.875rem, 1.5rem + 1.875vw, 2.5rem);
  --text-4xl: clamp(2.25rem, 1.75rem + 2.5vw, 3.5rem);
}

@layer base {
  h1, h2 { line-height: 1.15; letter-spacing: -0.025em; }
  h3, h4 { line-height: 1.25; }
}
```

## WCAG 2.2 Accessibility Requirements

| Requirement | Value |
|-------------|-------|
| Normal text contrast | **4.5:1 minimum** |
| Large text (≥24px or ≥18.66px bold) | **3:1 minimum** |
| UI components | **3:1 minimum** |
| Minimum body text | **16px (1rem)** |
| Mobile body text | **16px** (prevents iOS zoom) |

**Line-Height Guidelines:**
| Element | Line-Height |
|---------|-------------|
| Body text | **1.5 - 1.6** |
| Large headings (h1-h2) | **1.1 - 1.2** |
| Small headings (h3-h4) | **1.2 - 1.3** |
| UI text/labels | **1.25 - 1.4** |

## Typography Tools

| Tool | URL | Purpose |
|------|-----|---------|
| **Utopia** | https://utopia.fyi/type/calculator | Fluid type scale generator |
| Type Scale | https://type-scale.com | Classic modular scale |
| WebAIM Contrast | https://webaim.org/resources/contrastchecker | WCAG contrast validation |
| Fontsource | https://fontsource.org | Self-hosted font packages |
| Font Pairing | https://fontpair.co | Pairing suggestions |

