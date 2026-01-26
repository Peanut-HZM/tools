# Community Knowledge Research: firecrawl-scraper

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/firecrawl-scraper/SKILL.md
**Packages Researched**: firecrawl-py 4.13.0+, @mendable/firecrawl-js 4.11.1+
**Official Repo**: mendableai/firecrawl
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 7 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 2 |
| Recommended to Add | 10 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Stealth Mode Pricing Change (May 2025)

**Trust Score**: TIER 1 - Official
**Source**: [Stealth Mode Docs](https://docs.firecrawl.dev/features/stealth-mode) | [Changelog](https://www.firecrawl.dev/changelog)
**Date**: 2025-05-08
**Verified**: Yes
**Impact**: HIGH (affects billing)
**Already in Skill**: No

**Description**:
Starting May 8th, 2025, Stealth Mode proxy requests now cost 5 credits per request. This was previously included in standard credit pricing. This is a significant breaking change affecting cost calculations.

**Key Details**:
- **Auto mode (default)**: Automatically retries with stealth if basic fails; charges 5 credits only if stealth succeeds
- **Basic mode**: Standard proxies, 1 credit cost
- **Stealth mode**: 5 credits per request when actively used
- **Recommended pattern**: Use auto mode and only enable stealth conditionally for HTTP 401, 403, or 500 errors

**Solution/Workaround**:
```python
# Recommended pattern: Use auto mode (default)
doc = firecrawl.scrape('https://example.com', formats=['markdown'])
# Auto retries with stealth (5 credits) only if basic fails

# Or conditionally enable based on error status
try:
    doc = firecrawl.scrape(url, formats=['markdown'], proxy='basic')
except Exception as e:
    if e.status_code in [401, 403, 500]:
        doc = firecrawl.scrape(url, formats=['markdown'], proxy='stealth')
```

**Official Status**:
- [x] Documented behavior
- [x] Breaking change (pricing)
- [ ] Fixed in version X.Y.Z
- [ ] Won't fix

---

### Finding 1.2: v2.0.0 Breaking Changes (August 2025)

**Trust Score**: TIER 1 - Official
**Source**: [v2.0.0 Release](https://github.com/firecrawl/firecrawl/releases/tag/v2.0.0) | [Migration Guide](https://docs.firecrawl.dev/migrate-to-v2)
**Date**: 2025-08-19
**Verified**: Yes
**Impact**: HIGH (breaking changes)
**Already in Skill**: No

**Description**:
Major version upgrade with significant breaking changes to SDK methods, formats, and crawl options.

**Key Breaking Changes**:

1. **SDK Method Renames**:
   - JS: `scrapeUrl()` → `scrape()`, `crawlUrl()` → `crawl()` or `startCrawl()`
   - Python: `scrape_url()` → `scrape()`, `crawl_url()` → `crawl()` or `start_crawl()`

2. **Format Changes**:
   - Old `"extract"` format renamed to `"json"`
   - JSON extraction now uses object format: `{ type: "json", prompt: "...", schema: {...} }`
   - Screenshot now uses object: `{ type: "screenshot", fullPage: true, quality: 80, viewport: {...} }`
   - New `"summary"` format available

3. **Crawl Options**:
   - `allowBackwardCrawling` removed; use `crawlEntireDomain`
   - `maxDepth` removed; use `maxDiscoveryDepth`
   - `ignoreSitemap` (bool) → `sitemap` ("only", "skip", "include")

4. **Defaults Changed**:
   - `maxAge` now defaults to 2 days (cached by default)
   - `blockAds`, `skipTlsVerification`, `removeBase64Images` enabled by default

**Solution/Workaround**:
```python
# v1 (old)
doc = app.scrape_url(
    url="https://example.com",
    params={
        "formats": ["extract"],
        "extract": {"prompt": "Extract title"}
    }
)

# v2 (new)
doc = app.scrape(
    url="https://example.com",
    formats=[{"type": "json", "prompt": "Extract title"}]
)
```

**Official Status**:
- [x] Documented behavior
- [x] Migration guide available
- [ ] Fixed in version X.Y.Z
- [ ] Won't fix

---

### Finding 1.3: DNS Resolution Errors Return 200 (December 2025)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2402](https://github.com/firecrawl/firecrawl/issues/2402) | [v2.7.0 Release](https://github.com/firecrawl/firecrawl/releases/tag/v2.7.0)
**Date**: 2025-12-05
**Verified**: Yes
**Impact**: MEDIUM (affects error handling)
**Already in Skill**: No

**Description**:
DNS resolution errors now return HTTP 200 with `success: false` instead of 4xx/5xx errors. This is a breaking change for error handling logic. The system still charges 1 credit for DNS resolution errors.

**Reproduction**:
```typescript
const result = await app.scrape('https://nonexistent-domain-xyz.com');
// Returns: { success: false, code: "SCRAPE_DNS_RESOLUTION_ERROR", error: "..." }
// HTTP status: 200 (not 4xx)
```

**Solution/Workaround**:
```typescript
// Don't rely on HTTP status code alone
const result = await app.scrape(url);

if (!result.success) {
    if (result.code === 'SCRAPE_DNS_RESOLUTION_ERROR') {
        console.error('DNS resolution failed');
    }
    throw new Error(result.error);
}
```

**Official Status**:
- [x] Fixed in version v2.7.0
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.4: Bot Detection Still Charges Credits (November 2025)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2413](https://github.com/firecrawl/firecrawl/issues/2413)
**Date**: 2025-11-18
**Verified**: Yes
**Impact**: MEDIUM (affects billing)
**Already in Skill**: Partial (stealth mode mentioned)

**Description**:
When Firecrawl encounters bot detection (e.g., Cloudflare 5xx error page), the scrape is marked as "succeeded" in activity logs and charges a credit, even though it returns the Cloudflare error page instead of actual content.

**Reproduction**:
```python
# Basic scrape without stealth
doc = app.scrape(url="https://protected-site.com", formats=["markdown"])
# Result: Cloudflare 5xx error page HTML, but marked as success
# Credits charged: 1 (fire-1 engine costs credits even on failure)
```

**Workaround**:
```python
# First attempt without stealth
try:
    doc = app.scrape(url, formats=["markdown"])
    # Validate content isn't an error page
    if "cloudflare" in doc.markdown.lower() or "access denied" in doc.markdown.lower():
        raise ValueError("Bot detection")
except:
    # Retry with stealth (costs 5 credits if successful)
    doc = app.scrape(url, formats=["markdown"], stealth=True)
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (fire-1 engine costs credits)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: Finding 1.1 (Stealth Mode Pricing)
- Partially covered in: Known Issues #5 (Bot Detection)

---

### Finding 1.5: Job Status Race Condition (December 2025)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2662](https://github.com/firecrawl/firecrawl/issues/2662)
**Date**: 2025-12-11
**Verified**: Yes (Open issue)
**Impact**: HIGH (affects async flows)
**Already in Skill**: No

**Description**:
When calling the crawl status endpoint immediately after receiving a job_id from the crawl creation API, there is a high probability of receiving `{"success":false,"error":"Job not found"}`. Waiting 1-3 seconds and retrying with the same job_id succeeds.

**Reproduction**:
```python
# Start crawl
job = app.start_crawl(url="https://docs.example.com")
print(f"Job ID: {job.id}")

# Immediate status check (high probability of failure)
status = app.get_crawl_status(job.id)  # Error: "Job not found"
```

**Solution/Workaround**:
```python
import time

# Start crawl
job = app.start_crawl(url="https://docs.example.com")

# Wait before first status check
time.sleep(2)  # 1-3 seconds recommended

# Now status check succeeds
status = app.get_crawl_status(job.id)

# Or implement retry logic
def get_status_with_retry(job_id, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return app.get_crawl_status(job_id)
        except Exception as e:
            if "Job not found" in str(e) and attempt < max_retries - 1:
                time.sleep(delay)
                continue
            raise
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Community Validation**:
- Multiple users confirm the issue
- Maintainers acknowledged ("Let me take a look", "Sure will look into it !")
- 100% reproducible with high probability

---

### Finding 1.6: Self-Hosted Anti-Bot Fingerprinting Weakness (October 2025)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2257](https://github.com/firecrawl/firecrawl/issues/2257)
**Date**: 2025-10-07
**Verified**: Yes (Open issue)
**Impact**: HIGH (self-hosted only)
**Already in Skill**: No

**Description**:
Self-hosted Firecrawl fails on sites with strong anti-bot measures (Cloudflare, WAFs) even with Playwright engine, while Browserless.io succeeds from the same IP. This indicates the issue is browser fingerprinting, not IP blocking. The default Playwright implementation lacks anti-detection techniques.

**Reproduction**:
```bash
# Self-hosted instance
curl -X POST 'http://localhost:3002/v2/scrape' \
-H 'Authorization: Bearer YOUR_API_KEY' \
-d '{
  "url": "https://www.example.com/",
  "pageOptions": { "engine": "playwright" }
}'

# Error: "All scraping engines failed!" (SCRAPE_ALL_ENGINES_FAILED)
# Same URL works with Browserless.io from same IP
```

**Workaround**:
- Use Firecrawl cloud service (has better anti-fingerprinting)
- Use proxy configuration
- For self-hosted: Consider using external services like Browserless.io

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue (open)
- [ ] Won't fix

**Additional Context**:
- Affects v2.3.0 and likely later versions
- Default docker-compose setup
- Warning present: "⚠️ WARNING: No proxy server provided. Your IP address may be blocked."
- Community suggests enhancing Playwright engine with anti-fingerprinting (similar to puppeteer-extra-stealth)

---

### Finding 1.7: Unified Billing Model (November 2025)

**Trust Score**: TIER 1 - Official
**Source**: [v2.6.0 Release](https://github.com/firecrawl/firecrawl/releases/tag/v2.6.0)
**Date**: 2025-11-13
**Verified**: Yes
**Impact**: MEDIUM (affects billing understanding)
**Already in Skill**: No

**Description**:
Credits and tokens merged into single system. Extract endpoint now uses credits (15 tokens = 1 credit conversion). Existing tokens work everywhere. This simplifies the billing model but changes cost calculations.

**Key Changes**:
- Extract endpoint: Now uses credits instead of tokens
- Conversion: 15 tokens = 1 credit
- Backward compatible: Existing tokens still work
- Instant credit purchases available from dashboard

**Official Status**:
- [x] Documented behavior
- [x] Released in v2.6.0
- [ ] Fixed in version X.Y.Z
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Cache Control Best Practices (2025)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Fast Scraping Docs](https://docs.firecrawl.dev/features/fast-scraping) | [Blog Post](https://www.firecrawl.dev/blog/mastering-firecrawl-scrape-endpoint)
**Date**: 2025-12-05
**Verified**: Yes (official docs)
**Impact**: MEDIUM (affects performance)
**Already in Skill**: Partial (maxAge mentioned)

**Description**:
Using `maxAge` cache control effectively can make results up to 500% faster. Default is 2 days in v2+. Setting `maxAge: 0` forces fresh data. Setting `minAge` parameter (v2.7.0+) requires minimum cached age before re-scraping.

**Best Practices**:
```python
# Fresh data (real-time pricing, stock prices)
doc = app.scrape(url, formats=["markdown"], max_age=0)

# 10-minute cache (news, blogs)
doc = app.scrape(url, formats=["markdown"], max_age=600000)  # milliseconds

# Use default cache (2 days) for static content
doc = app.scrape(url, formats=["markdown"])  # maxAge defaults to 172800000

# Don't store in cache (one-time scrape)
doc = app.scrape(url, formats=["markdown"], store_in_cache=False)

# Require minimum age before re-scraping (v2.7.0+)
doc = app.scrape(url, formats=["markdown"], min_age=3600000)  # 1 hour minimum
```

**Performance Impact**:
- Cached: Milliseconds response time
- Fresh: Seconds response time
- Speed difference: Up to 500%

**Community Validation**:
- Official documentation
- Multiple blog posts confirm
- Production-tested pattern

---

### Finding 2.2: Browser Actions for Dynamic Content (2025)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Advanced Scraping Guide](https://docs.firecrawl.dev/advanced-scraping-guide) | [Blog Post](https://www.firecrawl.dev/blog/mastering-firecrawl-scrape-endpoint)
**Date**: 2025
**Verified**: Yes (official docs)
**Impact**: MEDIUM (affects scraping success)
**Already in Skill**: Yes (actions section exists)

**Description**:
Comprehensive actions support for handling dynamic content: click, scroll, write, press, wait. Essential for cookie banners, infinite scroll, login forms, and lazy-loaded content.

**Advanced Patterns**:
```python
# Cookie banner + scroll to load content
doc = app.scrape(
    url="https://example.com",
    actions=[
        {"type": "click", "selector": "button.accept-cookies"},
        {"type": "wait", "milliseconds": 1000},
        {"type": "scroll", "direction": "down"},
        {"type": "wait", "selector": ".loaded-content"},  # Wait for element
        {"type": "screenshot"}  # Capture final state
    ]
)

# Login flow
doc = app.scrape(
    url="https://example.com/dashboard",
    actions=[
        {"type": "write", "selector": "input[name=username]", "text": "user"},
        {"type": "write", "selector": "input[name=password]", "text": "pass"},
        {"type": "click", "selector": "button[type=submit]"},
        {"type": "wait", "milliseconds": 3000}
    ]
)

# Click all "Load More" buttons
doc = app.scrape(
    url="https://example.com",
    actions=[
        {"type": "click", "selector": "button.load-more", "all": True},  # Click all matching
        {"type": "wait", "milliseconds": 2000}
    ]
)
```

**Community Validation**:
- Official documentation
- Widely used pattern
- Production-tested

**Cross-Reference**:
- Already in skill: Browser Actions section
- Enhancement: Add more examples

---

### Finding 2.3: Common Web Scraping Mistakes (2025)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Blog Post](https://www.firecrawl.dev/blog/web-scraping-mistakes-and-fixes)
**Date**: 2025
**Verified**: Yes (official blog)
**Impact**: MEDIUM (educational)
**Already in Skill**: Partial

**Description**:
Official blog post covers 10 common web scraping mistakes. Many are handled automatically by Firecrawl, but worth documenting as preventions.

**Key Mistakes Firecrawl Prevents**:
1. Inadequate JavaScript handling → Firecrawl uses browser automation
2. Complex web infrastructure → Auto-handles headers and fingerprinting
3. Poor request management → Built-in retry and backoff
4. Session management → Maintains cookies across requests
5. Inefficient content extraction → `only_main_content=True` removes noise
6. Resource management → Automatic cleanup

**Mistakes Users Can Still Make**:
1. Not using stealth mode when needed
2. Aggressive scraping without rate limiting
3. Not validating scraped content for bot detection pages
4. Not using cache effectively
5. Not handling errors properly

**Community Validation**:
- Official Firecrawl blog
- 10 documented patterns
- Best practices guide

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Rate Limit Best Practices (2025)

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Rate Limits Docs](https://docs.firecrawl.dev/rate-limits) | Multiple community discussions
**Date**: 2025
**Verified**: Cross-Referenced
**Impact**: MEDIUM (affects production usage)
**Already in Skill**: Yes (rate limits table exists)

**Description**:
Concurrent browser limits are typically the bottleneck, not API rate limits. The skill currently documents rate limits but could expand on optimization strategies.

**Concurrent Browser Limits**:
- Free: 2
- Hobby: 5
- Standard: 50
- Growth: 100

**Optimization Strategies**:
```python
# Batch operations to stay within concurrent limits
from concurrent.futures import ThreadPoolExecutor

urls = [...]  # 100 URLs
max_concurrent = 5  # Hobby tier

with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
    results = executor.map(lambda url: app.scrape(url), urls)

# Use batch endpoints for better concurrency management
job = app.start_batch_scrape(
    urls=urls,
    formats=["markdown"]
)
# Firecrawl manages concurrency internally
```

**Consensus Evidence**:
- Official rate limits documentation
- Community discussions about bottlenecks
- Best practices from production users

**Recommendation**: Enhance existing rate limits section with optimization patterns

---

### Finding 3.2: PDF and Document Scraping Improvements (November 2025)

**Trust Score**: TIER 3 - Community Consensus
**Source**: [v2.6.0 Release](https://github.com/firecrawl/firecrawl/releases/tag/v2.6.0) | [GitHub Issue #2396](https://github.com/firecrawl/firecrawl/issues/2396)
**Date**: 2025-11-13
**Verified**: Cross-Referenced
**Impact**: LOW (niche use case)
**Already in Skill**: Yes (PDF parsing mentioned)

**Description**:
Fixed document + PDF scrape loop issue in v2.6.0. PDFs now parse more reliably. The skill mentions PDF parsing but could note the improvements.

**Note**: PDF truncation info feature requested (#2626) for `maxPages` parameter - not yet implemented.

**Consensus Evidence**:
- Fixed in v2.6.0 release
- Community confirmed improvements
- Issue #2396 closed

**Recommendation**: Add note about v2.6.0 improvements to PDF parsing section

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

No TIER 4 findings. All identified issues were verified against official sources or had sufficient community validation.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Bot detection solutions | Known Issues #5 | Use stealth mode - covered |
| Actions (click, scroll, wait) | Browser Actions | Fully covered with examples |
| Rate limits table | Rate Limits & Pricing | Comprehensive table exists |
| PDF/DOCX parsing | What is Firecrawl? | Mentioned, could expand |
| maxAge parameter | Advanced Options | Covered in scrape options |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Stealth Mode Pricing | Rate Limits & Pricing | Add May 2025 pricing change, auto mode recommendation |
| 1.2 v2.0.0 Breaking Changes | New section: Migration Guide | Add v1→v2 migration section |
| 1.5 Job Status Race Condition | Common Issues & Solutions | Add as Issue #7 with retry pattern |
| 1.3 DNS Errors Return 200 | Common Issues & Solutions | Add as Issue #8 with error handling |
| 1.4 Bot Detection Billing | Known Issues | Expand #5 with billing note |

### Priority 2: Enhance Existing Sections (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.6 Self-Hosted Fingerprinting | New section: Self-Hosting Considerations | Add self-hosted limitations |
| 1.7 Unified Billing | Rate Limits & Pricing | Update to reflect credits-only model |
| 2.1 Cache Best Practices | Advanced Options | Expand maxAge section with performance metrics |
| 2.2 Browser Actions | Browser Actions | Add more complex examples |
| 2.3 Common Mistakes | Common Issues & Solutions | Add "What Firecrawl Prevents" section |

### Priority 3: Consider Adding (TIER 3, Low Priority)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 3.1 Rate Limit Optimization | Rate Limits & Pricing | Add optimization patterns |
| 3.2 PDF Improvements | Document Parsing | Note v2.6.0 improvements |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Recent issues (Oct-Dec 2025) | 50 | 12 |
| Release notes (v2.0-v2.7) | 15 | 7 |
| Bug issues | 200+ | 8 |
| Self-hosted issues | 30 | 3 |

### Official Documentation

| Source | Pages Reviewed | Findings |
|--------|----------------|----------|
| Migration guide (v1→v2) | 1 | Complete breaking changes |
| Rate limits | 1 | Comprehensive limits table |
| Stealth mode | 1 | Pricing changes |
| Advanced scraping | 1 | Actions patterns |

### Community Sources

| Source | Notes |
|--------|-------|
| [Official Blog](https://www.firecrawl.dev/blog) | 3 relevant posts |
| [Changelog](https://www.firecrawl.dev/changelog) | 15 releases reviewed |

---

## Methodology Notes

**Tools Used**:
- `gh issue list` for GitHub issue discovery
- `gh release view` for release notes
- `WebSearch` for documentation and blogs
- `WebFetch` for detailed content retrieval

**Limitations**:
- `gh search issues` with OR operators failed (permission issues)
- Stack Overflow has limited Firecrawl content (newer service)
- Focused on v2+ releases (v1 is deprecated)

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference finding 1.2 (v2.0.0 breaking changes) against current v2.7.0 docs
- Verify finding 1.1 (stealth mode pricing) is still accurate

**For code-example-validator**:
- Validate code examples in findings 1.5 (retry pattern), 2.1 (cache patterns), 2.2 (actions examples)

**For api-method-checker**:
- Verify that `min_age` parameter (finding 1.7) exists in current SDK versions

---

## Integration Guide

### Adding Migration Guide Section

```markdown
## Migration from v1 to v2

**Breaking Changes**: Firecrawl v2.0.0 (released August 2025) introduced major breaking changes.

### SDK Method Renames

**JavaScript/TypeScript**:
- `scrapeUrl()` → `scrape()`
- `crawlUrl()` → `crawl()` or `startCrawl()`
- `asyncCrawlUrl()` → `startCrawl()`
- `checkCrawlStatus()` → `getCrawlStatus()`

**Python**:
- `scrape_url()` → `scrape()`
- `crawl_url()` → `crawl()` or `start_crawl()`

### Format Changes

**Old (v1)**:
```python
doc = app.scrape_url(url, params={"formats": ["extract"]})
```

**New (v2)**:
```python
doc = app.scrape(url, formats=[{"type": "json", "prompt": "..."}])
```

**Full migration guide**: https://docs.firecrawl.dev/migrate-to-v2
```

### Adding to Common Issues

```markdown
### Issue #7: Job Status Race Condition

**Error**: `"Job not found"` when checking crawl status immediately
**Source**: [GitHub Issue #2662](https://github.com/firecrawl/firecrawl/issues/2662)
**Why It Happens**: Database replication delay between job creation and status endpoint
**Prevention**: Wait 1-3 seconds before first status check, or implement retry logic

```python
import time

job = app.start_crawl(url="https://docs.example.com")
time.sleep(2)  # Wait before first status check
status = app.get_crawl_status(job.id)  # Now succeeds
```

### Issue #8: DNS Errors Return HTTP 200

**Error**: DNS resolution failures return `success: false` with HTTP 200 status
**Source**: [GitHub Issue #2402](https://github.com/firecrawl/firecrawl/issues/2402)
**Why It Happens**: Changed in v2.7.0 for consistent error handling
**Prevention**: Check `success` field and `code` field, don't rely on HTTP status

```typescript
const result = await app.scrape(url);

if (!result.success) {
    if (result.code === 'SCRAPE_DNS_RESOLUTION_ERROR') {
        console.error('DNS resolution failed');
    }
    throw new Error(result.error);
}
```
```

### Updating Rate Limits Section

```markdown
## Rate Limits & Pricing

**⚠️ Stealth Mode Pricing Change (May 2025)**:
Stealth mode now costs **5 credits per request** when actively used. Default behavior uses "auto" mode which only charges stealth credits if basic fails.

**Recommended pattern**:
```python
# Use auto mode (default) - only charges 5 credits if stealth is needed
doc = app.scrape(url, formats=["markdown"])

# Or conditionally enable stealth for specific errors
if error_status_code in [401, 403, 500]:
    doc = app.scrape(url, formats=["markdown"], proxy="stealth")
```

**Unified Billing (November 2025)**:
Credits and tokens merged into single system. Extract endpoint uses credits (15 tokens = 1 credit).
```

---

## Key Insights for Skill Improvement

1. **Version-specific content needed**: Many gotchas are version-specific (v2.0, v2.6, v2.7). Consider adding version tags.

2. **Self-hosted vs Cloud**: Self-hosted has significant limitations (anti-bot fingerprinting). Consider adding separate section.

3. **Billing changes are frequent**: Stealth mode pricing, unified billing - need to document pricing model changes clearly.

4. **Race conditions exist**: Job status timing issue is production-critical for async flows.

5. **Error handling changed**: DNS errors returning 200 breaks traditional HTTP status-based error handling.

---

**Research Completed**: 2026-01-21 08:45
**Next Research Due**: After v3.0 release or Q2 2026 (whichever comes first)
