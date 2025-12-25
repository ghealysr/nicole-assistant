<!-- category: qa -->
<!-- keywords: react, typescript, hooks, components, patterns, errors, anti-patterns -->

# React & TypeScript QA Standards

## Code Quality Severity Levels

| Level | Description | Example |
|-------|-------------|---------|
| 🔴 CRITICAL | Security/crash risk | XSS vulnerability, infinite loops |
| 🟠 HIGH | Performance/UX impact | Unnecessary re-renders, memory leaks |
| 🟡 MEDIUM | Maintainability issue | Missing types, poor naming |
| 🟢 LOW | Style/preference | Formatting, comments |

---

## 1. TypeScript Strictness

### Required tsconfig Settings

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### Common Type Issues

```tsx
// 🔴 CRITICAL - any type
const handleData = (data: any) => { ... }

// ✅ CORRECT - proper typing
interface UserData {
  id: string;
  name: string;
  email: string;
}
const handleData = (data: UserData) => { ... }

// 🔴 CRITICAL - type assertion without validation
const user = response.data as User;

// ✅ CORRECT - runtime validation
import { z } from 'zod';
const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email()
});
const user = UserSchema.parse(response.data);
```

---

## 2. React Hooks Rules

### Hook Rules (MUST Follow)

1. Only call hooks at top level (not in loops, conditions, nested functions)
2. Only call hooks from React functions
3. Dependencies must be exhaustive

### Common Hook Violations

```tsx
// 🔴 CRITICAL - conditional hook
function Component({ isEnabled }) {
  if (isEnabled) {
    const [state, setState] = useState(false); // ❌ Hook in condition
  }
}

// ✅ CORRECT - unconditional hook
function Component({ isEnabled }) {
  const [state, setState] = useState(false);
  
  if (!isEnabled) return null;
  // ... rest of component
}
```

### useEffect Dependency Issues

```tsx
// 🟠 HIGH - missing dependency
useEffect(() => {
  fetchData(userId);
}, []); // ❌ Missing userId

// 🟠 HIGH - object/function in deps causes infinite loop
useEffect(() => {
  doSomething(options);
}, [options]); // ❌ New object every render

// ✅ CORRECT - memoized dependency
const options = useMemo(() => ({ limit: 10 }), []);
useEffect(() => {
  doSomething(options);
}, [options]);
```

### useCallback/useMemo Requirements

```tsx
// 🟠 HIGH - unmemoized callback passed to child
<Child onClick={() => doSomething(id)} /> // ❌ New function every render

// ✅ CORRECT - memoized callback
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
<Child onClick={handleClick} />

// When to memoize:
// 1. Callbacks passed to memoized children
// 2. Expensive computations
// 3. Values used in other hooks' dependency arrays
```

---

## 3. Component Patterns

### Proper Component Structure

```tsx
// ✅ Well-structured component
import { memo, useCallback, useMemo } from 'react';
import type { FC } from 'react';

// 1. Types at top
interface ProductCardProps {
  product: Product;
  onAddToCart: (id: string) => void;
  isLoading?: boolean;
}

// 2. Memoized component
export const ProductCard: FC<ProductCardProps> = memo(function ProductCard({
  product,
  onAddToCart,
  isLoading = false
}) {
  // 3. Hooks first
  const [quantity, setQuantity] = useState(1);
  
  // 4. Memoized values
  const totalPrice = useMemo(
    () => product.price * quantity,
    [product.price, quantity]
  );
  
  // 5. Callbacks
  const handleAddToCart = useCallback(() => {
    onAddToCart(product.id);
  }, [product.id, onAddToCart]);
  
  // 6. Early returns
  if (isLoading) return <Skeleton />;
  
  // 7. Render
  return (
    <div className="product-card">
      {/* ... */}
    </div>
  );
});
```

### Component Anti-Patterns

```tsx
// 🔴 CRITICAL - component inside component
function Parent() {
  // ❌ This creates new component every render, destroying state
  const Child = () => <div>Child</div>;
  return <Child />;
}

// ✅ CORRECT - separate component
const Child = () => <div>Child</div>;
function Parent() {
  return <Child />;
}
```

---

## 4. State Management

### State Location Guidelines

```
Local state (useState)     → UI state, form inputs
Lifted state              → Shared between siblings
Context                   → App-wide settings, theme, auth
External store (Zustand)  → Complex async state, caching
Server state (SWR/Query)  → Remote data fetching
```

### Zustand Best Practices

```tsx
// ✅ Well-structured Zustand store
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface ProjectState {
  // State
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  
  // Actions
  setProjects: (projects: Project[]) => void;
  selectProject: (id: string) => void;
  reset: () => void;
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        projects: [],
        currentProject: null,
        isLoading: false,
        
        // Actions with immer-like updates
        setProjects: (projects) => set({ projects }),
        
        selectProject: (id) => set((state) => ({
          currentProject: state.projects.find(p => p.id === id) ?? null
        })),
        
        reset: () => set({ 
          projects: [], 
          currentProject: null, 
          isLoading: false 
        })
      }),
      { name: 'project-storage' }
    )
  )
);

// ✅ Selector for performance
const currentProject = useProjectStore(state => state.currentProject);
```

---

## 5. Error Handling

### Error Boundaries (Required)

```tsx
// ✅ Error boundary wrapper
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div role="alert" className="error-container">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// Wrap critical sections
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <CriticalComponent />
</ErrorBoundary>
```

### Async Error Handling

```tsx
// 🔴 CRITICAL - unhandled promise rejection
async function fetchData() {
  const data = await api.get('/users'); // ❌ No try/catch
}

// ✅ CORRECT - proper error handling
async function fetchData() {
  try {
    const data = await api.get('/users');
    return { data, error: null };
  } catch (error) {
    console.error('Fetch failed:', error);
    return { data: null, error: error instanceof Error ? error : new Error('Unknown error') };
  }
}
```

---

## 6. Performance Patterns

### Re-render Prevention

```tsx
// 🟠 HIGH - object literal in JSX causes re-renders
<Component style={{ color: 'red' }} /> // ❌ New object every render

// ✅ CORRECT - stable reference
const style = { color: 'red' }; // Outside component or useMemo
<Component style={style} />

// 🟠 HIGH - array methods in render
{items.filter(x => x.active).map(item => ...)} // ❌ New array every render

// ✅ CORRECT - memoized
const activeItems = useMemo(
  () => items.filter(x => x.active),
  [items]
);
{activeItems.map(item => ...)}
```

### List Rendering

```tsx
// 🔴 CRITICAL - index as key
{items.map((item, index) => (
  <Item key={index} item={item} /> // ❌ Causes re-mount on reorder
))}

// ✅ CORRECT - stable unique key
{items.map(item => (
  <Item key={item.id} item={item} />
))}
```

### Lazy Loading

```tsx
// ✅ Code splitting for routes
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

---

## 7. Form Handling

### React Hook Form + Zod

```tsx
// ✅ Proper form with validation
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const formSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be 8+ characters'),
});

type FormData = z.infer<typeof formSchema>;

function LoginForm() {
  const { 
    register, 
    handleSubmit, 
    formState: { errors, isSubmitting } 
  } = useForm<FormData>({
    resolver: zodResolver(formSchema)
  });

  const onSubmit = async (data: FormData) => {
    await login(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} aria-invalid={!!errors.email} />
      {errors.email && <span role="alert">{errors.email.message}</span>}
      
      <input type="password" {...register('password')} />
      {errors.password && <span role="alert">{errors.password.message}</span>}
      
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Loading...' : 'Login'}
      </button>
    </form>
  );
}
```

---

## 8. Security Patterns

### XSS Prevention

```tsx
// 🔴 CRITICAL - dangerouslySetInnerHTML with user input
<div dangerouslySetInnerHTML={{ __html: userInput }} /> // ❌ XSS risk

// ✅ CORRECT - use DOMPurify if HTML is required
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

// ✅ BEST - don't use dangerouslySetInnerHTML at all
<div>{userInput}</div> // React auto-escapes
```

### API Security

```tsx
// 🔴 CRITICAL - secrets in client code
const API_KEY = 'sk_live_xxx'; // ❌ Exposed in bundle

// ✅ CORRECT - environment variables (still be careful)
const API_URL = process.env.NEXT_PUBLIC_API_URL; // Only public info

// ✅ BEST - API routes for sensitive operations
// /api/payment.ts (server-side)
export async function POST(request: Request) {
  const API_KEY = process.env.STRIPE_SECRET_KEY; // Server-only
  // ... process payment
}
```

---

## 9. Testing Patterns

### Component Testing

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

describe('Button', () => {
  it('calls onClick when clicked', async () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    await userEvent.click(screen.getByRole('button', { name: /click me/i }));
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
  
  it('is disabled when loading', () => {
    render(<Button isLoading>Submit</Button>);
    
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

---

## 10. QA Review Checklist

### Must Check Every Component

- [ ] All props typed (no `any`)
- [ ] Hooks at top level only
- [ ] useEffect has correct dependencies
- [ ] Callbacks memoized if passed to children
- [ ] Error boundaries around critical sections
- [ ] Loading states handled
- [ ] Empty states handled
- [ ] Keys are stable unique identifiers

### Must Check Every Page

- [ ] Lazy loading for heavy components
- [ ] Meta tags for SEO
- [ ] Error handling for data fetching
- [ ] Loading skeletons during fetch
- [ ] 404 handling for invalid routes

### Security Review

- [ ] No secrets in client code
- [ ] No dangerouslySetInnerHTML with user input
- [ ] API routes for sensitive operations
- [ ] Input validation on forms
- [ ] CSRF protection if using cookies

