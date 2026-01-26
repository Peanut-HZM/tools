# Community Knowledge Research: Vercel Blob

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/vercel-blob/SKILL.md
**Packages Researched**: @vercel/blob@2.0.0
**Official Repo**: vercel/storage
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 11 |
| TIER 1 (Official) | 4 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 3 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 2 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Client Upload Token Expiration for Large Files

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #443](https://github.com/vercel/storage/issues/443) - Verified by Maintainer
**Date**: 2023-10-27 (Closed, solution documented)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Client upload tokens expire by default after 30 seconds. For large files (>100MB), the upload may take longer than 30 seconds to transfer, causing the token to expire before the file is fully uploaded and validated. This results in an "Access denied, please provide a valid token" error.

**Reproduction**:
```typescript
// Large file upload fails with default token expiration
const jsonResponse = await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      maximumSizeInBytes: 200 * 1024 * 1024, // 200MB
      // validUntil not set - defaults to 30 seconds
    };
  },
});
```

**Solution/Workaround**:
```typescript
// Increase token expiration for large files
const jsonResponse = await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      maximumSizeInBytes: 200 * 1024 * 1024,
      validUntil: Date.now() + 300000, // 5 minutes for large files
    };
  },
});
```

**Official Status**:
- [x] Documented behavior
- [x] Known issue, workaround required
- [x] Fixed by adding `validUntil` parameter

**Cross-Reference**:
- Official documentation: https://vercel.com/docs/storage/vercel-blob/using-blob-sdk#onbeforegeneratetoken
- Maintainer comment confirms buffering entire body before validation

---

### Finding 1.2: Breaking Change in v2.0.0 - onUploadCompleted Callback URL

**Trust Score**: TIER 1 - Official
**Source**: [Release Notes @vercel/blob@2.0.0](https://github.com/vercel/storage/releases/tag/%40vercel/blob%402.0.0)
**Date**: 2025-09-16
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
v2.0.0 introduced a breaking change for `onUploadCompleted` callbacks when NOT hosted on Vercel. Previously, the callback URL was inferred from `location.href` on the client side, which posed a security risk (browser could redirect callback to different website). Now, when not using Vercel system environment variables, you must explicitly provide `callbackUrl` in `onBeforeGenerateToken`.

**Reproduction**:
```typescript
// Pre-v2.0.0: Works but insecure
await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return { /* no callbackUrl needed */ };
  },
  onUploadCompleted: async ({ blob, tokenPayload }) => {
    // This callback fires
  },
});

// Post-v2.0.0: Callback won't fire without callbackUrl (non-Vercel hosting)
```

**Solution/Workaround**:
```typescript
// v2.0.0+: Explicitly provide callbackUrl for non-Vercel hosting
await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      callbackUrl: 'https://example.com', // Required for non-Vercel hosting
    };
  },
  onUploadCompleted: async ({ blob, tokenPayload }) => {
    // Callback now works
  },
});

// For local development with ngrok
// Set environment variable:
// VERCEL_BLOB_CALLBACK_URL=https://abc123.ngrok-free.app
```

**Official Status**:
- [x] Breaking change in v2.0.0
- [x] Documented behavior
- [x] Security improvement (prevents redirect attacks)

**Cross-Reference**:
- Official docs: https://vercel.com/docs/storage/vercel-blob/client-upload#onuploadcompleted-callback-behavior
- When hosted on Vercel: Auto-inferred from `VERCEL_BRANCH_URL`, `VERCEL_URL`, or `VERCEL_PROJECT_PRODUCTION_URL`

---

### Finding 1.3: ReadableStream Upload Not Supported in Firefox

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #881](https://github.com/vercel/storage/issues/881)
**Date**: 2025-09-30
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The TypeScript interface for `put()` and `upload()` accepts `ReadableStream` as a body type, but Firefox does not support `ReadableStream` as a fetch body. This causes stream uploads to never complete in Firefox, despite being documented as a supported type.

**Reproduction**:
```typescript
// Works in Chrome/Edge, hangs in Firefox
const stream = new ReadableStream({
  start(controller) {
    controller.enqueue(new Uint8Array([...]));
    controller.close();
  }
});

await put('file.bin', stream, { access: 'public' }); // Never completes in Firefox
```

**Solution/Workaround**:
```typescript
// Convert stream to Blob or ArrayBuffer for cross-browser support
const chunks: Uint8Array[] = [];
const reader = stream.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  chunks.push(value);
}
const blob = new Blob(chunks);
await put('file.bin', blob, { access: 'public' });
```

**Official Status**:
- [x] Known issue
- [ ] Type definition should be updated to reflect browser limitations
- [x] Workaround required for Firefox support

**Cross-Reference**:
- Browser compatibility: ReadableStream as fetch body is not supported in Firefox
- Maintainer comment suggests removing ReadableStream from type interface

---

### Finding 1.4: Pathname Cannot Be Modified in onBeforeGenerateToken

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #863](https://github.com/vercel/storage/issues/863)
**Date**: 2025-06-17
**Verified**: Yes by Maintainer (vvo)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `pathname` parameter received in `onBeforeGenerateToken` cannot be changed. It's set at the `upload(pathname, ...)` time on the client side. `onBeforeGenerateToken` can only validate the pathname or reject the upload, but cannot override the destination path.

**Reproduction**:
```typescript
// Client uploads to user-provided path
await upload('user-uploads/my-file.jpg', file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
});

// Server tries to override pathname - DOESN'T WORK
await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      pathname: `secure/${userId}/file.jpg`, // ❌ Ignored!
    };
  },
});
```

**Solution/Workaround**:
```typescript
// Use clientPayload to pass metadata, validate pathname on server
// Client
await upload(`uploads/${Date.now()}-${file.name}`, file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
  clientPayload: JSON.stringify({ userId: '123' }),
});

// Server validates pathname matches expected pattern
await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname, clientPayload) => {
    const { userId } = JSON.parse(clientPayload || '{}');

    // Validate pathname starts with expected prefix
    if (!pathname.startsWith(`uploads/`)) {
      throw new Error('Invalid upload path');
    }

    return {
      allowedContentTypes: ['image/jpeg', 'image/png'],
      tokenPayload: JSON.stringify({ userId }), // Pass to onUploadCompleted
    };
  },
});
```

**Official Status**:
- [x] Known limitation
- [x] Future enhancement planned
- [x] Workaround: Client-side pathname construction with server-side validation

**Cross-Reference**:
- Maintainer (vvo) comment: "pathname property cannot be set as a response of onBeforeGenerateToken"
- Alternative: Use `addRandomSuffix: true` for automatic unique paths

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: 4.5MB Server-Side Upload Limit (Vercel Serverless Functions)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Payload CMS Discussion #7569](https://github.com/payloadcms/payload/discussions/7569), [Medium Article](https://medium.com/@jpnreddy25/how-to-bypass-vercels-4-5mb-body-size-limit-for-serverless-functions-using-supabase-09610d8ca387)
**Date**: 2024-2025
**Verified**: Cross-referenced with official Vercel limits
**Impact**: HIGH
**Already in Skill**: Partially covered as Issue #8

**Description**:
Vercel serverless functions have a hard 4.5MB request body size limit. When uploading files via `put()` in a server action/API route, files larger than 4.5MB will fail. This is NOT a Vercel Blob limitation but a Vercel platform limitation. This contradicts the common expectation that Blob supports up to 500MB (which it does for client uploads).

**Community Validation**:
- Multiple users confirm across Payload CMS, Vercel Community forums
- Medium article with 500+ views documenting workarounds
- Official Vercel docs confirm 4.5MB limit

**Solution/Workaround**:
```typescript
// ❌ Fails for files >4.5MB (serverless function limit)
export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('file') as File;
  await put(file.name, file, { access: 'public' }); // Fails at 4.5MB
}

// ✅ Use client upload for files >4.5MB
// Client
const blob = await upload(file.name, file, {
  access: 'public',
  handleUploadUrl: '/api/upload/token',
});

// Server just generates token (no file in request body)
export async function POST(request: Request) {
  const body = await request.json();
  return NextResponse.json(await handleUpload({ body, request, ... }));
}
```

**Recommendation**: Expand Issue #8 to explicitly mention 4.5MB server-side vs 500MB client-side distinction.

---

### Finding 2.2: Multipart Upload Minimum Chunk Size (5MB)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Official Docs](https://vercel.com/docs/storage/vercel-blob/using-blob-sdk#manual), [Community Discussions](https://community.vercel.com/t/4-5-mb-payload-limit/10500)
**Date**: 2024-2025
**Verified**: Official documentation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using manual multipart uploads with `uploadPart()`, each part MUST be at least 5MB (except the last part). This conflicts with Vercel's 4.5MB serverless function limit, making manual multipart uploads impossible via server-side routes. You must use automatic multipart (`multipart: true` in `put()`) or client uploads.

**Solution/Workaround**:
```typescript
// ❌ Manual multipart upload fails (can't upload 5MB chunks via serverless function)
const upload = await createMultipartUpload('large.mp4', { access: 'public' });
// uploadPart() requires 5MB minimum - hits serverless limit

// ✅ Use automatic multipart via client upload
await upload('large.mp4', file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
  multipart: true, // Automatically handles 5MB+ chunks
});
```

**Community Validation**:
- Official docs explicitly state "5MB minimum per part"
- Multiple users report confusion about this limitation
- Workaround confirmed by community

**Recommendation**: Add to Known Issues or Common Patterns section.

---

### Finding 2.3: Missing File Extension Causes Access Denied

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #664](https://github.com/vercel/storage/issues/664), Community Forums
**Date**: 2024
**Verified**: Multiple users confirm
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When uploading files without file extensions in the pathname, Vercel Blob may fail with "Access denied, please provide a valid token" error. The error message is non-descriptive and doesn't indicate the root cause is the missing extension.

**Reproduction**:
```typescript
// Fails with confusing error
await upload('user-12345', file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
}); // Error: Access denied

// Works
await upload('user-12345.jpg', file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
});
```

**Solution/Workaround**:
```typescript
// Always include file extension in pathname
const extension = file.name.split('.').pop();
await upload(`user-${userId}.${extension}`, file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
});
```

**Community Validation**:
- GitHub issue with multiple confirmations
- Non-descriptive error message acknowledged
- Workaround verified

**Recommendation**: Add to Known Issues Prevention section.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Storage Capacity Hard Limit (10GB)

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Vercel Community Discussion](https://community.vercel.com/t/blob-storage-limit/5637), [Vercel Community](https://community.vercel.com/t/vercel-blob-storage-size/8013)
**Date**: 2025
**Verified**: Cross-referenced community discussions
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Multiple users report that Vercel Blob has a hard limit of 10GB storage without the option to purchase additional capacity. This is not clearly documented in official pricing pages, which focus on bandwidth costs.

**Consensus Evidence**:
- Multiple community threads discussing 10GB limit
- Users report hitting limit with no upgrade path
- No official documentation contradicts this

**Recommendation**: Verify with Vercel support before adding. If confirmed, add to Limits/Quotas section.

---

### Finding 3.2: CDN Cache May Not Purge Immediately After Delete

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Official Docs](https://vercel.com/docs/storage/vercel-blob/using-blob-sdk#del), Community Reports
**Date**: 2025
**Verified**: Official docs mention "up to one minute"
**Impact**: LOW
**Already in Skill**: Partially (Issue #7 mentions delete)

**Description**:
When deleting a blob with `del()`, the official docs state "it may take up to one minute for them to be fully removed from the Vercel CDN cache." Some users report cached files serving for longer than one minute.

**Solution/Workaround**:
```typescript
// After deleting, file may still be accessible briefly
await del(blobUrl);

// For immediate replacement, use unique filenames
await put(`avatars/${userId}-${Date.now()}.jpg`, file, { access: 'public' });
// Or use addRandomSuffix: true
```

**Consensus Evidence**:
- Official docs confirm "up to one minute"
- Some users report longer cache times
- Workaround: Use unique filenames for updates

**Recommendation**: Expand Issue #7 to mention CDN cache delay.

---

### Finding 3.3: onUploadCompleted Doesn't Work on Localhost

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Official Docs](https://vercel.com/docs/storage/vercel-blob/client-upload#local-development), Community Forums
**Date**: 2024-2025
**Verified**: Official docs confirm
**Impact**: LOW (development only)
**Already in Skill**: Partially (Issue #10 mentions callback)

**Description**:
The `onUploadCompleted` callback requires Vercel Blob to make an HTTP request to your server. On localhost, this callback will never fire because Vercel cannot reach your local machine. Official docs recommend using ngrok or similar tunneling service for local development.

**Solution/Workaround**:
```bash
# Use ngrok for local development
ngrok http 3000

# Set environment variable
VERCEL_BLOB_CALLBACK_URL=https://abc123.ngrok-free.app
```

**Consensus Evidence**:
- Official docs explicitly document this limitation
- Common confusion in community forums
- Workaround confirmed by Vercel

**Recommendation**: Expand Issue #10 or add to Development Tips section.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Production Image Loading Issues

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #923](https://github.com/vercel/storage/issues/923)
**Date**: 2026-01-03
**Verified**: No
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [x] No maintainer response yet
- [x] Insufficient detail to reproduce
- [x] May be environment-specific

**Description**:
User reports "vercel/blob not loading images in production webpage, permanent Vercel Blob Storage URLs" but provides no code examples or reproduction steps.

**Recommendation**: Monitor issue for updates. DO NOT add to skill without reproduction steps and maintainer confirmation.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Server upload timeout for large files | Known Issues #8 | Fully covered |
| Missing upload callback | Known Issues #10 | Fully covered |
| 4.5MB limit | Known Issues #8 | Mentions timeout but could clarify 4.5MB hard limit |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Token Expiration for Large Files | Known Issues Prevention | Add as Issue #11 |
| 1.2 v2.0.0 Breaking Change (callbackUrl) | Known Issues Prevention | Add as Issue #12 with version note |
| 2.1 4.5MB Server Limit | Known Issues #8 | Expand to clarify server vs client limits |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 ReadableStream Firefox Support | Known Issues | Add with browser compatibility note |
| 1.4 Pathname Cannot Be Modified | Common Patterns | Add validation pattern example |
| 2.2 Multipart Minimum Chunk Size | Known Issues or Multipart section | Technical detail for advanced users |
| 2.3 Missing File Extension | Known Issues Prevention | Add as Issue #13 |

### Priority 3: Verify Before Adding (TIER 3)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 3.1 10GB Storage Limit | Limits/Quotas | Verify with Vercel support first |
| 3.2 CDN Cache Delay | Known Issues #7 | Expand with cache timing |
| 3.3 Localhost Callback Limitation | Development Tips | Minor, could add to docs |

### Priority 4: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 Production Image Loading | Insufficient detail | Wait for maintainer response |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "blob edge case OR gotcha" in vercel/storage | 0 | 0 |
| "blob multipart" in vercel/storage | 20 | 1 |
| "blob client upload" in vercel/storage | 20 | 5 |
| Created after May 2025 | 9 | 4 |
| Recent releases | 10 | 1 (v2.0.0) |

**Key Issues Reviewed**:
- #903: Client upload filename retention (open, no resolution)
- #881: Stream upload never completes (Firefox issue)
- #874: onUploadComplete not triggering (no comments)
- #863: Pathname not settable (confirmed limitation)
- #443: Large file upload failures (solved with validUntil)

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "vercel blob site:stackoverflow.com gotcha 2024 2025" | 0 | N/A |

**Note**: Limited Stack Overflow content for Vercel Blob. Most discussion happens in GitHub issues and Vercel Community forums.

### Official Documentation

| Source | Notes |
|--------|-------|
| [Vercel Blob Docs](https://vercel.com/docs/storage/vercel-blob) | Primary reference, up to date |
| [Client Upload Guide](https://vercel.com/docs/storage/vercel-blob/client-upload) | Detailed callback behavior |
| [Using Blob SDK](https://vercel.com/docs/storage/vercel-blob/using-blob-sdk) | API method documentation |
| [Release Notes v2.0.0](https://github.com/vercel/storage/releases/tag/%40vercel/blob%402.0.0) | Breaking changes |

### Community Sources

| Source | Notes |
|--------|-------|
| [Payload CMS Discussions](https://github.com/payloadcms/payload/discussions/7569) | Real-world 4.5MB limit issues |
| [Vercel Community Forums](https://community.vercel.com) | Multiple threads on limits, callbacks |
| [Medium Article](https://medium.com/@jpnreddy25/...) | Workarounds for size limits |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue analysis
- `gh release view` for breaking changes
- `WebSearch` for community discussions
- `WebFetch` for official documentation

**Limitations**:
- Limited Stack Overflow content (newer service)
- Some GitHub issues lack maintainer responses
- 404 error on `/docs/storage/vercel-blob/limits` (docs may have moved)

**Time Spent**: ~18 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference finding 1.2 (v2.0.0 breaking change) against current official documentation to ensure callback behavior is accurately described.

**For api-method-checker**: Verify that the `validUntil` parameter in finding 1.1 exists in @vercel/blob@2.0.0 type definitions.

**For code-example-validator**: Validate code examples in findings 1.1, 1.2, 1.4, 2.1 before adding to skill.

**For web-researcher**: If finding 3.1 (10GB limit) needs verification, contact Vercel support or check latest pricing documentation.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

```markdown
### Issue #11: Client Upload Token Expiration for Large Files

**Error**: `Error: Access denied, please provide a valid token for this resource`
**Source**: https://github.com/vercel/storage/issues/443
**Why It Happens**: Default token expires after 30 seconds. Large files (>100MB) take longer to upload, causing token expiration before validation.
**Prevention**: Set `validUntil` parameter for large file uploads.

```typescript
// For large files (>100MB), extend token expiration
const jsonResponse = await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      maximumSizeInBytes: 200 * 1024 * 1024,
      validUntil: Date.now() + 300000, // 5 minutes
    };
  },
});
```

### Issue #12: v2.0.0 Breaking Change - onUploadCompleted Requires callbackUrl (Non-Vercel Hosting)

**Error**: onUploadCompleted callback doesn't fire when not hosted on Vercel
**Source**: https://github.com/vercel/storage/releases/tag/%40vercel/blob%402.0.0
**Why It Happens**: v2.0.0 removed automatic callback URL inference from client-side `location.href` for security.
**Prevention**: Explicitly provide `callbackUrl` when not using Vercel system environment variables.

```typescript
// v2.0.0+ for non-Vercel hosting
await handleUpload({
  body,
  request,
  onBeforeGenerateToken: async (pathname) => {
    return {
      callbackUrl: 'https://example.com',
    };
  },
  onUploadCompleted: async ({ blob, tokenPayload }) => {
    // Now fires correctly
  },
});

// For local development with ngrok:
// VERCEL_BLOB_CALLBACK_URL=https://abc123.ngrok-free.app
```

### Issue #13: Missing File Extension Causes Access Denied Error

**Error**: `Error: Access denied, please provide a valid token for this resource`
**Source**: https://github.com/vercel/storage/issues/664
**Why It Happens**: Pathname without file extension causes non-descriptive access denied error
**Prevention**: Always include file extension in pathname

```typescript
// Extract extension and include in pathname
const extension = file.name.split('.').pop();
await upload(`user-${userId}.${extension}`, file, {
  access: 'public',
  handleUploadUrl: '/api/upload',
});
```
```

### Expanding Existing Issues

**Issue #8 (Upload Timeout)**:

Add clarification:
```markdown
### Issue #8: Upload Timeout (Large Files) + Server-Side 4.5MB Limit

**Error**: `Error: Request timeout` for files >100MB (server) OR file upload fails at 4.5MB (serverless function limit)
**Source**: Vercel function timeout limits + [4.5MB serverless limit](https://vercel.com/docs/limits)
**Why It Happens**:
- Serverless function timeout (10s free tier, 60s pro) for server-side uploads
- **CRITICAL**: Vercel serverless functions have a hard 4.5MB request body limit. Using `put()` in server actions/API routes fails for files >4.5MB.
**Prevention**: Use client-side upload with `handleUpload()` for files >4.5MB OR use multipart upload.

```typescript
// ❌ Server-side upload fails at 4.5MB
export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('file') as File; // Fails if >4.5MB
  await put(file.name, file, { access: 'public' });
}

// ✅ Client upload bypasses 4.5MB limit
const blob = await upload(file.name, file, {
  access: 'public',
  handleUploadUrl: '/api/upload/token',
  multipart: true, // For files >500MB, use multipart
});
```
```

---

**Research Completed**: 2026-01-21 05:15 UTC
**Next Research Due**: After @vercel/blob@3.0.0 release or Q2 2026 (whichever comes first)

---

## Sources

- [Payload CMS Discussion #7569](https://github.com/payloadcms/payload/discussions/7569)
- [5 TB file transfers with Blob multipart uploads - Vercel](https://vercel.com/changelog/5tb-file-transfers-with-vercel-blob-multipart-uploads)
- [Vercel Blob Multiple File Upload Discussion](https://github.com/vercel/next.js/discussions/64178)
- [4.5 MB Payload Limit - Vercel Community](https://community.vercel.com/t/4-5-mb-payload-limit/10500)
- [Upload fails with clientUpload - Payload Issue #14709](https://github.com/payloadcms/payload/issues/14709)
- [Client Uploads with Vercel Blob](https://vercel.com/docs/vercel-blob/client-upload)
- [Upload/Download Progress Issue #642](https://github.com/vercel/storage/issues/642)
- [GitHub Issue #638 - Client lib in Node.js](https://github.com/vercel/storage/issues/638)
- [Client Uploads Token Issue - Vercel Community](https://community.vercel.com/t/client-uploads-with-vercel-blob-token-issue/7230)
- [GenerateClientToken Error - Vercel Community](https://community.vercel.com/t/vercel-blob-client-upload-error-on-generateclienttoken/2671)
- [GitHub Issue #443 - Large file upload failures](https://github.com/vercel/storage/issues/443)
- [GitHub Issue #664 - Missing file extension](https://github.com/vercel/storage/issues/664)
- [Prefix + clientUpload errors - Payload Issue #12544](https://github.com/payloadcms/payload/issues/12544)
- [Vercel Limits Documentation](https://vercel.com/docs/limits)
- [Vercel Blob Documentation](https://vercel.com/docs/vercel-blob)
- [Vercel Blob Pricing](https://vercel.com/docs/vercel-blob/usage-and-pricing)
- [Blob storage limit discussion](https://community.vercel.com/t/blob-storage-limit/5637)
- [Medium: Bypass 4.5MB limit with Supabase](https://medium.com/@jpnreddy25/how-to-bypass-vercels-4-5mb-body-size-limit-for-serverless-functions-using-supabase-09610d8ca387)
- [Vercel Blob storage size discussion](https://community.vercel.com/t/vercel-blob-storage-size/8013)
- [Vercel Storage Overview](https://vercel.com/docs/storage)
- [Vercel 2025 Pricing Breakdown](https://flexprice.io/blog/vercel-pricing-breakdown)
- [GitHub Issue #594 - downloadUrl expiration](https://github.com/vercel/storage/issues/594)
- [@vercel/blob NPM package](https://www.npmjs.com/package/@vercel/blob)
- [Blob Storage No Token Error](https://community.vercel.com/t/blob-storage-no-token-found-error/1450)
- [GitHub Issue #456 - Access denied error](https://github.com/vercel/storage/issues/456)
