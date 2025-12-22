# 🎨 Image Generation Dashboard - Comprehensive Test Plan

## ✅ All Critical Fixes Applied

### Priority 1: Critical Blockers (FIXED)
1. ✅ Added `replicate>=0.22.0` and `Pillow>=10.0.0` to requirements.txt
2. ✅ Fixed GZip middleware to exclude SSE streaming endpoints
3. ✅ Implemented Cloudinary upload for ALL models (prevents link rot)

### Priority 2: Code Quality (FIXED)
4. ✅ Deprecated legacy `alphawave_replicate.py`
5. ✅ Updated schema documentation
6. ✅ Verified MCP configuration

---

## 📋 Pre-Testing Setup

### 1. Backend Deployment

```bash
# SSH into droplet
ssh -i SSH-Nicole root@137.184.40.230

# Navigate to backend
cd /root/nicole_api

# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install -r requirements.txt

# Verify installations
python -c "import replicate; print(f'replicate: {replicate.__version__}')"
python -c "from PIL import Image; print('Pillow: OK')"

# Restart services
supervisorctl restart nicole-api
supervisorctl restart nicole-worker
supervisorctl status
```

### 2. Environment Variables Check

```bash
# Verify all required API keys are set
cat /root/nicole_api/.env | grep -E "REPLICATE_API_TOKEN|CLOUDINARY_|GEMINI_|OPENAI_API_KEY|RECRAFT_"
```

Required keys:
- `REPLICATE_API_TOKEN` (for FLUX, Ideogram, Seedream)
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `GEMINI_API_KEY` (for Imagen 3)
- `OPENAI_API_KEY` (for DALL-E 3)
- Recraft via MCP bridge (check MCP .env)

### 3. MCP Bridge Check

```bash
# Check MCP bridge status
cd /root/mcp
docker-compose ps

# Verify Recraft API key in MCP .env
cat .env | grep RECRAFT_API_KEY

# Restart if needed
docker-compose restart
```

### 4. Frontend Deployment

```bash
# Verify Vercel deployment
# Check: https://nicole-assistant.vercel.app/image

# Or deploy manually
cd frontend
npm run build
# Push to trigger Vercel deployment
```

---

## 🧪 Test Suite

### Test 1: Recraft V3 Generation (via MCP)

**Purpose:** Verify MCP bridge integration and Cloudinary upload

**Steps:**
1. Navigate to `/image` dashboard
2. Select model: **Recraft V3**
3. Enter prompt: "Modern tech startup logo, minimalist, blue and white"
4. Set style: "vector_illustration"
5. Set batch: 4 images
6. Click "Generate"

**Expected Results:**
- ✅ Progress bar shows real-time updates (0% → 25% → 50% → 75% → 100%)
- ✅ 4 images appear in slots 1-4
- ✅ Images load from Cloudinary URLs (not Recraft CDN)
- ✅ Images persist in history panel
- ✅ No 403/404 errors after 24 hours

**Check Database:**
```sql
SELECT 
    variant_id, 
    model_key, 
    cdn_url, 
    width, 
    height,
    generation_time_ms,
    cost_usd
FROM image_variants 
WHERE model_key = 'recraft' 
ORDER BY created_at DESC 
LIMIT 4;
```

**Verify:**
- `cdn_url` starts with `https://res.cloudinary.com/`
- `width` and `height` are correct
- `generation_time_ms` is reasonable
- `cost_usd` is calculated

---

### Test 2: FLUX 1.1 Pro Generation (via Replicate)

**Purpose:** Verify Replicate SDK integration and Cloudinary upload

**Steps:**
1. Select model: **FLUX 1.1 Pro**
2. Enter prompt: "Photorealistic portrait of a futuristic AI assistant, cinematic lighting"
3. Set aspect ratio: "16:9"
4. Set guidance: 3.5
5. Set steps: 28
6. Set batch: 2 images
7. Click "Generate"

**Expected Results:**
- ✅ Progress bar shows real-time updates
- ✅ 2 high-quality images appear
- ✅ Images load from Cloudinary URLs (not Replicate CDN)
- ✅ Images persist in history
- ✅ Generation time ~20-40 seconds

**Check Database:**
```sql
SELECT 
    variant_id, 
    model_key, 
    cdn_url, 
    replicate_prediction_id,
    generation_time_ms
FROM image_variants 
WHERE model_key = 'flux_pro' 
ORDER BY created_at DESC 
LIMIT 2;
```

**Verify:**
- `cdn_url` starts with `https://res.cloudinary.com/`
- `replicate_prediction_id` is populated
- Images are 1920x1080 (16:9 aspect)

---

### Test 3: Ideogram V2 Generation (via Replicate)

**Purpose:** Verify text-in-image capabilities and Cloudinary upload

**Steps:**
1. Select model: **Ideogram V2**
2. Enter prompt: "Instagram post with text 'Grace & Grit' in elegant serif font, fitness theme"
3. Set aspect ratio: "1:1"
4. Set style: "Design"
5. Enable magic prompt: "Auto"
6. Set batch: 1 image
7. Click "Generate"

**Expected Results:**
- ✅ Progress bar shows real-time updates
- ✅ Image contains clear, legible text "Grace & Grit"
- ✅ Image loads from Cloudinary URL
- ✅ Image persists in history

**Check Database:**
```sql
SELECT 
    variant_id, 
    model_key, 
    original_prompt,
    enhanced_prompt,
    cdn_url
FROM image_variants 
WHERE model_key = 'ideogram' 
ORDER BY created_at DESC 
LIMIT 1;
```

**Verify:**
- `enhanced_prompt` shows magic prompt enhancement
- Text is visible and legible in generated image

---

### Test 4: Imagen 3 Generation (via Gemini)

**Purpose:** Verify Google Gemini integration and Cloudinary upload

**Steps:**
1. Select model: **Imagen 3**
2. Enter prompt: "Serene mountain landscape at sunset, photorealistic"
3. Set aspect ratio: "16:9"
4. Set batch: 1 image
5. Click "Generate"

**Expected Results:**
- ✅ Progress bar shows real-time updates
- ✅ High-quality photorealistic image appears
- ✅ Image loads from Cloudinary URL
- ✅ Image persists in history
- ✅ Generation time ~10-20 seconds

**Check Database:**
```sql
SELECT 
    variant_id, 
    model_key, 
    cdn_url,
    width,
    height
FROM image_variants 
WHERE model_key = 'imagen3' 
ORDER BY created_at DESC 
LIMIT 1;
```

**Verify:**
- `cdn_url` starts with `https://res.cloudinary.com/`
- Aspect ratio matches request

---

### Test 5: OpenAI DALL-E 3 Generation

**Purpose:** Verify OpenAI integration and Cloudinary upload

**Steps:**
1. Select model: **DALL-E 3**
2. Enter prompt: "Abstract digital art representing artificial intelligence"
3. Set size: "1024x1024"
4. Set quality: "hd"
5. Set batch: 1 image
6. Click "Generate"

**Expected Results:**
- ✅ Progress bar shows real-time updates
- ✅ Artistic image appears
- ✅ Image loads from Cloudinary URL
- ✅ Image persists in history

**Check Database:**
```sql
SELECT 
    variant_id, 
    model_key, 
    cdn_url,
    width,
    height,
    cost_usd
FROM image_variants 
WHERE model_key = 'dall_e_3' 
ORDER BY created_at DESC 
LIMIT 1;
```

---

### Test 6: SSE Streaming Progress

**Purpose:** Verify real-time progress updates work correctly

**Steps:**
1. Open browser DevTools → Network tab
2. Filter for "stream"
3. Select any model and generate
4. Watch for `/images/generate/stream` request

**Expected Results:**
- ✅ Request shows "text/event-stream" content type
- ✅ Response is NOT gzipped
- ✅ Events stream in real-time:
  ```
  data: {"status": "analyzing", "progress": 0}
  data: {"status": "routing", "progress": 10}
  data: {"status": "generating", "progress": 25}
  data: {"status": "generating", "progress": 50}
  data: {"status": "generating", "progress": 75}
  data: {"status": "completed", "progress": 100}
  ```
- ✅ Progress bar updates smoothly (not jumping 0% → 100%)

**Check Logs:**
```bash
# On droplet
tail -f /var/log/supervisor/nicole-api-stdout.log | grep "\[IMAGE\]"
```

**Verify:**
- No GZip compression warnings
- SSE events sent immediately
- No buffering delays

---

### Test 7: History & Persistence

**Purpose:** Verify images persist and load from history

**Steps:**
1. Generate 3-4 images using different models
2. Wait 5 minutes
3. Refresh the page
4. Click "History" tab
5. Click on a past generation

**Expected Results:**
- ✅ All past images appear in history
- ✅ Images load instantly from Cloudinary
- ✅ No 403/404 errors
- ✅ Clicking history item reloads images in slots
- ✅ All metadata visible (model, prompt, time, cost)

**Check Database:**
```sql
SELECT 
    j.job_id,
    j.title,
    j.project,
    COUNT(v.variant_id) as variant_count,
    j.created_at
FROM image_jobs j
LEFT JOIN image_variants v ON j.job_id = v.job_id
GROUP BY j.job_id
ORDER BY j.created_at DESC
LIMIT 10;
```

**Verify:**
- All jobs have correct variant counts
- Jobs are properly linked to variants

---

### Test 8: Multi-Model Comparison

**Purpose:** Verify multi-slot generation works correctly

**Steps:**
1. Enable "Multi-Model" mode
2. Slot 1: Recraft V3
3. Slot 2: FLUX 1.1 Pro
4. Slot 3: Ideogram V2
5. Slot 4: Imagen 3
6. Use same prompt for all: "Futuristic city skyline at night"
7. Click "Generate All"

**Expected Results:**
- ✅ All 4 models generate simultaneously
- ✅ Progress bars update independently
- ✅ Each image reflects model's style
- ✅ All images load from Cloudinary
- ✅ All images persist in history

---

### Test 9: Error Handling

**Purpose:** Verify graceful degradation when APIs fail

**Steps:**
1. Temporarily set invalid API key in .env
2. Attempt generation
3. Restore valid API key
4. Attempt generation again

**Expected Results:**
- ✅ Clear error message shown to user
- ✅ No 500 errors
- ✅ Other models still work
- ✅ Logs show detailed error info
- ✅ Recovery after fixing API key

**Check Logs:**
```bash
tail -f /var/log/supervisor/nicole-api-stderr.log | grep "ERROR"
```

---

### Test 10: Link Rot Prevention (24-Hour Test)

**Purpose:** Verify Cloudinary upload prevents link rot

**Steps:**
1. Generate images using Recraft and FLUX
2. Note the `cdn_url` from database
3. Wait 24 hours
4. Reload the images from history
5. Test direct URL access

**Expected Results:**
- ✅ Images still load after 24 hours
- ✅ No 403 Forbidden errors
- ✅ No 404 Not Found errors
- ✅ Cloudinary URLs remain valid

**Before Fix:**
- Recraft CDN URLs expired after 1-24 hours
- Replicate URLs expired after 1 hour

**After Fix:**
- All images uploaded to Cloudinary
- Cloudinary URLs valid indefinitely

---

## 🔍 Monitoring & Validation

### Real-Time Monitoring

```bash
# Watch API logs
tail -f /var/log/supervisor/nicole-api-stdout.log | grep "\[IMAGE\]"

# Watch error logs
tail -f /var/log/supervisor/nicole-api-stderr.log

# Watch MCP bridge logs
cd /root/mcp && docker-compose logs -f
```

### Database Queries

```sql
-- Check generation stats
SELECT 
    model_key,
    COUNT(*) as total_generations,
    AVG(generation_time_ms) as avg_time_ms,
    SUM(cost_usd) as total_cost,
    MAX(created_at) as last_generation
FROM image_variants
GROUP BY model_key
ORDER BY total_generations DESC;

-- Check for failed generations
SELECT 
    job_id,
    title,
    created_at
FROM image_jobs
WHERE job_id NOT IN (SELECT DISTINCT job_id FROM image_variants);

-- Check Cloudinary adoption rate
SELECT 
    model_key,
    COUNT(*) as total,
    SUM(CASE WHEN cdn_url LIKE '%cloudinary%' THEN 1 ELSE 0 END) as cloudinary_count,
    ROUND(100.0 * SUM(CASE WHEN cdn_url LIKE '%cloudinary%' THEN 1 ELSE 0 END) / COUNT(*), 2) as cloudinary_percent
FROM image_variants
GROUP BY model_key;
```

### Frontend Console Checks

```javascript
// Open browser console
// Check for errors
console.log('Image Generation Errors:', window.__imageErrors || []);

// Check SSE connection
console.log('SSE Status:', window.__sseStatus || 'unknown');

// Check Cloudinary URLs
document.querySelectorAll('img[src*="cloudinary"]').length;
```

---

## ✅ Success Criteria

### Critical (Must Pass)
- [ ] All 5 models generate images successfully
- [ ] SSE streaming shows real-time progress (not buffered)
- [ ] All images upload to Cloudinary (100% adoption)
- [ ] Images persist in history after page refresh
- [ ] No 403/404 errors after 24 hours

### Important (Should Pass)
- [ ] Generation times are reasonable (<60s for most models)
- [ ] Error messages are clear and actionable
- [ ] Multi-model generation works correctly
- [ ] Database records are accurate and complete
- [ ] Costs are calculated correctly

### Nice to Have (Can Improve Later)
- [ ] Progress bars show granular updates (not just 0/50/100)
- [ ] Thumbnail generation for faster history loading
- [ ] Image deduplication based on hash
- [ ] Advanced preset management

---

## 🐛 Known Issues & Workarounds

### Issue 1: Replicate Dependency Missing
**Status:** ✅ FIXED
**Fix:** Added `replicate>=0.22.0` to requirements.txt

### Issue 2: SSE Streaming Buffered by GZip
**Status:** ✅ FIXED
**Fix:** Added image streaming endpoints to GZip exclusions

### Issue 3: Link Rot (Recraft/Replicate URLs)
**Status:** ✅ FIXED
**Fix:** Implemented Cloudinary upload for all models

### Issue 4: Legacy Code Confusion
**Status:** ✅ FIXED
**Fix:** Deprecated `alphawave_replicate.py`

### Issue 5: Schema Documentation Drift
**Status:** ✅ FIXED
**Fix:** Updated `nicole_v7_final_schema.sql`

---

## 📊 Performance Benchmarks

### Expected Generation Times

| Model | Batch Size | Expected Time | Cost per Image |
|-------|------------|---------------|----------------|
| Recraft V3 | 4 | 10-15s | $0.04 |
| FLUX 1.1 Pro | 1 | 20-40s | $0.05 |
| FLUX Schnell | 1 | 5-10s | $0.02 |
| Ideogram V2 | 1 | 15-25s | $0.08 |
| Imagen 3 | 1 | 10-20s | $0.04 |
| DALL-E 3 | 1 | 15-30s | $0.04 |

### Expected Cloudinary Upload Times
- Small images (512x512): 1-2s
- Medium images (1024x1024): 2-4s
- Large images (1920x1080): 3-6s

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [x] All fixes committed and pushed
- [x] Requirements.txt updated
- [x] Schema documentation updated
- [x] Legacy code deprecated
- [ ] Dependencies installed on droplet
- [ ] Services restarted
- [ ] MCP bridge verified

### Post-Deployment
- [ ] Run Test Suite (Tests 1-10)
- [ ] Monitor logs for errors
- [ ] Check database for correct data
- [ ] Verify Cloudinary adoption rate
- [ ] Test from multiple browsers
- [ ] Test from mobile devices

### 24-Hour Follow-Up
- [ ] Verify no link rot (Test 10)
- [ ] Check error rates
- [ ] Review generation costs
- [ ] Analyze performance metrics
- [ ] Gather user feedback

---

## 📞 Support & Troubleshooting

### If Generation Fails

1. **Check API Keys:**
   ```bash
   cat /root/nicole_api/.env | grep -E "REPLICATE|GEMINI|OPENAI"
   ```

2. **Check Service Status:**
   ```bash
   supervisorctl status
   ```

3. **Check Logs:**
   ```bash
   tail -100 /var/log/supervisor/nicole-api-stderr.log
   ```

4. **Restart Services:**
   ```bash
   supervisorctl restart nicole-api
   supervisorctl restart nicole-worker
   ```

### If SSE Streaming Fails

1. **Verify GZip Exclusions:**
   ```bash
   grep "EXCLUDED_PATHS" /root/nicole_api/app/main.py
   ```

2. **Check Nginx Config:**
   ```bash
   cat /etc/nginx/sites-available/nicole | grep gzip
   ```

3. **Test SSE Endpoint:**
   ```bash
   curl -N http://localhost:8000/images/generate/stream
   ```

### If Cloudinary Upload Fails

1. **Check Cloudinary Credentials:**
   ```bash
   cat /root/nicole_api/.env | grep CLOUDINARY
   ```

2. **Test Cloudinary Connection:**
   ```python
   from app.services.alphawave_cloudinary_service import cloudinary_service
   result = cloudinary_service.upload_from_base64("test_data", folder="test")
   print(result)
   ```

---

## 🎯 Next Steps After Testing

1. **If All Tests Pass:**
   - Mark feature as production-ready
   - Update user documentation
   - Announce new capabilities
   - Monitor usage and costs

2. **If Issues Found:**
   - Document issues in detail
   - Prioritize by severity
   - Create fix plan
   - Re-test after fixes

3. **Future Enhancements:**
   - Add Seedream 4.5 model
   - Implement image upscaling
   - Add style transfer
   - Implement batch editing
   - Add image-to-image generation

---

**Test Plan Version:** 1.0  
**Created:** December 19, 2025  
**Status:** Ready for Testing  
**Quality Standard:** Anthropic Engineer Level 🎯


