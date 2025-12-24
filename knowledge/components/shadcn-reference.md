<!-- category: components -->
<!-- keywords: shadcn, components, aceternity, magic ui, tailwind v4, react, radix, forms, navigation -->

# shadcn/ui Component Reference (December 2025)

shadcn/ui provides accessible, customizable components built on Radix UI primitives. Components are copied into your project, not installed as dependencies, giving full control over styling and behavior.

## Quick Start

```bash
# Initialize
npx shadcn@latest init

# Add any component
npx shadcn@latest add [component]
```

## Complete Component Catalog

### Form Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Button | `npx shadcn@latest add button` | CTAs, actions, submit |
| Checkbox | `npx shadcn@latest add checkbox` | Multi-select options |
| Form | `npx shadcn@latest add form` | Form wrapper (React Hook Form) |
| Input | `npx shadcn@latest add input` | Text inputs |
| Input OTP | `npx shadcn@latest add input-otp` | One-time passwords |
| Label | `npx shadcn@latest add label` | Form labels |
| Radio Group | `npx shadcn@latest add radio-group` | Single selection |
| Select | `npx shadcn@latest add select` | Custom dropdowns |
| Slider | `npx shadcn@latest add slider` | Range selection |
| Switch | `npx shadcn@latest add switch` | Toggle on/off |
| Textarea | `npx shadcn@latest add textarea` | Multi-line input |

### Navigation Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Breadcrumb | `npx shadcn@latest add breadcrumb` | Page hierarchy |
| Dropdown Menu | `npx shadcn@latest add dropdown-menu` | Action menus |
| Navigation Menu | `npx shadcn@latest add navigation-menu` | Site navigation |
| Pagination | `npx shadcn@latest add pagination` | Page controls |
| Sidebar | `npx shadcn@latest add sidebar` | App sidebar (25 variants) |
| Tabs | `npx shadcn@latest add tabs` | Content organization |

### Feedback Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Alert | `npx shadcn@latest add alert` | Static notifications |
| Alert Dialog | `npx shadcn@latest add alert-dialog` | Confirmations |
| Dialog | `npx shadcn@latest add dialog` | Modal windows |
| Drawer | `npx shadcn@latest add drawer` | Slide-in panels |
| Progress | `npx shadcn@latest add progress` | Loading indicators |
| Skeleton | `npx shadcn@latest add skeleton` | Loading placeholders |
| Sonner | `npx shadcn@latest add sonner` | Toast notifications |
| Tooltip | `npx shadcn@latest add tooltip` | Hover information |

### Data Display Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Avatar | `npx shadcn@latest add avatar` | User images |
| Badge | `npx shadcn@latest add badge` | Status labels |
| Card | `npx shadcn@latest add card` | Content containers |
| Chart | `npx shadcn@latest add chart` | Visualizations (Recharts) |
| Data Table | `npx shadcn@latest add data-table` | Complex tables |
| Hover Card | `npx shadcn@latest add hover-card` | Preview cards |
| Table | `npx shadcn@latest add table` | Basic tables |

### Layout Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Accordion | `npx shadcn@latest add accordion` | Collapsible sections |
| Aspect Ratio | `npx shadcn@latest add aspect-ratio` | Fixed ratios |
| Calendar | `npx shadcn@latest add calendar` | Date selection |
| Carousel | `npx shadcn@latest add carousel` | Image sliders |
| Collapsible | `npx shadcn@latest add collapsible` | Expandable sections |
| Resizable | `npx shadcn@latest add resizable` | Resizable panels |
| Scroll Area | `npx shadcn@latest add scroll-area` | Custom scrollbars |
| Sheet | `npx shadcn@latest add sheet` | Side panels |

### Utility Components
| Component | Command | Use Case |
|-----------|---------|----------|
| Command | `npx shadcn@latest add command` | Command palette (⌘K) |
| Combobox | `npx shadcn@latest add combobox` | Searchable select |
| Context Menu | `npx shadcn@latest add context-menu` | Right-click menus |
| Date Picker | `npx shadcn@latest add date-picker` | Date selection |
| Popover | `npx shadcn@latest add popover` | Floating content |

## Server Component Compatibility

**RSC Compatible (no "use client"):**
Card, Avatar, Badge, Table, Separator, Skeleton, Alert, Progress

**Client Components Required:**
Dialog, Dropdown Menu, Popover, Tabs, Accordion, Form inputs, Toast/Sonner

## Aceternity UI Components

Animated components for marketing sites. Install with:
```bash
npm install framer-motion clsx tailwind-merge
```

**Top Components for SaaS:**

| Category | Components |
|----------|------------|
| Backgrounds | Aurora, Background Beams, Gradient Animation, Sparkles, Meteors, Spotlight, Lamp Effect |
| Cards | 3D Card, Wobble Card, Expandable Card, Focus Cards, Glare Card |
| Hero | Hero Parallax, Macbook Scroll, Container Scroll, Sticky Scroll Reveal, Bento Grid |
| Text | Text Generate Effect, Typewriter, Flip Words, Hero Highlight |
| Navigation | Floating Navbar, Floating Dock, Navbar Menu |

## Magic UI Components

150+ free animated components. Install pattern:
```bash
pnpm dlx shadcn@latest add @magicui/[component]
```

**Top Components:**

| Category | Components | Command Example |
|----------|------------|-----------------|
| Display | Marquee, Globe, Dock, Terminal, Icon Cloud | `@magicui/marquee` |
| Text | Typing Animation, Number Ticker, Word Rotate, Hyper Text | `@magicui/number-ticker` |
| Buttons | Shimmer Button, Rainbow Button, Ripple Button | `@magicui/shimmer-button` |
| Effects | Border Beam, Shine Border, Magic Card, Confetti | `@magicui/border-beam` |
| Backgrounds | Dot Pattern, Grid Pattern, Retro Grid, Particles | `@magicui/retro-grid` |

## Tailwind v4 Configuration

```css
/* globals.css */
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --muted: oklch(0.97 0 0);
  --accent: oklch(0.97 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --radius: 0.625rem;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
}
```

## Variant Composition with CVA

```tsx
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);
```

## Form Integration (React Hook Form)

```tsx
"use client"

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const formSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export function LoginForm() {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input placeholder="email@example.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Login</Button>
      </form>
    </Form>
  );
}
```

## When to Use What

| Use Case | Recommendation |
|----------|----------------|
| Standard UI (forms, tables, modals) | **shadcn/ui** |
| Marketing "wow factor" | **Aceternity UI / Magic UI** |
| Highly specialized business logic | **Custom build** |
| Rapid prototyping | **shadcn/ui** |
| Performance-critical rendering | **Custom build** |

