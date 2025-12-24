<!-- category: core -->
<!-- keywords: anti patterns, mistakes, avoid, wcag, performance, ux, conversion, accessibility, carousels, modals -->

# Modern Web Design Anti-Patterns to Avoid

The WebAIM Million 2025 study found **94.8% of home pages had WCAG failures**. Combined with UX research from Nielsen Norman Group and performance data from Core Web Vitals, this document catalogs the critical anti-patterns to eliminate.

## UX Anti-Patterns

**Carousels Are Conversion Killers**
- Users scroll past carousels **64% of the time** without engaging
- First slide: 40% engagement → Second slide: **18%** (Notre Dame study)
- Auto-rotating carousels cause banner blindness
- Users failed tasks even when target was first item in carousel (98pt font!)

*What to Do Instead:* Use static hero images. If carousels needed: never auto-advance, provide clear controls, stop on hover/touch.

**Modal Overuse**
- Popups are the **#1 most-hated** advertising technique
- **82%** of users dislike popups
- Users instinctively dismiss without reading

*Problematic Patterns:* Email signup before content viewed, feedback modals during tasks, stacked modals.

*When Modals ARE Appropriate:* Critical confirmations, short focused data entry, legal requirements.

**Auto-Playing Media**
- Audio >3 seconds without stop mechanism = **WCAG failure**
- Creates unexpected data costs on mobile
- Disrupts screen reader users

*What to Do Instead:* Require user action. If auto-play needed, mute by default with visible controls.

**Hidden Navigation (Hamburger Menu)**
Nielsen Norman study (179 participants):
- Reduces task success rates
- Reduces content discoverability
- **Worse on desktop than mobile**
- 25% of apps deleted after first use partly due to hidden features

*What to Do Instead:* Show top 4-5 nav items visibly. Use hamburger only for secondary items. Always show primary nav on desktop.

**Dark Patterns (Now Illegal in Some Jurisdictions)**
India banned 12 dark patterns (2023), FTC enforcing ($141M Intuit settlement):

| Pattern | Description |
|---------|-------------|
| Confirmshaming | Guilt-trip language |
| Roach Motel | Easy signup, impossible cancel |
| Basket Sneaking | Adding items without consent |
| Hidden Costs | Drip pricing at checkout |
| False Urgency | Fake countdown timers |

## Visual Design Anti-Patterns

**Color Mistakes**
- Using default framework colors (breaks brand)
- Insufficient contrast (WCAG requires **4.5:1** for text)
- Too many accent colors competing

*What to Do Instead:* Define semantic tokens, limit to 3-5 colors, use 60-30-10 rule.

**Spacing Inconsistencies**
- Magic number values (`p-[123px]`)
- Cramped touch targets (<44px)

*What to Do Instead:* Use spacing scale (4, 8, 16, 24, 32px), maintain 44×44px touch targets.

**Typography Hierarchy Failures**
- No visual distinction between heading levels
- Skipping heading levels (h1 → h3) = **WCAG failure**
- Body text <16px

*What to Do Instead:* Use modular scale (1.25× or 1.333×), 16-18px minimum body, line-height 1.4-1.6.

## Performance Anti-Patterns

**Animation Blocking (INP)**
INP Thresholds: Good ≤200ms, Poor >500ms

| ❌ Avoid (Layout) | ✅ Use (GPU) |
|-------------------|--------------|
| `left`, `top` | `transform` |
| `width`, `height` | `scale` |
| `margin`, `padding` | `opacity` |

**Layout Shift Causes (CLS)**
Target: ≤0.1

| Cause | Fix |
|-------|-----|
| Images without dimensions | Use `next/image`, set width/height |
| Web fonts FOUT | Use `next/font` |
| Dynamic content injection | Reserve space with skeleton |
| Cookie banners pushing content | Use overlay positioning |

**JavaScript Blocking**
- Synchronous third-party scripts in `<head>`
- Large bundles blocking first paint

*What to Do Instead:* Use `next/script` with `strategy="lazyOnload"`, code-split, lazy-load non-critical components.

## Accessibility Anti-Patterns

**WebAIM Million 2025 - Top 6 Failures:**

| Failure | % of Pages |
|---------|------------|
| Low contrast text | **83.6%** |
| Missing alt text | 54.5% |
| Empty links | 48.6% |
| Missing form labels | 45.0% |
| Empty buttons | 27.5% |
| Missing document language | 17.1% |

**Keyboard Navigation Failures**
- Custom components without keyboard support
- Focus trapped in modals without escape
- Removing focus outlines (`:focus { outline: none }`)

*What to Do Instead:* Use semantic HTML, ensure focus indicators visible, test with keyboard only.

**WCAG 2.2 New Requirements**
- Focus Not Obscured (2.4.11): Focused elements partially visible
- Target Size Minimum (2.5.8): **24×24px** minimum touch targets

## Conversion Anti-Patterns

**CTA Visibility Issues**
- **53%** of Fortune 500 lack proper homepage CTAs
- **70%** of small business sites have no homepage CTA
- Adding CTA increases conversions by **80%**

*What to Do Instead:* Contrasting colors, above the fold, one primary CTA per viewport, action-oriented text.

**Form Friction**
- Asking unnecessary information
- Error messages only after submission
- No inline validation

*What to Do Instead:* Ask only essential info, inline validation, clear error messages next to fields.

## Code Anti-Patterns

**React Anti-Patterns**
| Anti-Pattern | Fix |
|--------------|-----|
| Prop drilling | Use Context or Zustand/Jotai |
| Index as key | Use unique stable IDs |
| Mutating state | Return new objects in updates |
| Huge components | Break into smaller focused components |

**Next.js 15 Anti-Patterns**
| Anti-Pattern | Fix |
|--------------|-----|
| Not using Server Components | Default to RSC, use 'use client' only when needed |
| Raw `<img>` tags | Always use `next/image` |
| CSS @import for fonts | Use `next/font` |
| Blocking scripts | Use `strategy="lazyOnload"` |

**Tailwind Anti-Patterns**
| Anti-Pattern | Fix |
|--------------|-----|
| Magic values (`p-[123px]`) | Use theme tokens |
| Overusing @apply | Use raw utilities |
| Dynamic classes (`bg-${color}-500`) | Use complete strings or safelist |
| Default colors in production | Customize theme |

**shadcn/ui Anti-Pattern**
Do NOT rebuild shadcn components. They're accessible and battle-tested. Customize via Tailwind and extend variants.

## Top 10 Anti-Patterns to Eliminate

1. **Auto-rotating carousels** → Static content or user-controlled
2. **Premature email popups** → Wait until engagement
3. **Hidden desktop navigation** → Show primary nav
4. **Low contrast text** → 4.5:1 minimum
5. **Images without dimensions** → Always set width/height
6. **Animating layout properties** → Use transform/opacity
7. **Index as React key** → Use unique IDs
8. **Magic values in Tailwind** → Use design tokens
9. **Missing form labels** → Always use `<label>`
10. **Dark patterns** → Increasingly illegal

