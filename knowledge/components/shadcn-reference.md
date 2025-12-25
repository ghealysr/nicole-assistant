<!-- category: components -->
<!-- keywords: shadcn, components, radix ui, tailwind, react hook form, zod, forms, navigation, theming, cva, accessibility -->

# shadcn/ui Component Library Reference

**The copy-paste component system built on Radix UI and Tailwind CSS that gives you full code ownership without the constraints of traditional npm packages.**

shadcn/ui has become the dominant React component library in 2025 with **103,000+ GitHub stars**, powering production applications at Vercel, OpenAI, Adobe, Supabase, and Sonos. Unlike traditional libraries, shadcn/ui components are copied directly into your codebase—you own them completely, modify them freely, and update on your terms.

---

## Current state and compatibility

**Repository:** github.com/shadcn-ui/ui (103k+ stars)  
**Documentation:** ui.shadcn.com  
**Maintainer:** @shadcn (Vercel)  
**React 19:** Fully compatible  
**Next.js 15/16:** Fully compatible  
**Tailwind CSS v4:** Full support with OKLCH colors

### Major 2025 updates

**December 2025** introduced `npx shadcn create` with 5 visual styles: Vega (classic), Nova (compact), Maia (soft/rounded), Lyra (boxy/sharp), and Mira (dense). Support for both Radix UI and Base UI component libraries was added.

**October 2025** brought 7 new components: Spinner, Kbd, Button Group, Input Group, Field, Item, and Empty.

**August 2025** delivered CLI 3.0 with namespaced registries (`@registry/name` format), private registries with authentication, MCP Server integration, and new `view`, `search`, `list` commands.

**June 2025** migrated to unified `radix-ui` package from `@radix-ui/react-*` individual imports. Calendar upgraded to React DayPicker with 30+ calendar blocks.

**February 2025** added Tailwind v4 + React 19 full support. HSL colors converted to OKLCH. Deprecated `default` style (new projects use `new-york`) and toast in favor of Sonner.

---

## Installation and setup

### Quick start for Next.js 15

```bash
# Create Next.js app
npx create-next-app@latest my-app --typescript --tailwind --eslint

# Initialize shadcn/ui
cd my-app
npx shadcn@latest init

# Add components
npx shadcn@latest add button card dialog form
```

### Required dependencies (auto-installed)

| Package | Purpose |
|---------|---------|
| `tailwindcss@^4` | Styling framework |
| `radix-ui` | Unified Radix primitives package |
| `class-variance-authority` | Component variants (CVA) |
| `clsx` | Conditional class names |
| `tailwind-merge` | Merge Tailwind classes without conflicts |
| `tw-animate-css` | Animation utilities |
| `lucide-react` | Icons (new-york style) |

### Configuration file (components.json)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "rsc": true,
  "tsx": true,
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui"
  },
  "registries": {
    "@aceternity": "https://ui.aceternity.com/registry/{name}.json"
  }
}
```

### Essential cn() utility function

```typescript
// lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

---

## Complete component catalog (56 components)

### Layout components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Aspect Ratio | @radix-ui/react-aspect-ratio | `npx shadcn@latest add aspect-ratio` |
| Card | None (custom) | `npx shadcn@latest add card` |
| Resizable | react-resizable-panels | `npx shadcn@latest add resizable` |
| Scroll Area | @radix-ui/react-scroll-area | `npx shadcn@latest add scroll-area` |
| Separator | @radix-ui/react-separator | `npx shadcn@latest add separator` |

### Form components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Button | None (custom) | `npx shadcn@latest add button` |
| Button Group | None (custom) | `npx shadcn@latest add button-group` |
| Checkbox | @radix-ui/react-checkbox | `npx shadcn@latest add checkbox` |
| Field | None (custom) | `npx shadcn@latest add field` |
| Form | react-hook-form + @hookform/resolvers | `npx shadcn@latest add form` |
| Input | None (custom) | `npx shadcn@latest add input` |
| Input Group | None (custom) | `npx shadcn@latest add input-group` |
| Input OTP | input-otp | `npx shadcn@latest add input-otp` |
| Label | @radix-ui/react-label | `npx shadcn@latest add label` |
| Native Select | None (custom) | `npx shadcn@latest add native-select` |
| Radio Group | @radix-ui/react-radio-group | `npx shadcn@latest add radio-group` |
| Select | @radix-ui/react-select | `npx shadcn@latest add select` |
| Slider | @radix-ui/react-slider | `npx shadcn@latest add slider` |
| Switch | @radix-ui/react-switch | `npx shadcn@latest add switch` |
| Textarea | None (custom) | `npx shadcn@latest add textarea` |
| Toggle | @radix-ui/react-toggle | `npx shadcn@latest add toggle` |
| Toggle Group | @radix-ui/react-toggle-group | `npx shadcn@latest add toggle-group` |

### Navigation components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Breadcrumb | None (custom) | `npx shadcn@latest add breadcrumb` |
| Menubar | @radix-ui/react-menubar | `npx shadcn@latest add menubar` |
| Navigation Menu | @radix-ui/react-navigation-menu | `npx shadcn@latest add navigation-menu` |
| Pagination | None (custom) | `npx shadcn@latest add pagination` |
| Sidebar | None (custom) | `npx shadcn@latest add sidebar` |
| Tabs | @radix-ui/react-tabs | `npx shadcn@latest add tabs` |

### Feedback components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Alert | None (custom) | `npx shadcn@latest add alert` |
| Progress | @radix-ui/react-progress | `npx shadcn@latest add progress` |
| Skeleton | None (custom) | `npx shadcn@latest add skeleton` |
| Sonner | sonner | `npx shadcn@latest add sonner` |
| Spinner | None (custom) | `npx shadcn@latest add spinner` |
| Toast | @radix-ui/react-toast | `npx shadcn@latest add toast` |

### Overlay components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Alert Dialog | @radix-ui/react-alert-dialog | `npx shadcn@latest add alert-dialog` |
| Context Menu | @radix-ui/react-context-menu | `npx shadcn@latest add context-menu` |
| Dialog | @radix-ui/react-dialog | `npx shadcn@latest add dialog` |
| Drawer | vaul | `npx shadcn@latest add drawer` |
| Dropdown Menu | @radix-ui/react-dropdown-menu | `npx shadcn@latest add dropdown-menu` |
| Hover Card | @radix-ui/react-hover-card | `npx shadcn@latest add hover-card` |
| Popover | @radix-ui/react-popover | `npx shadcn@latest add popover` |
| Sheet | @radix-ui/react-dialog | `npx shadcn@latest add sheet` |
| Tooltip | @radix-ui/react-tooltip | `npx shadcn@latest add tooltip` |

### Data display components

| Component | Radix Primitive | Installation |
|-----------|-----------------|--------------|
| Accordion | @radix-ui/react-accordion | `npx shadcn@latest add accordion` |
| Avatar | @radix-ui/react-avatar | `npx shadcn@latest add avatar` |
| Badge | None (custom) | `npx shadcn@latest add badge` |
| Calendar | react-day-picker | `npx shadcn@latest add calendar` |
| Carousel | embla-carousel-react | `npx shadcn@latest add carousel` |
| Chart | recharts | `npx shadcn@latest add chart` |
| Collapsible | @radix-ui/react-collapsible | `npx shadcn@latest add collapsible` |
| Combobox | cmdk | `npx shadcn@latest add combobox` |
| Command | cmdk | `npx shadcn@latest add command` |
| Data Table | @tanstack/react-table | `npx shadcn@latest add data-table` |
| Date Picker | react-day-picker | `npx shadcn@latest add date-picker` |
| Empty | None (custom) | `npx shadcn@latest add empty` |
| Kbd | None (custom) | `npx shadcn@latest add kbd` |
| Table | None (custom) | `npx shadcn@latest add table` |

---

## Form handling with react-hook-form and Zod

Form handling is the most common use case. shadcn/ui integrates react-hook-form with Zod validation for type-safe, accessible forms.

### Complete form example with validation

```typescript
"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"

const formSchema = z.object({
  username: z.string()
    .min(3, "Username must be at least 3 characters.")
    .max(20, "Username must be at most 20 characters.")
    .regex(/^[a-zA-Z0-9_]+$/, "Only letters, numbers, and underscores."),
  email: z.string().email("Invalid email format"),
})

type FormValues = z.infer<typeof formSchema>

export function ProfileForm() {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { username: "", email: "" },
    mode: "onBlur",
  })

  function onSubmit(values: FormValues) {
    console.log(values) // Fully validated and typed
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      <Controller
        name="username"
        control={form.control}
        render={({ field, fieldState }) => (
          <Field data-invalid={fieldState.invalid}>
            <FieldLabel htmlFor="username">Username</FieldLabel>
            <Input
              {...field}
              id="username"
              aria-invalid={fieldState.invalid}
            />
            {fieldState.invalid && (
              <FieldError>{fieldState.error?.message}</FieldError>
            )}
          </Field>
        )}
      />
      <Button type="submit">Save</Button>
    </form>
  )
}
```

### Server Actions integration (Next.js 15)

```typescript
// actions.ts
"use server"

import { formSchema, type FormState } from "./schema"

export async function submitFormAction(
  _prevState: FormState,
  formData: FormData
): Promise<FormState> {
  const values = {
    title: formData.get("title") as string,
    description: formData.get("description") as string,
  }

  const result = formSchema.safeParse(values)

  if (!result.success) {
    return {
      values,
      success: false,
      errors: result.error.flatten().fieldErrors,
    }
  }

  await saveToDatabase(result.data)
  return { values: { title: "", description: "" }, errors: null, success: true }
}
```

```typescript
// form.tsx
"use client"

import * as React from "react"
import Form from "next/form"
import { submitFormAction } from "./actions"
import { Spinner } from "@/components/ui/spinner"

export function ServerActionForm() {
  const [formState, formAction, pending] = React.useActionState(
    submitFormAction,
    { values: { title: "", description: "" }, errors: null, success: false }
  )

  return (
    <Form action={formAction}>
      <Field data-invalid={!!formState.errors?.title?.length}>
        <FieldLabel htmlFor="title">Title</FieldLabel>
        <Input
          id="title"
          name="title"
          defaultValue={formState.values.title}
          disabled={pending}
        />
        {formState.errors?.title && (
          <FieldError>{formState.errors.title[0]}</FieldError>
        )}
      </Field>
      <Button type="submit" disabled={pending}>
        {pending && <Spinner />} Submit
      </Button>
    </Form>
  )
}
```

---

## Theming and customization

### CSS variables system (OKLCH colors)

shadcn/ui uses OKLCH color format with CSS custom properties for maximum flexibility:

```css
/* globals.css */
:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --primary: oklch(0.985 0 0);
  --primary-foreground: oklch(0.205 0 0);
}
```

### Adding custom colors

```css
:root {
  --warning: oklch(0.84 0.16 84);
  --warning-foreground: oklch(0.28 0.07 46);
  --brand: oklch(0.6 0.2 264);
  --brand-foreground: oklch(0.98 0 0);
}

/* Tailwind 4 - Register with @theme directive */
@theme inline {
  --color-warning: var(--warning);
  --color-brand: var(--brand);
}
```

### Dark mode with next-themes

```typescript
// components/theme-provider.tsx
"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"

export function ThemeProvider({ children, ...props }) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}

// app/layout.tsx
import { ThemeProvider } from "@/components/theme-provider"

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
```

### Creating component variants with CVA

```typescript
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        brand: "bg-brand text-brand-foreground hover:bg-brand/90", // Custom
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
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}
```

---

## Common patterns and recipes

### Data tables with TanStack Table

```typescript
"use client"

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table"

export const columns: ColumnDef<User>[] = [
  {
    accessorKey: "email",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting()}>
        Email
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={row.getValue("status") === "active" ? "default" : "secondary"}>
        {row.getValue("status")}
      </Badge>
    ),
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon"><MoreHorizontal /></Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={() => handleEdit(row.original)}>Edit</DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleDelete(row.original)}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
]

export function DataTable<TData, TValue>({ columns, data }) {
  const [sorting, setSorting] = React.useState([])
  const [columnFilters, setColumnFilters] = React.useState([])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    state: { sorting, columnFilters },
  })

  return (
    <div>
      <Input
        placeholder="Filter emails..."
        value={(table.getColumn("email")?.getFilterValue() as string) ?? ""}
        onChange={(e) => table.getColumn("email")?.setFilterValue(e.target.value)}
      />
      <Table>{/* ... render table */}</Table>
      <div className="flex items-center justify-end space-x-2">
        <Button variant="outline" size="sm" onClick={() => table.previousPage()}>Previous</Button>
        <Button variant="outline" size="sm" onClick={() => table.nextPage()}>Next</Button>
      </div>
    </div>
  )
}
```

### Command palette (Cmd+K)

```typescript
"use client"

import { useEffect, useState } from "react"
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"

export function CommandMenu() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => router.push("/dashboard")}>
            <LayoutDashboard className="mr-2 h-4 w-4" /> Dashboard
          </CommandItem>
          <CommandItem onSelect={() => router.push("/settings")}>
            <Settings className="mr-2 h-4 w-4" /> Settings
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
```

### Toast notifications with Sonner

```typescript
import { toast } from "sonner"

// Basic usage
toast("Event has been created")
toast.success("Successfully saved!")
toast.error("Something went wrong")

// With description
toast("Event created", { description: "Monday, January 3rd at 6:00pm" })

// With action
toast("File uploaded", {
  action: { label: "Undo", onClick: () => handleUndo() },
})

// Promise toast
toast.promise(saveData(), {
  loading: "Saving...",
  success: "Data saved!",
  error: "Could not save.",
})
```

---

## Accessibility features from Radix UI

shadcn/ui inherits WAI-ARIA compliance from Radix UI primitives:

- **ARIA attributes**: Automatically applied `aria-*` attributes and roles
- **Keyboard navigation**: Arrow keys, Enter, Escape, Tab support
- **Focus management**: Programmatic focus, focus trapping in modals
- **Screen reader support**: Proper announcements and semantic markup

### Accessible form pattern

```typescript
<Field data-invalid={hasError}>
  <FieldLabel htmlFor="email">Email</FieldLabel>
  <Input
    id="email"
    name="email"
    type="email"
    aria-invalid={hasError}
    aria-describedby={hasError ? "email-error" : "email-description"}
  />
  <FieldDescription id="email-description">
    We'll never share your email.
  </FieldDescription>
  {hasError && (
    <FieldError id="email-error" role="alert">
      {errorMessage}
    </FieldError>
  )}
</Field>
```

### Screen reader only text

```typescript
<Button variant="outline" size="icon">
  <Sun className="h-4 w-4" />
  <span className="sr-only">Toggle theme</span>
</Button>
```

---

## CLI commands reference

```bash
# Initialize project
npx shadcn@latest init [options] [components...]
  -t, --template        next, next-monorepo
  -b, --base-color      neutral, gray, zinc, stone, slate
  -y, --yes             skip confirmation
  --css-variables       use CSS variables (default: true)

# Add components
npx shadcn@latest add [components...]
  -a, --all             add all components
  -o, --overwrite       overwrite existing
  npx shadcn@latest add button card    # Multiple components
  npx shadcn@latest add @acme/button   # From namespace
  npx shadcn@latest add -a             # All components

# View components (CLI 3.0)
npx shadcn@latest view button card dialog

# Search registries (CLI 3.0)
npx shadcn@latest search @shadcn -q "button"
npx shadcn@latest list @acme

# Check for updates
npx shadcn@latest diff [component]

# Migrate to unified Radix package
npx shadcn@latest migrate radix

# Initialize MCP Server
npx shadcn@latest mcp init
```

---

## Production sites using shadcn/ui

- **Vercel** (vercel.com) — Creator's platform
- **OpenAI** — Listed as trusted user
- **Adobe** — Listed as trusted user
- **Supabase** — Database UI extends shadcn
- **Sonos** — Listed as trusted user
- **Linear** — Combobox patterns
- **Cal.com** — Scheduling interface
- **v0.dev** — Vercel's AI tool generates shadcn components

---

## Troubleshooting common issues

### Hydration errors

```typescript
// Use useEffect for browser-only code
const [isClient, setIsClient] = useState(false)
useEffect(() => { setIsClient(true) }, [])

// Or dynamic import
const NoSSRComponent = dynamic(() => import('./Component'), { ssr: false })

// Suppress warning (use sparingly)
<time suppressHydrationWarning>{new Date().toLocaleString()}</time>
```

### CSS conflicts

Always use the `cn()` utility for proper class merging:

```typescript
<Button className={cn(
  "bg-primary",      // shadcn default
  "hover:scale-105", // Custom animation
  className          // User override
)} />
```

---

## Comparison with alternatives

| Feature | shadcn/ui | Radix UI | Chakra UI | MUI |
|---------|-----------|----------|-----------|-----|
| Approach | Copy-paste | npm | npm | npm |
| Styling | Tailwind | Unstyled | CSS-in-JS | CSS-in-JS |
| Customization | ⭐⭐⭐⭐⭐ Full | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Bundle Size | ~2-5KB/component | ~10-20KB | ~47KB+ | ~91KB+ |
| TypeScript | Excellent | Excellent | Good | Excellent |
| Accessibility | WAI-ARIA (Radix) | WAI-ARIA | Built-in | Built-in |
| Learning Curve | Medium | Low-Medium | Low | Medium |
