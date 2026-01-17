# Hotspot - Astro + Supabase

An Astro project pre-configured with Supabase database integration.

## Features

- ✅ Astro framework with TypeScript
- ✅ Supabase client integration
- ✅ Environment variable configuration
- ✅ Example API route for database operations
- ✅ UI component to display database data

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Create a Supabase Project

If you don't have a Supabase project yet:

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign in or create an account
4. Create a new project with your desired organization

### 3. Configure Environment Variables

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Get your Supabase credentials:
   - Go to your project dashboard at [app.supabase.com](https://app.supabase.com)
   - Navigate to **Settings** → **API**
   - Copy your **Project URL** and **anon/public** key

3. Update `.env` with your credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. Verify Your Setup

Run the verification script:

```bash
npm run verify
```

This will test:
- Supabase connection
- Access to `hotspots` table
- API endpoint functionality

If you see "✅ ALL TESTS PASSED!", your setup is complete!

## Development

### Start the Dev Server

```bash
npm run dev
```

Visit `http://localhost:4321` to see your application.

### Test the Connection

1. Open `http://localhost:4321` in your browser
2. Click "Fetch Data from Supabase" button
3. You should see your hotspots data displayed with:
   - Title
   - Summary
   - Source
   - Publication status
   - Link to original source

## Project Structure

```
/
├── public/                  # Static assets
├── src/
│   ├── components/          # Astro components
│   │   └── DataDisplay.astro   # Hotspots data display
│   ├── lib/                # Utilities and configurations
│   │   └── supabase.ts         # Supabase client setup
│   ├── pages/              # Page routes
│   │   ├── api/            # API endpoints
│   │   │   └── test-connection.ts  # Test hotspots connection
│   │   └── index.astro         # Main page
│   └── env.d.ts            # TypeScript environment definitions
├── .env                  # Your Supabase credentials (not in git)
├── .env.example           # Environment variable template
├── verify-setup.js        # Full verification script
├── test-db-connection.js # Quick connection test
├── DATABASE_SETUP.md      # Setup documentation
└── package.json
```

## Using Supabase in Your Code

### Server-Side (API Routes)

```typescript
import { supabase } from '../lib/supabase'

const { data, error } = await supabase
  .from('hotspots')
  .select('*')
  .eq('is_published', true)
  .order('created_at', { ascending: false })
```

### Client-Side (Components)

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  import.meta.env.SUPABASE_URL,
  import.meta.env.SUPABASE_ANON_KEY
)
```

## Build for Production

```bash
npm run build
```

The optimized files will be in `./dist/`.

## Learn More

- [Astro Documentation](https://docs.astro.build)
- [Supabase Documentation](https://supabase.com/docs)
