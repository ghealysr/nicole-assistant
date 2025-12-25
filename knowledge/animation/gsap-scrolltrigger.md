# GSAP ScrollTrigger: Advanced Production Techniques (December 2025)

<!-- category: animation -->
<!-- keywords: gsap, scrolltrigger, scroll animation, react, nextjs, performance, inp, usegsap, pinning, scrubbing, horizontal scroll -->

## GSAP 3.14.2 + Free Plugin Era

**Every GSAP plugin is now free** following Webflow's acquisition in October 2024. This includes ScrollTrigger, ScrollSmoother, SplitText v3, MorphSVG, DrawSVG, MotionPath, and all premium plugins. For $2-5K client websites, this means access to production-grade animation tools at zero licensing cost.

**Current Version:** GSAP 3.14.2 (December 2025)  
**ScrollTrigger:** Bundled with core  
**useGSAP Hook:** v2.1.2 for React integration  
**React 19/Next.js 15:** Fully compatible

## React 19 & Next.js 15 Integration

### useGSAP Hook: Drop-In Replacement for useEffect

The `useGSAP` hook solves React-specific friction by auto-handling cleanup via `gsap.context()`. All GSAP animations, ScrollTriggers, Draggables, and SplitText instances created during hook execution get reverted automatically on unmount.

```typescript
// app/components/AnimatedSection.tsx
"use client";

import { useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(ScrollTrigger, useGSAP);

export default function AnimatedSection() {
  const container = useRef<HTMLDivElement>(null);
  
  useGSAP(() => {
    // All animations auto-scoped to container
    gsap.from('.fade-in', {
      opacity: 0,
      y: 50,
      stagger: 0.1,
      scrollTrigger: {
        trigger: container.current,
        start: 'top 80%',
        end: 'bottom 20%',
        toggleActions: 'play none none reverse'
      }
    });
  }, { scope: container }); // Magic: selector text scoped to container

  return (
    <div ref={container}>
      <div className="fade-in">Item 1</div>
      <div className="fade-in">Item 2</div>
      <div className="fade-in">Item 3</div>
    </div>
  );
}
```

### Context-Safe Functions for Event Handlers

Animations in click handlers, setTimeout, or delayed callbacks need `contextSafe()` wrapper:

```typescript
const container = useRef();

const { contextSafe } = useGSAP({ scope: container });

// ✅ Context-safe click handler
const handleClick = contextSafe(() => {
  gsap.to('.box', { rotation: 360, duration: 1 });
});

return <button onClick={handleClick}>Animate</button>;
```

### Next.js App Router Setup (Client Components)

```typescript
// lib/gsap.ts - Centralized GSAP configuration
"use client";

import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ScrollSmoother } from 'gsap/ScrollSmoother';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(ScrollTrigger, ScrollSmoother, SplitText);

// Global defaults
gsap.defaults({
  duration: 0.6,
  ease: 'power2.out'
});

gsap.config({
  autoSleep: 60,
  nullTargetWarn: false
});

export { gsap, ScrollTrigger, ScrollSmoother, SplitText };
```

```typescript
// app/components/ScrollSection.tsx
"use client";

import { useRef } from 'react';
import { gsap, ScrollTrigger } from '@/lib/gsap';
import { useGSAP } from '@gsap/react';

gsap.registerPlugin(useGSAP);

export default function ScrollSection() {
  const sectionRef = useRef<HTMLElement>(null);
  
  useGSAP(() => {
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: sectionRef.current,
        start: 'top top',
        end: '+=100%',
        pin: true,
        scrub: 1,
        anticipatePin: 1,
        invalidateOnRefresh: true
      }
    });

    tl.to('.hero-title', { scale: 1.5, opacity: 0 })
      .to('.hero-bg', { opacity: 0 }, '<0.1');
      
  }, { scope: sectionRef, dependencies: [] });

  return <section ref={sectionRef}>...</section>;
}
```

**Critical:** Always add `"use client"` directive for components using GSAP in Next.js App Router.

## Performance Optimization for INP ≤200ms

**INP (Interaction to Next Paint)** replaced FID as Core Web Vital in March 2024. Good INP: ≤200ms, Poor: >500ms.

### GPU-Accelerated Properties Only

| Property | Compositor Thread | INP Impact |
|----------|-------------------|------------|
| `transform` | ✅ Yes | Minimal |
| `opacity` | ✅ Yes | Minimal |
| `filter` | ❌ No (expensive) | High |
| `box-shadow` | ❌ No (very expensive) | Very High |
| `width`, `height` | ❌ No (layout) | Critical |
| `top`, `left` | ❌ No (layout) | Critical |

```javascript
// ❌ BAD - Triggers layout, destroys INP
gsap.to('.box', { width: 500, height: 300 });

// ✅ GOOD - GPU-accelerated, maintains INP
gsap.to('.box', { scale: 1.5, x: 100, opacity: 0.8 });
```

### ScrollTrigger.batch() for Many Elements

When animating 50+ elements, `batch()` creates a single ScrollTrigger managing multiple targets:

```javascript
ScrollTrigger.batch('.batch-item', {
  onEnter: batch => gsap.to(batch, {
    opacity: 1,
    y: 0,
    stagger: 0.1,
    overwrite: true
  }),
  once: true,
  start: 'top 85%'
});
```

**Performance win:** 1 ScrollTrigger instance instead of 50, ~80% reduction in scroll handler overhead.

### Scrub Performance Tuning

```javascript
scrollTrigger: {
  scrub: true,    // ❌ Updates every scroll pixel (janky on low-end)
  scrub: 1,       // ✅ 1-second smooth catch-up (recommended)
  scrub: 0.5      // ⚡ Faster response, less smooth
}
```

Higher scrub values = smoother but delayed. Lower = more responsive but less smooth. **Sweet spot:** 0.8-1.5s for most use cases.

## Advanced ScrollTrigger Techniques

### Pinning with anticipatePin

```javascript
gsap.timeline({
  scrollTrigger: {
    trigger: '#hero',
    start: 'top top',
    end: '+=200%',
    pin: true,
    anticipatePin: 1,        // Prevents flash of unpinned content
    pinSpacing: true,        // Adds space below pinned element
    invalidateOnRefresh: true // Recalculates on resize
  }
});
```

**anticipatePin:** Applies pin slightly early to combat browser repaint lag on fast scrolling. Value of 1 is typically sufficient.

### Horizontal Scroll Containers

```javascript
const sections = gsap.utils.toArray('.panel');

gsap.to(sections, {
  xPercent: -100 * (sections.length - 1),
  ease: 'none',
  scrollTrigger: {
    trigger: '.container',
    pin: true,
    scrub: 1,
    snap: 1 / (sections.length - 1),
    end: () => "+=" + document.querySelector('.container').offsetWidth
  }
});
```

**Production pattern:** Horizontal scroll driven by vertical scroll, with snap points for each panel.

### matchMedia() for Responsive Animations

```javascript
const mm = gsap.matchMedia();

mm.add({
  isDesktop: '(min-width: 1024px)',
  isMobile: '(max-width: 1023px)',
  reduceMotion: '(prefers-reduced-motion: reduce)'
}, (context) => {
  const { isDesktop, isMobile, reduceMotion } = context.conditions;
  
  if (reduceMotion) {
    // Simple fade only
    gsap.set('.animated', { opacity: 1 });
    return;
  }
  
  gsap.to('.hero', {
    y: isDesktop ? -200 : -100,
    scrollTrigger: {
      start: 'top top',
      end: '+=100%',
      scrub: isDesktop ? 1 : true
    }
  });
});

// Cleanup on component unmount
return () => mm.revert();
```

**Why this pattern?** Animations/ScrollTriggers auto-revert when media query stops matching. No manual cleanup.

### invalidateOnRefresh for Dynamic Layouts

```javascript
scrollTrigger: {
  invalidateOnRefresh: true  // Recalculates start/end on window resize
}
```

**Use when:** Element positions change on resize (flexbox, grid, responsive type scaling). Without this, ScrollTrigger uses cached pixel values that become stale.

## SplitText v3 for Typography Animations

**SplitText now free (rewritten for accessibility in v3):**

```javascript
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(SplitText);

const split = new SplitText('.headline', { 
  type: 'chars,words',
  charsClass: 'char',
  wordsClass: 'word'
});

gsap.from(split.chars, {
  opacity: 0,
  y: 20,
  rotateX: -90,
  stagger: 0.02,
  scrollTrigger: {
    trigger: '.headline',
    start: 'top 80%'
  }
});

// Cleanup
return () => split.revert();
```

**Accessibility:** SplitText v3 preserves text content for screen readers while visually splitting for animation.

## CSS Scroll-Driven Animations vs GSAP

**Browser Support (December 2025):**

| Feature | Chrome | Firefox | Safari | Coverage |
|---------|--------|---------|--------|----------|
| `scroll()` | 115+ | 127+ (flag) | ❌ None | ~70% |
| `view()` | 115+ | 127+ (flag) | ❌ None | ~70% |
| Relative color syntax | 119+ | 128+ | 18.0+ | ~86% |

**Decision Matrix:**

| Use Case | CSS | GSAP ScrollTrigger |
|----------|-----|-------------------|
| Simple fade on scroll | ✅ CSS | ⚠️ Overkill |
| Parallax effects | ✅ CSS | ✅ GSAP |
| Multi-timeline orchestration | ❌ Limited | ✅ GSAP |
| Pinning sections | ❌ Not possible | ✅ GSAP |
| Horizontal scroll | ⚠️ Complex | ✅ GSAP |
| Snap points | ✅ CSS | ✅ GSAP |
| Cross-browser compat | ❌ 70% | ✅ 100% |

**Production Recommendation:** Use CSS for simple viewport-based fades, GSAP for everything else. Don't mix both on same elements.

### CSS Scroll Animation Example

```css
.fade-in {
  animation: fade-in linear;
  animation-timeline: view();
  animation-range: entry 0% cover 40%;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@supports not (animation-timeline: view()) {
  .fade-in {
    opacity: 1; /* Fallback for Safari */
  }
}
```

## Accessibility: prefers-reduced-motion

**WCAG 2.2 Success Criterion 2.3.1:** No content flashes more than 3 times per second.

```javascript
const mm = gsap.matchMedia();

mm.add('(prefers-reduced-motion: reduce)', () => {
  // Instant state changes, no animation
  gsap.set('.animated', { opacity: 1, y: 0 });
});

mm.add('(prefers-reduced-motion: no-preference)', () => {
  // Full animations
  gsap.from('.animated', {
    opacity: 0,
    y: 50,
    duration: 0.8,
    scrollTrigger: { trigger: '.animated' }
  });
});
```

**Alternative pattern:**

```javascript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

gsap.from('.hero', {
  opacity: 0,
  y: prefersReducedMotion ? 0 : 100,
  duration: prefersReducedMotion ? 0 : 1
});
```

## Debugging Tools

### Visual Markers

```javascript
scrollTrigger: {
  markers: true,  // Shows start/end triggers
  id: 'hero-pin'  // Labels markers
}
```

**Remove in production** - adds ~2kb per ScrollTrigger and impacts performance.

### ScrollTrigger.refresh()

Call after DOM changes:

```javascript
// After dynamically adding content
document.querySelector('.container').innerHTML += newContent;
ScrollTrigger.refresh();

// After lazy-loaded images
img.onload = () => ScrollTrigger.refresh();
```

### Common Gotchas

1. **Forgetting to register plugins:**
```javascript
gsap.registerPlugin(ScrollTrigger); // Required!
```

2. **Not scoping selectors in React:**
```javascript
// ❌ Selects ALL .box elements on page
gsap.to('.box', { x: 100 });

// ✅ Scoped to component
useGSAP(() => {
  gsap.to('.box', { x: 100 });
}, { scope: container });
```

3. **Pinning without pinSpacing:**
```javascript
// Content jumps when pin ends
pin: true,
pinSpacing: false  // ❌ Breaks layout

// Smooth transition
pin: true,
pinSpacing: true   // ✅ Adds placeholder space
```

## Production Examples (Awwwards Dec 2025)

**Lando Norris Website (Codrops, Dec 2025):**
- Responsive curved path animations with MotionPath
- Visual configurator for cubic Bezier control points
- `invalidateOnRefresh: true` for layout recalculation

```javascript
const pathString = buildPathString(positions, controlPoints);

gsap.timeline({
  scrollTrigger: {
    trigger: section,
    start: 'top top',
    end: 'bottom bottom',
    scrub: true,
    invalidateOnRefresh: true
  }
}).to(img, {
  motionPath: {
    path: pathString,
    autoRotate: false
  },
  ease: 'none'
});
```

## Performance Checklist

- [ ] Animate only `transform` and `opacity`
- [ ] Use `ScrollTrigger.batch()` for 20+ elements
- [ ] Set `scrub: 1` instead of `scrub: true`
- [ ] Add `anticipatePin: 1` on pinned sections
- [ ] Include `invalidateOnRefresh: true` for responsive layouts
- [ ] Use `matchMedia()` for mobile/desktop variants
- [ ] Implement `prefers-reduced-motion` fallbacks
- [ ] Remove `markers: true` in production
- [ ] Test INP in Chrome DevTools (<200ms target)
- [ ] Call `ScrollTrigger.refresh()` after dynamic content

## Dos and Don'ts

**DO:**
- Use `useGSAP` hook in React (auto-cleanup)
- Animate `transform`, `opacity`, `filter` (GPU-accelerated)
- Batch similar animations with `ScrollTrigger.batch()`
- Use `contextSafe()` for delayed animations (clicks, setTimeout)
- Set `scrub: 0.8-1.5` for smooth scrolling
- Add `"use client"` in Next.js App Router components
- Provide `prefers-reduced-motion` alternatives

**DON'T:**
- Animate `width`, `height`, `margin`, `top`, `left` (layout thrashing)
- Forget `gsap.registerPlugin(ScrollTrigger, useGSAP)`
- Use `markers: true` in production (performance cost)
- Mix CSS scroll animations + GSAP on same element
- Skip `invalidateOnRefresh` on responsive layouts
- Create 50+ individual ScrollTriggers (use batch instead)
- Ignore INP metrics (target ≤200ms)

## Version Reference

| Package | Version | Release |
|---------|---------|---------|
| GSAP | 3.14.2 | Dec 2025 |
| ScrollTrigger | 3.14.2 | Bundled |
| @gsap/react | 2.1.2 | Dec 2024 |
| React | 19.0.0 | Dec 2024 |
| Next.js | 15.x | Oct 2024 |

---

**All GSAP plugins free since October 2024.** Use ScrollTrigger, ScrollSmoother, SplitText, MorphSVG, DrawSVG without licensing costs.
