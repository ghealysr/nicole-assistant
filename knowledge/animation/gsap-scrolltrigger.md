<!-- category: animation -->
<!-- keywords: gsap, scrolltrigger, scroll animation, react, nextjs, parallax, pin, scrub, performance -->

# GSAP ScrollTrigger Reference for React/Next.js 15

Since Webflow's acquisition of GreenSock in 2024, **all GSAP plugins including ScrollTrigger are completely free** for all uses. ScrollTrigger enables scroll-driven animations with precise control over timing, pinning, and scrubbing.

## Installation

```bash
npm install gsap @gsap/react
```

## Basic Setup

```typescript
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);
```

## Core API Reference

| Property | Description |
|----------|-------------|
| `trigger` | Element that triggers the animation |
| `start` | When animation starts: `"top bottom"`, `"center center"` |
| `end` | When animation ends: `"bottom top"`, `"+=500"` |
| `scrub` | Links to scrollbar. `true` = instant, `1` = 1s catch-up |
| `pin` | Pins element during active state |
| `markers` | Shows visual debugging markers |
| `toggleActions` | Actions on enter/leave: `"play pause resume reset"` |
| `snap` | Snap to progress values |
| `anticipatePin` | Anticipate pin to avoid flash (0-1) |

**Start/End Syntax:**
```javascript
start: "top bottom"      // trigger's top meets viewport bottom
start: "center center"   // trigger's center meets viewport center
start: "top 80%"         // trigger's top at 80% from viewport top
end: "+=500"             // 500px beyond start
end: () => `+=${element.offsetHeight}` // dynamic
```

## useGSAP Hook (React 18+)

```tsx
"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP, ScrollTrigger);

export default function AnimatedSection() {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.to(".box", {
        x: 200,
        scrollTrigger: {
          trigger: ".box",
          start: "top 80%",
          end: "bottom 20%",
          scrub: 1,
        },
      });
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef}>
      <div className="box">Animated Box</div>
    </div>
  );
}
```

## Next.js 15 Integration

```tsx
// lib/gsapConfig.ts
"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

if (typeof window !== "undefined" && !gsap.core.globals()["ScrollTrigger"]) {
  gsap.registerPlugin(ScrollTrigger);
}

export { gsap, ScrollTrigger };
```

## Code Examples

**Basic Scroll-Triggered Reveal:**
```tsx
"use client";

import { useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger);

export default function RevealOnScroll() {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.from(".reveal-item", {
        y: 100,
        opacity: 0,
        duration: 1,
        stagger: 0.2,
        ease: "power2.out",
        scrollTrigger: {
          trigger: ".reveal-container",
          start: "top 80%",
          toggleActions: "play none none reverse",
        },
      });
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef}>
      <div className="reveal-container">
        <div className="reveal-item">Item 1</div>
        <div className="reveal-item">Item 2</div>
        <div className="reveal-item">Item 3</div>
      </div>
    </div>
  );
}
```

**Pinned Section with Scrub:**
```tsx
"use client";

export default function PinnedSection() {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: ".pin-container",
          start: "top top",
          end: "+=200%",
          pin: true,
          scrub: 1,
          anticipatePin: 1,
        },
      });

      tl.to(".pinned-content", { scale: 1.5, opacity: 0.5 })
        .to(".pinned-text", { y: -100, opacity: 1 })
        .to(".pinned-content", { rotation: 360 });
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef}>
      <div className="pin-container h-screen flex items-center justify-center">
        <div className="pinned-content w-64 h-64 bg-blue-500" />
        <h2 className="pinned-text opacity-0 absolute text-4xl">Scroll to reveal</h2>
      </div>
    </div>
  );
}
```

**Horizontal Scroll Section:**
```tsx
"use client";

export default function HorizontalScroll() {
  const containerRef = useRef<HTMLDivElement>(null);
  const horizontalRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const sections = gsap.utils.toArray<HTMLElement>(".panel");

      gsap.to(sections, {
        xPercent: -100 * (sections.length - 1),
        ease: "none",
        scrollTrigger: {
          trigger: horizontalRef.current,
          pin: true,
          scrub: 1,
          snap: 1 / (sections.length - 1),
          end: () => "+=" + (horizontalRef.current?.scrollWidth || 0),
        },
      });
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef}>
      <div ref={horizontalRef} className="flex" style={{ width: "400vw" }}>
        {["red", "blue", "green", "purple"].map((color, i) => (
          <section key={i} className={`panel w-screen h-screen flex items-center justify-center bg-${color}-500`}>
            <h2 className="text-4xl text-white">Section {i + 1}</h2>
          </section>
        ))}
      </div>
    </div>
  );
}
```

**Parallax Effect:**
```tsx
useGSAP(() => {
  // Background (slower)
  gsap.to(".parallax-bg", {
    yPercent: -30,
    ease: "none",
    scrollTrigger: {
      trigger: ".parallax-section",
      start: "top bottom",
      end: "bottom top",
      scrub: true,
    },
  });

  // Foreground (faster)
  gsap.to(".parallax-fg", {
    yPercent: 20,
    ease: "none",
    scrollTrigger: {
      trigger: ".parallax-section",
      start: "top bottom",
      end: "bottom top",
      scrub: true,
    },
  });
}, { scope: containerRef });
```

## Performance Optimization

**GPU-Accelerated Properties (Always Use):**
```javascript
// ✅ GOOD - GPU accelerated
gsap.to(".element", {
  x: 100,          // transform: translateX()
  y: 50,           // transform: translateY()
  scale: 1.2,      // transform: scale()
  rotation: 45,    // transform: rotate()
  opacity: 0.5,
});

// ❌ AVOID - Triggers layout recalculation
gsap.to(".element", {
  left: 100,       // Expensive
  width: 200,      // Triggers reflow
  boxShadow: "...", // Expensive paint
});
```

**Performance Checklist:**
- Use `transform` and `opacity` only
- Use numerical scrub (`scrub: 0.5`) for smoother performance
- Batch similar animations with stagger
- Avoid `will-change: transform` on pinned element ancestors (breaks `position: fixed`)
- Call `ScrollTrigger.refresh()` after dynamic content loads

## Accessibility with prefers-reduced-motion

```tsx
useGSAP(() => {
  const mm = gsap.matchMedia();

  mm.add(
    {
      isDesktop: "(min-width: 800px)",
      reduceMotion: "(prefers-reduced-motion: reduce)",
    },
    (context) => {
      const { isDesktop, reduceMotion } = context.conditions!;

      gsap.to(".box", {
        x: isDesktop ? 400 : 200,
        rotation: reduceMotion ? 0 : 360,
        duration: reduceMotion ? 0 : 1,
        scrollTrigger: {
          trigger: ".box",
          start: "top 80%",
          scrub: reduceMotion ? false : 1,
        },
      });
    }
  );
}, { scope: containerRef });
```

## Debugging

```javascript
scrollTrigger: {
  trigger: ".element",
  markers: true,  // Shows start/end markers
  onUpdate: (self) => {
    console.log("progress:", self.progress.toFixed(3));
    console.log("direction:", self.direction);
  },
}

// Get all ScrollTriggers
console.log(ScrollTrigger.getAll());

// Force refresh
ScrollTrigger.refresh();
```

## Common Pitfalls in React

| Problem | Solution |
|---------|----------|
| Duplicate ScrollTriggers in Strict Mode | Use `useGSAP()` hook |
| Pin not working | Check for transforms on parents; use `pinReparent: true` |
| Animations fire on load | Use `start: "top 80%"` instead of `"top bottom"` |
| Nested ScrollTrigger in timeline | Put ScrollTrigger on timeline, not individual tweens |

## Server vs Client Components

- **Client Components Required** — All GSAP code needs `"use client"` directive
- **Hybrid Pattern** — Fetch data in Server Component, pass to Client Component with animations
- **Avoid Hydration Mismatches** — Use `mounted` state check if needed

