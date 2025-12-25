<!-- category: qa -->
<!-- keywords: performance, core-web-vitals, lcp, inp, cls, lighthouse, bundle-size -->

# Performance & Core Web Vitals Standards

## Core Web Vitals Thresholds (2024)

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| **LCP** (Largest Contentful Paint) | ≤2.5s | 2.5-4s | >4s |
| **INP** (Interaction to Next Paint) | ≤200ms | 200-500ms | >500ms |
| **CLS** (Cumulative Layout Shift) | ≤0.1 | 0.1-0.25 | >0.25 |

---

## 1. Largest Contentful Paint (LCP)

### What Counts as LCP

- `<img>` elements
- `<image>` inside SVG
- `<video>` poster images
- Elements with `background-image`
- Block-level elements with text nodes

### LCP Optimization Checklist

```tsx
// ✅ Priority hints for hero images
<Image
  src="/hero.jpg"
  alt="Hero"
  priority // Next.js: preloads
  fetchPriority="high" // Browser hint
/>

// ✅ Preload critical resources
<Head>
  <link 
    rel="preload" 
    href="/fonts/inter.woff2" 
    as="font" 
    type="font/woff2"
    crossOrigin=""
  />
</Head>

// ✅ Avoid lazy loading above-fold images
<Image
  src="/hero.jpg"
  loading="eager" // NOT "lazy" for hero
  priority
/>
```

### LCP Blockers to Fix

| Issue | Impact | Fix |
|-------|--------|-----|
| Unoptimized images | +500-2000ms | Use WebP/AVIF, responsive sizes |
| Render-blocking CSS | +200-500ms | Inline critical CSS |
| Slow server response | +100-500ms | CDN, edge caching |
| No preconnect | +100-300ms | `<link rel="preconnect">` |
| Client-side rendering | +500-1500ms | SSR/SSG for above-fold |

---

## 2. Interaction to Next Paint (INP)

### What Triggers INP

- Click/tap handlers
- Key presses
- Focus events

### INP Optimization

```tsx
// 🔴 BAD - heavy computation in handler
const handleClick = () => {
  const result = heavyCalculation(data); // ❌ Blocks main thread
  setState(result);
};

// ✅ GOOD - defer heavy work
const handleClick = () => {
  // Immediate visual feedback
  setIsProcessing(true);
  
  // Defer heavy work
  requestIdleCallback(() => {
    const result = heavyCalculation(data);
    setState(result);
    setIsProcessing(false);
  });
};

// ✅ GOOD - web worker for CPU-intensive work
const worker = new Worker('/workers/calculate.js');
const handleClick = () => {
  setIsProcessing(true);
  worker.postMessage({ data });
};
worker.onmessage = (e) => {
  setState(e.data.result);
  setIsProcessing(false);
};
```

### React-Specific INP Fixes

```tsx
// 🔴 BAD - large state update
const handleInput = (value: string) => {
  setQuery(value);
  setFilteredItems(items.filter(item => item.name.includes(value))); // ❌ Sync filter
};

// ✅ GOOD - debounced + deferred
const handleInput = (value: string) => {
  setQuery(value); // Immediate
  startTransition(() => {
    setFilteredItems(items.filter(item => item.name.includes(value))); // Deferred
  });
};

// ✅ GOOD - virtualized lists for large data
import { useVirtualizer } from '@tanstack/react-virtual';
```

---

## 3. Cumulative Layout Shift (CLS)

### What Causes CLS

- Images without dimensions
- Ads/embeds without reserved space
- Dynamically injected content
- Web fonts causing FOIT/FOUT
- Animations that trigger layout

### CLS Prevention

```tsx
// ✅ Always specify image dimensions
<Image
  src="/photo.jpg"
  width={800}
  height={600}
  alt="Photo"
/>

// ✅ Reserve space for dynamic content
<div className="min-h-[300px]"> {/* Reserve banner space */}
  {banner && <Banner />}
</div>

// ✅ Font display swap (prevents FOIT)
// next.config.js
const font = Inter({
  subsets: ['latin'],
  display: 'swap', // Shows fallback immediately
});
```

### Animation CLS Safety

```css
/* 🔴 BAD - triggers layout shift */
.element {
  animation: slide 0.3s;
}
@keyframes slide {
  from { margin-left: -100px; } /* ❌ margin causes layout */
  to { margin-left: 0; }
}

/* ✅ GOOD - transform doesn't trigger layout */
.element {
  animation: slide 0.3s;
}
@keyframes slide {
  from { transform: translateX(-100px); } /* ✅ transform is free */
  to { transform: translateX(0); }
}
```

---

## 4. Bundle Size Optimization

### Target Sizes

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Initial JS | <100KB | 100-200KB | >200KB |
| Total JS (lazy) | <300KB | 300-500KB | >500KB |
| First-party JS | <50KB | 50-100KB | >100KB |
| CSS | <50KB | 50-100KB | >100KB |

### Bundle Analysis

```bash
# Next.js bundle analyzer
npm install @next/bundle-analyzer
ANALYZE=true npm run build

# Check specific imports
npx import-cost . # VS Code extension data
```

### Code Splitting Patterns

```tsx
// ✅ Route-based splitting (automatic in Next.js App Router)
// app/dashboard/page.tsx → separate chunk

// ✅ Component-level splitting
const HeavyChart = dynamic(() => import('./HeavyChart'), {
  loading: () => <Skeleton className="h-[400px]" />,
  ssr: false // Client-only component
});

// ✅ Conditional loading
const AdminPanel = dynamic(
  () => import('./AdminPanel'),
  { ssr: false }
);

function Dashboard({ isAdmin }) {
  return (
    <div>
      <MainContent />
      {isAdmin && <AdminPanel />} {/* Only loads when admin */}
    </div>
  );
}
```

### Tree Shaking

```tsx
// 🔴 BAD - imports entire library
import _ from 'lodash'; // ❌ 70KB+
_.debounce(fn, 300);

// ✅ GOOD - import specific function
import debounce from 'lodash/debounce'; // ✅ 2KB

// 🔴 BAD - barrel file imports
import { Button, Card, Dialog } from '@/components'; // ❌ May import all

// ✅ GOOD - direct imports
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
```

---

## 5. Image Optimization

### Modern Image Formats

| Format | Use Case | Savings |
|--------|----------|---------|
| WebP | Default for all images | 25-35% smaller |
| AVIF | Modern browsers | 50%+ smaller |
| SVG | Icons, logos, illustrations | Scalable, tiny |

### Next.js Image Optimization

```tsx
// ✅ Proper Next.js image usage
import Image from 'next/image';

<Image
  src="/hero.jpg"
  alt="Hero"
  width={1200}
  height={800}
  priority // Above-fold
  placeholder="blur"
  blurDataURL="data:image/..." // Tiny placeholder
  sizes="(max-width: 768px) 100vw, 50vw" // Responsive
/>

// ✅ For background images, use CSS with image-set
.hero {
  background-image: image-set(
    url('/hero.avif') type('image/avif'),
    url('/hero.webp') type('image/webp'),
    url('/hero.jpg') type('image/jpeg')
  );
}
```

---

## 6. Font Optimization

### Best Practices

```tsx
// next.config.ts - optimal font loading
import { Inter, JetBrains_Mono } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
  preload: true
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
  preload: false // Secondary font, don't preload
});
```

### Font Subsetting

```css
/* Only load characters you need */
@font-face {
  font-family: 'Brand';
  src: url('/fonts/brand.woff2') format('woff2');
  unicode-range: U+0000-00FF; /* Basic Latin only */
}
```

---

## 7. Caching Strategy

### Cache Headers

```ts
// next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/:all*(svg|jpg|png|webp|avif)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable' // 1 year
          }
        ]
      },
      {
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          }
        ]
      }
    ];
  }
};
```

### React Query Caching

```tsx
const { data } = useQuery({
  queryKey: ['projects'],
  queryFn: fetchProjects,
  staleTime: 5 * 60 * 1000, // 5 minutes
  cacheTime: 30 * 60 * 1000, // 30 minutes
});
```

---

## 8. Rendering Strategy

### When to Use Each

| Strategy | Use When | LCP Impact |
|----------|----------|------------|
| **SSG** | Content doesn't change often | Best |
| **ISR** | Content changes periodically | Great |
| **SSR** | Content must be fresh | Good |
| **CSR** | User-specific, behind auth | Worst |

### Next.js 15 Examples

```tsx
// SSG - generated at build time
export default async function Page() {
  const posts = await getPosts();
  return <PostList posts={posts} />;
}

// ISR - regenerate every 60 seconds
export const revalidate = 60;

// Dynamic - SSR on every request
export const dynamic = 'force-dynamic';

// Client - SPA behavior
'use client';
```

---

## 9. Lighthouse Audit Checklist

### Performance (Target: 90+)

- [ ] LCP ≤ 2.5s
- [ ] INP ≤ 200ms
- [ ] CLS ≤ 0.1
- [ ] First Contentful Paint ≤ 1.8s
- [ ] Time to Interactive ≤ 3.8s
- [ ] Total Blocking Time ≤ 200ms
- [ ] Speed Index ≤ 3.4s

### Diagnostics to Check

- [ ] Images properly sized
- [ ] Preconnect to required origins
- [ ] Minimize main-thread work
- [ ] Avoid enormous network payloads
- [ ] Serve static assets with efficient cache policy
- [ ] Avoid DOM size > 800 nodes
- [ ] Avoid large layout shifts

---

## 10. Performance Testing Commands

```bash
# Lighthouse CLI
npx lighthouse https://your-site.com --view

# Bundle analyzer
ANALYZE=true npm run build

# Check Core Web Vitals in production
# Chrome DevTools → Performance → Web Vitals

# Check unused CSS/JS
# Chrome DevTools → Coverage (Cmd+Shift+P → "Coverage")

# Network throttling test
# Chrome DevTools → Network → Slow 3G
```

### Performance Budgets

```json
// next.config.js or separate config
{
  "budgets": [
    {
      "resourceTypes": ["script"],
      "budget": 100000 // 100KB
    },
    {
      "resourceTypes": ["image"],
      "budget": 500000 // 500KB
    },
    {
      "resourceTypes": ["total"],
      "budget": 1000000 // 1MB
    }
  ]
}
```

---

## QA Pass/Fail Criteria

### MUST PASS

- ✅ LCP ≤ 2.5s on 4G connection
- ✅ CLS ≤ 0.1 (no unexpected layout shifts)
- ✅ All images have explicit dimensions
- ✅ Hero images have `priority` attribute
- ✅ No render-blocking resources
- ✅ Bundle size < 200KB initial JS

### SHOULD PASS

- ⚠️ INP ≤ 200ms (measure in production)
- ⚠️ Lighthouse Performance ≥ 90
- ⚠️ Fonts use `display: swap`
- ⚠️ Modern image formats (WebP/AVIF)
- ⚠️ Code splitting for heavy components

