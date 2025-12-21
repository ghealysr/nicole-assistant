# FAZ CODE - COMPREHENSIVE CLEANUP AUDIT
**Date:** December 21, 2025  
**Status:** Production Quality Review

---

## 🔴 CRITICAL ISSUES

### 1. **Missing Backend Endpoint**
- **Issue:** Frontend calls `/projects/{id}/reset` but backend doesn't have this endpoint
- **Location:** `frontend/src/lib/faz/api.ts:101-107`
- **Impact:** Reset functionality will fail with 404
- **Fix:** Either remove from frontend or implement in backend

### 2. **Unused Component Files (Technical Debt)**
- **`FazCodePanel.tsx`** (1,229 lines) - OLD panel implementation, never imported
- **`LivePreview.tsx`** - Unused preview component  
- **`FazLivePreview.tsx`** - Unused StackBlitz preview
- **`PreviewPane.tsx`** - Duplicate preview component
- **Impact:** ~2,000 lines of dead code, confusing for maintainers
- **Fix:** Delete all unused files

---

## 🟡 MEDIUM PRIORITY ISSUES

### 3. **Inline Components in Workspace Page**
**Location:** `frontend/src/app/(app)/faz/projects/[id]/page.tsx`

**Issues:**
- `PreviewWithFrame` component defined inline (lines ~558-600)
- `generatePreviewFromFiles` function inline (lines ~54-100)
- Makes the file 627 lines (too large)

**Recommendation:**
- Extract `PreviewWithFrame` to `/components/faz/PreviewFrame.tsx`
- Move `generatePreviewFromFiles` to `/lib/faz/preview-utils.ts`

### 4. **Error Handling Gaps**
**Issues:**
- No error boundaries around preview iframe
- No loading states for file operations
- No retry logic for failed WebSocket connections

### 5. **Type Safety Issues**
**Location:** `frontend/src/types/faz.ts`

**Issues:**
- `Architecture` interface has optional `design_tokens` that duplicates `DesignSystem`
- `FazActivity.details` is `Record<string, unknown>` (too loose)
- Missing types for WebSocket message payloads

---

## 🟢 LOW PRIORITY / POLISH

### 6. **Code Organization**
- Workspace page mixes layout, state management, and business logic
- No separation of concerns between UI and data fetching

### 7. **Performance Optimizations Needed**
- Preview iframe reloads on every file change (should debounce)
- File tree doesn't virtualize (will be slow with 100+ files)
- No lazy loading for activities feed

### 8. **Missing Documentation**
- No JSDoc comments on API functions
- No README for Faz Code feature
- No architecture diagram

---

## ✅ WHAT'S WORKING WELL

1. **Type definitions** are comprehensive and match backend schemas
2. **API client** has consistent error handling
3. **WebSocket integration** is clean and functional
4. **Component architecture** (excluding unused files) is well-structured
5. **Routing** is now correctly set up as full-page feature

---

## 📋 CLEANUP CHECKLIST

### Phase 1: Delete Dead Code ✅
- [ ] Delete `FazCodePanel.tsx`
- [ ] Delete `LivePreview.tsx`
- [ ] Delete `FazLivePreview.tsx`
- [ ] Delete `PreviewPane.tsx`
- [ ] Update `components/faz/index.ts` exports

### Phase 2: Fix API Inconsistencies ✅
- [ ] Remove `resetProject` from frontend API (unused feature)
- [ ] Verify all backend endpoints match frontend calls

### Phase 3: Refactor Workspace Page ✅
- [ ] Extract `PreviewFrame` component
- [ ] Create `preview-utils.ts` for HTML generation
- [ ] Split workspace into smaller, focused components

### Phase 4: Improve Error Handling ✅
- [ ] Add error boundary to preview
- [ ] Add loading states to file operations
- [ ] Add retry logic to WebSocket

### Phase 5: Documentation ✅
- [ ] Add JSDoc to all API functions
- [ ] Create Faz Code README
- [ ] Document component props

---

## 🎯 RECOMMENDED EXECUTION ORDER

1. **Delete unused files** (5 min) - Immediate win
2. **Remove reset endpoint call** (2 min) - Prevents errors
3. **Extract inline components** (15 min) - Better maintainability
4. **Add error boundaries** (10 min) - Better UX
5. **Add documentation** (20 min) - Better DX

**Total Estimated Time:** ~1 hour

---

## 📊 METRICS

- **Files to Delete:** 4
- **Lines of Code Reduced:** ~2,000
- **Components to Extract:** 2
- **Functions to Extract:** 1
- **Documentation to Add:** 3 files

---

## 🚀 POST-CLEANUP STATE

After cleanup:
- ✅ Zero dead code
- ✅ All API calls map to real endpoints
- ✅ Components are focused and reusable
- ✅ Better error handling and UX
- ✅ Fully documented codebase
- ✅ Production-ready quality

---

## VERDICT

**Current State:** 7/10 - Functional but with technical debt  
**Post-Cleanup:** 10/10 - Production-grade, maintainable codebase

The core architecture is solid. The issues are all cosmetic/organizational, not fundamental design flaws.

