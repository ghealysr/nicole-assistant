# Nicole V7 - Personal AI Companion System

<p align="center">
  <img src="frontend/public/images/nicole-thinking-avatar.png" alt="Nicole" width="120" />
</p>

<p align="center">
  <strong>A deeply personal AI companion for Glen Healy and family</strong><br>
  <em>Built with love, designed to remember everything forever</em>
</p>

---

## 🎯 What is Nicole?

Nicole is a **personal AI companion** built specifically for 8 people: Glen (creator/admin), his 4 sons, mother-in-law, father-in-law, and 1 friend. 

**This is NOT** a generic chatbot or SaaS product. It's a deeply integrated, personalized system that:

- **Remembers everything forever** - 3-tier memory system with vector search
- **Embodies Nicole's spirit** - Warm, intelligent, loving personality
- **Helps with business** - AlphaWave client work, proposals, web design
- **Supports the family** - Homework help, schedules, age-appropriate content
- **Predicts sports** - Sports Oracle for NFL/NBA/MLB/NHL

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      NICOLE V7 SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         ┌─────────────────────────────────┐   │
│  │   Frontend  │         │          Backend (FastAPI)      │   │
│  │  (Next.js)  │◄────────┤                                 │   │
│  │   Vercel    │   SSE   │  ┌─────────────────────────────┐│   │
│  └─────────────┘         │  │    Agent Orchestrator       ││   │
│                          │  │  ┌──────┐ ┌──────┐ ┌──────┐ ││   │
│                          │  │  │Think │ │Memory│ │ Tools│ ││   │
│                          │  │  │ Tool │ │Search│ │Search│ ││   │
│                          │  │  └──────┘ └──────┘ └──────┘ ││   │
│                          │  └─────────────────────────────┘│   │
│                          │                                 │   │
│                          │  ┌──────────────────────────────┤   │
│                          │  │        AI Layer              │   │
│                          │  │ ┌────────┐    ┌──────────┐  │   │
│                          │  │ │ Claude │    │  OpenAI  │  │   │
│                          │  │ │Sonnet/ │    │Embeddings│  │   │
│                          │  │ │ Haiku  │    │Moderation│  │   │
│                          │  │ └────────┘    └──────────┘  │   │
│                          │  └──────────────────────────────┤   │
│                          └─────────────────────────────────┘   │
│                                         │                       │
│  ┌──────────────────────────────────────┴────────────────────┐ │
│  │                    Data Layer                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                │ │
│  │  │  Tiger   │  │  Redis   │  │  Qdrant  │                │ │
│  │  │ Postgres │  │  Cache   │  │  Vector  │                │ │
│  │  │(Primary) │  │(Tier 1)  │  │(Tier 3)  │                │ │
│  │  └──────────┘  └──────────┘  └──────────┘                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** 
- **Node.js 18+** and npm
- **Docker** and Docker Compose
- **PostgreSQL 15+** (via Tiger Cloud or local)
- API Keys: Anthropic, OpenAI

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/nicole-v7.git
cd nicole-v7

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  # Windows
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Verify critical packages
python -c "import anthropic; print(f'anthropic: {anthropic.__version__}')"
python -c "import httpx; print(f'httpx: {httpx.__version__}')"
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials (see Environment Variables section below)
nano .env
```

### 4. Start Infrastructure Services

```bash
# From project root - start Redis and Qdrant
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Initialize Database

```bash
# Run database migrations (Tiger Postgres)
# Option A: Using psql directly
psql $TIGER_DATABASE_URL -f database/schema.sql

# Option B: Using the setup script
python scripts/setup_database.py
```

### 6. Start Backend Server

```bash
cd backend

# Development (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 7. Start Frontend

```bash
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

---

## 🔧 Environment Variables

Create a `.env` file in the project root with these variables:

```bash
# =============================================================================
# NICOLE V7 ENVIRONMENT CONFIGURATION
# =============================================================================

# -----------------------------------------------------------------------------
# ENVIRONMENT
# -----------------------------------------------------------------------------
ENVIRONMENT=development  # development | staging | production
DEBUG=true

# -----------------------------------------------------------------------------
# DATABASE (Tiger Postgres - Primary)
# -----------------------------------------------------------------------------
TIGER_DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require
TIGER_SPORTS_URL=postgresql://user:password@host:port/sports_db  # Optional

# -----------------------------------------------------------------------------
# CACHE & VECTOR DB
# -----------------------------------------------------------------------------
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# -----------------------------------------------------------------------------
# AI APIS (Required)
# -----------------------------------------------------------------------------
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
OPENAI_API_KEY=sk-xxxxx

# -----------------------------------------------------------------------------
# SUPABASE (Legacy - for auth)
# -----------------------------------------------------------------------------
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1...
SUPABASE_JWT_SECRET=your-jwt-secret

# -----------------------------------------------------------------------------
# SECURITY
# -----------------------------------------------------------------------------
JWT_SECRET_KEY=your-super-secret-jwt-key-at-least-32-chars
SESSION_SECRET=your-session-secret-key
ALLOWED_USERS=glen@alphawavetech.com,family@example.com

# -----------------------------------------------------------------------------
# FRONTEND
# -----------------------------------------------------------------------------
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1...

# -----------------------------------------------------------------------------
# VOICE (Optional)
# -----------------------------------------------------------------------------
ELEVENLABS_API_KEY=xxxxx
NICOLE_VOICE_ID=xxxxx
REPLICATE_API_TOKEN=xxxxx

# -----------------------------------------------------------------------------
# FILE PROCESSING (Optional)
# -----------------------------------------------------------------------------
AZURE_DOCUMENT_ENDPOINT=https://xxxxx.cognitiveservices.azure.com
AZURE_DOCUMENT_KEY=xxxxx
AZURE_VISION_ENDPOINT=https://xxxxx.cognitiveservices.azure.com
AZURE_VISION_KEY=xxxxx

# -----------------------------------------------------------------------------
# FILE STORAGE (Optional)
# -----------------------------------------------------------------------------
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
DO_SPACES_BUCKET=nicole-files
DO_SPACES_BACKUP_BUCKET=nicole-backups
DO_SPACES_ACCESS_KEY=xxxxx
DO_SPACES_SECRET_KEY=xxxxx

# -----------------------------------------------------------------------------
# MCP INTEGRATIONS (Optional)
# -----------------------------------------------------------------------------
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxx
TELEGRAM_BOT_TOKEN=xxxxx:xxxxx
GLEN_TELEGRAM_CHAT_ID=123456789
NOTION_API_KEY=secret_xxxxx
NOTION_GLEN_WORKSPACE_ID=xxxxx

# -----------------------------------------------------------------------------
# MONITORING (Production)
# -----------------------------------------------------------------------------
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx

# -----------------------------------------------------------------------------
# SAFETY SETTINGS
# -----------------------------------------------------------------------------
SAFETY_ENABLE=true
SAFETY_ENABLE_PROVIDER_MODERATION=true
COPPA_REQUIRE_PARENTAL_CONSENT=true
COPPA_MIN_AGE_NO_CONSENT=13
```

---

## 📁 Project Structure

```
nicole-v7/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── agents/            # Agent prompts and routing
│   │   │   └── prompts/       # Markdown prompt files
│   │   ├── integrations/      # External API clients
│   │   │   ├── alphawave_claude.py
│   │   │   ├── alphawave_openai.py
│   │   │   └── alphawave_qdrant.py
│   │   ├── mcp/               # MCP server integrations
│   │   ├── middleware/        # Auth, CORS, logging, rate limiting
│   │   ├── models/            # Pydantic data models
│   │   ├── routers/           # API route handlers
│   │   ├── services/          # Business logic services
│   │   │   ├── agent_orchestrator.py
│   │   │   ├── alphawave_memory_service.py
│   │   │   └── ...
│   │   ├── skills/            # Skill system (plugins)
│   │   └── main.py            # FastAPI application
│   ├── database/              # SQL migrations
│   ├── scripts/               # Utility scripts
│   ├── requirements.txt
│   └── worker.py              # Background job scheduler
│
├── frontend/                   # Next.js React frontend
│   ├── src/
│   │   ├── app/               # Next.js app router pages
│   │   ├── components/        # React components
│   │   │   ├── chat/          # Chat UI components
│   │   │   ├── widgets/       # Dashboard widgets
│   │   │   └── ui/            # Base UI components
│   │   └── lib/               # Utilities, hooks, API clients
│   ├── public/                # Static assets
│   └── package.json
│
├── database/                   # Database schemas
│   ├── schema.sql             # Main Postgres schema
│   └── migrations/            # Migration files
│
├── deploy/                     # Deployment configs
│   ├── nginx.conf
│   └── supervisor-*.conf
│
├── docker-compose.yml          # Local infrastructure
└── README.md                   # You are here
```

---

## 🗃️ Database Setup

### Using Tiger Postgres (Recommended)

1. Create a database in [Tiger Cloud](https://console.timescale.cloud/)
2. Copy the connection string to `TIGER_DATABASE_URL`
3. Run the schema:

```bash
psql $TIGER_DATABASE_URL -f database/schema.sql
```

### Local PostgreSQL

```bash
# Add Postgres to docker-compose (if needed)
docker run -d \
  --name nicole-postgres \
  -e POSTGRES_PASSWORD=nicole \
  -e POSTGRES_DB=nicole \
  -p 5432:5432 \
  postgres:15

# Connect and run schema
psql postgresql://postgres:nicole@localhost:5432/nicole -f database/schema.sql
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `users` | User profiles with roles (admin/child/parent) |
| `conversations` | Chat conversation sessions |
| `messages` | Individual chat messages |
| `memory_entries` | Long-term memory storage with embeddings |
| `knowledge_bases` | Memory organization containers |
| `memory_tags` | Tag system for memories |
| `daily_journals` | Daily journal entries with Spotify/health data |
| `corrections` | User corrections for learning |

---

## 🔌 API Endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/message` | Send message, receive SSE stream |
| `GET` | `/chat/conversations` | List user's conversations |
| `GET` | `/chat/history/{id}` | Get conversation messages |
| `DELETE` | `/chat/conversations/{id}` | Delete conversation |
| `POST` | `/chat/conversations/{id}/pin` | Pin/unpin conversation |

### Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/memory/search` | Search memories |
| `POST` | `/memory/` | Create memory |
| `GET` | `/memory/{id}` | Get memory details |
| `GET` | `/memory/knowledge-bases` | List knowledge bases |
| `POST` | `/memory/knowledge-bases` | Create knowledge base |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload` | Upload document |
| `GET` | `/documents/search` | Search documents |
| `GET` | `/documents/{id}` | Get document |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/health/ready` | Readiness check |

---

## 🧠 Memory System

Nicole uses a **3-tier memory architecture**:

### Tier 1: Redis Hot Cache (24h TTL)
- Recent conversation context
- Active session data
- Fast retrieval for current interactions

### Tier 2: PostgreSQL Structured (Permanent)
- Facts, preferences, relationships
- Tagged and categorized memories
- Full-text search support

### Tier 3: Qdrant Vector (Semantic)
- Embedded memories for semantic search
- Cross-conversation pattern detection
- Long-term relationship understanding

### Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `preference` | User preferences | "Glen prefers tea over coffee" |
| `fact` | Factual information | "Glen has 4 sons" |
| `relationship` | People connections | "Alex is Glen's oldest son" |
| `event` | Important events | "Family reunion is June 15" |
| `workflow` | How to do things | "Glen's morning routine" |
| `insight` | Patterns observed | "Glen seems stressed on Mondays" |

---

## 🤖 Agent System

Nicole uses specialized agents for different tasks:

| Agent | File | Purpose |
|-------|------|---------|
| `nicole_core` | `nicole_core.md` | Base personality and identity |
| `design_agent` | `design_agent.md` | Web design and UI work |
| `business_agent` | `business_agent.md` | AlphaWave client work |
| `sports_agent` | `sports_agent.md` | Sports Oracle predictions |

### Tools Available

| Tool | Description |
|------|-------------|
| `think` | Explicit reasoning (Think Tool) |
| `search_tools` | Dynamic tool discovery |
| `memory_search` | Search stored memories |
| `memory_store` | Store new memories |
| `document_search` | Search uploaded documents |

---

## ⏰ Background Jobs

The worker (`backend/worker.py`) runs 8 scheduled tasks:

| Time | Job | Description |
|------|-----|-------------|
| 5:00 AM | Sports Data | Collect sports data from APIs |
| 6:00 AM | Sports Predictions | Generate daily predictions |
| 8:00 AM | Dashboard Update | Update user dashboards |
| 9:00 AM | Blog Generation | Create sports analysis blog |
| 11:59 PM | Daily Journals | Process journal entries |
| Sunday 2 AM | Memory Decay | Reduce unused memory confidence |
| Sunday 3 AM | Weekly Reflection | Nicole's self-reflection |
| Sunday 4 AM | Self-Audit | Performance review |

### Running the Worker

```bash
# Development
cd backend
python worker.py

# Production (with Supervisor)
supervisorctl start nicole-worker
```

---

## 🚢 Deployment

### Production Architecture

```
Internet → Cloudflare → Nginx (DO Droplet) → Backend (FastAPI)
                              ↓
                        Vercel → Frontend (Next.js)
```

### Digital Ocean Droplet Setup

```bash
# Install dependencies
apt update && apt install -y python3.11 python3.11-venv nginx supervisor

# Clone and setup
cd /opt
git clone https://github.com/your-org/nicole-v7.git nicole
cd nicole

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Configure nginx
cp deploy/nginx.conf /etc/nginx/sites-available/nicole
ln -s /etc/nginx/sites-available/nicole /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Configure supervisor
cp deploy/supervisor-nicole-api.conf /etc/supervisor/conf.d/
cp deploy/supervisor-nicole-worker.conf /etc/supervisor/conf.d/
supervisorctl reread && supervisorctl update
```

### Vercel Frontend Deployment

```bash
cd frontend
vercel --prod
```

---

## 🔒 Security

### Authentication Flow

1. User authenticates via Supabase OAuth
2. Frontend receives JWT token
3. Backend validates JWT on each request
4. Row Level Security (RLS) enforces data access

### Content Safety

- **Input filtering** - Check messages before processing
- **Age-tier filtering** - Appropriate content for children
- **COPPA compliance** - Parental consent for under-13
- **Streaming moderation** - Real-time output checks

### Rate Limiting

- Default: 60 requests per 60 seconds per user
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`

---

## 🧪 Testing

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

---

## 🐛 Troubleshooting

### Common Issues

#### "AttributeError: 'Anthropic' object has no attribute 'proxy'"
```bash
pip install --upgrade "httpx>=0.27.0"
```

#### Database connection errors
```bash
# Check Tiger Postgres connection
psql $TIGER_DATABASE_URL -c "SELECT 1"
```

#### Redis connection refused
```bash
# Verify Redis is running
docker-compose ps
docker-compose up -d redis
```

#### Memory search returns no results
```bash
# Check Qdrant is running and collections exist
curl http://localhost:6333/collections
```

### Logs

```bash
# Backend logs
tail -f /var/log/nicole-api.log

# Worker logs
tail -f /var/log/nicole-worker.log

# Nginx access logs
tail -f /var/log/nginx/nicole-access.log
```

---

## 📊 Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Ready check (includes database)
curl http://localhost:8000/health/ready
```

### Sentry Integration

Set `SENTRY_DSN` in environment to enable error tracking.

---

## 🤝 Contributing

This is a private project for Glen's family. No external contributions accepted.

---

## 📜 License

Private - All Rights Reserved

---

## 👨‍👩‍👧‍👦 Built With Love

Nicole V7 is built to honor the memory of Glen's late wife Nicole, providing the family with an AI companion that remembers, supports, and helps with daily life.

*"Embodies Nicole's spirit: loving, supportive, protective"*

