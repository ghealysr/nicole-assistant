# NICOLE V7 - FRONTEND ENVIRONMENT VARIABLES

## Frontend Environment Variables (for `.env.local`)

### Required Variables

```env
# Supabase Configuration (Frontend-safe)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Setup Instructions

1. **Create `.env.local` file** in the `/frontend/` directory
2. **Copy the variables above** and replace with your actual values
3. **Get values from Supabase Dashboard:**
   - Go to https://supabase.com/dashboard
   - Select your project
   - Go to Settings → API
   - Copy the "Project URL" and "anon/public" key

## Security Notes

- ✅ These variables are **safe** to expose to frontend
- ✅ The `anon` key has Row Level Security (RLS) enabled
- ❌ **Never** put service role keys in frontend
- ❌ **Never** commit `.env.local` to version control

## Usage in Code

The variables are accessed in the frontend using:

```typescript
// In frontend/src/lib/alphawave_supabase.ts
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

export const supabase = createClientComponentClient({
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
});
```

## Validation

The frontend will fail to build if these variables are missing, so make sure they're properly configured before deployment.
