<!-- category: patterns -->
<!-- keywords: bento grid, css grid, subgrid, container queries, modular layout, feature tiles, apple design, saas, responsive -->

# Bento Grid Design Systems (2025-2026)

Bento grids became the dominant UI pattern of 2024-2025, evolving from Apple's promotional material into a widespread design language for showcasing complex products elegantly. CSS Grid made implementation trivial, and the pattern's inherent modularity suits modern component-based development perfectly.

## Origin and Evolution

The bento grid draws from Japanese bento boxes (弁当)—compartmentalized lunch containers that organize varied dishes while maintaining visual harmony. Microsoft's Metro design language (Windows Phone 7, 2010) introduced the "boxy" grid aesthetic, but **Apple popularized the modern interpretation** through product videos and marketing pages around 2020-2022.

**Why Bento Grids Dominate:**
- Reduces cognitive load by **~25%** compared to text-heavy layouts
- CSS Grid and Flexbox made implementation trivial
- Mobile-responsive by nature
- Perfect for showcasing complex information elegantly
- Aligns with minimalist design philosophy

## Production Site Analysis (Q4 2025)

**43+ documented SaaS implementations** currently using bento grids:

| Company | URL | Implementation Notes |
|---------|-----|---------------------|
| **Vercel** | vercel.com | Dark theme, developer-focused feature bento |
| **Linear** | linear.app | Sleek dark bento blending text/imagery |
| **Diagram** | diagram.com | Multiple bento sections, interactive |
| **Supabase** | supabase.com | Modular layout for backend tools |
| **Framer** | framer.com | Homepage features in visual grid |
| **WorkOS** | workos.com | Clean bento grid section |
| **Mintlify** | mintlify.com | Documentation-focused bento |
| **Cal.com** | cal.com | Feature section bento |
| **GitBook** | gitbook.com | Documentation features |
| **Mercury** | mercury.com | Banking features in bento |
| **Attio** | attio.com | CRM features section |

**Apple Benchmarks:**
- iPhone product pages (14 Pro through 16 series)
- Mac promotional videos
- Apple Vision Pro marketing
- **Pattern:** 6-9 boxes per slide, varied sizes signaling importance

## Tile Type Taxonomy

**Hero Tiles (Large Focal Point)**
- Sizes: 2×2, span 6 columns, 1×2
- Usage: Primary product image, main value proposition
- Content: Large imagery, minimal text, dramatic visuals

**Feature Tiles (Medium Emphasis)**
- Sizes: 1×1, span 3-4 columns
- Usage: Individual product features, benefits
- Content: Icon + headline + brief description

**Micro Tiles (Small Accents)**
- Sizes: Small squares, 1 row span
- Usage: Stats, icons, secondary information
- Content: Single metric or icon

**Spanning Tiles (Cross Multiple Tracks)**
- Sizes: 2×1 (horizontal), 3×2 (wide feature)
- Usage: Featured content, important CTAs
- CSS: `grid-column: span 2` or `grid-row: span 2`

**Interactive Tiles**
- Hover state animations (scale, elevation, glow)
- Click-through to expanded content
- Video previews on hover

**Media Tiles**
- Product photography
- Video embeds/previews
- Illustrations and animated demonstrations

**Text Tiles**
- Testimonials, feature descriptions
- Blog excerpts, quotes

**Data Tiles**
- Statistics and metrics
- Social proof numbers
- Performance indicators, award badges

## CSS Grid Implementation (December 2025)

**Core Bento Grid Structure:**
```css
.bento {
  --bento-cols: 5;
  --bento-rows: 3;
  --bento-gap: 1rem;
  --bento-radius: 1rem;
  
  display: grid;
  grid-template-columns: repeat(var(--bento-cols), 1fr);
  grid-template-rows: repeat(var(--bento-rows), 1fr);
  gap: var(--bento-gap);
  width: 100%;
  aspect-ratio: var(--bento-cols) / var(--bento-rows);
}

.bento > * {
  overflow: hidden;
  border-radius: var(--bento-radius);
  background: var(--card-bg);
}
```

**Grid Template Areas for Semantic Layouts:**
```css
.bento-semantic {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-areas:
    "featured featured featured featured"
    "card1 card1 card2 card3"
    "card1 card1 card4 card5";
  gap: 1rem;
}

.featured { grid-area: featured; }
.card-1 { grid-area: card1; }
.card-2 { grid-area: card2; }
/* ... */
```

**Span Positioning Patterns:**
```css
.tile-wide { grid-column: span 2; }
.tile-tall { grid-row: span 2; }
.tile-large { grid-column: span 2; grid-row: span 2; }
.tile-featured { grid-column: 2 / 7; grid-row: 2 / 4; }
```

## Subgrid Support (December 2025)

**Browser Support: ~93% global**
| Browser | Version |
|---------|---------|
| Chrome/Edge | 117+ ✅ |
| Safari | 16.0+ ✅ |
| Firefox | 71+ ✅ |

```css
.parent-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 1rem;
}

.nested-bento {
  grid-column: span 6;
  display: grid;
  grid-template-columns: subgrid;
}

/* Progressive enhancement */
@supports (grid-template-columns: subgrid) {
  .nested-bento {
    grid-template-columns: subgrid;
  }
}
```

## Container Queries for Nested Grids

**Browser Support: ~93.9% for size queries**

```css
.bento-card {
  container-type: inline-size;
  container-name: bento-card;
}

@container bento-card (min-width: 300px) {
  .card-content {
    flex-direction: row;
  }
}

@container bento-card (min-width: 500px) {
  .card-content {
    grid-template-columns: 1fr 1fr;
  }
}
```

**Tailwind CSS with Container Queries:**
```html
<div class="@container">
  <div class="grid grid-cols-1 @md:grid-cols-2 @lg:grid-cols-3 gap-4">
    <div class="@md:col-span-2">Featured Item</div>
  </div>
</div>
```

## Responsive Breakpoint Strategies

**Mobile-First Pattern:**
```css
/* Mobile: Single column */
.bento-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

/* Tablet: 2-column */
@media (min-width: 768px) {
  .bento-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .featured { grid-column: span 2; }
}

/* Desktop: Full bento */
@media (min-width: 1024px) {
  .bento-grid {
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: repeat(3, auto);
  }
}

/* Aspect ratio swap for portrait viewports */
@media screen and (aspect-ratio < 1) {
  .bento {
    --bento-cols: 3;
    --bento-rows: 5;
  }
}
```

## Animation Patterns

**Scroll-Driven Animations (CSS):**
```css
@supports (animation-timeline: scroll()) {
  .bento-tile {
    animation: reveal-tile linear both;
    animation-timeline: view();
    animation-range: entry 0% cover 40%;
  }
  
  @keyframes reveal-tile {
    from {
      opacity: 0;
      transform: translateY(50px) scale(0.95);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
}
```

**Browser Support:** Chrome 115+ ✅, Safari 26 beta 🔄, Firefox behind flag ⚠️

**Framer Motion Staggered Reveal:**
```jsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.5, ease: "easeOut" },
  },
};

<motion.div variants={containerVariants} initial="hidden" animate="visible">
  {items.map((item) => (
    <motion.div key={item.id} variants={itemVariants}>
      {item.content}
    </motion.div>
  ))}
</motion.div>
```

**GSAP ScrollTrigger:**
```javascript
gsap.from('.bento-tile', {
  scrollTrigger: {
    trigger: '.bento-grid',
    start: 'top 80%',
    toggleActions: 'play none none reverse'
  },
  y: 60,
  opacity: 0,
  duration: 0.8,
  stagger: { amount: 0.6, from: 'start' },
  ease: 'power2.out'
});
```

**Hover Effects:**
```css
.bento-tile {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.bento-tile:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}
```

## Visual Design Specifications

**Spacing & Gap Values:**
| Gap Size | Usage |
|----------|-------|
| **1rem (16px)** | Standard compact grids |
| **1.5rem (24px)** | Spacious grids |
| **2rem (32px)** | Premium/luxury layouts |

**Border Radius:**
- Standard tiles: **1rem (16px)**
- Large outer container: **2.5rem (40px)**

**Common Aspect Ratios:**
| Ratio | Usage |
|-------|-------|
| **1:1** | Feature squares, icons |
| **16:9** | Video tiles, hero images |
| **4:3** | Content cards |
| **3:2** | Landscape imagery |

**Color Strategies:**

*Dark Theme (Dominant):*
```css
:root {
  --card-bg: #1a1a1a;
  --card-border: #2a2a2a;
  --background: #060606;
}
```

*Light Theme:*
```css
:root {
  --card-bg: #ffffff;
  --card-shadow: 0 20px 30px -10px rgba(16, 16, 39, 0.07);
}
```

## React/Next.js Bento Component

```jsx
import { cn } from "@/lib/utils";

export function BentoGrid({ className, children }) {
  return (
    <div className={cn(
      "grid md:auto-rows-[18rem] grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto",
      className
    )}>
      {children}
    </div>
  );
}

export function BentoCard({ className, title, description, header, icon }) {
  return (
    <div className={cn(
      "row-span-1 rounded-xl group/bento",
      "hover:shadow-xl transition duration-200",
      "p-4 dark:bg-black dark:border-white/[0.2] bg-white border",
      "flex flex-col space-y-4",
      className
    )}>
      {header}
      <div className="group-hover/bento:translate-x-2 transition duration-200">
        {icon}
        <div className="font-bold text-neutral-600 dark:text-neutral-200 mb-2 mt-2">
          {title}
        </div>
        <div className="font-normal text-neutral-600 text-sm dark:text-neutral-300">
          {description}
        </div>
      </div>
    </div>
  );
}

// Usage with spanning
<BentoGrid>
  <BentoCard className="md:col-span-2 lg:row-span-2" title="Featured" />
  <BentoCard title="Feature Two" />
  <BentoCard title="Feature Three" />
  <BentoCard className="md:col-span-2" title="Wide Feature" />
</BentoGrid>
```

## Accessibility Requirements

**Semantic HTML Structure:**
```html
<section class="bento-grid" aria-label="Product features">
  <article class="bento-tile">
    <h3>Feature Name</h3>
    <p>Feature description</p>
  </article>
</section>
```

**Keyboard Navigation:**
- Tab order must follow logical visual flow
- Interactive tiles must be focusable
- Use `tabindex="0"` only where semantically appropriate

**Focus Management:**
```css
.bento-tile:focus-visible {
  outline: 3px solid #0066CC;
  outline-offset: 2px;
  z-index: 10;
}
```

**Touch Targets:**
```css
@media (max-width: 768px) {
  .bento-tile a,
  .bento-tile button {
    min-width: 44px;
    min-height: 44px;
  }
}
```

## Performance Optimization

**Lazy Loading with Intersection Observer:**
```javascript
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      observer.unobserve(img);
    }
  });
}, { rootMargin: '100px', threshold: 0.1 });

document.querySelectorAll('img.lazy').forEach(img => observer.observe(img));
```

**CLS Prevention:**
```css
.bento-tile-image {
  aspect-ratio: 16 / 9;
  object-fit: cover;
  width: 100%;
}
```

**Skeleton Loading:**
```jsx
const BentoSkeleton = () => (
  <div className="animate-pulse grid grid-cols-4 gap-4">
    <div className="col-span-2 row-span-2 bg-gray-200 rounded-xl h-64" />
    <div className="bg-gray-200 rounded-xl h-32" />
    <div className="bg-gray-200 rounded-xl h-32" />
    <div className="col-span-2 bg-gray-200 rounded-xl h-32" />
  </div>
);
```

## Component Libraries

| Library | Framework | Install |
|---------|-----------|---------|
| **Aceternity UI** | React/Next.js | `npx shadcn@latest add @aceternity/bento-grid` |
| **Magic UI** | React | `pnpm dlx shadcn@latest add @magicui/bento-grid` |
| **shadcn/ui** | React | CLI installation, multiple variants |

## Common Bento Grid Mistakes

❌ **Overcrowding:** More than 9 tiles per grid section

❌ **Inconsistent spacing:** Varying gap sizes within the same grid

❌ **Ignoring visual hierarchy:** All tiles same importance (no focal point)

❌ **Poor mobile responsiveness:** Grid breaks down or overflows

❌ **Accessibility failures:** Keyboard traps, insufficient contrast

❌ **Missing animations:** Static bento grids feel dated in 2025

