# Gemini 3 Pro Frontend Build Prompt

## Overview

Build a modern, Bolt.new-style code generation dashboard for **Faz Code**. This is a personal project for Glen Healy - make it exceptional.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict)
- **Styling**: Tailwind CSS with CSS variables
- **Components**: shadcn/ui
- **Animations**: Framer Motion
- **Icons**: Lucide Icons
- **State**: React Query + Zustand
- **Real-time**: WebSocket (native)

## Design Direction

**Theme**: Dark mode first, cyberpunk-meets-professional
**Inspiration**: Bolt.new, v0.dev, Vercel Dashboard
**Feel**: Fast, responsive, AI-native

### Color Palette
```css
:root {
  --background: #0A0A0F;
  --card: #12121A;
  --border: #1E1E2E;
  --primary: #6366F1;       /* Indigo */
  --primary-hover: #818CF8;
  --accent: #22D3EE;        /* Cyan */
  --success: #22C55E;
  --warning: #F59E0B;
  --error: #EF4444;
  --text: #F1F5F9;
  --text-muted: #64748B;
}
```

### Typography
- Headings: `"Cal Sans", "Inter", system-ui`
- Body: `"Inter", -apple-system, system-ui`
- Code: `"JetBrains Mono", "Fira Code", monospace`

---

## Page Structure

### `/faz` - Main Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│  🚀 FAZ CODE                    [+ New Project]        [User Avatar] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  YOUR PROJECTS                                                       │
│                                                                      │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐           │
│  │ 🟢 Landing     │ │ 🟡 Portfolio   │ │ ➕ New Project │           │
│  │ Page           │ │ Site           │ │                │           │
│  │ Deployed       │ │ Building...    │ │                │           │
│  │ 12 files       │ │ 4 files        │ │                │           │
│  └────────────────┘ └────────────────┘ └────────────────┘           │
│                                                                      │
│  RECENT ACTIVITY                                                     │
│  ─────────────────                                                   │
│  • Nicole routed to Planning Agent              2m ago               │
│  • Architecture generated (5 pages, 12 components)                   │
│  • Design Agent created color palette                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### `/faz/new` - Create Project

Large centered input with real-time prompt validation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    What would you like to build?                     │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Build a landing page for my AI startup called AlphaWave... │   │
│  │                                                              │   │
│  │ • Dark theme                                                 │   │
│  │ • Pricing section with 3 tiers                              │   │
│  │ • Contact form                                               │   │
│  │ • Testimonials                                               │   │
│  │                                                  [✨ Create] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  💡 Tip: Be specific about features, style, and content              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### `/faz/projects/[id]` - Project Workspace

Three-panel layout (resizable):

```
┌────────────────────┬────────────────────────────┬───────────────────┐
│ FILES              │ PREVIEW                    │ AGENT ACTIVITY    │
├────────────────────┼────────────────────────────┼───────────────────┤
│ 📁 app             │                            │ 🟢 LIVE           │
│   └─ layout.tsx    │   ┌──────────────────┐    │                   │
│   └─ page.tsx      │   │                  │    │ 🤖 Nicole         │
│   └─ globals.css   │   │  [Live Preview]  │    │ "Routing to      │
│ 📁 components      │   │                  │    │  Planning..."    │
│   └─ Hero.tsx      │   │                  │    │                   │
│   └─ Features.tsx  │   │                  │    │ 📐 Planning       │
│   └─ Footer.tsx    │   └──────────────────┘    │ "Creating arch..." │
│ 📄 tailwind.config │                            │                   │
│ 📄 package.json    │   [📱] [💻] [🖥️]  [🔗]    │ 🎨 Design         │
│                    │                            │ "Color palette..." │
│                    │   ▼ ARCHITECTURE           │                   │
│                    │   5 pages, 12 components   │ 💻 Coding         │
│                    │   Tech: Next.js + Tailwind │ ████████░░ 80%   │
│                    │                            │                   │
├────────────────────┴────────────────────────────┼───────────────────┤
│ 💬 Chat with Nicole                             │ [📤 Deploy]       │
│ ┌──────────────────────────────────────────┐   │                   │
│ │ Add a testimonials section...             │   │ $0.04 spent       │
│ └──────────────────────────────────────────┘   │ 2,450 tokens      │
└─────────────────────────────────────────────────┴───────────────────┘
```

---

## Component Specifications

### 1. `ProjectCard`
```typescript
interface ProjectCardProps {
  id: number;
  name: string;
  status: 'intake' | 'planning' | 'designing' | 'building' | 'qa' | 'deployed';
  fileCount: number;
  updatedAt: string;
  previewUrl?: string;
}
```

Features:
- Hover to show quick preview thumbnail
- Status indicator with color coding
- Click to open workspace

### 2. `FileTree`
- Collapsible folders
- File icons by type (.tsx, .css, .json)
- Click to view file content
- Active file highlight

### 3. `PreviewPane`
- iframe for live HTML preview
- Responsive mode toggles (mobile/tablet/desktop)
- Full-screen option
- Link to deployed URL

### 4. `AgentActivityFeed`
Real-time feed showing:
- Agent name + avatar
- Activity type (route, generate, review, etc.)
- Message content
- Timestamp
- Token usage badge
- Expandable thinking/response content

### 5. `ChatInput`
- Multi-line textarea with auto-resize
- Cmd+Enter to send
- File attachment support (future)
- Quick prompts dropdown

### 6. `CodeViewer`
- Syntax highlighting (use Prism or Shiki)
- Line numbers
- Copy button
- File path header

---

## API Integration

### Endpoints

```typescript
// Base URL from env: NEXT_PUBLIC_API_URL

// Projects
GET    /faz/projects                    // List projects
POST   /faz/projects                    // Create project
GET    /faz/projects/:id                // Get project
DELETE /faz/projects/:id                // Delete project

// Pipeline
POST   /faz/projects/:id/run            // Start pipeline
POST   /faz/projects/:id/stop           // Stop pipeline

// Files
GET    /faz/projects/:id/files          // Get all files
GET    /faz/projects/:id/files/:fileId  // Get single file

// Activities
GET    /faz/projects/:id/activities     // Get activities (polling fallback)

// Chat
GET    /faz/projects/:id/chat           // Get chat history
POST   /faz/projects/:id/chat           // Send message

// Architecture
GET    /faz/projects/:id/architecture   // Get architecture
PUT    /faz/projects/:id/architecture   // Update architecture

// Deploy
POST   /faz/projects/:id/deploy         // Deploy to Vercel
```

### WebSocket

```typescript
// Connect: ws://api.host/faz/projects/:id/ws

// Send
{ type: "chat", message: "..." }
{ type: "run", start_agent: "nicole" }
{ type: "ping" }

// Receive
{ type: "activity", agent: "...", message: "...", ... }
{ type: "chat", role: "assistant", content: "...", ... }
{ type: "status", status: "building", current_agent: "coding" }
{ type: "file", path: "...", action: "created|updated" }
{ type: "complete", status: "approved", file_count: 12 }
{ type: "error", message: "..." }
```

---

## Zustand Store

```typescript
interface FazStore {
  // Projects
  projects: Project[];
  currentProject: Project | null;
  setCurrentProject: (id: number) => void;
  
  // Files
  files: Map<string, FileContent>;
  selectedFile: string | null;
  selectFile: (path: string) => void;
  
  // Activities
  activities: Activity[];
  addActivity: (activity: Activity) => void;
  
  // Chat
  messages: ChatMessage[];
  sendMessage: (content: string) => void;
  
  // WebSocket
  ws: WebSocket | null;
  connected: boolean;
  connect: (projectId: number) => void;
  disconnect: () => void;
  
  // UI State
  previewMode: 'mobile' | 'tablet' | 'desktop';
  setPreviewMode: (mode: 'mobile' | 'tablet' | 'desktop') => void;
}
```

---

## Animation Specifications

### Page Transitions
```typescript
const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 }
};
```

### Activity Feed Items
```typescript
const activityVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 }
};
```

### Status Pulse
```css
@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-indicator.active {
  animation: status-pulse 2s ease-in-out infinite;
}
```

---

## File Structure

```
frontend/src/
├── app/
│   ├── faz/
│   │   ├── page.tsx                  # Dashboard
│   │   ├── new/
│   │   │   └── page.tsx              # Create project
│   │   └── projects/
│   │       └── [id]/
│   │           └── page.tsx          # Workspace
│   └── globals.css
├── components/
│   └── faz/
│       ├── ProjectCard.tsx
│       ├── ProjectGrid.tsx
│       ├── FileTree.tsx
│       ├── PreviewPane.tsx
│       ├── AgentActivity.tsx
│       ├── AgentActivityFeed.tsx
│       ├── ChatInput.tsx
│       ├── ChatMessages.tsx
│       ├── CodeViewer.tsx
│       ├── StatusBadge.tsx
│       └── WorkspaceLayout.tsx
├── lib/
│   ├── faz/
│   │   ├── api.ts                    # API client
│   │   ├── websocket.ts              # WebSocket manager
│   │   └── store.ts                  # Zustand store
│   └── utils.ts
└── types/
    └── faz.ts                        # TypeScript types
```

---

## Authentication

Use existing Nicole auth system:
- JWT tokens in cookies
- `Authorization: Bearer <token>` header
- Redirect to `/login` if 401

---

## Must-Have Features

1. **Real-time activity feed** - WebSocket-powered, shows all agent activity
2. **Live preview** - Updates as files are generated
3. **File tree with code viewer** - Click to view any generated file
4. **Chat with Nicole** - Send messages to adjust the project
5. **Deploy button** - One-click deploy to Vercel
6. **Cost tracking** - Show tokens used and cost in dollars

---

## Nice-to-Have Features

1. **Split view** - Show code and preview side by side
2. **History timeline** - Visual timeline of agent handoffs
3. **Diff view** - Show changes between file versions
4. **Export** - Download project as ZIP
5. **Template gallery** - Start from pre-built templates

---

## Quality Checklist

- [ ] All TypeScript - no `any` types
- [ ] Mobile responsive (works on tablet+)
- [ ] Dark mode only (no light mode toggle needed)
- [ ] Loading states for all async operations
- [ ] Error boundaries for each major section
- [ ] Keyboard shortcuts (Cmd+Enter to send, Cmd+K for search)
- [ ] Accessible (WCAG 2.1 AA)
- [ ] < 3s initial page load

---

## Sample Data for Development

Use this mock data while building:

```typescript
const mockProject = {
  project_id: 1,
  name: "AlphaWave Landing",
  slug: "alphawave-landing-1",
  status: "building",
  original_prompt: "Build a landing page for my AI startup...",
  current_agent: "coding",
  file_count: 8,
  total_tokens_used: 2450,
  total_cost_cents: 4,
  created_at: "2025-12-16T10:00:00Z",
  updated_at: "2025-12-16T10:05:00Z",
};

const mockFiles = [
  { path: "app/layout.tsx", content: "..." },
  { path: "app/page.tsx", content: "..." },
  { path: "components/Hero.tsx", content: "..." },
];

const mockActivities = [
  { agent: "nicole", type: "route", message: "Routing to Planning Agent" },
  { agent: "planning", type: "generate", message: "Architecture: 5 pages, 12 components" },
  { agent: "design", type: "generate", message: "Created color palette: indigo/cyan theme" },
  { agent: "coding", type: "generate", message: "Generating app/layout.tsx..." },
];
```

---

## Delivery

Generate all files with proper structure. Include:
1. All page components
2. All UI components
3. API client
4. WebSocket manager
5. Zustand store
6. TypeScript types
7. Tailwind config updates
8. Global CSS with dark theme

**Begin generation.**

