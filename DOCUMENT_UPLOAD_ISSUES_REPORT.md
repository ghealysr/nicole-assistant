# Document Upload & Analysis System - Forensic Report
**Date:** December 10, 2025  
**Scope:** Complete review of document upload, processing, chunking, and storage pipeline  
**Status:** 🔴 **CRITICAL - System Non-Functional**

---

## Executive Summary

The document upload and analysis system is **completely broken** due to multiple critical schema mismatches between the database tables and the service code. Documents **cannot be uploaded, stored, or analyzed** until these issues are resolved.

**Impact:**
- ❌ All document uploads will **fail immediately** with SQL errors
- ❌ No documents can be processed, chunked, or embedded
- ❌ Memory Dashboard "Documents" tab will always be empty
- ❌ Nicole cannot analyze or remember uploaded files

---

## Critical Issues Found

### 🔴 Issue 1: `uploaded_files` Table Schema Mismatch

**Location:** `backend/app/services/alphawave_document_service.py:159-170`

**Problem:** Service code attempts to insert into columns that don't exist in the database schema.

**Service Code Attempts:**
```sql
INSERT INTO uploaded_files (
    user_id, file_name, file_path, file_type, file_size, upload_source, created_at
) VALUES ($1, $2, $3, $4, $5, $6, NOW())
```

**Actual Database Schema** (`001_complete_tiger_schema.sql:215-231`):
```sql
CREATE TABLE uploaded_files (
    file_id BIGINT,
    user_id BIGINT,
    filename TEXT NOT NULL,           -- Service uses: file_name ❌
    original_filename TEXT NOT NULL,  -- Service doesn't provide ❌
    file_type TEXT NOT NULL,          -- ✅ Matches
    file_size BIGINT NOT NULL,        -- ✅ Matches
    storage_url TEXT NOT NULL,        -- Service uses: file_path ❌
    cdn_url TEXT,
    thumbnail_url TEXT,
    checksum TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending',  -- Service doesn't provide ❌
    processing_error TEXT,
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- Service uses: created_at ❌
    processed_at TIMESTAMPTZ
);
```

**Columns Mismatched:**
1. `file_name` → Should be `filename`
2. `file_path` → Should be `storage_url`
3. `upload_source` → Column doesn't exist (should be in metadata?)
4. `created_at` → Should be `uploaded_at`
5. Missing required field: `original_filename`
6. Missing required field: `storage_url` (NOT NULL constraint)

**Result:** `INSERT` will fail with PostgreSQL error `column "file_name" does not exist`

---

### 🔴 Issue 2: `document_repository` Table - Primary Key Mismatch

**Location:** `backend/app/services/alphawave_document_service.py:176-186`

**Problem:** Service uses `doc_id` but schema defines `document_id` as the primary key.

**Service Code:**
```python
doc_row = await db.fetchrow(
    """
    INSERT INTO document_repository (
        user_id, file_id, title, doc_type, created_at, updated_at
    ) VALUES ($1, $2, $3, $4, NOW(), NOW())
    RETURNING doc_id
    """,
    ...
)
doc_id = doc_row["doc_id"]
```

**Actual Database Schema** (`001_complete_tiger_schema.sql:237-251`):
```sql
CREATE TABLE document_repository (
    document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- NOT doc_id ❌
    user_id BIGINT,
    file_id BIGINT,
    document_type TEXT NOT NULL,  -- Service uses: doc_type ❌
    title TEXT,
    extracted_text TEXT,
    extracted_entities JSONB DEFAULT '{}',
    page_count INTEGER,
    language TEXT DEFAULT 'en',
    summary TEXT,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- ✅ Matches
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()   -- ✅ Matches
);
```

**Columns Mismatched:**
1. Primary key: `doc_id` → Should be `document_id`
2. `doc_type` → Should be `document_type`

**Result:** Query will fail with `column "doc_id" does not exist`

---

### 🔴 Issue 3: `document_chunks` Table - Multiple Mismatches

**Location:** `backend/app/services/alphawave_document_service.py:679-687`

**Problem:** Service uses different column names and misses required fields.

**Service Code:**
```sql
INSERT INTO document_chunks (
    doc_id, chunk_index, content, embedding, created_at
) VALUES ($1, $2, $3, $4, NOW())
```

**Actual Database Schema** (`001_complete_tiger_schema.sql:257-267`):
```sql
CREATE TABLE document_chunks (
    chunk_id BIGINT,
    document_id BIGINT NOT NULL,  -- Service uses: doc_id ❌
    user_id BIGINT NOT NULL,      -- Service doesn't provide ❌
    chunk_index INTEGER NOT NULL,  -- ✅ Matches
    chunk_text TEXT NOT NULL,      -- Service uses: content ❌
    embedding VECTOR(1536),        -- ✅ Matches
    page_number INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- ✅ Matches
);
```

**Columns Mismatched:**
1. `doc_id` → Should be `document_id`
2. `content` → Should be `chunk_text`
3. Missing required field: `user_id` (NOT NULL constraint)

**Result:** `INSERT` will fail with multiple column errors

---

### 🔴 Issue 4: Document Retrieval Queries - Field Name Mismatches

**Location:** Multiple locations in `alphawave_document_service.py`

**Problem:** All SELECT queries reference `doc_id` which doesn't exist.

**Examples:**
1. Line 238: `WHERE doc_id = $2` → Should be `document_id`
2. Line 787: `JOIN document_repository dr ON dr.doc_id = dc.doc_id` → Should be `document_id`
3. Line 869: `WHERE dr.doc_id = $1` → Should be `document_id`
4. Line 898: `dr.doc_id` → Should be `document_id`

**Result:** All document listing, retrieval, and search operations will fail

---

### 🟡 Issue 5: API Router Expecting Wrong Field Names

**Location:** `backend/app/routers/alphawave_documents.py`

**Problem:** Router returns `doc_id` but service now needs to return `document_id`.

**Current Code (Line 344-356):**
```python
return DocumentDetailResponse(
    id=document["doc_id"],  # ❌ Should be document_id
    title=document.get("title", "Untitled"),
    ...
)
```

---

### 🟡 Issue 6: Frontend Expects `doc_id` in API Response

**Location:** `frontend/src/lib/hooks/useMemoryDashboardData.ts`

**Current Mapping (Line 48):**
```typescript
documents: documentsData.documents.map((d: Record<string, unknown>) => ({
  doc_id: d.doc_id as number,  // Backend will now return document_id
  ...
}))
```

---

## Impact Analysis

### Severity: 🔴 **P0 - System Down**

**What's Broken:**
1. ✅ Frontend upload UI → Works (uploads to `/documents/upload`)
2. ❌ Backend document insert → **FAILS** (SQL errors)
3. ❌ Document processing → **NEVER STARTS** (insert fails first)
4. ❌ Text extraction → **NEVER RUNS** (insert fails first)
5. ❌ Chunking & embedding → **NEVER RUNS** (insert fails first)
6. ❌ Memory creation → **NEVER RUNS** (insert fails first)
7. ❌ Document listing → **FAILS** (queries use wrong fields)
8. ❌ Document search → **FAILS** (queries use wrong fields)

### User Experience:
- User uploads a file
- Frontend shows "Processing..." spinner
- Backend returns 500 Internal Server Error
- Frontend shows "Upload failed" error
- No document is stored
- Memory Dashboard shows "No documents uploaded yet"

---

## Root Cause

**The schema in `001_complete_tiger_schema.sql` was designed with standard SQL naming conventions:**
- `document_id` (full word, standard)
- `filename` (single word, compact)
- `uploaded_at` (timestamp suffix)

**But the service code was written assuming different conventions:**
- `doc_id` (abbreviated)
- `file_name` (underscore separated)
- `created_at` (generic timestamp)

**This indicates:**
1. Schema and service were written by different people or at different times
2. No integration testing was performed
3. No documents have been successfully uploaded since deployment

---

## Required Fixes

### Option A: Update Service Code to Match Schema (RECOMMENDED)

**Pros:**
- Schema follows SQL best practices
- No database migration required
- Safer (no data loss risk)

**Cons:**
- More code changes required
- Need to update service, router, and frontend

**Files to Modify:**
1. `backend/app/services/alphawave_document_service.py` (20+ changes)
2. `backend/app/routers/alphawave_documents.py` (5 changes)
3. `frontend/src/lib/hooks/useMemoryDashboardData.ts` (2 changes)
4. `frontend/src/components/memory/AlphawaveMemoryDashboard.tsx` (minor)

---

### Option B: Update Schema to Match Service Code

**Pros:**
- Less code changes
- Service code stays as-is

**Cons:**
- Requires database migration on production
- Risk of data loss if documents exist
- Non-standard SQL naming

**Required Migration:**
```sql
-- Rename columns in uploaded_files
ALTER TABLE uploaded_files RENAME COLUMN filename TO file_name;
ALTER TABLE uploaded_files RENAME COLUMN storage_url TO file_path;
ALTER TABLE uploaded_files RENAME COLUMN uploaded_at TO created_at;
ALTER TABLE uploaded_files ADD COLUMN upload_source TEXT;
ALTER TABLE uploaded_files ALTER COLUMN original_filename DROP NOT NULL;

-- Rename columns in document_repository
ALTER TABLE document_repository RENAME COLUMN document_id TO doc_id;
ALTER TABLE document_repository RENAME COLUMN document_type TO doc_type;

-- Rename columns in document_chunks
ALTER TABLE document_chunks RENAME COLUMN document_id TO doc_id;
ALTER TABLE document_chunks RENAME COLUMN chunk_text TO content;
ALTER TABLE document_chunks ALTER COLUMN user_id DROP NOT NULL;

-- Update all foreign key references
... (complex cascade updates)
```

---

## Recommended Action Plan

### Phase 1: Fix Service Code (2-3 hours)
1. Update `alphawave_document_service.py` to use correct column names
2. Fix all SQL queries to use `document_id` instead of `doc_id`
3. Fix uploaded_files INSERT to match schema
4. Add `user_id` to document_chunks INSERT

### Phase 2: Fix API Layer (30 minutes)
1. Update `alphawave_documents.py` router to use `document_id`
2. Ensure response models match database fields

### Phase 3: Fix Frontend (30 minutes)
1. Update `useMemoryDashboardData.ts` to expect `document_id`
2. Update `AlphawaveMemoryDashboard.tsx` if needed

### Phase 4: Testing (1 hour)
1. Test PDF upload
2. Test image upload with OCR
3. Test text file upload
4. Verify chunking and embedding
5. Verify memory creation
6. Test document listing
7. Test document search

### Phase 5: Production Deployment (30 minutes)
1. Deploy backend changes
2. Deploy frontend changes
3. Test on production with real file

---

## Testing Checklist

After fixes are applied, verify:

- [ ] Upload PDF document → Success, no SQL errors
- [ ] Upload image file → Success, OCR runs
- [ ] Upload text file → Success, processed immediately
- [ ] Check database: `SELECT * FROM uploaded_files WHERE user_id = 1;`
- [ ] Check database: `SELECT * FROM document_repository WHERE user_id = 1;`
- [ ] Check database: `SELECT COUNT(*) FROM document_chunks WHERE document_id = <doc_id>;`
- [ ] Check database: `SELECT COUNT(*) FROM memory_entries WHERE memory_type = 'fact' AND context LIKE '%document%';`
- [ ] Memory Dashboard shows documents count > 0
- [ ] Documents tab shows uploaded files
- [ ] Click document → shows summary and key points

---

## Additional Observations

### Missing Features (Not Bugs):
1. **No file storage implementation** - Service generates `file_path` but doesn't actually store bytes to disk/S3
2. **No Azure credentials check** - Service will fail silently if Azure keys are missing
3. **No progress updates** - Frontend shows "Processing..." indefinitely
4. **No retry logic** - If Azure times out, no retry
5. **No thumbnail generation** - Images uploaded but thumbnails not created

### Performance Concerns:
1. **Synchronous processing** - Upload endpoint blocks until document fully processed (can take 60s+ for PDFs)
2. **No queue** - Should use background worker (Celery/RQ) for document processing
3. **No rate limiting** - User can upload unlimited files simultaneously

---

## Conclusion

The document upload system is **architecturally sound** but **completely non-functional** due to schema mismatches. The code quality is high, but it was never integration tested with the actual database.

**Recommended Path:** Fix service code to match schema (Option A). This is the safest and most maintainable approach.

**Estimated Time to Fix:** 4-5 hours for complete implementation and testing.

**Priority:** P0 - Should be fixed immediately as it's a core feature that's completely broken.

