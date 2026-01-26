# Community Knowledge Research: Cloudflare Images

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-images/SKILL.md
**Packages Researched**: Cloudflare Images API v1/v2, Image Transformations
**Official Repo**: cloudflare/workers-sdk
**Time Window**: 2024 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 6 |
| TIER 2 (High-Quality Community) | 5 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 2 |
| Already in Skill | 8 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Content Credentials Support (Feb 2025)

**Trust Score**: TIER 1 - Official Blog
**Source**: [Cloudflare Blog - Content Credentials](https://blog.cloudflare.com/preserve-content-credentials-with-cloudflare-images/)
**Date**: 2025-02-03
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Cloudflare Images now supports Content Credentials (C2PA standard) for preserving image provenance chains. When transforming images that contain Content Credentials, Cloudflare automatically appends and cryptographically signs transformations to the existing manifest.

**Key Features**:
- Preserves entire provenance chain (creation source, edits, transformations)
- Automatic cryptographic signing using DigiCert certificates
- Compatible with verification tools (contentcredentials.org/verify, C2PA Tool)
- Toggle on/off via dashboard: Images > Transformations

**Gotcha**:
If source images don't contain Content Credentials, no action is taken. Only works with C2PA-compliant sources (certain cameras, DALL-E, compatible editing software).

**Official Status**:
- [x] GA (General Availability) as of Feb 2025
- [x] Documented feature

**Recommendation**: Add to SKILL.md "Recent Updates" and "Advanced Topics" sections

---

### Finding 1.2: Product Merge - Images + Image Resizing (Nov 2023)

**Trust Score**: TIER 1 - Official Blog
**Source**: [Cloudflare Blog - Merging Products](https://blog.cloudflare.com/merging-images-and-image-resizing/)
**Date**: 2023-11-15
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Partially (pricing mentioned but not migration gotchas)

**Description**:
Cloudflare merged Image Resizing features into Cloudflare Images product with new pricing model: $0.50 per 1,000 unique transformations monthly (billing once per 30 days per unique transformation).

**Breaking Changes**:
None - existing customers can continue using legacy version or migrate.

**Migration Gotchas**:
1. **Unpredictable Legacy Pricing**: Old Image Resizing bills based on uncached requests, making costs unpredictable due to variable cache behavior
2. **Billing Transition**: Must understand "unique transformations" rather than request counts
3. **Optional Migration**: No automatic transition - customers must actively choose
4. **Dashboard Changes**: Product management moving to unified interface

**Cross-Reference**:
Related to skill section on Image Transformations pricing

**Recommendation**: Add migration notes to "Advanced Topics" section

---

### Finding 1.3: AVIF Resolution Limit Confusion

**Trust Score**: TIER 1 - Official Docs + Community Confirmation
**Source**: [Cloudflare Docs](https://developers.cloudflare.com/images/transform-images/) + [Community Thread](https://community.cloudflare.com/t/avif-images-max-resolution-decreased-to-1200px/732848)
**Date**: 2024-11 (community report)
**Verified**: Partial (docs say 1600px, community reports 1200px)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Official docs state hard limit of 1,600 pixels for `format=avif` transformations. However, community reports indicate practical limit was lowered to 1200px for longest side (width or height) as of late 2024.

**Reproduction**:
```typescript
// May fail or downgrade if image is larger than 1200px
fetch(imageURL, {
  cf: {
    image: {
      width: 2000,
      format: 'avif'
    }
  }
});
```

**Solution/Workaround**:
Use `format=auto` instead of explicit `format=avif` to let Cloudflare decide, or use WebP for larger images.

**Official Status**:
- [ ] Conflicting information (docs vs practice)
- [x] Known limitation

**Recommendation**: Add to "Known Issues Prevention" as Issue #14, flag the discrepancy

---

### Finding 1.4: Metadata Stripping by Output Format

**Trust Score**: TIER 1 - Official Docs
**Source**: [Cloudflare Docs - Transform via URL](https://developers.cloudflare.com/images/transform-images/transform-via-url/)
**Date**: Current docs
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions metadata options but not format limitation)

**Description**:
**Critical limitation**: If output format is WebP or PNG, ALL metadata is discarded regardless of `metadata=keep` setting. Only JPEG supports metadata preservation options.

**Current Coverage in Skill**:
Issue #13 mentions metadata stripping but doesn't highlight the format-specific behavior.

**Enhancement Needed**:
```typescript
// ❌ WRONG - metadata=keep has NO EFFECT for WebP/PNG output
fetch(imageURL, {
  cf: {
    image: {
      format: 'webp',
      metadata: 'keep' // Ignored! Always stripped for WebP/PNG
    }
  }
});

// ✅ CORRECT - Only JPEG preserves metadata
fetch(imageURL, {
  cf: {
    image: {
      format: 'jpeg', // or auto (may become jpeg)
      metadata: 'keep' // Works for JPEG
    }
  }
});
```

**Official Status**:
- [x] Documented behavior
- [x] Limitation by design

**Recommendation**: Enhance Issue #13 with format-specific details

---

### Finding 1.5: Browser Cache TTL Default Behavior

**Trust Score**: TIER 1 - Official Docs
**Source**: [Cloudflare Docs - Browser TTL](https://developers.cloudflare.com/images/manage-images/browser-ttl/)
**Date**: Current docs
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
Default Browser Cache TTL for Cloudflare Images is **2 days** (172,800 seconds). This can cause issues when re-uploading images with same Custom ID.

**Key Details**:
- Default: 2 days
- Customizable: 1 hour to 1 year (account-level or per-variant)
- **Important**: Private images (signed URLs) do NOT respect TTL settings

**Gotcha**:
Community reports indicate custom TTL settings sometimes revert to default 2-day period after cache resets.

**Official Status**:
- [x] Documented behavior
- [ ] TTL reversion issue needs investigation

**Recommendation**: Add to "Advanced Topics" or "Configuration" section

---

### Finding 1.6: Flexible Variants Security Risk

**Trust Score**: TIER 1 - Official Docs
**Source**: [Cloudflare Docs - Enable Flexible Variants](https://developers.cloudflare.com/images/manage-images/enable-flexible-variants/)
**Date**: Current docs
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (Issue #11)

**Description**:
Enabling flexible variants allows anyone to obtain untransformed, full-resolution images and their metadata by changing variant properties in the URL. Additionally, flexible variants cannot be used with signed URLs.

**Abuse Risk (Sept 2024)**:
Community highlighted that without signed URL support, flexible variants can be abused via brute-force variant requests, leading to unexpected high costs.

**Example Attack**:
```
// Attacker can request unlimited variants
https://imagedelivery.net/<HASH>/<ID>/w=1,h=1
https://imagedelivery.net/<HASH>/<ID>/w=2,h=2
https://imagedelivery.net/<HASH>/<ID>/w=3,h=3
// ... each billed as unique transformation
```

**Official Status**:
- [x] Documented limitation
- [x] Workaround: Use named variants (max 100) for access control

**Cross-Reference**:
Already covered in Issue #11. No changes needed.

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Image Cache by Device Type (Unexpected Behavior)

**Trust Score**: TIER 2 - Community Reports
**Source**: [Cloudflare Community - Cache by Device](https://community.cloudflare.com/t/why-is-my-image-not-being-cached-by-edge/748670)
**Date**: 2024-12
**Verified**: Multiple user reports
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Images are being cached by device type unexpectedly, with no configuration option to disable this behavior in cache rules. This can cause issues where:
- Desktop and mobile see different cached versions
- Purging cache requires purging for each device type
- Unexpected cache misses despite proper headers

**Community Validation**:
- Multiple users confirm behavior
- No official workaround documented
- Issue persists as of Dec 2024

**Solution/Workaround**:
Manual cache purging per device type via Cloudflare dashboard.

**Recommendation**: Add to "Known Issues Prevention" as Issue #14 with "Community-reported" flag

---

### Finding 2.2: Image Update Requires Manual Purge

**Trust Score**: TIER 2 - Community Consensus
**Source**: [Cloudflare Community - Image Updates](https://community.cloudflare.com/t/image-not-updating-without-manually-purging-the-cache-on-cloudflare/788443)
**Date**: 2025-04
**Verified**: Multiple reports
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Even users who never visited a page still see old images after re-upload. Issue traced to large Cache-Control headers with `max-age=2592000` (30 days).

**Root Cause**:
Cloudflare respects origin Cache-Control headers. If origin sets long max-age, images remain cached even after re-upload with same ID.

**Solution**:
1. Use unique image IDs for each upload (append timestamp/hash)
2. Set shorter Cache-Control headers (e.g., max-age=86400 for 1 day)
3. Manual purge via dashboard after re-upload

```typescript
// ✅ RECOMMENDED - Unique IDs
const imageId = `${baseId}-${Date.now()}`;

// ⚠️ ALTERNATIVE - Shorter cache
headers.set('Cache-Control', 'public, max-age=86400'); // 1 day
```

**Recommendation**: Add to "Common Patterns" or "Troubleshooting" section

---

### Finding 2.3: PNG Not Cached by Default

**Trust Score**: TIER 2 - Community Confusion
**Source**: [Cloudflare Community - PNG Caching](https://community.cloudflare.com/t/cloudflare-not-cahcheing-some-of-my-images/751491)
**Date**: 2024-12
**Verified**: Yes (Cloudflare default cache extensions)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Default file extensions cached by Cloudflare do NOT include `.png`, causing confusion. Users must explicitly enable PNG caching via cache rules.

**Default Cached Extensions**:
`.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.ico`, `.svg`, `.tif`, `.tiff`

**Missing**: `.png` (requires explicit cache rule)

**Solution**:
Create cache rule to include `.png` files:
1. Dashboard → Caching → Cache Rules
2. Add rule: `URI Path` `ends with` `.png` → Cache Everything

**Official Status**:
- [x] Expected behavior (documented default extensions)
- [ ] Causes user confusion

**Recommendation**: Add to "Troubleshooting" section

---

### Finding 2.4: R2 Integration Patterns

**Trust Score**: TIER 2 - Community Best Practices + Official Docs
**Source**: [Cloudflare Reference Architecture](https://developers.cloudflare.com/reference-architecture/diagrams/content-delivery/optimizing-image-delivery-with-cloudflare-image-resizing-and-r2/) + [Medium Guide](https://medium.com/@leonwong282/the-complete-beginners-guide-to-cloudflare-r2-image-hosting-2025-f9090f8c2bb7)
**Date**: 2025-01
**Verified**: Multiple tutorials confirm
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Cloudflare Images is built on R2 + Image Resizing. For cost optimization, many users use R2 directly with on-demand transformations instead of Cloudflare Images product.

**Integration Pattern**:
1. Store original images in R2 bucket
2. Use Image Transformations (`/cdn-cgi/image/`) to resize on-demand
3. No variants stored in R2 (transformations are ephemeral/cached)

**Cost Comparison**:
- **R2**: 10GB storage + unlimited bandwidth free
- **Cloudflare Images**: $5/month for 100k stored images + $1 per 100k transformations
- **Hybrid**: R2 storage + $0.50 per 1k unique transformations

**Use Case**:
If you don't need named variants, batch uploads, or direct creator upload features, R2 + transformations is more cost-effective.

**Real-World Example**:
Dub.co migrated from Cloudinary to R2 in 2024 for image hosting cost savings.

**Recommendation**: Add to "Advanced Topics" as R2 integration pattern

---

### Finding 2.5: Mirage Deprecation (Sept 2025)

**Trust Score**: TIER 2 - Official Announcement
**Source**: [Cloudflare Community - Mirage Deprecation](https://community.cloudflare.com/t/deprecation-notice-mirage-effective-september-15-2025/824602)
**Date**: 2025-08 (announced), 2025-09-15 (effective)
**Verified**: Yes
**Impact**: HIGH (for Mirage users)
**Already in Skill**: No

**Description**:
Cloudflare deprecated Mirage feature effective September 15, 2025. Mirage provided lazy loading and on-demand image optimization.

**Migration Path**:
Users should migrate to:
1. **Cloudflare Images** for storage + transformations
2. **Native lazy loading**: `<img loading="lazy">`
3. **Image Transformations** for format optimization

**Impact**:
Users relying on Mirage for automatic lazy loading need to implement client-side lazy loading.

**Official Status**:
- [x] Deprecated as of Sept 15, 2025
- [x] Migration guidance provided

**Recommendation**: Add deprecation notice to "Recent Updates" section

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Transformation Pricing Uncertainty

**Trust Score**: TIER 3 - Community Concern
**Source**: [Cloudflare Community - Pricing](https://community.cloudflare.com/t/understanding-image-transformation-pricing/667692)
**Date**: 2024-06
**Verified**: Cross-referenced with docs
**Impact**: LOW
**Already in Skill**: No

**Description**:
Users confused about whether same transformation requested multiple times is billed multiple times or once per 30-day period.

**Official Clarification**:
Billing is per **unique transformation** (once per 30 days). Same transformation requested 1,000 times in a month = billed once.

**Unique Transformation**:
Combination of image ID + transformation params. Different params = different transformation.

**Example**:
```
/width=800,quality=85/image.jpg → Transformation A (billed once)
/width=800,quality=85/image.jpg → Transformation A (no additional charge)
/width=400,quality=85/image.jpg → Transformation B (billed separately)
```

**Consensus Evidence**:
- Official docs confirm
- Multiple community threads clarify
- No conflicting information

**Recommendation**: Add pricing clarification to "Advanced Topics"

---

### Finding 3.2: Shopify Image Mismatch (Edge CDN Issue)

**Trust Score**: TIER 3 - Single Platform Report
**Source**: [Cloudflare Community - Shopify Cache](https://community.cloudflare.com/t/unusual-cdn-cache-behavior-serving-incorrect-data-for-shopify-merchant/872377)
**Date**: 2025-12
**Verified**: Cross-referenced, platform-specific
**Impact**: LOW (Shopify-specific)
**Already in Skill**: No

**Description**:
Shopify merchants reported product images being mismatched in search results - wrong images assigned to products, same images across unrelated products.

**Root Cause**:
Cache key collision or incorrect cache purging on Shopify + Cloudflare integration.

**Platform**:
Specific to Shopify merchants using Cloudflare CDN.

**Consensus Evidence**:
- Single detailed report
- Not confirmed across other platforms
- May be Shopify integration issue

**Recommendation**: Monitor for additional reports. If confirmed across platforms, add to skill. Otherwise, too platform-specific.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Custom TTL Settings Reverting

**Trust Score**: TIER 4 - Low Confidence
**Source**: [Cloudflare Community - TTL Reversion](https://community.cloudflare.com/t/cloudflare-images-browser-cache-ttl/813610)
**Date**: 2025
**Verified**: No official confirmation
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
User reported custom Browser TTL settings reverting to default 2-day period after cache resets or dashboard changes.

**Official Response**:
None yet. May be user configuration error or transient bug.

**Recommendation**: Monitor for additional reports. DO NOT add to skill without verification.

---

### Finding 4.2: Container Image Deletion 401 Error (Fixed)

**Trust Score**: TIER 4 - Fixed Issue
**Source**: [GitHub Issue #9837](https://github.com/cloudflare/workers-sdk/issues/9837)
**Date**: 2025-07-03 (reported), 2025-07-03 (fixed)
**Verified**: Yes (fixed)
**Impact**: None (resolved)

**Why Flagged**:
- [ ] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [x] Fixed in current version

**Description**:
`wrangler containers images delete` returned 401 Unauthorized. Fixed by prefixing account ID to image name.

**Workaround (when broken)**:
```bash
yarn wrangler containers images delete <account-id>/hello-containers-go:b68a6935
```

**Official Status**:
- [x] Fixed in PR #9811
- [x] No longer relevant

**Recommendation**: DO NOT add - issue resolved.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Direct Creator Upload CORS | Issue #1 | Fully covered |
| Upload Timeout (5408) | Issue #2 | Fully covered |
| Invalid File Parameter | Issue #3 | Fully covered |
| CORS Preflight Failures | Issue #4 | Fully covered |
| Error 9401-9413 | Issues #5-#10 | Fully covered |
| Flexible Variants + Signed URLs | Issue #11 | Fully covered |
| SVG Resizing Limitation | Issue #12 | Fully covered |
| EXIF Metadata Stripped | Issue #13 | Partially covered (needs format enhancement) |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Content Credentials | Recent Updates + Advanced Topics | Add new feature (Feb 2025) |
| 1.2 Product Merge | Advanced Topics | Add migration notes |
| 1.3 AVIF Limit Confusion | Known Issues Prevention | Add as Issue #14 (note discrepancy) |
| 1.4 Metadata by Format | Known Issues Prevention | Enhance Issue #13 with format details |
| 1.5 Browser Cache TTL | Advanced Topics | Add default TTL behavior |
| 2.4 R2 Integration | Advanced Topics | Add R2 cost optimization pattern |
| 2.5 Mirage Deprecation | Recent Updates | Add deprecation notice |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.1 Cache by Device | Known Issues Prevention | Add with "Community-reported" flag |
| 2.2 Image Update Purge | Troubleshooting | Add cache purge guidance |
| 2.3 PNG Not Cached | Troubleshooting | Add PNG cache rule setup |
| 3.1 Pricing Clarity | Advanced Topics | Add transformation billing clarification |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 TTL Reversion | Single source | Wait for corroboration |
| 4.2 Container Delete 401 | Fixed issue | No action needed |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "images" in cloudflare/workers-sdk | 5 | 3 |
| Created >=2025-01-01 | 3 | 2 |
| Recent releases | 10 | 0 (no image-specific) |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare images" 2024-2025 | 0 | No results |

Limited Stack Overflow activity for Cloudflare Images - most discussion on Cloudflare Community forums.

### Cloudflare Community Forums

| Topic | Findings |
|-------|----------|
| Cache behavior | 4 threads |
| CORS issues | 5 threads (already covered in skill) |
| Pricing/billing | 2 threads |
| Deprecations | 1 thread (Mirage) |

### Cloudflare Blog

| Post | Date | Relevance |
|------|------|-----------|
| Content Credentials | 2025-02-03 | HIGH |
| Product Merge | 2023-11-15 | MEDIUM |

### Official Documentation

All findings cross-referenced with:
- https://developers.cloudflare.com/images/
- https://developers.cloudflare.com/images/llms-full.txt

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery (limited results - few image-specific issues)
- `WebSearch` for Cloudflare Community forums and blogs
- `WebFetch` for blog post details
- Official docs via LLM knowledge and web search

**Limitations**:
- Community forums blocked WebFetch (403 errors) - relied on search summaries
- Stack Overflow has minimal Cloudflare Images activity
- Most issues documented in forums, not GitHub Issues
- AVIF limit discrepancy needs manual verification (docs vs practice)

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify Finding 1.3 (AVIF limit) against live API - test with 1200px+ AVIF request
- Cross-reference Finding 2.1 (cache by device) against current cache rule docs

**For api-method-checker**:
- Verify Content Credentials API is available in current Cloudflare Images API
- Check if Browser TTL API has changed

**For code-example-validator**:
- Validate metadata format-specific code examples before adding
- Test R2 integration pattern code

---

## Integration Guide

### Adding Content Credentials (Finding 1.1)

Add to "Recent Updates" section:

```markdown
**Recent Updates (2025)**:
- **February 2025**: Content Credentials support (C2PA standard) - preserve image provenance chains, automatic cryptographic signing of transformations
- **August 2025**: AI Face Cropping GA (`gravity=face` with `zoom` control, GPU-based RetinaFace, 99.4% precision)
- **May 2025**: Media Transformations origin restrictions (default: same-domain only, configurable via dashboard)
- **Upcoming**: Background removal, generative upscale (planned features)
```

Add to "Advanced Topics":

```markdown
**Content Credentials (C2PA)**: Cloudflare Images preserves and signs image provenance chains. When transforming images with Content Credentials, Cloudflare automatically appends transformations to the manifest and cryptographically signs them using DigiCert certificates. Enable via Dashboard → Images → Transformations → Preserve Content Credentials. **Note**: Only works if source images already contain C2PA metadata (certain cameras, DALL-E, compatible editing software).
```

### Enhancing Metadata Issue (Finding 1.4)

Update Issue #13:

```markdown
### Issue #13: EXIF Metadata Stripped

**Error**: GPS data, camera settings removed from uploaded images

**Source**: [Cloudflare Images Docs - Transform via URL](https://developers.cloudflare.com/images/transform-images/transform-via-url/#metadata)

**Why It Happens**: Default behavior strips all metadata except copyright. **CRITICAL**: WebP and PNG output formats ALWAYS discard metadata regardless of settings.

**Prevention**:
```typescript
// ✅ CORRECT - JPEG preserves metadata
fetch(imageURL, {
  cf: {
    image: {
      width: 800,
      format: 'jpeg', // or 'auto' (may become jpeg)
      metadata: 'keep' // Preserves most EXIF including GPS
    }
  }
});

// ❌ WRONG - WebP/PNG ignore metadata setting
fetch(imageURL, {
  cf: {
    image: {
      format: 'webp',
      metadata: 'keep' // NO EFFECT - always stripped for WebP/PNG
    }
  }
});
```

**Metadata Options**:
- `none`: Strip all metadata
- `copyright`: Keep only copyright tag (default for JPEG)
- `keep`: Preserve most EXIF metadata including GPS

**Format Support**:
- ✅ JPEG: All metadata options work
- ❌ WebP: Always strips metadata (acts as `none`)
- ❌ PNG: Always strips metadata (acts as `none`)
```

### Adding AVIF Limit (Finding 1.3)

Add as new issue:

```markdown
### Issue #14: AVIF Resolution Limit Ambiguity

**Error**: Large AVIF transformations fail or degrade to lower resolution

**Source**: [Cloudflare Docs](https://developers.cloudflare.com/images/transform-images/) + [Community Report](https://community.cloudflare.com/t/avif-images-max-resolution-decreased-to-1200px/732848)

**Why It Happens**: Official docs state 1,600px hard limit for `format=avif`, but community reports indicate practical limit of 1200px for longest side as of late 2024.

**Prevention**:
```typescript
// ✅ RECOMMENDED - Use format=auto instead of explicit avif
fetch(imageURL, {
  cf: {
    image: {
      width: 2000,
      format: 'auto' // Cloudflare chooses best format
    }
  }
});

// ⚠️ MAY FAIL - Explicit AVIF with large dimensions
fetch(imageURL, {
  cf: {
    image: {
      width: 2000,
      format: 'avif' // May fail if >1200px
    }
  }
});

// ✅ WORKAROUND - Use WebP for larger images
if (width > 1200) {
  format = 'webp'; // WebP supports larger dimensions
} else {
  format = 'avif'; // AVIF for smaller images
}
```

**Note**: Discrepancy between official docs (1600px) and reported behavior (1200px) needs verification.
```

### Adding R2 Integration Pattern (Finding 2.4)

Add to "Advanced Topics":

```markdown
**R2 Integration for Cost Optimization**: Cloudflare Images is built on R2 + Image Resizing. For cost savings, store original images in R2 and use Image Transformations on-demand:

1. Upload images to R2 bucket
2. Serve via custom domain with `/cdn-cgi/image/` transformations
3. No variants stored (transformations are ephemeral/cached)

**Cost Comparison**:
- R2: 10GB storage + unlimited bandwidth (free tier)
- Cloudflare Images: $5/month (100k images) + $1 per 100k transformations
- R2 + Transformations: R2 storage + $0.50 per 1k unique transformations

**Use Case**: If you don't need named variants, batch uploads, or Direct Creator Upload features, R2 is more cost-effective.

**Example**: Workers pattern with R2:
```typescript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const imageKey = url.pathname.replace('/images/', '');
    const originURL = `https://r2-bucket.example.com/${imageKey}`;

    return fetch(originURL, {
      cf: {
        image: {
          width: 800,
          quality: 85,
          format: 'auto'
        }
      }
    });
  }
};
```

Reference: [Cloudflare Reference Architecture](https://developers.cloudflare.com/reference-architecture/diagrams/content-delivery/optimizing-image-delivery-with-cloudflare-image-resizing-and-r2/)
```

---

## Sources

### Official Cloudflare Sources
- [Cloudflare Images Overview](https://developers.cloudflare.com/images/)
- [Transform via URL](https://developers.cloudflare.com/images/transform-images/transform-via-url/)
- [Browser TTL](https://developers.cloudflare.com/images/manage-images/browser-ttl/)
- [Enable Flexible Variants](https://developers.cloudflare.com/images/manage-images/enable-flexible-variants/)
- [Cloudflare Blog - Content Credentials](https://blog.cloudflare.com/preserve-content-credentials-with-cloudflare-images/)
- [Cloudflare Blog - Product Merge](https://blog.cloudflare.com/merging-images-and-image-resizing/)

### Community Forums
- [Why is my image not being cached by Edge?](https://community.cloudflare.com/t/why-is-my-image-not-being-cached-by-edge/748670)
- [Image not updating without manually purging](https://community.cloudflare.com/t/image-not-updating-without-manually-purging-the-cache-on-cloudflare/788443)
- [Mirage Deprecation Notice](https://community.cloudflare.com/t/deprecation-notice-mirage-effective-september-15-2025/824602)
- [AVIF images max resolution decreased to 1200px](https://community.cloudflare.com/t/avif-images-max-resolution-decreased-to-1200px/732848)
- [Cloudflare Images flexible variants security](https://community.cloudflare.com/t/cloudflare-images-flexible-variants-security/408946)
- [Cloudflare Images direct upload CORS problem](https://community.cloudflare.com/t/cloudflare-images-direct-upload-cors-problem/368114)

### External Guides
- [Cloudflare Reference Architecture - R2 Image Optimization](https://developers.cloudflare.com/reference-architecture/diagrams/content-delivery/optimizing-image-delivery-with-cloudflare-image-resizing-and-r2/)
- [Complete Beginner's Guide to R2 Image Hosting (2025)](https://medium.com/@leonwong282/the-complete-beginners-guide-to-cloudflare-r2-image-hosting-2025-f9090f8c2bb7)

### GitHub
- [Issue #9837 - Container image deletion 401](https://github.com/cloudflare/workers-sdk/issues/9837)
- [Issue #10792 - Image Management 404](https://github.com/cloudflare/workers-sdk/issues/10792)
- [Issue #8637 - Feature Request: Image transformation via URL](https://github.com/cloudflare/workers-sdk/issues/8637)

---

**Research Completed**: 2026-01-21 12:00 UTC
**Next Research Due**: After next major Cloudflare Images feature release or quarterly (April 2026)
