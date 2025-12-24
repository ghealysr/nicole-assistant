<!-- category: patterns -->
<!-- keywords: hero section, cta, conversion, above fold, lcp, mobile optimization, video background, split screen -->

# Modern Hero Section Design Patterns

Hero sections remain the most critical conversion element on any landing page. **57% of viewing time is spent above the fold**, making hero optimization essential. The dominant patterns in 2024-2025 emphasize minimalism, clear value propositions, and performance-optimized imagery.

## Current Hero Pattern Taxonomy

**Minimalist Hero** — Clean lines, ample whitespace, singular value proposition with large typography. Best for high-end products, sophisticated brands, SaaS platforms. Example: Jasper AI's white-space-focused hero highlighting AI capabilities.

**Split-Screen Hero** — Two-column layout with image/graphic on one side, text/CTA on the other. Nielsen Norman research shows asymmetrical layouts guide eyes more predictably, reducing cognitive load. Best for product showcases and service descriptions.

**Bento Grid Hero (Trending)** — Compartmentalized boxes inspired by Apple/Microsoft design. Creates "choose-your-own-journey" experience with self-contained cards. Best for feature-rich products and multi-offering brands.

**Isolated Components Hero** — Deconstructed app/product UI components floating in the hero. Highlights specific features without showing the entire product. Popular with SaaS and app showcases.

**Full-Width Immersive Hero** — Full-screen background with overlaid text. Creates immediate emotional impact but carries risk: Nielsen Norman found **75% of users didn't realize they could scroll** past full-page heroes (creates "false floor" illusion).

## Award-Winning Examples (2024-2025)

| Site | Key Elements |
|------|--------------|
| **Linear** | Dark-themed, minimal, set the B2B SaaS standard |
| **Runway** | Bold fonts, immersive background video, dark theme |
| **Glide** | "Build business software you actually want" - clear value prop |
| **Memorisely** | Real user photos (not stock), community trust signals |

## CTA Placement Rules

**Conversion Data:**
- HubSpot CTAs embedded in content: **+121% conversions** vs bottom placement
- Button CTAs vs text links: **45% higher conversion rate**
- Upper-right quadrant: **17% more clicks** than center (B2B sites)
- Adding CTA button to landing pages: **+80% conversions**

**Placement Best Practices:**
- Primary CTA must be above fold
- Same CTA in multiple spots for longer pages
- Minimum 44×44px touch targets for mobile
- High contrast with background
- Action verbs ("Get Started" vs "Submit")

## Value Proposition Frameworks

**Formula 1: Problem → Solution**
```
[Action Verb] + [Specific Outcome] + [Without/In] + [Time/Pain Point]
"Simulate any business decision in seconds"
```

**Formula 2: Transformation Statement**
```
[End Result] + [Qualifier]
"Build something beautiful"
```

**Formula 3: Jobs-to-Be-Done**
```
[Product Type] for your [jobs-to-be-done]
"Smart search for your creative assets"
```

**Formula 4: Pain Point Elimination**
```
Do [focus on JTBD], not [time-consuming task]
"Say it with video, not meetings"
```

## Mobile Hero Guidelines

| Element | Desktop | Mobile |
|---------|---------|--------|
| Height | 400-600px | Fit viewport, show content peek |
| Headline | 48-72px | 28-40px |
| CTA size | 44×44px minimum | 44×44px minimum |
| Layout | Grid/split | Stack vertically |

**Mobile-Specific Rules:**
- Design mobile layouts separately, not as afterthoughts
- Show hint of content below hero to encourage scrolling
- Remove heavy animations for performance
- Background images need mobile-specific crops (portrait)

## Animation Recommendations

**Framer Motion (~32kb gzipped):**
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.6, ease: "easeOut" }}
>
  <HeroContent />
</motion.div>
```

Best for: UI transitions, page transitions, gesture support, layout animations.

**GSAP (~23kb gzipped):**
Best for: Complex timelines, SVG animations, scroll-driven animations (ScrollTrigger), performance-critical work.

**CSS Scroll-Driven Animations (Native):**
```css
.hero-text {
  animation: fadeScale linear;
  animation-timeline: view();
  animation-range: exit 0% exit 100%;
}
```
Status: Chrome stable (Dec 2024), Firefox behind flag, Safari needs polyfill.

**Performance Rules:**
- Use `transform` and `opacity` only (GPU-accelerated)
- Respect `prefers-reduced-motion`
- Limit simultaneous animations to 3-5 elements

## LCP Optimization for Heroes

**Target:** ≤2.5 seconds (75th percentile)

```html
<!-- Priority loading for LCP images -->
<img 
  src="/hero.webp" 
  fetchpriority="high" 
  loading="eager"
  width="1200"
  height="630"
  alt="Hero description"
/>

<!-- Preload critical images -->
<link rel="preload" fetchpriority="high" as="image" href="/hero.webp" type="image/webp">
```

**Next.js Implementation:**
```tsx
<Image 
  src="/hero.webp" 
  alt="Hero"
  priority // Preloads image
  quality={75}
/>
```

**Critical Rules:**
- Never lazy-load hero images
- Use `fetchpriority="high"` on hero images
- Use WebP or AVIF (25-50% smaller than JPEG)
- Set explicit dimensions to prevent CLS
- Use `<img>` with `object-fit: cover`, not `background-image`

## Production Hero Component

```tsx
import { motion } from 'framer-motion'
import Image from 'next/image'

export function Hero() {
  return (
    <section className="relative min-h-[600px] flex items-center">
      <Image
        src="/hero-bg.webp"
        alt=""
        fill
        priority
        className="object-cover -z-10"
      />
      
      <div className="container mx-auto px-4">
        <div className="max-w-2xl">
          <span className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-sm mb-4">
            Trusted by 10,000+ teams
          </span>
          
          <motion.h1 
            className="text-4xl md:text-6xl font-bold mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            Build products users love
          </motion.h1>
          
          <p className="text-xl text-gray-600 mb-8">
            Ship faster with our developer-first platform.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <button className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
              Start Free Trial
            </button>
            <button className="px-8 py-4 border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              Watch Demo
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
```

## Hero Section Checklist

**✅ DO:**
- Lead with benefit, not feature
- Use one primary CTA
- Show product in action (screenshot, video, demo)
- Include social proof early
- Keep hero images under 200KB (WebP)
- Show peek of content below
- Use high contrast for text

**❌ DON'T:**
- Use full-screen heroes without scroll cues
- Lazy-load hero images
- Use vague headlines
- Use stock photos
- Animate more than 3-5 elements
- Block rendering with large CSS/JS

