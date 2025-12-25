# Motion for React: Production Animation Guide (December 2025)

<!-- category: animation -->
<!-- keywords: motion, framer motion, react animation, nextjs, gestures, layout animations, scroll, performance, bundle size -->

## Motion v12: The Framer Motion Rebrand

**Motion (formerly Framer Motion) v12.23.26** is now framework-agnostic. In November 2024, Matt Perry announced independence from Framer, rebranding as Motion with support for React, vanilla JavaScript, and Vue (coming soon).

**CRITICAL PACKAGE CHANGE:**

```javascript
// ❌ OLD (still works but deprecated)
import { motion } from "framer-motion";

// ✅ NEW (December 2025)
import { motion } from "motion/react";
```

**This solves React 19 compatibility issues.** The `motion/react` import works seamlessly with React 19 and Next.js 15, while `framer-motion` has peer dependency conflicts.

**Current Version:** 12.23.26 (December 2025)  
**React 19:** ✅ Compatible via `motion/react`  
**Next.js 15:** ✅ App Router + Server Components supported  
**Bundle Size:** 34kb (motion) → 4.6kb (m + LazyMotion)

## React 19 & Next.js 15 Integration

### Next.js App Router Setup

```typescript
// app/components/FadeIn.tsx
"use client";

import { motion } from "motion/react";

export default function FadeIn({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {children}
    </motion.div>
  );
}
```

**Server Component Boundary:**
```typescript
// app/page.tsx (Server Component)
import FadeIn from './components/FadeIn'; // Client Component

export default function Page() {
  return (
    <main>
      <FadeIn>
        <h1>This fades in</h1>
      </FadeIn>
    </main>
  );
}
```

**Critical:** Motion components MUST be Client Components (`"use client"`). Server Components cannot use hooks or browser APIs.

### Page Transitions in App Router

```typescript
// app/template.tsx
"use client";

import { motion, AnimatePresence } from "motion/react";
import { usePathname } from "next/navigation";

export default function Template({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

**Why template.tsx?** Re-renders on route changes, enabling exit animations. `layout.tsx` persists across routes.

## Bundle Size Optimization

### LazyMotion: 34kb → 4.6kb

The `motion` component includes ALL features. The `m` component + `LazyMotion` loads features on-demand:

```typescript
// app/components/OptimizedMotion.tsx
"use client";

import { LazyMotion, domAnimation, m } from "motion/react";

export default function OptimizedMotion() {
  return (
    <LazyMotion features={domAnimation}>
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        whileHover={{ scale: 1.05 }}
      >
        Lightweight animation
      </m.div>
    </LazyMotion>
  );
}
```

### Feature Packages

| Package | Size | Features |
|---------|------|----------|
| `domAnimation` | +15kb | Animations, variants, exit, tap/hover/focus gestures |
| `domMax` | +25kb | All above + pan/drag gestures, layout animations |

**Production Strategy:** Use `domAnimation` for most sites. Only load `domMax` if you need drag or layout animations.

### Lazy Loading Features

```typescript
// features.ts
import { domMax } from "motion/react";
export default domMax;

// Component.tsx
import { LazyMotion, m } from "motion/react";

const loadFeatures = () => import("./features").then(res => res.default);

function App() {
  return (
    <LazyMotion features={loadFeatures} strict>
      <m.div animate={{ opacity: 1 }} />
    </LazyMotion>
  );
}
```

**`strict` mode:** Throws error if regular `motion` component used (prevents accidental 34kb import).

### useAnimate: The Smallest Option (2.3kb)

For imperative animations without declarative API:

```typescript
import { useAnimate } from "motion/react";

function Component() {
  const [scope, animate] = useAnimate();
  
  const handleClick = () => {
    animate(scope.current, { rotate: 360 }, { duration: 0.5 });
  };
  
  return <div ref={scope} onClick={handleClick}>Click me</div>;
}
```

**When to use:** Simple manual animations. **When not:** Complex orchestration, variants, gestures.

## Core Animation Patterns

### Variants for Orchestration

```typescript
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

function List({ items }) {
  return (
    <motion.ul variants={container} initial="hidden" animate="show">
      {items.map(item => (
        <motion.li key={item.id} variants={item}>
          {item.text}
        </motion.li>
      ))}
    </motion.ul>
  );
}
```

**Why variants?** Children automatically inherit parent's animation state. No prop drilling.

### AnimatePresence for Exit Animations

```typescript
import { motion, AnimatePresence } from "motion/react";

function Modal({ isOpen, onClose }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.2 }}
        >
          <div onClick={onClose}>Close</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

**Critical:** Component MUST be direct child of `AnimatePresence`. Wrapping divs break exit detection.

### Layout Animations (Auto FLIP)

```typescript
import { motion } from "motion/react";

function ExpandingCard({ isExpanded }) {
  return (
    <motion.div layout>
      <motion.h2 layout>Title</motion.h2>
      {isExpanded && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          Content
        </motion.p>
      )}
    </motion.div>
  );
}
```

**How it works:** Motion measures element before/after state change, then animates the difference using FLIP technique (First, Last, Invert, Play).

**Performance:** Layout animations are expensive (~16-32ms). Use sparingly on complex layouts.

## Scroll Animations

### useScroll Hook

```typescript
import { motion, useScroll, useTransform } from "motion/react";

function ParallaxSection() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], ['0%', '-50%']);
  const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [1, 0.5, 0]);
  
  return (
    <motion.div style={{ y, opacity }}>
      Parallax content
    </motion.div>
  );
}
```

### useInView for Viewport Triggers

```typescript
import { motion, useInView } from "motion/react";
import { useRef } from "react";

function FadeInWhenVisible({ children }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5 }}
    >
      {children}
    </motion.div>
  );
}
```

**`margin` option:** Triggers before element fully enters viewport. `"-100px"` = trigger 100px before entering.

### Scroll-Linked Progress Bars

```typescript
import { motion, useScroll } from "motion/react";

function ProgressBar() {
  const { scrollYProgress } = useScroll();
  
  return (
    <motion.div
      style={{
        scaleX: scrollYProgress,
        transformOrigin: 'left',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 4,
        background: 'blue'
      }}
    />
  );
}
```

## Gesture Handling

### Drag with Constraints

```typescript
<motion.div
  drag
  dragConstraints={{ left: 0, right: 300, top: 0, bottom: 300 }}
  dragElastic={0.2}
  dragTransition={{ bounceStiffness: 600, bounceDamping: 20 }}
>
  Drag me
</motion.div>
```

**dragElastic:** 0 = no overshoot, 1 = full elastic. **Sweet spot:** 0.1-0.3.

### Hover & Tap States

```typescript
<motion.button
  whileHover={{ scale: 1.05, backgroundColor: "#3b82f6" }}
  whileTap={{ scale: 0.95 }}
  transition={{ duration: 0.2 }}
>
  Interactive Button
</motion.button>
```

**Accessibility:** These work with keyboard focus too. `whileFocus` also available.

### Drag Momentum & Snap

```typescript
<motion.div
  drag="x"
  dragSnapToOrigin
  onDragEnd={(event, info) => {
    if (Math.abs(info.offset.x) > 100) {
      // Threshold reached, navigate
    }
  }}
>
  Swipe to dismiss
</motion.div>
```

## Performance Optimization

### Motion Values (Prevents Re-renders)

```typescript
import { motion, useMotionValue, useTransform } from "motion/react";

function Component() {
  const x = useMotionValue(0);
  const opacity = useTransform(x, [-100, 0, 100], [0, 1, 0]);
  
  return (
    <motion.div
      drag="x"
      style={{ x, opacity }}
    />
  );
}
```

**Why this matters:** `x` updates don't trigger React re-renders. Only GPU-accelerated transform updates.

### useReducedMotion Hook

```typescript
import { motion, useReducedMotion } from "motion/react";

function Component() {
  const shouldReduceMotion = useReducedMotion();
  
  return (
    <motion.div
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.5 }}
    >
      Content
    </motion.div>
  );
}
```

**WCAG 2.2 SC 2.3.1:** Respect user preferences for reduced motion.

### GPU Acceleration Best Practices

```typescript
// ✅ GOOD - GPU-accelerated
<motion.div
  animate={{ x: 100, scale: 1.2, rotate: 45, opacity: 0.5 }}
/>

// ❌ BAD - Forces layout recalculation
<motion.div
  animate={{ width: 500, height: 300, marginLeft: 100 }}
/>
```

**Allowed:** `transform` (x, y, scale, rotate), `opacity`  
**Avoid:** `width`, `height`, `top`, `left`, `margin`, `padding`

## Integration Patterns

### Motion + Tailwind CSS

```typescript
import { motion } from "motion/react";

const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

function Card() {
  return (
    <motion.div
      className="rounded-lg bg-white p-6 shadow-lg"
      variants={variants}
      initial="hidden"
      animate="visible"
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.3 }}
    >
      Content
    </motion.div>
  );
}
```

**Pattern:** Tailwind for static styles, Motion for animation states.

### Motion + shadcn/ui

```typescript
"use client";

import { motion } from "motion/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const MotionCard = motion.create(Card);

export function AnimatedCard() {
  return (
    <MotionCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
    >
      <CardHeader>
        <CardTitle>Animated shadcn Card</CardTitle>
      </CardHeader>
      <CardContent>...</CardContent>
    </MotionCard>
  );
}
```

**`motion.create()`:** Wraps existing components while preserving TypeScript types.

### Motion + React Hook Form

```typescript
import { motion, AnimatePresence } from "motion/react";
import { useForm } from "react-hook-form";

function Form() {
  const { register, formState: { errors } } = useForm();
  
  return (
    <form>
      <input {...register("email", { required: true })} />
      <AnimatePresence>
        {errors.email && (
          <motion.span
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-red-500"
          >
            Email is required
          </motion.span>
        )}
      </AnimatePresence>
    </form>
  );
}
```

## Production Patterns

### Loading States

```typescript
import { motion } from "motion/react";

function LoadingButton({ isLoading, children, ...props }) {
  return (
    <motion.button
      {...props}
      animate={isLoading ? { opacity: 0.6 } : { opacity: 1 }}
      disabled={isLoading}
    >
      <motion.div
        animate={isLoading ? { rotate: 360 } : {}}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        style={{ display: "inline-block" }}
      >
        {isLoading ? "⟳" : children}
      </motion.div>
    </motion.button>
  );
}
```

### Stagger Animations

```typescript
const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const item = {
  hidden: { opacity: 0, scale: 0.8 },
  show: { opacity: 1, scale: 1 }
};

function Grid({ items }) {
  return (
    <motion.div
      className="grid grid-cols-3 gap-4"
      variants={container}
      initial="hidden"
      animate="show"
    >
      {items.map((item, i) => (
        <motion.div key={i} variants={item} className="aspect-square bg-gray-200" />
      ))}
    </motion.div>
  );
}
```

### Modal Animations

```typescript
import { motion, AnimatePresence } from "motion/react";
import { createPortal } from "react-dom";

function Modal({ isOpen, onClose, children }) {
  if (typeof window === 'undefined') return null;
  
  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="fixed inset-0 bg-black"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed inset-0 flex items-center justify-center"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              {children}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
}
```

## Motion vs GSAP: When to Use What

| Feature | Motion | GSAP ScrollTrigger |
|---------|--------|-------------------|
| React integration | ✅ Native | ⚠️ useGSAP hook |
| Bundle size | 4.6kb (optimized) | ~20kb |
| Declarative API | ✅ Yes | ❌ Imperative |
| Layout animations | ✅ Built-in | ❌ Manual |
| Drag gestures | ✅ Native | ⚠️ Via Draggable |
| Scroll pinning | ❌ No | ✅ Advanced |
| Complex timelines | ⚠️ Limited | ✅ Powerful |
| SVG morphing | ❌ Basic | ✅ MorphSVG |
| Learning curve | Gentle | Steep |

**Decision:**
- **Motion:** React-first projects, UI components, simple scroll effects
- **GSAP:** Complex scroll narratives, pinning, SVG animations, cross-framework

## Common Pitfalls

### 1. Forgetting AnimatePresence

```typescript
// ❌ Exit animation won't work
{isOpen && <motion.div exit={{ opacity: 0 }}>...</motion.div>}

// ✅ Wrap with AnimatePresence
<AnimatePresence>
  {isOpen && <motion.div exit={{ opacity: 0 }}>...</motion.div>}
</AnimatePresence>
```

### 2. Layout Animations Breaking Scroll

```typescript
// ❌ Janky scroll
<motion.div layout style={{ height: '100vh' }}>
  {items.map(...)}
</motion.div>

// ✅ Disable layout on scroll container
<div style={{ height: '100vh', overflow: 'auto' }}>
  {items.map(item => (
    <motion.div key={item.id} layout>...</motion.div>
  ))}
</div>
```

### 3. Using String Refs

```typescript
// ❌ Won't work
const ref = "myElement";

// ✅ Use useRef
const ref = useRef(null);
```

## Version Reference

| Package | Version | Import |
|---------|---------|--------|
| motion/react | 12.23.26 | `import { motion } from "motion/react"` |
| framer-motion | 12.23.26 | ⚠️ Deprecated, use motion/react |
| React | 19.0.0+ | Compatible |
| Next.js | 15.x+ | App Router supported |

## Performance Checklist

- [ ] Use `m` + `LazyMotion` instead of `motion` (34kb → 4.6kb)
- [ ] Load `domAnimation` (15kb) unless drag/layout needed
- [ ] Animate only `transform` and `opacity`
- [ ] Use `useMotionValue` to prevent re-renders
- [ ] Implement `useReducedMotion` for accessibility
- [ ] Wrap conditional renders in `AnimatePresence`
- [ ] Test on low-end devices (layout animations are expensive)
- [ ] Add `"use client"` directive in Next.js

## Dos and Don'ts

**DO:**
- Import from `motion/react` (not `framer-motion`)
- Use `m` + `LazyMotion` for bundle optimization
- Wrap exit animations in `AnimatePresence`
- Animate `transform` and `opacity` for GPU acceleration
- Use variants for complex orchestrations
- Implement `useReducedMotion` for WCAG compliance

**DON'T:**
- Animate `width`, `height`, `top`, `left` (layout shift)
- Forget `AnimatePresence` for exit animations
- Use layout animations on scroll containers
- Import `motion` if using `LazyMotion` (breaks strict mode)
- Nest `AnimatePresence` without `mode` prop
- Skip accessibility testing

---

**Motion v12 (December 2025)** is production-ready for React 19 and Next.js 15 via the `motion/react` import. Bundle size optimizations with LazyMotion make it viable even for performance-critical sites.

