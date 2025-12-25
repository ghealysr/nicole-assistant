<!-- category: components -->
<!-- keywords: aceternity, animated components, framer motion, motion, 3d card, bento grid, aurora, parallax, landing page, marketing -->

# Aceternity UI Component Library Reference

**Beautiful, animated React components for landing pages and marketing sites, built on Tailwind CSS and Framer Motion with a copy-paste approach.**

Aceternity UI provides **90+ free animated components** trusted by 12,000+ developers worldwide. The library excels at creating stunning visual effects for landing pages, portfolios, and SaaS marketing—the "wow factor" that converts visitors.

---

## Current state and compatibility

**Documentation:** ui.aceternity.com  
**Creator:** Manu Arora (@mannupaaji)  
**Component Count:** 90+ free, 70+ premium templates  
**React 19:** Compatible with Motion for React  
**Next.js 15:** Fully compatible  
**Tailwind CSS v4:** Full support

---

## Installation and setup

### CLI installation (recommended)

```bash
# Create Next.js app
npx create-next-app@latest my-app --typescript --tailwind --eslint

# Initialize shadcn CLI
cd my-app
npx shadcn@latest init

# Add Aceternity registry to components.json
{
  "registries": {
    "@aceternity": "https://ui.aceternity.com/registry/{name}.json"
  }
}

# Install components via CLI
npx shadcn@latest add @aceternity/3d-card
npx shadcn@latest add @aceternity/bento-grid
npx shadcn@latest add @aceternity/aurora-background
```

### Manual installation

```bash
# Install core dependencies
npm i motion clsx tailwind-merge
# For React 18 (legacy):
npm i framer-motion clsx tailwind-merge
```

Create utility function (`lib/utils.ts`):

```typescript
import { ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Dependency versions

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 15.0.3+ | Framework |
| `react` | 19.0.0 | UI Library |
| `tailwindcss` | v4.x | Styling |
| `motion` | ^12.0.0-alpha.1+ | Animations (React 19) |
| `framer-motion` | ^12.0.0-alpha.1+ | Animations (React 18) |
| `clsx` | latest | Class name utility |
| `tailwind-merge` | ^2.5.5+ | Class merging |

---

## Complete component catalog (90+ components)

### Background and effect components (24 components)

| Component | Description |
|-----------|-------------|
| **Dotted Glow Background** ⭐NEW | Opacity animation with glow effect |
| **Background Ripple Effect** ⭐NEW | Grid cells that ripple when clicked |
| **Sparkles** | Configurable sparkles effect |
| **Background Gradient** | Animated gradient background |
| **Wavy Background** | Moving wave animation |
| **Background Boxes** | Highlight-on-hover boxes |
| **Background Beams** | SVG path-following beams |
| **Background Beams With Collision** | Exploding beams effect |
| **Aurora Background** | Southern Lights effect |
| **Meteors** | Meteor shower background |
| **Shooting Stars** | Stars on starry background |
| **Vortex** | Swirly vortex background |
| **Spotlight** | Tailwind CSS spotlight effect |
| **Canvas Reveal Effect** | Dot expansion on hover (Clerk-style) |
| **SVG Mask Effect** | Cursor hover mask reveal |
| **Tracing Beam** | Scroll-following SVG beam |
| **Lamp Effect** | Linear-style section header |
| **Grid and Dot Backgrounds** | Simple grids and dots |
| **Glowing Effect** | Border glow (Cursor-style) |
| **Google Gemini Effect** | SVG animation from Gemini |

### Card components (15 components)

| Component | Description |
|-----------|-------------|
| **Tooltip Card** ⭐NEW | Mouse-following tooltip container |
| **Pixelated Canvas** ⭐NEW | Pixelated mouse distortion |
| **3D Card Effect** | Perspective tilt on hover |
| **Evervault Card** | Encrypted text reveal with gradient |
| **Card Stack** | Stacking cards for testimonials |
| **Card Hover Effect** | Sliding hover effect |
| **Wobble Card** | Translate/scale on mousemove |
| **Expandable Card** | Click-to-expand cards |
| **Card Spotlight** | Radial gradient spotlight reveal |
| **Focus Cards** | Blur unfocused cards on hover |
| **Infinite Moving Cards** | Infinite loop card carousel |
| **Draggable Card** | Tiltable, draggable with bounds |
| **Comet Card** ⭐NEW | 3D tilt (Perplexity Comet-style) |
| **Glare Card** | Glare effect (Linear-style) |
| **Direction Aware Hover** | Direction-based hover animation |

### Text animation components (10 components)

| Component | Description |
|-----------|-------------|
| **Encrypted Text** ⭐NEW | Gibberish text reveal effect |
| **Layout Text Flip** ⭐NEW | Layout-changing text flip |
| **Colourful Text** | Multi-color filter effects |
| **Text Generate Effect** | Fade-in text on load |
| **Typewriter Effect** | Typing animation |
| **Flip Words** | Word container flip animation |
| **Text Hover Effect** | Gradient outline on hover (x.ai-style) |
| **Container Text Flip** | Width-animating word flip |
| **Hero Highlight** | Background highlight for hero text |
| **Text Reveal Card** | Mousemove text reveal |

### Scroll and parallax components

| Component | Description |
|-----------|-------------|
| **Parallax Scroll** | Opposite-direction column scroll |
| **Sticky Scroll Reveal** | Sticky container with text reveal |
| **Macbook Scroll** | Image emerging from screen (Fey.com-style) |
| **Container Scroll Animation** | 3D rotation on scroll |
| **Hero Parallax** | Rotation/translation/opacity animations |

### Button components

| Component | Description |
|-----------|-------------|
| **Tailwind CSS Buttons** | Curated button collection |
| **Hover Border Gradient** | Expanding gradient border hover |
| **Moving Border** | Animated border movement |
| **Stateful Button** | Loading/success state button |
| **Noise Background** ⭐NEW | Animated gradient noise |

### Navigation components (7 components)

| Component | Description |
|-----------|-------------|
| **Floating Navbar** | Hide-on-scroll sticky navbar |
| **Navbar Menu** | Animated hover children |
| **Sidebar** | Expandable mobile-responsive sidebar |
| **Floating Dock** | macOS-style dock navigation |
| **Tabs** | Animated tab switching |
| **Resizable Navbar** | Width-changing navbar on scroll |
| **Sticky Banner** | Hide-on-scroll-down banner |

### Interactive components

| Component | Description |
|-----------|-------------|
| **Images Slider** | Full-page keyboard-navigable slider |
| **Carousel** | Microinteraction carousel with slider |
| **Apple Cards Carousel** | Minimal Apple.com-style carousel |
| **Compare** | Image comparison slider |
| **Timeline** | Sticky header with scroll beam |
| **Lens** | Zoom lens for images/videos |

### Layout components

| Component | Description |
|-----------|-------------|
| **Layout Grid** | Framer Motion layout animation |
| **Bento Grid** | Skewed grid with header components |
| **Container Cover** | Beams/space effect wrapper |

### 3D and special components

| Component | Description |
|-----------|-------------|
| **3D Pin** | Animated gradient pin on hover |
| **3D Marquee** | 3D grid marquee for testimonials |
| **GitHub Globe** | Interactive 3D globe (Three.js) |
| **World Map** | Animated lines and dots on map |

---

## Top component deep dives

### 3D Card Effect

Perspective-based card with hover elevation:

```typescript
import { CardContainer, CardBody, CardItem } from "@/components/ui/3d-card"

export function ThreeDCardDemo() {
  return (
    <CardContainer className="inter-var">
      <CardBody className="bg-gray-50 relative group/card dark:bg-black w-auto sm:w-[30rem] h-auto rounded-xl p-6 border">
        <CardItem translateZ="50" className="text-xl font-bold">
          Make things float in air
        </CardItem>
        <CardItem translateZ="100" className="w-full mt-4">
          <img src="/product.png" className="h-60 w-full object-cover rounded-xl" />
        </CardItem>
        <CardItem translateZ={20} className="mt-4">
          <button className="px-4 py-2 rounded-xl bg-black text-white">
            Sign up
          </button>
        </CardItem>
      </CardBody>
    </CardContainer>
  )
}
```

### Bento Grid

Modern asymmetric grid layout:

```typescript
import { BentoGrid, BentoGridItem } from "@/components/ui/bento-grid"

export function BentoGridDemo() {
  return (
    <BentoGrid className="max-w-4xl mx-auto">
      {items.map((item, i) => (
        <BentoGridItem
          key={i}
          title={item.title}
          description={item.description}
          header={item.header}
          icon={item.icon}
          className={i === 3 || i === 6 ? "md:col-span-2" : ""}
        />
      ))}
    </BentoGrid>
  )
}
```

### Floating Navbar

Responsive navbar that hides on scroll down, reveals on scroll up:

```typescript
import { FloatingNav } from "@/components/ui/floating-navbar"

const navItems = [
  { name: "Home", link: "/" },
  { name: "About", link: "/about" },
  { name: "Contact", link: "/contact" },
]

export function FloatingNavDemo() {
  return <FloatingNav navItems={navItems} />
}
```

### Text Generate Effect

Gradual text reveal with character animation:

```typescript
import { TextGenerateEffect } from "@/components/ui/text-generate-effect"

export function TextGenerateDemo() {
  return (
    <TextGenerateEffect 
      words="Oxygen gets you high. In a catastrophic emergency, we're taking giant, panicked breaths."
      className="text-4xl"
    />
  )
}
```

### Infinite Moving Cards (Marquee)

Continuously scrolling testimonial carousel:

```typescript
import { InfiniteMovingCards } from "@/components/ui/infinite-moving-cards"

export function InfiniteMovingCardsDemo() {
  return (
    <InfiniteMovingCards
      items={testimonials}
      direction="right"
      speed="slow"
      pauseOnHover={true}
    />
  )
}
```

---

## Framer Motion integration patterns

### Scroll-triggered animations

```typescript
const { scrollYProgress } = useScroll({
  target: ref,
  offset: ["start end", "end start"]
})

const y = useTransform(scrollYProgress, [0, 1], [0, -200])
const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [0, 1, 0])

// Spring smoothing for natural feel
const smoothY = useSpring(y, { stiffness: 400, damping: 90 })
```

### Stagger animations

```typescript
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3,
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
}

<motion.div variants={containerVariants} initial="hidden" animate="show">
  {items.map((item) => (
    <motion.div key={item.id} variants={itemVariants}>
      {item.content}
    </motion.div>
  ))}
</motion.div>
```

### AnimatePresence for mount/unmount

```typescript
<AnimatePresence mode="wait">
  {isVisible && (
    <motion.div
      key="modal"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
    />
  )}
</AnimatePresence>
```

### Spring physics configurations

```typescript
const springPresets = {
  gentle: { stiffness: 120, damping: 14 },
  wobbly: { stiffness: 180, damping: 12 },
  stiff: { stiffness: 400, damping: 30 },
  slow: { stiffness: 80, damping: 20, mass: 2 }
}

// Duration-based springs
transition={{ 
  type: "spring", 
  visualDuration: 0.5, 
  bounce: 0.25 
}}
```

---

## Accessibility implementation

### prefers-reduced-motion support

CSS approach:

```css
@media (prefers-reduced-motion: reduce) {
  .animated-element {
    animation: none !important;
    transition: none !important;
  }
}
```

Framer Motion approach:

```typescript
import { useReducedMotion, MotionConfig } from "motion/react"

// Global configuration
<MotionConfig reducedMotion="user">
  {children}
</MotionConfig>

// Per-component
function AnimatedComponent() {
  const shouldReduceMotion = useReducedMotion()
  
  return (
    <motion.div
      animate={{
        opacity: isVisible ? 1 : 0,
        x: shouldReduceMotion ? 0 : isVisible ? 0 : -100
      }}
    />
  )
}
```

### Custom reduced motion hook

```typescript
function usePrefersReducedMotion() {
  const [prefersReduced, setPrefersReduced] = useState(false)
  
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    setPrefersReduced(mediaQuery.matches)
    
    const handler = (e) => setPrefersReduced(e.matches)
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [])
  
  return prefersReduced
}
```

---

## Performance optimization

### GPU-accelerated properties

```typescript
// Use transform and opacity for GPU acceleration
animate={{ transform: 'translateX(100px)', opacity: 1 }}

// Avoid animating layout properties
// ❌ width, height, top, left, margin, padding
// ✅ transform, opacity, filter, clip-path
```

### will-change optimization

```tsx
<motion.div
  style={{ willChange: 'transform' }}
  animate={{ x: 100 }}
  onAnimationComplete={() => {
    ref.current.style.willChange = 'auto' // Remove after animation
  }}
/>
```

### Intersection Observer pattern

```typescript
<motion.div
  initial={{ opacity: 0 }}
  whileInView={{ opacity: 1 }}
  viewport={{ once: true, margin: "-100px" }}
/>
```

### Core Web Vitals tips

- Use `initial={false}` to skip mount animation (reduces CLS)
- Lazy load heavy components (Canvas, Three.js)
- Batch animations with `requestAnimationFrame`
- Prefer CSS animations for simple infinite loops

---

## Common landing page patterns

### Animated hero section

```tsx
<section className="relative min-h-screen">
  <AuroraBackground />
  <div className="relative z-10">
    <FloatingNavbar />
    <div className="container pt-32">
      <TextGenerateEffect words="Build amazing products" />
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        Subtitle text here
      </motion.p>
      <MovingBorderButton>Get Started</MovingBorderButton>
    </div>
  </div>
</section>

<section>
  <BentoGrid items={features} />
</section>

<section>
  <InfiniteMovingCards items={testimonials} direction="right" />
</section>
```

### Portfolio with 3D cards

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
  {projects.map((project, i) => (
    <motion.div
      key={project.id}
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: i * 0.1 }}
    >
      <CardContainer>
        <CardBody>
          <CardItem translateZ={50}>{project.title}</CardItem>
          <CardItem translateZ={100}>
            <img src={project.image} alt={project.title} />
          </CardItem>
        </CardBody>
      </CardContainer>
    </motion.div>
  ))}
</div>
```

---

## Special component dependencies

Some components require additional packages:

| Component | Extra Dependencies |
|-----------|-------------------|
| **GitHub Globe / World Map** | `three`, `three-globe`, `@react-three/fiber`, `@react-three/drei` |
| **Vortex** | `simplex-noise` |
| **Codeblock** | `react-syntax-highlighter` |

---

## Integration with shadcn/ui

Both libraries work well together:

| Use Case | Library | Reason |
|----------|---------|--------|
| Form components | shadcn/ui | Radix primitives, accessible |
| Data tables | shadcn/ui | TanStack Table integration |
| Dialog/Modal | shadcn/ui | WAI-ARIA compliant |
| Landing page hero | Aceternity UI | Stunning animations |
| Background effects | Aceternity UI | Particles, beams, aurora |
| Card hover effects | Aceternity UI | 3D transforms, spotlight |
| Navigation menus | shadcn/ui | Accessibility-first |
| Text animations | Aceternity UI | Typewriter, glowing |

### Shared configuration

```json
// components.json
{
  "registries": {
    "@aceternity": "https://ui.aceternity.com/registry/{name}.json"
  }
}
```

Both use the same `cn()` utility from `clsx` + `tailwind-merge`.

---

## Comparison: shadcn/ui vs Aceternity UI

| Aspect | shadcn/ui | Aceternity UI |
|--------|-----------|---------------|
| **Focus** | Functional UI components | Animated effects, visuals |
| **Animation** | Minimal (Radix defaults) | Heavy (Framer Motion) |
| **Best For** | Apps, dashboards, forms | Landing pages, portfolios |
| **Accessibility** | Excellent (Radix) | Good (needs reduced motion) |
| **Performance** | Excellent | Good (animation overhead) |
| **Learning Curve** | Moderate | Moderate-High |
| **Bundle Size** | Smaller | Larger (Framer Motion) |
| **Customization** | Full code ownership | Full code ownership |

---

## Production checklist

### Accessibility

- [ ] Implement `prefers-reduced-motion` for all animations
- [ ] Test keyboard navigation through all interactive elements
- [ ] Verify focus indicators visible during animations
- [ ] Check color contrast (≥4.5:1 for text)
- [ ] Add skip-animation controls for auto-playing content
- [ ] Touch targets ≥24x24px (WCAG 2.2)

### Performance

- [ ] Run Lighthouse audit (target: 90+ performance)
- [ ] INP <200ms verified
- [ ] Lazy load below-fold animations
- [ ] Use `viewport={{ once: true }}` for scroll animations
- [ ] Test on actual mobile devices
- [ ] Profile animation frame rates

### Browser compatibility

| Browser | Support Notes |
|---------|---------------|
| Chrome 76+ | Full support |
| Safari 9+ | backdrop-filter supported |
| Firefox 103+ | Full support |
| Edge 79+ | Full support |

### Mobile

- [ ] Test animations on low-end devices
- [ ] Reduce particle counts on mobile
- [ ] Test orientation changes
- [ ] Verify touch interactions

---

## Troubleshooting

### Hydration errors

```typescript
// Wrap client-only animations in Suspense
<Suspense fallback={<div className="animate-pulse" />}>
  <BackgroundBeams />
</Suspense>
```

### Safari animation issues

```css
/* Force GPU acceleration */
.animated-element {
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
}
```

### Mobile performance

```typescript
const isLowPerformance = 
  navigator.hardwareConcurrency <= 4 || 
  navigator.deviceMemory <= 4

const particleCount = isLowPerformance ? 20 : 100
```

---

## CLI commands reference

```bash
# View all Aceternity components
npx shadcn@latest view @aceternity

# Search components
npx shadcn@latest search @aceternity -q "card"

# List all components
npx shadcn@latest list @aceternity

# Install specific component
npx shadcn@latest add @aceternity/[component-name]

# Install via URL
npx shadcn@latest add https://ui.aceternity.com/registry/[component].json
```

---

## Summary

**shadcn/ui** is ideal for building accessible, functional UI components in applications, dashboards, and forms. It provides battle-tested accessibility through Radix UI primitives with minimal bundle size.

**Aceternity UI** excels at creating stunning visual effects for landing pages, portfolios, and marketing sites. The heavy use of Framer Motion enables impressive animations but requires attention to performance and accessibility.

**For $2-5K client websites**, combine both: use shadcn/ui for core functionality (forms, navigation, data display) and Aceternity UI for visual impact on landing pages and marketing sections. Both use the same Tailwind + copy-paste approach, making integration seamless.

