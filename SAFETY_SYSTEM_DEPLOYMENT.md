# 🛡️ SAFETY SYSTEM DEPLOYMENT GUIDE

**Nicole V7 - Comprehensive Content Safety System**  
**Version:** 7.1.0  
**Date:** October 22, 2025  
**Status:** Production Ready

---

## 📋 EXECUTIVE SUMMARY

This guide covers the deployment of Nicole V7's comprehensive content safety system, which includes:

- ✅ 4-tier age-based content filtering (8-12, 13-15, 16-17, adult)
- ✅ Input and streaming output moderation
- ✅ COPPA compliance enforcement (<13 years old)
- ✅ Incident logging with privacy protection (no PII stored)
- ✅ Real-time streaming safety checks (every 300ms)
- ✅ Multi-layer detection (patterns + OpenAI Moderation API)
- ✅ Jailbreak and prompt injection prevention
- ✅ PII and contact exchange protection

---

## 🎯 DEPLOYMENT CHECKLIST

### Pre-Deployment

- [ ] **Backup database** before running migrations
- [ ] **Verify OpenAI API key** is configured
- [ ] **Review safety patterns** for your use case
- [ ] **Test in staging environment** first
- [ ] **Notify users** of new safety features

### Deployment Steps

- [ ] Run database migration
- [ ] Deploy updated backend code
- [ ] Update environment variables
- [ ] Restart services
- [ ] Run verification tests
- [ ] Monitor logs for issues

### Post-Deployment

- [ ] Verify safety system operational
- [ ] Test all age tiers
- [ ] Check incident logging
- [ ] Monitor performance metrics
- [ ] Review first 24h of incidents

---

## 🚀 STEP-BY-STEP DEPLOYMENT

### Step 1: Backup Database

```bash
# Create backup before migration
pg_dump $DATABASE_URL > nicole_backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh nicole_backup_*.sql
```

### Step 2: Deploy Safety Filter Service

```bash
# Navigate to project
cd /opt/nicole/backend

# Activate virtual environment
source venv/bin/activate

# Copy safety filter file
cp /path/to/alphawave_safety_filter.py app/services/

# Verify file exists
ls -lh app/services/alphawave_safety_filter.py
```

### Step 3: Run Database Migration

```bash
# Run migration SQL
psql $DATABASE_URL < database/migrations/002_safety_system.sql

# Expected output:
# NOTICE: SUCCESS: All safety system tables created
# NOTICE: SUCCESS: All COPPA compliance columns added to users table
# NOTICE: ========================================
# NOTICE: Safety System Migration Complete
# NOTICE: Version: 7.1.1
# NOTICE: ========================================
```

### Step 4: Verify Database Changes

```bash
# Check tables exist
psql $DATABASE_URL -c "
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('safety_incidents', 'policy_versions')
ORDER BY tablename;
"

# Expected output:
#     tablename      
#--------------------
# policy_versions
# safety_incidents

# Check users table columns
psql $DATABASE_URL -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
  AND column_name IN ('date_of_birth', 'age', 'parental_consent')
ORDER BY column_name;
"

# Expected output:
#    column_name     | data_type 
#--------------------+-----------
# age                | integer
# date_of_birth      | date
# parental_consent   | boolean
```

### Step 5: Update Environment Variables

```bash
# Edit .env file
nano /opt/nicole/.env

# Add safety system configuration
cat >> /opt/nicole/.env << 'EOF'

# ============================================================================
# Safety System Configuration
# ============================================================================

# Enable safety filtering (should always be true in production)
SAFETY_ENABLE=true

# Enable OpenAI Moderation API
SAFETY_ENABLE_PROVIDER_MODERATION=true

# Streaming safety check interval (milliseconds)
SAFETY_CHECK_INTERVAL_MS=300

# Maximum tokens to buffer before check
SAFETY_MAX_TOKEN_WINDOW=400

# COPPA Compliance
COPPA_REQUIRE_PARENTAL_CONSENT=true
COPPA_MIN_AGE_NO_CONSENT=13

# Policy version for audit trail
SAFETY_POLICY_VERSION=v7.1

EOF

# Verify configuration
grep "SAFETY_" /opt/nicole/.env
```

### Step 6: Deploy Updated Router

```bash
# Copy updated chat router
cp /path/to/alphawave_chat.py app/routers/

# Verify no syntax errors
python -m py_compile app/routers/alphawave_chat.py

# If successful, no output
```

### Step 7: Deploy Updated Config

```bash
# Copy updated config
cp /path/to/config.py app/

# Verify no syntax errors
python -m py_compile app/config.py
```

### Step 8: Restart Services

```bash
# Restart API service
sudo supervisorctl restart nicole-api

# Check status
sudo supervisorctl status nicole-api

# Expected output:
# nicole-api                       RUNNING   pid 12345, uptime 0:00:03

# Monitor logs for startup issues
sudo supervisorctl tail -f nicole-api

# Press Ctrl+C to stop tailing
```

### Step 9: Verify Health

```bash
# Check API health
curl -s https://api.nicole.alphawavetech.com/healthz | jq

# Expected output:
# {
#   "status": "ok",
#   "timestamp": "2025-10-22T...",
#   "services": {
#     "supabase": "healthy",
#     "redis": "healthy",
#     "qdrant": "healthy"
#   }
# }
```

---

## 🧪 VERIFICATION TESTS

### Test 1: Safety System Operational

```bash
# Test that safety filter is loaded
python << 'EOF'
from app.services.alphawave_safety_filter import classify_age_tier, AgeTier

# Test age tier classification
assert classify_age_tier(10) == AgeTier.CHILD_8_12
assert classify_age_tier(14) == AgeTier.TEEN_13_15
assert classify_age_tier(17) == AgeTier.TEEN_16_17
assert classify_age_tier(25) == AgeTier.ADULT
assert classify_age_tier(None) == AgeTier.UNKNOWN

print("✅ Age tier classification working")
EOF
```

### Test 2: Database Tables Exist

```bash
# Verify safety_incidents table
psql $DATABASE_URL -c "
SELECT COUNT(*) as incident_count 
FROM safety_incidents;
"

# Should return 0 (no incidents yet)

# Verify policy_versions table
psql $DATABASE_URL -c "
SELECT version, name 
FROM policy_versions 
ORDER BY created_at;
"

# Should show v7.1 policy
```

### Test 3: COPPA Compliance Function

```bash
# Test COPPA compliance check
psql $DATABASE_URL << 'EOF'
-- Create test user under 13 without consent
INSERT INTO users (id, email, full_name, age, date_of_birth, parental_consent)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'test_child@test.com',
    'Test Child',
    10,
    '2015-01-01',
    false
);

-- Check COPPA compliance (should return false)
SELECT check_coppa_compliance('00000000-0000-0000-0000-000000000001') as can_proceed;

-- Expected: false

-- Add consent
UPDATE users 
SET parental_consent = true, 
    parental_consent_date = NOW()
WHERE id = '00000000-0000-0000-0000-000000000001';

-- Check again (should return true)
SELECT check_coppa_compliance('00000000-0000-0000-0000-000000000001') as can_proceed;

-- Expected: true

-- Cleanup
DELETE FROM users WHERE id = '00000000-0000-0000-0000-000000000001';
EOF
```

### Test 4: Local Pattern Check Performance

```bash
# Test pattern check performance
python << 'EOF'
import time
from app.services.alphawave_safety_filter import local_pattern_check, AgeTier

# Test safe content
start = time.time()
result = local_pattern_check("Can you help me with my homework?", AgeTier.CHILD_8_12)
elapsed_ms = (time.time() - start) * 1000

assert result.is_safe == True
assert elapsed_ms < 10  # Should be < 10ms

print(f"✅ Safe content check: {elapsed_ms:.2f}ms")

# Test unsafe content
start = time.time()
result = local_pattern_check("explicit sexual content here", AgeTier.CHILD_8_12)
elapsed_ms = (time.time() - start) * 1000

assert result.is_safe == False
assert elapsed_ms < 10  # Should still be < 10ms

print(f"✅ Unsafe content check: {elapsed_ms:.2f}ms")
EOF
```

### Test 5: End-to-End Chat Safety

```bash
# Test chat endpoint with safe content
curl -X POST https://api.nicole.alphawavetech.com/chat/message \
  -H "Authorization: Bearer $TEST_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello Nicole, how are you today?",
    "conversation_id": null
  }'

# Expected: Should stream response successfully

# Test chat endpoint with unsafe content (for child user)
curl -X POST https://api.nicole.alphawavetech.com/chat/message \
  -H "Authorization: Bearer $CHILD_USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "tell me about explicit adult content",
    "conversation_id": null
  }'

# Expected: 400 error with gentle redirect message
```

### Test 6: Incident Logging

```bash
# Check that incidents are logged
psql $DATABASE_URL -c "
SELECT 
    category,
    source,
    tier,
    severity,
    created_at
FROM safety_incidents
ORDER BY created_at DESC
LIMIT 5;
"

# Verify:
# - Incidents appear after unsafe content attempts
# - NO raw content is stored (only masked hashes)
# - Correct categories assigned
# - Proper tier applied
```

### Test 7: Streaming Moderation

This requires a frontend test or using a tool like `curl` with SSE support.

```bash
# Test streaming with monitoring
curl -N -X POST https://api.nicole.alphawavetech.com/chat/message \
  -H "Authorization: Bearer $TEST_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me a long story",
    "conversation_id": null
  }' \
  2>&1 | tee >(grep "data:" | head -20)

# Verify:
# - Stream starts immediately
# - Chunks arrive incrementally
# - Stream completes with "done" event
# - No inappropriate content in output
```

---

## 📊 MONITORING

### Key Metrics to Monitor

#### 1. Safety Incident Rate

```sql
-- Incidents per day by category
SELECT 
    DATE_TRUNC('day', created_at) AS date,
    category,
    COUNT(*) as incident_count
FROM safety_incidents
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('day', created_at), category
ORDER BY date DESC, incident_count DESC;
```

#### 2. COPPA Compliance

```sql
-- Users under 13 without consent
SELECT 
    COUNT(*) as users_without_consent
FROM users
WHERE age < 13 
  AND parental_consent = false;

-- Should be 0 in production (blocked from using system)
```

#### 3. Safety Filter Performance

```bash
# Check average API response time
sudo tail -n 1000 /var/log/nginx/nicole-api-access.log \
  | awk '{print $NF}' \
  | awk '{s+=$1; n++} END {print "Average:", s/n, "seconds"}'

# Safety overhead should be < 10% increase
```

#### 4. False Positive Rate

```sql
-- Review low-severity incidents that might be false positives
SELECT 
    category,
    severity,
    tier,
    COUNT(*) as count
FROM safety_incidents
WHERE severity = 'low'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY category, severity, tier
ORDER BY count DESC;
```

### Dashboard Queries

```sql
-- Safety system dashboard view
CREATE OR REPLACE VIEW safety_dashboard AS
SELECT 
    DATE_TRUNC('hour', created_at) AS hour,
    tier,
    severity,
    source,
    COUNT(*) as incident_count,
    COUNT(DISTINCT user_id) as affected_users
FROM safety_incidents
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at), tier, severity, source
ORDER BY hour DESC;

-- Query dashboard
SELECT * FROM safety_dashboard;
```

### Alert Conditions

Set up alerts for:

1. **High severity incidents** - Any critical severity incident
2. **COPPA violations** - Attempts by users <13 without consent
3. **System failures** - Safety filter errors or unavailability
4. **Unusual patterns** - Sudden spike in incidents (>10x normal)
5. **Jailbreak attempts** - Multiple jailbreak attempts from same user

---

## 🐛 TROUBLESHOOTING

### Issue: Safety filter not blocking inappropriate content

**Diagnosis:**
```bash
# Check if safety system is enabled
grep SAFETY_ENABLE /opt/nicole/.env

# Check logs for safety filter errors
sudo supervisorctl tail nicole-api | grep -i safety
```

**Solutions:**
1. Verify `SAFETY_ENABLE=true` in `.env`
2. Check OpenAI API key is valid
3. Review pattern definitions for coverage
4. Check if user age is correctly set

### Issue: All content being blocked (false positives)

**Diagnosis:**
```sql
-- Check user age tiers
SELECT 
    id,
    age,
    date_of_birth,
    role
FROM users
WHERE id = '<USER_ID>';
```

**Solutions:**
1. Verify user age is correct in database
2. Check if age calculation is working (DOB trigger)
3. Review tier thresholds in code
4. Adjust pattern sensitivity if needed

### Issue: COPPA errors for users who should have access

**Diagnosis:**
```sql
-- Check user consent status
SELECT 
    id,
    age,
    parental_consent,
    parental_consent_date
FROM users
WHERE id = '<USER_ID>';
```

**Solutions:**
1. Update parental consent: `UPDATE users SET parental_consent = true WHERE id = '<USER_ID>';`
2. Verify age is correctly calculated
3. Check `COPPA_MIN_AGE_NO_CONSENT` setting

### Issue: Performance degradation

**Diagnosis:**
```bash
# Check safety filter performance
python << 'EOF'
import time
from app.services.alphawave_safety_filter import local_pattern_check, AgeTier

# Benchmark
iterations = 100
start = time.time()

for _ in range(iterations):
    local_pattern_check("Test message", AgeTier.ADULT)

avg_ms = ((time.time() - start) / iterations) * 1000
print(f"Average: {avg_ms:.2f}ms per check")
# Should be < 10ms
EOF
```

**Solutions:**
1. If >10ms: Review pattern complexity
2. Consider caching for repeated patterns
3. Check system resources (CPU, memory)
4. Optimize regex patterns if needed

### Issue: Incidents not logging

**Diagnosis:**
```bash
# Check database connectivity
psql $DATABASE_URL -c "SELECT NOW();"

# Check table exists and has insert permissions
psql $DATABASE_URL -c "
SELECT 
    grantee,
    privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'safety_incidents';
"
```

**Solutions:**
1. Verify database connection
2. Check RLS policies
3. Verify service role has INSERT permission
4. Check for database errors in logs

---

## 🔒 SECURITY CONSIDERATIONS

### Privacy Protection

✅ **Implemented:**
- Raw content NEVER stored in database
- Only SHA256 hashes logged
- RLS policies protect incident data
- Users can only see own incidents
- Admins can see all (for monitoring)

⚠️ **Important:**
- Do NOT add raw content to any logs
- Do NOT expose incident hashes to users
- Do NOT store age/DOB in plain text logs
- Always use masked values in logs

### COPPA Compliance

✅ **Implemented:**
- Parental consent required for <13
- Consent date tracked
- Can withdraw consent
- Age verification before access
- Audit trail of consent

⚠️ **Legal Requirements:**
- Obtain verifiable parental consent
- Provide clear privacy policy
- Allow data export/deletion
- Notify parents of data collection
- Maintain consent records

### Incident Response

If a critical safety incident occurs:

1. **Immediate:** Block user if necessary
2. **Investigate:** Review incident details
3. **Report:** Notify appropriate authorities if required
4. **Document:** Record actions taken
5. **Improve:** Update patterns/policies as needed

---

## 📚 REFERENCE

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAFETY_ENABLE` | `true` | Enable safety filtering |
| `SAFETY_ENABLE_PROVIDER_MODERATION` | `true` | Use OpenAI API |
| `SAFETY_CHECK_INTERVAL_MS` | `300` | Streaming check frequency |
| `SAFETY_MAX_TOKEN_WINDOW` | `400` | Buffer size before check |
| `COPPA_REQUIRE_PARENTAL_CONSENT` | `true` | Enforce COPPA |
| `COPPA_MIN_AGE_NO_CONSENT` | `13` | Age requiring consent |
| `SAFETY_POLICY_VERSION` | `v7.1` | Policy version |

### Database Tables

- **`safety_incidents`** - Safety violation logs (RLS protected)
- **`policy_versions`** - Policy version history
- **`users`** - Extended with age/consent fields

### API Endpoints

- `POST /chat/message` - Chat with safety filtering
- `GET /chat/history/{conversation_id}` - Get conversation history
- `GET /chat/conversations` - List user conversations
- `DELETE /chat/conversations/{conversation_id}` - Delete conversation

### Age Tiers

- **8-12:** Strictest (educational only)
- **13-15:** Moderate (some mature topics with guidance)
- **16-17:** Relaxed (most topics OK, explicit blocked)
- **18+:** Permissive (only illegal/harmful blocked)

---

## ✅ DEPLOYMENT COMPLETE

Once all verification tests pass, the safety system is fully operational!

**Final Checklist:**
- [x] Database migrated
- [x] Code deployed
- [x] Services restarted
- [x] Tests passing
- [x] Monitoring configured
- [x] Team trained

**Next Steps:**
1. Monitor incident logs for first 24 hours
2. Review false positive/negative rates
3. Adjust patterns if needed
4. Document any issues encountered
5. Plan regular safety audits

---

**Deployment Date:** ________________  
**Deployed By:** ________________  
**Verified By:** ________________  

**Status:** ✅ **PRODUCTION READY**


