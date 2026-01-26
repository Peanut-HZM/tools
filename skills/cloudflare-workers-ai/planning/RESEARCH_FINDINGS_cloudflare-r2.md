# Community Knowledge Research: cloudflare-r2

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-r2/SKILL.md
**Packages Researched**: @cloudflare/workers-types@4.20260109.0, wrangler@4.59.2
**Official Repo**: cloudflare/workers-sdk
**Time Window**: May 2024 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 14 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 5 |
| Recommended to Add | 9 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: R2 list() Doesn't Return Metadata by Default

**Trust Score**: TIER 1 - Official (GitHub Issue #10870)
**Source**: [GitHub Issue #10870](https://github.com/cloudflare/workers-sdk/issues/10870)
**Date**: 2025-10-03
**Verified**: Yes - Resolved, documented behavior
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `list()` method returns empty `customMetadata` and `httpMetadata` objects by default, even when metadata is stored on objects. This is intentional behavior but commonly trips up developers who expect metadata to be included automatically like with `get()` and `head()`.

**Reproduction**:
```typescript
// Upload with metadata
await env.MY_BUCKET.put('file.txt', data, {
  httpMetadata: { contentType: 'text/plain' },
  customMetadata: { userId: '123' }
});

// List without include parameter
const { objects } = await env.MY_BUCKET.list();
console.log(objects[0].httpMetadata); // undefined
console.log(objects[0].customMetadata); // undefined
```

**Solution/Workaround**:
```typescript
// Must explicitly request metadata in list options
const { objects } = await env.MY_BUCKET.list({
  include: ['httpMetadata', 'customMetadata']
});

console.log(objects[0].httpMetadata); // Now populated
console.log(objects[0].customMetadata); // Now populated
```

**Official Status**:
- [x] Documented behavior (intentional design)
- [x] Requires opt-in via `include` parameter

**Cross-Reference**:
- Official docs: https://developers.cloudflare.com/r2/api/workers/workers-api-reference/#r2listoptions
- Related to: SKILL.md line 106-116 (list() method) - needs update

---

### Finding 1.2: Local R2 Delete Operations Don't Cleanup Blob Files

**Trust Score**: TIER 1 - Official (GitHub Issue #10795)
**Source**: [GitHub Issue #10795](https://github.com/cloudflare/workers-sdk/issues/10795)
**Date**: 2025-09-28
**Verified**: Acknowledged by Cloudflare team
**Impact**: LOW (local dev only)
**Already in Skill**: No

**Description**:
When using `wrangler dev` with local R2 buckets, DELETE operations succeed from the API perspective but blob files remain in `.wrangler/state/v3/r2/{bucket-name}/blobs/`, causing local storage to grow indefinitely during development.

**Reproduction**:
```typescript
// 1. Create and run local dev
// wrangler dev

// 2. Upload file
await env.MY_BUCKET.put('test.txt', 'Hello World');

// 3. Delete file
await env.MY_BUCKET.delete('test.txt');

// 4. Check filesystem - file still exists in:
// .wrangler/state/v3/r2/{bucket-name}/blobs/{hash}
```

**Solution/Workaround**:
```bash
# Manual cleanup of local R2 storage
rm -rf .wrangler/state/v3/r2/

# Or use remote R2 for development to avoid issue
wrangler dev --remote
```

**Official Status**:
- [ ] Issue closed without fix (low priority)
- [ ] Workaround: Use --remote or manual cleanup
- [ ] Production not affected

**Cross-Reference**:
- Local dev specific issue
- Add to "Development Best Practices" section

---

### Finding 1.3: R2 CORS Configuration Format Confusion

**Trust Score**: TIER 1 - Official (GitHub Issue #10076)
**Source**: [GitHub Issue #10076](https://github.com/cloudflare/workers-sdk/issues/10076)
**Date**: 2025-07-26
**Verified**: Yes - Team acknowledged error messages need improvement
**Impact**: MEDIUM
**Already in Skill**: Partially (CORS section exists but doesn't warn about this)

**Description**:
The wrangler CLI CORS file format differs from the dashboard UI format, causing confusing errors. CLI expects `rules` wrapper with different field structure (`allowed` object) while dashboard accepts flat structure.

**Reproduction**:
```json
// Dashboard format (works in UI, fails in CLI)
[{
  "AllowedOrigins": ["https://example.com"],
  "AllowedMethods": ["GET", "PUT"],
  "AllowedHeaders": ["*"],
  "ExposeHeaders": ["ETag"],
  "MaxAgeSeconds": 3600
}]
```

```bash
wrangler r2 bucket cors set my-bucket --file cors-config.json
# Error: The CORS configuration file must contain a 'rules' array
```

**Solution/Workaround**:
```json
// Correct CLI format
{
  "rules": [{
    "allowed": {
      "origins": ["https://www.example.com"],
      "methods": ["GET", "PUT"],
      "headers": ["Content-Type", "Authorization"]
    },
    "exposeHeaders": ["ETag", "Content-Length"],
    "maxAgeSeconds": 8640
  }]
}
```

**Official Status**:
- [x] Known issue - error messages being improved
- [x] CLI format documented at: https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/cors/methods/update/

**Cross-Reference**:
- Related to: SKILL.md lines 184-201 (CORS Configuration section)
- Should add warning about CLI vs Dashboard format difference

---

### Finding 1.4: API Tokens Require Admin Permissions for Wrangler Upload

**Trust Score**: TIER 1 - Official (GitHub Issue #9235)
**Source**: [GitHub Issue #9235](https://github.com/cloudflare/workers-sdk/issues/9235)
**Date**: 2025-05-13
**Verified**: Yes - Intended behavior confirmed by Cloudflare
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When uploading to R2 via wrangler CLI, "Object Read & Write" API token permissions are insufficient and return 403 errors. Admin-level "Admin Read & Write" permissions are required for wrangler operations, despite the name suggesting object-level permissions would suffice.

**Reproduction**:
```bash
# Create API token with "R2: Object Read & Write" permission
export CLOUDFLARE_API_TOKEN="token_with_object_readwrite"

# Attempt upload
wrangler r2 object put my-bucket/file.txt --file=./file.txt --remote

# Result: ✘ [ERROR] Failed to fetch - 403: Forbidden
```

**Solution/Workaround**:
```bash
# Create API token with "R2: Admin Read & Write" permission instead
# Then same command works
wrangler r2 object put my-bucket/file.txt --file=./file.txt --remote
```

**Official Status**:
- [x] Intended behavior - wrangler requires admin permissions
- [x] "Object Read & Write" is for S3 API direct access, not wrangler

**Cross-Reference**:
- Should add to "Presigned URLs" section (line 149-181) as alternative for non-admin access
- Add warning about token permissions in setup section

---

### Finding 1.5: Major R2 Outages in 2025 Due to Operational Issues

**Trust Score**: TIER 1 - Official (Cloudflare Blog)
**Source**: [Feb 6 Incident](https://blog.cloudflare.com/cloudflare-incident-on-february-6-2025/), [Mar 21 Incident](https://blog.cloudflare.com/cloudflare-incident-march-21-2025/)
**Date**: February 6, 2025 and March 21, 2025
**Verified**: Yes - Official incident reports
**Impact**: HIGH (production outages)
**Already in Skill**: No

**Description**:
Two significant R2 outages occurred in Q1 2025:

1. **February 6, 2025**: 59-minute global outage where all R2 operations failed due to accidental disabling of production R2 Gateway during abuse remediation.

2. **March 21, 2025**: 1 hour 7 minutes of errors (100% write failures, 35% read failures) due to credentials being deployed to dev instance instead of production during rotation.

**Impact on Users**:
- HTTP 500 responses for all operations (Feb)
- 5xx errors for writes and significant read failures (Mar)
- Services depending on R2 also affected

**Solution/Workaround**:
```typescript
// Implement exponential backoff retry for transient R2 errors
async function r2WithRetry<T>(
  operation: () => Promise<T>,
  maxRetries = 5
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error: any) {
      const message = error.message;

      // Retry on 5xx errors (platform issues)
      const isRetryable =
        message.includes('500') ||
        message.includes('502') ||
        message.includes('503') ||
        message.includes('504') ||
        message.includes('temporarily unavailable');

      if (!isRetryable || attempt === maxRetries - 1) {
        throw error;
      }

      // Exponential backoff: 1s, 2s, 4s, 8s, 16s
      const delay = Math.min(1000 * Math.pow(2, attempt), 16000);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw new Error('Max retries exceeded');
}

// Usage
const object = await r2WithRetry(() =>
  env.MY_BUCKET.get('important-file.txt')
);
```

**Official Status**:
- [x] Both incidents resolved
- [x] Root causes identified (human operational errors)
- [x] Process improvements implemented

**Cross-Reference**:
- Related to: SKILL.md lines 254-289 (Error Handling and Retry Logic)
- Current retry logic should be enhanced with longer backoff for 5xx errors
- Add note about platform reliability in production considerations

---

### Finding 1.6: Bucket Limit Increased to 1 Million

**Trust Score**: TIER 1 - Official (Cloudflare Docs)
**Source**: [R2 Limits Documentation](https://developers.cloudflare.com/r2/platform/limits/)
**Date**: 2025 (documented)
**Verified**: Yes - Official documentation
**Impact**: LOW (most users won't hit limit)
**Already in Skill**: No

**Description**:
The maximum number of buckets per account increased from 1,000 to 1,000,000. This change benefits multi-tenant applications that need per-user or per-tenant buckets.

**Previous Limit**:
- 1,000 buckets per account (required support ticket for more)

**New Limit**:
- 1,000,000 buckets per account (contact support if more needed)

**Solution/Workaround**:
```typescript
// Multi-tenant pattern now viable with high bucket limits
// Option 1: Per-tenant buckets (now scalable to 1M tenants)
const bucketName = `tenant-${tenantId}`;
const bucket = env[bucketName]; // Dynamic binding

// Option 2: Still prefer key prefixing for most use cases
await env.MY_BUCKET.put(`tenants/${tenantId}/file.txt`, data);
```

**Official Status**:
- [x] Production change - documented in official limits
- [x] No breaking changes, just increased ceiling

**Cross-Reference**:
- Should add note in "Best Practices" about choosing per-tenant buckets vs key prefixing
- SKILL.md line 315-337 (Best Practices Summary)

---

### Finding 1.7: R2.dev Domain Has Variable Rate Limiting and Throttling

**Trust Score**: TIER 1 - Official (Cloudflare Docs)
**Source**: [R2 Limits Documentation](https://developers.cloudflare.com/r2/platform/limits/)
**Date**: Documented in 2024-2025
**Verified**: Yes - Official documentation
**Impact**: HIGH (production usage)
**Already in Skill**: No

**Description**:
The `r2.dev` subdomain for public bucket access is NOT intended for production use. It has:
- Variable rate limiting (unspecified threshold)
- Bandwidth throttling
- No SLA or performance guarantees

**Reproduction**:
```typescript
// Using r2.dev endpoint (NOT for production)
const publicUrl = `https://${bucketName}.${accountId}.r2.cloudflarestorage.com/${key}`;
// This endpoint will be rate limited at "hundreds of requests/second"
// You'll receive 429 Too Many Requests responses
```

**Solution/Workaround**:
```typescript
// Production: Use custom domain instead
// 1. Connect custom domain to bucket in dashboard
// 2. Use custom domain for all public access
const productionUrl = `https://cdn.example.com/${key}`;

// Benefits:
// - No rate limiting beyond account limits
// - Cloudflare Cache support
// - Custom cache rules via Workers
// - Full CDN features
```

**Official Status**:
- [x] Documented behavior - r2.dev is for testing only
- [x] Custom domains required for production

**Cross-Reference**:
- Related to: SKILL.md line 382 (Public Buckets documentation link)
- Should add prominent warning in setup section about r2.dev limitations
- Already mentions custom domains for presigned URLs, should expand to all public access

---

### Finding 1.8: Concurrent Writes to Same Object Name Are Rate Limited

**Trust Score**: TIER 1 - Official (Cloudflare Docs)
**Source**: [R2 Limits Documentation](https://developers.cloudflare.com/r2/platform/limits/)
**Date**: Documented in 2024-2025
**Verified**: Yes - Official documentation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
High-frequency concurrent writes to the same object key will trigger HTTP 429 rate limiting. This affects append-heavy workloads or hot-key scenarios.

**Reproduction**:
```typescript
// Multiple Workers writing to same key rapidly
async function logToSharedFile(env: Env, logEntry: string) {
  // This pattern will trigger 429 if many Workers do it simultaneously
  const existing = await env.LOGS.get('global-log.txt');
  const content = (await existing?.text()) || '';

  await env.LOGS.put('global-log.txt', content + logEntry);
  // ❌ High write frequency to same key = 429 errors
}
```

**Solution/Workaround**:
```typescript
// Option 1: Shard by timestamp or ID (distribute writes)
async function logWithSharding(env: Env, logEntry: string) {
  const timestamp = Date.now();
  const shard = Math.floor(timestamp / 60000); // 1-minute shards

  await env.LOGS.put(`logs/${shard}.txt`, logEntry, {
    customMetadata: { timestamp: timestamp.toString() }
  });
  // ✅ Different keys = no rate limiting
}

// Option 2: Use Durable Objects for append operations
// (Durable Objects can handle high-frequency updates to same state)

// Option 3: Use Queues + batch processing
// Buffer writes and batch them with unique keys
```

**Official Status**:
- [x] Documented limitation
- [x] Workaround: Shard writes or use Durable Objects

**Cross-Reference**:
- Add to "Performance Optimization" section (line 291-313)
- Add to "Known Issues Prevented" table (line 340-350)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Presigned URL Domain Requirements

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Ruan Martinelli Blog](https://ruanmartinelli.com/blog/cloudflare-r2-pre-signed-urls/), [Cloudflare Community](https://community.cloudflare.com/t/create-pre-signed-urls-for-r2-in-worker/753608)
**Date**: 2024-2025
**Verified**: Cross-referenced with community discussions
**Impact**: MEDIUM
**Already in Skill**: Partially (presigned URLs covered, but not this specific gotcha)

**Description**:
Presigned URLs only work with the S3 API domain (`{account}.r2.cloudflarestorage.com`) and **cannot** be used with custom domains. This is commonly misunderstood and causes configuration errors.

**Reproduction**:
```typescript
// ❌ WRONG - Presigned URLs don't work with custom domains
const url = new URL(`https://cdn.example.com/${filename}`);
const signed = await r2Client.sign(
  new Request(url, { method: 'PUT' }),
  { aws: { signQuery: true } }
);
// This URL won't work for direct upload

// ✅ CORRECT - Must use R2 storage domain
const url = new URL(
  `https://${accountId}.r2.cloudflarestorage.com/${filename}`
);
const signed = await r2Client.sign(
  new Request(url, { method: 'PUT' }),
  { aws: { signQuery: true } }
);
```

**Solution/Workaround**:
```typescript
// For uploads: Use S3 domain with presigned URLs
// For downloads: Custom domains work (no signing needed for public)

// Pattern: Upload via presigned to S3 domain, serve via custom domain
async function generateUploadUrl(filename: string) {
  // Upload to S3 domain
  const uploadUrl = new URL(
    `https://${accountId}.r2.cloudflarestorage.com/${filename}`
  );
  const signed = await r2Client.sign(
    new Request(uploadUrl, { method: 'PUT' }),
    { aws: { signQuery: true } }
  );

  return {
    uploadUrl: signed.url, // For client upload
    publicUrl: `https://cdn.example.com/${filename}` // For serving
  };
}
```

**Community Validation**:
- Multiple blog posts confirm this behavior
- Community discussions corroborate
- Official docs don't explicitly state this limitation

**Cross-Reference**:
- Related to: SKILL.md lines 149-181 (Presigned URLs section)
- Should add explicit warning about domain requirements

---

### Finding 2.2: Custom Domain CORS Handling

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Medium Article by Michael Esteban](https://mikeesto.medium.com/pre-signed-urls-cors-on-cloudflare-r2-c90d43370dc4)
**Date**: 2024-2025
**Verified**: Cross-referenced with official CORS docs
**Impact**: MEDIUM
**Already in Skill**: Partially (CORS mentioned but not custom domain specifics)

**Description**:
When using custom domains with R2, CORS configuration still applies to the underlying R2 bucket, but can be further controlled via Cloudflare Cache/CDN settings. This dual-layer CORS handling can be confusing.

**Solution/Workaround**:
```typescript
// Bucket CORS (applies to all access methods)
// Set via dashboard or API
{
  "rules": [{
    "allowed": {
      "origins": ["https://app.example.com"],
      "methods": ["GET", "PUT"],
      "headers": ["Content-Type"]
    },
    "maxAgeSeconds": 3600
  }]
}

// Additional CORS via Transform Rules on custom domain
// Dashboard → Rules → Transform Rules → Modify Response Header
// Add: Access-Control-Allow-Origin: https://app.example.com

// Order of CORS evaluation:
// 1. R2 bucket CORS (if presigned URL or direct R2 access)
// 2. Transform Rules CORS (if via custom domain)
```

**Community Validation**:
- Multiple sources discuss this pattern
- Works for production use cases
- Recommended over r2.dev domain

**Cross-Reference**:
- Related to: SKILL.md lines 184-201 (CORS Configuration)
- Should add note about custom domain CORS layer

---

### Finding 2.3: Local Dev Remote R2 Access Can Be Unreliable

**Trust Score**: TIER 2 - Community Reports
**Source**: [GitHub Issue #8868](https://github.com/cloudflare/workers-sdk/issues/8868)
**Date**: 2025-04-09
**Verified**: Multiple users report similar issues
**Impact**: LOW (workaround available)
**Already in Skill**: No

**Description**:
When using `wrangler dev --remote` to access remote R2 buckets, `.get()` operations can return undefined/empty objects despite `.put()` working correctly. This appears to be intermittent.

**Reproduction**:
```typescript
// wrangler dev --remote
export default {
  async fetch(request, env, ctx) {
    // Put works
    await env.BUCKET.put("test.txt", "Hello");

    // Get returns undefined or empty object
    const obj = await env.BUCKET.get("test.txt");
    console.log(obj); // undefined or missing body

    // Works fine when deployed or with local buckets
  }
}
```

**Solution/Workaround**:
```typescript
// Option 1: Don't use --remote for R2 during development
// Use local buckets instead
wrangler dev  // No --remote flag

// Option 2: Deploy to preview environment for testing
wrangler deploy --env preview

// Option 3: If must use --remote, add retry logic
async function safeGet(bucket: R2Bucket, key: string) {
  for (let i = 0; i < 3; i++) {
    const obj = await bucket.get(key);
    if (obj && obj.body) return obj;
    await new Promise(r => setTimeout(r, 1000));
  }
  throw new Error('Failed to get object after retries');
}
```

**Community Validation**:
- GitHub issue closed without resolution
- Workaround recommended by community
- Not critical since local dev works

**Cross-Reference**:
- Add to "Development Best Practices" or troubleshooting section
- Related to Finding 1.2 about local R2 issues

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: DeleteObjects Batch Limit of 1000 Can Be Exceeded in Error

**Trust Score**: TIER 3 - Documented but edge case
**Source**: [Cloudflare R2 Limits](https://developers.cloudflare.com/r2/platform/limits/)
**Date**: 2024-2025
**Verified**: Official docs confirm 1000 limit
**Impact**: LOW
**Already in Skill**: Yes (line 103)

**Description**:
The skill documents the 1000-object batch delete limit, but doesn't explicitly show what happens when you exceed it or how to chunk properly for large deletes.

**Solution**:
```typescript
// Helper function for chunked deletes (not in current skill)
async function deleteMany(
  bucket: R2Bucket,
  keys: string[]
): Promise<void> {
  // Chunk into batches of 1000
  for (let i = 0; i < keys.length; i += 1000) {
    const chunk = keys.slice(i, i + 1000);
    await bucket.delete(chunk);
  }
}

// Usage
const allKeys = ['key1', 'key2', /* ... 5000 keys */];
await deleteMany(env.MY_BUCKET, allKeys);
```

**Consensus Evidence**:
- Official docs specify 1000 limit
- Skill mentions it but no helper implementation
- Common pattern in production

**Recommendation**: Add helper function to skill's "Common Patterns" section

---

### Finding 3.2: Object Lifecycle Rules Limited to 1000 Rules

**Trust Score**: TIER 3 - Official Docs
**Source**: [R2 Object Lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
**Date**: 2024-2025
**Verified**: Yes - Official documentation
**Impact**: LOW (most users won't hit limit)
**Already in Skill**: No

**Description**:
R2 object lifecycle rules have a maximum of 1000 rules per bucket. This can be a constraint for complex lifecycle policies.

**Solution**:
```typescript
// Instead of per-key rules, use prefix-based rules
// ❌ BAD: One rule per customer (hits 1000 limit at 1000 customers)
{
  id: 'customer-1-expiry',
  filter: { key_regex: '^customer-1/.*' },
  expiration_days: 90
}
// ... x 1000 customers

// ✅ GOOD: Use broader prefix rules
{
  id: 'all-temp-files',
  filter: { key_prefix: 'temp/' },
  expiration_days: 7
}
{
  id: 'all-logs',
  filter: { key_prefix: 'logs/' },
  expiration_days: 90
}
```

**Recommendation**: Add to skill if lifecycle rules are documented (currently not in skill)

---

### Finding 3.3: Dashboard Redesign Improved Bucket Settings Discoverability

**Trust Score**: TIER 3 - Official Release Notes
**Source**: [R2 Release Notes](https://developers.cloudflare.com/r2/platform/release-notes/)
**Date**: September 2025
**Verified**: Yes - Official changelog
**Impact**: LOW (UI change only)
**Already in Skill**: No

**Description**:
September 2025 dashboard redesign centralized bucket settings and improved documentation discoverability. Previously, some settings like CORS were harder to find.

**Cross-Reference**:
- SKILL.md mentions dashboard configuration at line 186 but doesn't note recent UI improvements
- Could add note about current UI layout being redesigned in Sep 2025

**Recommendation**: Update any dashboard navigation instructions if they reference old UI

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| CORS errors in browser | Known Issues #1 (line 344) | Fully covered |
| Files download as binary | Known Issues #2 (line 345) | Fully covered |
| Presigned URL expiry | Known Issues #3 (line 346) | Fully covered |
| Multipart upload limits | Known Issues #4 (line 347) | Fully covered |
| Bulk delete limits | Known Issues #5 (line 348) | Fully covered with delete([]) syntax at line 103 |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 list() metadata opt-in | Quick Start + list() examples (line 106) | Add include parameter to examples, add Known Issue |
| 1.4 API token permissions | Presigned URLs section (line 149) | Add warning about Admin vs Object permissions |
| 1.7 r2.dev rate limiting | Best Practices (line 315) + Setup | Add prominent WARNING about r2.dev not for production |
| 1.8 Concurrent write rate limits | Performance Optimization (line 291) + Known Issues | Add sharding pattern and Known Issue #7 |
| 1.5 Platform outages | Error Handling (line 254) | Enhance retry logic for 5xx errors, add longer backoff |

### Priority 2: Enhance Existing Content (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 CORS format confusion | CORS Configuration (line 184) | Add CLI vs Dashboard format comparison |
| 1.6 Bucket limit increase | Best Practices or Architecture section | Add note about 1M bucket limit for multi-tenant patterns |
| 2.1 Presigned URL domains | Presigned URLs (line 149) | Add explicit warning about S3 domain requirement |
| 2.2 Custom domain CORS | CORS Configuration (line 184) | Add section on dual-layer CORS with custom domains |

### Priority 3: Development Notes (TIER 1-2, Low Priority)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.2 Local delete cleanup | Development section (new) | Add note about local blob accumulation |
| 2.3 Remote R2 unreliable | Development section (new) | Add troubleshooting note about --remote issues |

### Priority 4: Consider Adding (TIER 3)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 3.1 Chunked delete helper | Common Patterns (new section) | Add helper function for large deletes |
| 3.2 Lifecycle rule limit | Add if lifecycle section created | Currently not documented in skill |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "r2" + bug label (closed, 2025) | 28 | 8 |
| "r2 edge case OR gotcha" | 0 | 0 |
| "r2 multipart OR presigned OR cors" | 0 | 0 |
| "r2 metadata OR checksum" | 0 | 0 |
| "r2 bucket" issues | 50 | 6 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| cloudflare r2 gotcha 2024-2025 | 0 | N/A |
| cloudflare r2 presigned url 2024-2025 | 0 | N/A |
| cloudflare r2 multipart 2024-2025 | 0 | N/A |

**Note**: Very limited Stack Overflow activity for R2. Most community discussion happens in Cloudflare Community forums and GitHub issues.

### Other Sources

| Source | Notes |
|--------|-------|
| [Cloudflare Blog - Incidents](https://blog.cloudflare.com/) | 2 major outage reports (Feb/Mar 2025) |
| [R2 Official Docs](https://developers.cloudflare.com/r2/) | Limits, release notes, troubleshooting |
| [Cloudflare Community Forums](https://community.cloudflare.com/) | Multiple threads on presigned URLs, CORS, custom domains |
| [Ruan Martinelli Blog](https://ruanmartinelli.com/blog/cloudflare-r2-pre-signed-urls/) | Presigned URL domain requirements |
| [Michael Esteban Medium](https://mikeesto.medium.com/pre-signed-urls-cors-on-cloudflare-r2-c90d43370dc4) | CORS with custom domains |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `WebSearch` for Stack Overflow, blogs, community forums
- `WebFetch` for official documentation

**Limitations**:
- Very limited Stack Overflow activity for R2 (most discussion on Cloudflare Community)
- Some GitHub issues closed without reproduction, limiting detail
- Local dev issues hard to verify without reproduction repos
- Platform outage details from official incident reports only

**Time Spent**: ~25 minutes

**Search Coverage**:
- GitHub: Comprehensive (2024-2026)
- Stack Overflow: Limited results (minimal community activity)
- Official Docs: Comprehensive (limits, release notes, troubleshooting)
- Community Forums: Sampled (found via WebSearch)
- Blog Posts: Found 2 high-quality technical posts

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify Finding 1.1 list() include parameter still required in latest workers-types
- Cross-reference Finding 1.7 r2.dev limitations against current official limits docs
- Validate Finding 1.8 concurrent write rate limiting is still documented behavior

**For api-method-checker**:
- Verify `list({ include: ['httpMetadata', 'customMetadata'] })` syntax in latest R2 API
- Confirm delete([array]) batch method accepts up to 1000 keys

**For code-example-validator**:
- Validate chunked delete helper in Finding 3.1
- Test enhanced retry logic with 5xx errors from Finding 1.5
- Verify sharding pattern in Finding 1.8

---

## Integration Guide

### Adding Critical Findings to SKILL.md

#### 1. Update list() Examples (Finding 1.1)

```markdown
// In "Core Methods" section, update list() example:

// list() - List objects
const listed = await env.MY_BUCKET.list({
  prefix: 'images/',
  limit: 100,
  cursor: cursor,
  delimiter: '/',
  include: ['httpMetadata', 'customMetadata'],  // ← ADD THIS
});

for (const object of listed.objects) {
  console.log(`${object.key}: ${object.size} bytes`);
  console.log(object.httpMetadata?.contentType);  // ← Now populated
  console.log(object.customMetadata);             // ← Now populated
}
```

#### 2. Add New Known Issue #7 (Finding 1.1)

```markdown
| Issue #7 | **list() metadata missing** | Metadata not returned | Use `include: ['httpMetadata', 'customMetadata']` parameter |
```

#### 3. Add Prominent Warning (Finding 1.7)

```markdown
## ⚠️ CRITICAL: R2.dev Domain Is NOT for Production

The `{bucket}.{account}.r2.cloudflarestorage.com` domain has:
- ❌ Variable rate limiting (starts at ~hundreds req/s)
- ❌ Bandwidth throttling
- ❌ No SLA or performance guarantees

**For production**: ALWAYS use custom domains via:
1. Dashboard → R2 → Bucket → Settings → Custom Domains
2. Benefits: No rate limits, Cloudflare Cache, custom rules

**r2.dev is for testing/development only.**
```

#### 4. Enhance Retry Logic (Finding 1.5)

```typescript
// In "Retry Logic" section, update delays for 5xx errors:

// Exponential backoff for platform errors (5xx)
const is5xxError =
  message.includes('500') ||
  message.includes('502') ||
  message.includes('503');

// Use longer backoff for platform issues: 1s, 2s, 4s, 8s, 16s
const delay = is5xxError
  ? Math.min(1000 * Math.pow(2, attempt), 16000)
  : Math.min(1000 * Math.pow(2, attempt), 5000);
```

#### 5. Add Token Permissions Warning (Finding 1.4)

```markdown
## Wrangler CLI Token Requirements

⚠️ Wrangler requires **Admin Read & Write** permissions, not Object Read & Write.

When creating API tokens for wrangler operations:
- ✅ Use: R2 → Admin Read & Write
- ❌ Don't use: R2 → Object Read & Write (causes 403 errors)

**Object Read & Write** is for S3 API direct access only.
```

---

**Research Completed**: 2026-01-20 14:45 PST
**Next Research Due**: After next major R2 feature release or Q2 2026 (whichever comes first)
**Follow-up Check**: Monitor cloudflare/workers-sdk for R2-related issues monthly
