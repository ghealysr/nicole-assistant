---
title: E-commerce & Retail Design
category: industries
tags: [ecommerce, retail, shopping, product, conversion]
priority: high
last_updated: 2026-01-02
---

# E-commerce & Retail Design

## Industry Context

E-commerce design must reduce friction between **discovery and purchase**. Every element should serve the conversion funnel while building trust and desire.

### Key User Psychology

1. **Instant gratification**: Users want products NOW
2. **Decision paralysis**: Too many options cause abandonment
3. **Trust anxiety**: Fear of fraud, poor quality, or hassle
4. **Social validation**: Others' opinions heavily influence purchase
5. **Urgency response**: Limited time/stock creates action

## Visual Design Principles

### Color Strategy

**By Product Category:**

| Category | Primary | Accent | Rationale |
|----------|---------|--------|-----------|
| Fashion/Luxury | Black, cream | Gold, burgundy | Sophistication |
| Electronics | Dark navy, silver | Electric blue | Technical precision |
| Wellness/Beauty | Soft pink, sage | Gold, coral | Calm, natural |
| Home/Furniture | Warm neutrals | Terracotta, olive | Comfort, livability |
| Sports/Outdoor | Bold primary colors | High-contrast accents | Energy, action |
| Kids/Toys | Bright primaries | Playful multi-color | Joy, excitement |

**Universal Requirements:**
- **Add to Cart**: High contrast, instantly recognizable (often orange, green, or blue)
- **Sale/Discount**: Red or contrasting accent
- **Stock alerts**: Warm colors (orange/red) for urgency

### Typography Patterns

**Luxury/Fashion:**
- Display: Didot, Bodoni Moda, Cormorant Garamond
- Body: Light-weight sans-serif (Montserrat Light, Lato)

**Modern/Minimal:**
- Display: Clash Grotesk, Cabinet Grotesk
- Body: Satoshi, General Sans

**Accessible/Mass Market:**
- Display: Poppins, Nunito Sans
- Body: Open Sans, Source Sans Pro

**Price Typography:**
```css
.price-current {
  font-weight: 700;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.price-original {
  font-weight: 400;
  font-size: 1rem;
  text-decoration: line-through;
  color: var(--text-muted);
}

.price-discount {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--error);
  background: var(--error-light);
  padding: 2px 8px;
  border-radius: 4px;
}
```

### Layout Patterns

**Product Grid:**
- 4 columns desktop, 2 columns mobile
- Consistent aspect ratios (1:1, 3:4, or 4:5)
- Hover state shows secondary image
- Quick-add button on hover

**Product Detail Page (PDP):**
```
┌─────────────────────────────────────────────┐
│  Breadcrumbs                                │
├──────────────────────┬──────────────────────┤
│                      │  Product Title       │
│                      │  Reviews (★★★★☆)     │
│   Product Gallery    │  Price               │
│   (Sticky on scroll) │  Variants (size/color)│
│                      │  Add to Cart [CTA]   │
│                      │  Trust badges        │
│                      │  Shipping info       │
├──────────────────────┴──────────────────────┤
│  Product Details Tabs                       │
│  (Description | Specs | Reviews | FAQ)      │
├─────────────────────────────────────────────┤
│  "You May Also Like" / Cross-sells          │
├─────────────────────────────────────────────┤
│  Recently Viewed                            │
└─────────────────────────────────────────────┘
```

## Conversion Optimization

### Above-the-Fold (Homepage)

1. **Hero**: Seasonal campaign or bestseller with strong CTA
2. **Category navigation**: Visual tiles or horizontal scroll
3. **Trending/Featured products**: Immediate shopping opportunity

### Trust Signal Placement

```
Header: Free shipping threshold, return policy
Below hero: Payment icons, security badges
Product cards: Review stars
PDP: Trust badges near Add to Cart
Cart: Security messaging, guarantee
Checkout: SSL indicator, payment logos
```

### Urgency & Scarcity (Ethical Use)

**Acceptable:**
- "Only 3 left in stock" (if true)
- "Sale ends in 24 hours" (if true)
- "Selling fast - 50 sold today"

**Dark patterns to AVOID:**
- Fake countdown timers that reset
- "2 people viewing this" (fake)
- Artificially low stock numbers
- Hidden fees revealed at checkout

## Component Specifications

### Product Card

```typescript
interface ProductCard {
  image: {
    primary: string;
    hover?: string;
    aspect: '1:1' | '3:4' | '4:5';
    lazy: true;
  };
  title: string;
  price: {
    current: number;
    original?: number;
    currency: string;
  };
  rating?: {
    score: number;
    count: number;
  };
  badges?: ('New' | 'Sale' | 'Bestseller' | 'Low Stock')[];
  quickAdd?: boolean;
  wishlist?: boolean;
}
```

### Add to Cart Button

```css
.add-to-cart {
  /* Size: Large enough for mobile taps */
  min-height: 48px;
  padding: 12px 32px;
  
  /* Color: High contrast, brand-aligned */
  background: var(--cta-primary);
  color: white;
  
  /* Shape: Rounded but not pill (for text legibility) */
  border-radius: 8px;
  
  /* Typography */
  font-weight: 600;
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  
  /* Feedback */
  transition: transform 0.15s, background 0.2s;
}

.add-to-cart:hover {
  transform: scale(1.02);
  background: var(--cta-primary-hover);
}

.add-to-cart:active {
  transform: scale(0.98);
}

/* Success state after adding */
.add-to-cart.added {
  background: var(--success);
}
```

### Cart Drawer

- Slide-in from right (standard pattern)
- Overlay with backdrop blur
- Product thumbnails with quantity controls
- Clear subtotal and checkout CTA
- Continue shopping link

## Mobile Optimization

### Critical Mobile Patterns

1. **Sticky Add to Cart**: Fixed bottom bar on PDP
2. **Swipe galleries**: Touch-friendly image browsing
3. **Bottom navigation**: Categories, Search, Cart, Account
4. **Large tap targets**: Minimum 44x44px
5. **Thumb-zone CTAs**: Primary actions in bottom half

### Mobile-First Considerations

```css
/* Product grid responsive */
.product-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }
}

@media (min-width: 1024px) {
  .product-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 32px;
  }
}
```

## Anti-Patterns to Avoid

1. **Slow product images**: Unoptimized, no lazy loading
2. **Complex checkout**: More than 3 steps or forced account creation
3. **Hidden costs**: Shipping surprises at checkout
4. **Poor search**: No autocomplete, no filters
5. **No reviews**: Missing social proof
6. **Tiny add-to-cart**: Hard to tap on mobile
7. **Auto-playing videos**: Distracting, data-heavy
8. **Infinite scroll without pagination**: Bad for SEO, no "end"

## Performance Requirements

- **LCP**: < 1.5s (product images are critical)
- **CLS**: < 0.05 (image dimensions must be set)
- **Image format**: WebP with JPEG fallback
- **Lazy loading**: All below-fold images
- **CDN**: Images served from edge locations

## SEO Considerations

- Unique product descriptions (not manufacturer copy)
- Schema.org Product markup
- Clean URL structure: `/category/product-name`
- Image alt text with product names
- Customer reviews indexed

