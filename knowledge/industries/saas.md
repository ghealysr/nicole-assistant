---
title: SaaS & Software Product Design
category: industries
tags: [saas, software, b2b, product, dashboard, pricing]
priority: high
last_updated: 2026-01-02
---

# SaaS & Software Product Design

## Industry Context

SaaS products must balance **feature communication** with **simplicity**. Users are evaluating multiple solutions simultaneously, so clarity and trust signals are paramount.

### Key User Psychology

1. **Evaluation mindset**: Users compare 3-5 solutions before deciding
2. **Risk aversion**: Switching costs make commitment scary
3. **Feature fatigue**: Too many features overwhelm; focus on outcomes
4. **Trust barriers**: Security, reliability, and support matter deeply

## Visual Design Principles

### Color Strategy

**Primary Palette Approach:**
- **Blues and teals** dominate for trust and professionalism
- **Purple accents** for innovation and premium positioning
- **Green** for growth-focused or sustainability messaging
- **Avoid**: Overly playful colors unless targeting SMB/consumer

**Recommended Palettes:**

```json
{
  "enterprise_trust": {
    "primary": "#0066FF",
    "secondary": "#1A1A2E",
    "accent": "#00D9FF",
    "success": "#10B981",
    "neutral": "#64748B"
  },
  "modern_saas": {
    "primary": "#6366F1",
    "secondary": "#0F172A",
    "accent": "#22D3EE",
    "success": "#34D399",
    "neutral": "#94A3B8"
  },
  "growth_focus": {
    "primary": "#059669",
    "secondary": "#111827",
    "accent": "#FBBF24",
    "success": "#10B981",
    "neutral": "#6B7280"
  }
}
```

### Typography Patterns

**Heading + Body Pairings:**
- **Inter + Inter**: Clean, neutral, Swiss-style precision
- **Geist Sans + Geist Mono**: Modern, technical, developer-friendly
- **Space Grotesk + DM Sans**: Contemporary with character
- **Manrope + Source Sans Pro**: Friendly but professional

**Scale for Product Pages:**
```css
--text-display: clamp(2.5rem, 5vw, 4rem);   /* Hero headline */
--text-h1: clamp(2rem, 4vw, 3rem);          /* Section titles */
--text-h2: clamp(1.5rem, 3vw, 2rem);        /* Feature headers */
--text-h3: 1.25rem;                          /* Card titles */
--text-body: 1rem;                           /* Default */
--text-small: 0.875rem;                      /* Captions, metadata */
```

### Layout Patterns

**Hero Section (Critical):**
1. **Split hero**: Product screenshot right, value prop left
2. **Video hero**: Animated product demo with overlay CTA
3. **Metrics hero**: Key stats proving value immediately

**Feature Sections:**
- Bento grid for feature overview (3-4 key features)
- Alternating image/text for deep dives
- Icon grids for comprehensive feature lists

**Pricing Section:**
- 3-tier pricing (essential pattern)
- Highlight "most popular" tier
- Annual/monthly toggle with savings emphasis
- Enterprise CTA for custom pricing

## Conversion Optimization

### Above-the-Fold Requirements

1. **Clear value proposition**: One sentence, outcome-focused
2. **Primary CTA**: "Start Free Trial" or "Get Started Free"
3. **Social proof**: Logo bar of recognizable customers
4. **Product visual**: Screenshot or short demo

### Trust Signal Hierarchy

```
Position 1: Logo bar (below hero)
Position 2: Customer count or metric ("Trusted by 10,000+ teams")
Position 3: Testimonials with photos and company names
Position 4: Security badges near signup forms
Position 5: Case study links in footer
```

### CTA Best Practices

**Primary CTAs:**
- "Start Free Trial" (no credit card)
- "Get Started Free"
- "Try [Product] Free"

**Secondary CTAs:**
- "Book a Demo"
- "Watch Demo"
- "See How It Works"

**Avoid:**
- "Learn More" (too vague)
- "Contact Sales" as primary (too high friction)
- "Sign Up" alone (no value communicated)

## Component Specifications

### Navigation

```typescript
// SaaS navigation pattern
interface SaaSNavigation {
  logo: { height: '32px', position: 'left' };
  links: ['Product', 'Solutions', 'Pricing', 'Resources', 'Company'];
  cta: { primary: 'Start Free Trial', secondary: 'Login' };
  style: 'transparent' | 'blur' | 'solid';
  sticky: true;
  mobileBreakpoint: '768px';
}
```

### Pricing Cards

```typescript
interface PricingTier {
  name: string;
  price: { monthly: number; annual: number };
  description: string;
  features: string[];
  cta: string;
  highlighted?: boolean;  // "Most Popular"
  badge?: string;         // "Best Value", "Enterprise"
}
```

### Feature Cards

- Minimum padding: 24px
- Icon size: 40-48px (line icons or gradients)
- Title: H3 weight
- Description: 2-3 sentences max
- Optional: "Learn more" link

## Anti-Patterns to Avoid

1. **Feature dump**: Listing 20+ features without hierarchy
2. **No social proof**: Missing logos, testimonials, metrics
3. **Buried pricing**: Making users hunt for cost information
4. **Generic stock photos**: Use product screenshots instead
5. **Wall of text**: Long paragraphs instead of scannable content
6. **No clear CTA hierarchy**: Multiple competing buttons
7. **Dark patterns**: Confusing pricing, hidden fees
8. **Slow page load**: Heavy animations, unoptimized images

## Performance Requirements

- **LCP**: < 2.0s (product screenshots must be optimized)
- **CLS**: < 0.1 (no layout shifts from loading content)
- **FID**: < 100ms (interactive elements respond immediately)
- **Bundle size**: < 200KB initial JS

## Accessibility Checklist

- [ ] Pricing tables are accessible (not just visual cards)
- [ ] Video demos have captions
- [ ] Interactive demos are keyboard navigable
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Form errors are announced to screen readers

