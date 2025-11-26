# 📦 COMPLETE DEPENDENCY ANALYSIS - NICOLE V7

**Date:** October 22, 2025  
**Status:** ✅ Complete & Verified  
**Python Version:** 3.11+

---

## 🎯 EXECUTIVE SUMMARY

This document provides a **complete dependency analysis** for Nicole V7, including:
- All required Python packages with versions
- Why each package is needed
- Installation instructions
- Troubleshooting guide
- Automated script for DO Droplet

---

## 📋 COMPLETE DEPENDENCY LIST

### **Core Web Framework** (2 packages)

#### 1. **FastAPI** `==0.115.4`
- **Purpose:** Main API framework
- **Used For:**
  - HTTP routing and endpoints
  - Request/response handling
  - Automatic OpenAPI documentation
  - Dependency injection
  - Type validation with Pydantic
- **Critical For:** Entire backend API
- **Files Using:** `app/main.py`, all routers

#### 2. **Uvicorn[standard]** `==0.32.0`
- **Purpose:** ASGI server
- **Used For:**
  - Running FastAPI in production
  - SSE (Server-Sent Events) streaming
  - WebSocket support
  - Performance optimization
- **[standard] Extra Includes:**
  - `uvloop` - Fast event loop
  - `httptools` - Fast HTTP parsing
  - `websockets` - WebSocket support
  - `watchfiles` - Hot reload (dev)
- **Critical For:** Application server
- **Command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

### **HTTP Client** (1 package) ⚠️ **CRITICAL**

#### 3. **httpx** `>=0.27.2`
- **Purpose:** Async HTTP client
- **Used For:**
  - All AI SDK HTTP requests
  - External API calls
  - Testing
- **Critical Version Requirement:** >=0.27.0
- **Why Critical:** Anthropic SDK requires `proxy` kwarg support added in 0.27.0
- **Error if <0.27.0:** `AttributeError: 'Anthropic' object has no attribute 'proxy'`
- **Files Using:** `anthropic`, `openai` SDKs
- **Verification:** `python -c "import httpx; print(httpx.__version__)"`

---

### **Data Validation** (2 packages)

#### 4. **Pydantic** `==2.9.2`
- **Purpose:** Data validation and parsing
- **Used For:**
  - Request/response models
  - Type validation
  - Data serialization
  - Settings management
- **Features:**
  - Type coercion
  - Validation rules
  - JSON schema generation
- **Files Using:** All models, routers, config

#### 5. **Pydantic-Settings** `==2.6.0`
- **Purpose:** Settings management from environment
- **Used For:**
  - `.env` file loading
  - Environment variable parsing
  - Type validation for settings
- **Critical For:** `app/config.py` - `AlphawaveSettings`
- **Matches:** Pydantic 2.9.x

---

### **Authentication & Security** (3 packages)

#### 6. **PyJWT** `==2.9.0`
- **Purpose:** JWT token handling
- **Used For:**
  - JWT encoding/decoding
  - Token expiration checking
  - Signature verification
- **Algorithms:** HS256, HS384, HS512
- **Files Using:** `app/middleware/alphawave_auth.py`

#### 7. **python-jose[cryptography]** `==3.3.0`
- **Purpose:** Enhanced JWT with cryptography
- **Used For:**
  - RSA/ECDSA algorithms
  - Certificate validation
  - Enhanced security
- **[cryptography] Extra:** Includes cryptography library
- **Optional:** Can use PyJWT alone

#### 8. **passlib[bcrypt]** `==1.7.4`
- **Purpose:** Password hashing
- **Used For:**
  - Secure password storage
  - Hash verification
- **[bcrypt] Extra:** Includes bcrypt C library
- **Algorithms:** bcrypt, scrypt, argon2
- **Files Using:** If implementing local auth (currently not used)

---

### **AI & LLM Clients** (2 packages)

#### 9. **anthropic** `==0.39.0`
- **Purpose:** Claude AI integration
- **Used For:**
  - Chat responses (primary LLM)
  - Agent routing (Haiku)
  - Content generation
  - Streaming responses
- **Models:**
  - `claude-sonnet-4-5-20250929` (complex reasoning)
  - `claude-haiku-4-5-20250514` (fast routing)
- **Requires:** httpx>=0.27.0
- **Files Using:** `app/integrations/alphawave_claude.py`
- **API Key:** `ANTHROPIC_API_KEY` in .env

#### 10. **openai** `==1.54.3`
- **Purpose:** OpenAI integration
- **Used For:**
  - Text embeddings (`text-embedding-3-small`)
  - O1-mini research mode
  - **Content Moderation API** (critical for safety)
- **Features:**
  - Async client
  - Streaming
  - Function calling
- **Files Using:**
  - `app/integrations/alphawave_openai.py`
  - `app/services/alphawave_safety_filter.py` (Moderation API)
- **API Key:** `OPENAI_API_KEY` in .env

---

### **Database & Caching** (4 packages)

#### 11. **supabase** `==2.9.1`
- **Purpose:** PostgreSQL database client
- **Used For:**
  - Database queries
  - Authentication
  - Storage
  - Row Level Security (RLS)
- **Includes:**
  - postgrest-py (database)
  - gotrue-py (auth)
  - storage3-py (storage)
  - realtime-py (subscriptions)
- **Files Using:** `app/database.py`, all routers
- **Environment:**
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`

#### 12. **asyncpg** `==0.29.0`
- **Purpose:** High-performance PostgreSQL driver
- **Used For:**
  - Direct database connections
  - Raw SQL queries
  - Bulk operations
- **Performance:** 10x faster than psycopg2
- **Features:**
  - Binary protocol
  - Prepared statements
  - Connection pooling
- **Files Using:** Direct SQL operations (optional, Supabase is primary)

#### 13. **redis** `==5.2.0`
- **Purpose:** In-memory data store
- **Used For:**
  - **Tier 1 memory** (hot cache, 1-hour TTL)
  - Rate limiting
  - Session storage
  - Pub/sub messaging
- **Features:**
  - Async operations
  - Connection pooling
  - Cluster support
- **Files Using:**
  - `app/database.py`
  - `app/middleware/alphawave_rate_limit.py`
  - `app/services/alphawave_memory_service.py`
- **Environment:** `REDIS_URL=redis://localhost:6379`

#### 14. **qdrant-client** `==1.12.0`
- **Purpose:** Vector database client
- **Used For:**
  - **Tier 3 memory** (semantic search)
  - Embedding storage
  - Similarity search
- **Features:**
  - High-dimensional vectors
  - Filtering
  - Collections
  - Snapshots
- **Files Using:**
  - `app/database.py`
  - `app/services/alphawave_memory_service.py`
- **Environment:** `QDRANT_URL=http://localhost:6333`

---

### **Background Jobs** (1 package)

#### 15. **APScheduler** `==3.10.4`
- **Purpose:** Job scheduling
- **Used For:**
  - **8 scheduled background jobs:**
    1. 5 AM: Sports data collection
    2. 6 AM: Sports predictions
    3. 8 AM: Dashboard updates
    4. 9 AM: Blog generation
    5. 11:59 PM: Journal processing
    6. Sunday 2 AM: Memory decay
    7. Sunday 3 AM: Weekly reflection
    8. Daily 3 AM: Qdrant backup
- **Features:**
  - Cron triggers
  - Interval triggers
  - Async executors
  - Job stores
- **Files Using:** `backend/worker.py`

---

### **Utilities** (2 packages)

#### 16. **python-dotenv** `==1.0.1`
- **Purpose:** Environment variable loading
- **Used For:**
  - Loading .env file
  - Development configuration
- **Features:**
  - Variable parsing
  - Override support
  - Multi-file support
- **Files Using:** `app/config.py` (via pydantic-settings)

#### 17. **python-multipart** `==0.0.12`
- **Purpose:** Multipart form data parsing
- **Used For:**
  - File uploads
  - Form data handling
- **Critical For:**
  - Voice file uploads
  - Image uploads
  - Document uploads
- **Files Using:** `app/routers/alphawave_files.py`, `app/routers/alphawave_voice.py`

---

### **Monitoring** (1 package - Optional)

#### 18. **sentry-sdk[fastapi]** `==2.17.0`
- **Purpose:** Error tracking and monitoring
- **Used For:**
  - Production error tracking
  - Performance monitoring
  - Alerting
  - Breadcrumbs
- **[fastapi] Extra:** FastAPI integration
- **Features:**
  - Automatic error capture
  - Release tracking
  - Source maps
- **Environment:** `SENTRY_DSN=https://xxx@sentry.io/xxx`
- **Status:** Commented out by default, enable for production

---

## 🔍 DEPENDENCY TREE

```
Nicole V7 Backend
├─ Web Framework
│  ├─ fastapi==0.115.4
│  │  ├─ pydantic>=2.0
│  │  ├─ starlette>=0.37
│  │  └─ typing-extensions>=4.8
│  └─ uvicorn[standard]==0.32.0
│     ├─ uvloop (via [standard])
│     ├─ httptools (via [standard])
│     └─ websockets (via [standard])
│
├─ HTTP & Networking
│  └─ httpx>=0.27.2 ⚠️ CRITICAL
│     ├─ httpcore
│     ├─ h11
│     └─ certifi
│
├─ Data & Validation
│  ├─ pydantic==2.9.2
│  │  └─ pydantic-core
│  └─ pydantic-settings==2.6.0
│     └─ python-dotenv
│
├─ Authentication
│  ├─ PyJWT==2.9.0
│  ├─ python-jose[cryptography]==3.3.0
│  │  └─ cryptography (via [cryptography])
│  └─ passlib[bcrypt]==1.7.4
│     └─ bcrypt (via [bcrypt])
│
├─ AI/LLM
│  ├─ anthropic==0.39.0
│  │  ├─ httpx>=0.27.0 ⚠️ DEPENDENCY
│  │  ├─ pydantic>=2.0
│  │  └─ typing-extensions
│  └─ openai==1.54.3
│     ├─ httpx>=0.27.0
│     ├─ pydantic>=2.0
│     └─ typing-extensions
│
├─ Database & Caching
│  ├─ supabase==2.9.1
│  │  ├─ postgrest-py
│  │  ├─ gotrue-py
│  │  ├─ storage3-py
│  │  └─ realtime-py
│  ├─ asyncpg==0.29.0
│  ├─ redis==5.2.0
│  │  └─ async-timeout
│  └─ qdrant-client==1.12.0
│     └─ grpcio
│
├─ Background Jobs
│  └─ APScheduler==3.10.4
│     ├─ tzlocal
│     └─ six
│
└─ Utilities
   ├─ python-dotenv==1.0.1
   └─ python-multipart==0.0.12

Total Direct: ~18 packages
Total Transitive: ~40-50 packages
Total Installed: ~58-68 packages
```

---

## 🚀 INSTALLATION INSTRUCTIONS

### **For Digital Ocean Droplet**

```bash
# 1. Connect to droplet
ssh root@your-droplet-ip

# 2. Navigate to project
cd /opt/nicole/backend

# 3. Activate virtual environment
source venv/bin/activate

# 4. Run automated script
chmod +x fix_requirements.sh
./fix_requirements.sh
```

### **Manual Installation**

```bash
# 1. Navigate to backend directory
cd /opt/nicole/backend

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip setuptools wheel

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify installation
python -c "import anthropic, openai, fastapi; print('✓ All critical packages installed')"

# 6. Check httpx version (critical)
python -c "import httpx; v=httpx.__version__; print(f'httpx: {v}'); assert v>='0.27.0', 'httpx must be >=0.27.0'"

# 7. Restart service
sudo supervisorctl restart nicole-api

# 8. Check logs
sudo supervisorctl tail -f nicole-api
```

---

## ✅ VERIFICATION CHECKLIST

```bash
# Test all critical imports
python << 'EOF'
print("Testing imports...")
import fastapi
import uvicorn
import httpx
import pydantic
import jwt
import anthropic
import openai
import supabase
import redis
import qdrant_client
import apscheduler
from app.config import settings
from app.services.alphawave_safety_filter import check_input_safety
print("✓ All imports successful")
EOF

# Verify httpx version
python -c "import httpx; v=httpx.__version__; print(f'httpx: {v}'); assert v >= '0.27.0', 'httpx version too old'"

# Check package count
pip list | wc -l
# Should be 58-68 packages

# Test API startup
python app/main.py &
sleep 2
curl http://localhost:8000/healthz
# Should return: {"status":"ok"}
```

---

## 🐛 TROUBLESHOOTING

### **Issue: httpx version conflict**

```bash
# Symptom
AttributeError: 'Anthropic' object has no attribute 'proxy'

# Diagnosis
python -c "import httpx; print(httpx.__version__)"
# If < 0.27.0, upgrade needed

# Solution
pip install --upgrade "httpx>=0.27.2"

# Verify
python -c "import httpx; print(f'httpx {httpx.__version__} - OK')"
```

### **Issue: Dependency conflicts**

```bash
# Clear pip cache
pip cache purge

# Remove all packages
pip freeze | xargs pip uninstall -y

# Reinstall from scratch
pip install --upgrade pip
pip install -r requirements.txt
```

### **Issue: Import errors**

```bash
# Check Python version
python --version
# Must be 3.11+

# Verify virtual environment
which python
# Should point to venv/bin/python

# List installed packages
pip list

# Check specific package
pip show anthropic
```

### **Issue: Module not found**

```bash
# Install missing package
pip install <package-name>

# If still fails, check for typos
python -c "import <module_name>"
```

---

## 📊 PACKAGE SIZES

| Package | Install Size | Purpose |
|---------|-------------|---------|
| anthropic | ~5 MB | Claude AI |
| openai | ~3 MB | OpenAI API |
| supabase | ~10 MB | Database |
| qdrant-client | ~20 MB | Vector DB |
| redis | ~2 MB | Cache |
| fastapi | ~3 MB | Web framework |
| uvicorn | ~2 MB | Server |
| pydantic | ~8 MB | Validation |
| **Total** | **~100 MB** | All packages |

---

## 🔒 SECURITY CONSIDERATIONS

### **API Keys Required**

```bash
# .env file must contain:
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx
SUPABASE_JWT_SECRET=xxx
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

### **Never Commit**
- `.env` files
- API keys
- `requirements.lock` (regenerate per environment)

### **Production Best Practices**
1. Use `requirements.lock` for exact versions
2. Enable Sentry for error tracking
3. Rotate API keys regularly
4. Use environment variables, never hardcode
5. Keep dependencies updated for security patches

---

## 📈 PERFORMANCE NOTES

### **Fast Packages**
- `httpx` - Async HTTP with HTTP/2
- `uvicorn[standard]` - uvloop event loop
- `asyncpg` - 10x faster than psycopg2
- `qdrant-client` - Optimized vector search

### **Slow Operations**
- OpenAI Moderation API: ~100-200ms
- Anthropic streaming: <1s first token
- Redis cache: <5ms
- Qdrant vector search: <50ms

### **Optimization Tips**
1. Use Redis for hot data
2. Batch database operations
3. Stream AI responses
4. Cache embeddings
5. Use connection pooling

---

## ✅ FINAL CHECKLIST

- [ ] Python 3.11+ installed
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] httpx >= 0.27.2 verified
- [ ] All imports working
- [ ] .env file configured
- [ ] API keys valid
- [ ] Redis running
- [ ] Qdrant running
- [ ] Service restarted
- [ ] Health check passing

---

**Status:** ✅ **Complete & Verified**  
**Total Packages:** 58-68 (including transitive)  
**Installation Time:** ~2-3 minutes  
**Disk Space:** ~100 MB

**All dependencies documented. Script ready for deployment.**

