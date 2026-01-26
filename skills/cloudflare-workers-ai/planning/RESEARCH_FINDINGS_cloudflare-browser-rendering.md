# Community Knowledge Research: Cloudflare Browser Rendering

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-browser-rendering/SKILL.md
**Packages Researched**: @cloudflare/puppeteer@1.0.4, @cloudflare/playwright@1.1.0, wrangler@4.59.3
**Official Repo**: cloudflare/workers-sdk, cloudflare/puppeteer, cloudflare/playwright
**Time Window**: Late 2024 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 18 |
| TIER 1 (Official) | 12 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 2 |
| Already in Skill | 4 |
| Recommended to Add | 10 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: browser.close() Hangs in Local Dev (Fixed)

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #9945](https://github.com/cloudflare/workers-sdk/issues/9945)
**Date**: 2025-07-13 (closed 2025-07-22)
**Verified**: Yes - Fixed in wrangler update
**Impact**: HIGH (blocked local development)
**Already in Skill**: No

**Description**:
`browser.close()` hung indefinitely in local development (`wrangler dev` and `@cloudflare/vite-plugin`). This was caused by WebSocket 'disconnect' event not being triggered in local dev mode. The issue was traced to workerd WebSocket handling differences between local and remote environments.

**Reproduction**:
```typescript
const browser = await puppeteer.launch(env.MYBROWSER);
const page = await browser.newPage();
await page.goto("https://www.example.com");
const content = await page.content();
// This line hangs in local dev (pre-fix)
await browser.close();
```

**Solution/Workaround**:
Fixed in wrangler update post-July 2025. Workaround before fix: Use `wrangler dev --remote` to test against production browser rendering.

**Official Status**:
- [x] Fixed (late July 2025)
- [x] Documented behavior

**Cross-Reference**:
- Related workerd issue: https://github.com/cloudflare/workerd/issues/4327
- Works in production, only affected local dev

---

### Finding 1.2: page.evaluate() with esbuild Minification (__name Injection)

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7107](https://github.com/cloudflare/workers-sdk/issues/7107)
**Date**: 2024-10-27 (closed 2025-10-08)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `page.evaluate()` with arrow functions containing nested function declarations, esbuild's minification injects `__name()` function calls for function naming. However, these functions run in the browser context (not Worker context), causing `ReferenceError: __name is not defined`. This was introduced in wrangler 3.80.1+ due to esbuild changes.

**Reproduction**:
```typescript
// This fails after wrangler 3.80.1
const data = await page.evaluate(async () => {
  function toNumber(str: string | undefined): number | undefined {
    const num = typeof str === 'string' ? str.replaceAll('.', '').replaceAll(',', '.').match(/[+-]?([0-9]*[.])?[0-9]+/) : false
    if (num) {
      return Number(num[0])
    } else {
      return undefined
    }
  }

  return toNumber('123.456')
});
// Error: ReferenceError: __name is not defined
```

**Solution/Workaround**:
1. **Recommended**: Keep functions simple in `page.evaluate()` - avoid nested function declarations
2. **Alternative**: Inline the logic without nested functions:
```typescript
const data = await page.evaluate(async () => {
  const str = '123.456';
  const num = typeof str === 'string' ? str.replaceAll('.', '').replaceAll(',', '.').match(/[+-]?([0-9]*[.])?[0-9]+/) : false;
  return num ? Number(num[0]) : undefined;
});
```
3. **Temporary**: Revert to wrangler 3.80.0 or earlier (not recommended)

**Official Status**:
- [x] Fixed in version 3.83.0+ (2024-11-08)
- [x] Documented in issue comments

**Cross-Reference**:
- Related to esbuild PR: https://github.com/cloudflare/workers-sdk/pull/6902
- Also affects `page.waitForSelector()` with complex callbacks

---

### Finding 1.3: interceptedRequest.respond() Hangs (Fixed)

**Trust Score**: TIER 1 - Official (Puppeteer Repo)
**Source**: [GitHub Issue #67](https://github.com/cloudflare/puppeteer/issues/67)
**Date**: 2024-08-11 (closed 2024-08-16)
**Verified**: Yes - Fixed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using request interception with `interceptedRequest.respond()`, the browser would hang until worker timeout. This prevented mocking responses or intercepting network requests.

**Reproduction**:
```typescript
await page.setRequestInterception(true);
page.on('request', (interceptedRequest) => {
  if (interceptedRequest.isInterceptResolutionHandled()) return;
  if (interceptedRequest.url().endsWith('.png'))
    // This would hang the browser
    interceptedRequest.respond({
      status: 200,
      contentType: 'image/png',
      body: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAADAAAAAlAQ...', 'base64')
    });
  else interceptedRequest.continue();
});
```

**Solution/Workaround**:
Fixed in `@cloudflare/puppeteer@0.0.13` (August 2024). Update to latest version.

**Official Status**:
- [x] Fixed in @cloudflare/puppeteer@0.0.13+
- [x] Documented in GitHub issue

---

### Finding 1.4: Screenshot Viewport Width Off by 10px (Fixed)

**Trust Score**: TIER 1 - Official (Puppeteer Repo)
**Source**: [GitHub Issue #41](https://github.com/cloudflare/puppeteer/issues/41)
**Date**: 2024-05-09 (closed 2024-08-14)
**Verified**: Yes - Fixed
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When setting viewport width via `setViewport()`, screenshots were consistently 10px narrower than specified (e.g., 1000px viewport → 990px screenshot). Height was also affected.

**Reproduction**:
```typescript
const page = await browser.newPage();
await page.setCacheEnabled(false);
await page.setViewport({ width: 1000, height: 1 });
await page.goto("https://www.google.com");

const screenshot = await page.screenshot({ fullPage: true, omitBackground: true });
// Screenshot is 990px wide, not 1000px
```

**Solution/Workaround**:
Fixed in @cloudflare/puppeteer release (August 2024). Update to latest version.

**Official Status**:
- [x] Fixed in version (August 2024)
- [x] Reported by multiple users

---

### Finding 1.5: WebSocket Page Rendering Error (Fixed)

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2026-01-07](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2026-01-07
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Pages that use WebSockets for real-time communication (chat apps, live updates, etc.) were not rendering correctly in Browser Rendering. This affected applications like Discord, Slack clones, or any site with WebSocket-based features.

**Solution/Workaround**:
Fixed in Browser Rendering update (January 7, 2026). Ensure using latest wrangler and browser rendering service.

**Official Status**:
- [x] Fixed (2026-01-07)
- [x] Breaking fix (behavior change)

---

### Finding 1.6: Screenshot Default Viewport Changed to 1920x1080

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-07-29](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-07-29
**Verified**: Yes
**Impact**: MEDIUM (Breaking change)
**Already in Skill**: Partially (mentions 1920x1080 default but not the breaking change)

**Description**:
REST API `/screenshot` endpoint default viewport increased from 800x600 to 1920x1080 in July 2025 update. This is a BREAKING CHANGE for existing implementations that relied on the old default.

**Solution/Workaround**:
Explicitly set viewport if you need specific dimensions:
```typescript
const screenshot = await page.screenshot({
  clip: {
    x: 0,
    y: 0,
    width: 800,
    height: 600
  }
});
```

**Official Status**:
- [x] Breaking change (2025-07-29)
- [x] Documented in changelog

**Cross-Reference**:
- Skill mentions 1920x1080 default but should call out the breaking change from 800x600

---

### Finding 1.7: waitForSelector Now Properly Times Out

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2026-01-07](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2026-01-07
**Verified**: Yes
**Impact**: MEDIUM (Breaking fix)
**Already in Skill**: No

**Description**:
`waitForSelector()` previously did NOT timeout when selectors weren't found, causing indefinite hangs. This has been fixed to properly timeout according to configured timeout values.

**Solution/Workaround**:
No workaround needed - this is a fix. However, code that relied on indefinite waiting may now timeout:
```typescript
// Now properly times out if selector not found
await page.waitForSelector('#dynamic-element', { timeout: 5000 });
```

**Official Status**:
- [x] Fixed (2026-01-07)
- [x] Breaking fix (behavior change)

---

### Finding 1.8: Debug Logging Default Changed

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-06-27](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-06-27
**Verified**: Yes
**Impact**: LOW (Breaking change)
**Already in Skill**: No

**Description**:
Debug logging was ON by default in early versions, causing verbose console output. This changed to OFF by default in late June 2025. Developers who relied on automatic debug logs will no longer see them.

**Solution/Workaround**:
Enable debug logging explicitly:
```typescript
// In Worker environment
process.env.DEBUG = 'puppeteer:*';  // Enable all Puppeteer debug logs
process.env.DEBUG = 'puppeteer:page'; // Enable only page-level logs
```

**Official Status**:
- [x] Breaking change (2025-06-27)
- [x] Documented in changelog

---

### Finding 1.9: JSON Endpoint Improved Error Handling

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-12-03](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-12-03
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
REST API `/json` endpoint now includes `rawAiResponse` field in error responses when AI-generated JSON fails to parse. This helps debug issues where the LLM returns invalid JSON or non-JSON text.

**Solution/Workaround**:
Use the new field for debugging:
```typescript
const response = await fetch('https://api.cloudflare.com/.../json?url=...');
const data = await response.json();
if (data.error) {
  console.log('Raw AI response:', data.rawAiResponse); // New field
}
```

**Official Status**:
- [x] Enhancement (2025-12-03)
- [x] Documented in changelog

---

### Finding 1.10: Playwright Version Updates (v1.55 GA, v1.57)

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-09-25](https://developers.cloudflare.com/browser-rendering/changelog/), [Changelog 2026-01-08](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-09-25, 2026-01-08
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions v1.55, not v1.57)

**Description**:
Playwright support reached GA with v1.55 in September 2025, then upgraded to v1.57 in January 2026. These updates bring new APIs and bug fixes from upstream Playwright.

**Solution/Workaround**:
Update package version:
```bash
npm install @cloudflare/playwright@1.1.0
```

**Official Status**:
- [x] GA release (v1.55)
- [x] Latest version (v1.57)

**Cross-Reference**:
- Skill shows v1.0.0, should update to v1.1.0
- Check Playwright v1.57 changelog for breaking changes

---

### Finding 1.11: Stagehand Framework Support (Beta)

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-09-25](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-09-25
**Verified**: Yes
**Impact**: MEDIUM (New feature)
**Already in Skill**: No

**Description**:
Stagehand, an open-source AI-powered browser automation framework, is now supported via Workers AI. This allows combining natural language instructions with code for browser automation.

**Example**:
```typescript
// Use natural language to control browser
// Details would depend on Stagehand API integration
```

**Official Status**:
- [x] Beta feature (2025-09-25)
- [x] Requires Workers AI binding

**Cross-Reference**:
- May warrant separate documentation or integration guide
- Not yet documented in skill

---

### Finding 1.12: Limit Increases (Free: 3→3, Paid: 10→30)

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog 2025-09-25](https://developers.cloudflare.com/browser-rendering/changelog/), [Changelog 2025-01-31](https://developers.cloudflare.com/browser-rendering/changelog/)
**Date**: 2025-09-25, 2025-01-31
**Verified**: Yes
**Impact**: MEDIUM (Limit changes)
**Already in Skill**: Partially (shows 3 free, 10 paid - should be 3 free, 30 paid)

**Description**:
Paid plan limits tripled in September 2025 from 10 concurrent browsers to 30, and 10 launches/min to 30 launches/min. Free plan limits remain at 3 concurrent, 3 launches/min.

**Current Limits** (as of Sept 2025):
- **Free**: 3 concurrent, 3/min, 10 min/day, 60s timeout
- **Paid**: 30 concurrent, 30/min, 10 hrs/month included, 60s-10min timeout

**Official Status**:
- [x] Current limits (2025-09-25)
- [x] Documented in changelog

**Cross-Reference**:
- Skill shows "10 concurrent, 10 launches/min" for paid → should be "30 concurrent, 30 launches/min"
- REST API rate limits also increased to 180/min paid (was not listed before)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Browser Binding Type Confusion (Fetcher vs Browser)

**Trust Score**: TIER 2 - High-Quality Community (Multiple sources agree)
**Source**: [GitHub Issue #10772](https://github.com/cloudflare/workers-sdk/issues/10772), Community discussions
**Date**: 2025-09-25
**Verified**: Official maintainer response
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions passing binding, not the Fetcher type detail)

**Description**:
Common mistake: developers try to call `env.MYBROWSER.launch()` directly, expecting a browser object. The browser binding is actually a Fetcher (REST API wrapper), not a browser instance. You MUST use `puppeteer.launch(env.MYBROWSER)` or `chromium.launch(env.MYBROWSER)` wrappers.

**Reproduction**:
```typescript
// ❌ WRONG - This fails with "RPC receiver does not implement the method 'launch'"
const browser = await env.MYBROWSER.launch();

// ✅ CORRECT - Use Puppeteer/Playwright wrapper
const browser = await puppeteer.launch(env.MYBROWSER);
```

**Community Validation**:
- Official maintainer (petebacondarwin) confirmed this is expected behavior
- Multiple users hit this issue
- Documented in official examples

**Cross-Reference**:
- Skill mentions "pass env.MYBROWSER to puppeteer.launch()" but doesn't explain WHY (Fetcher type)
- Adding TypeScript type info would prevent this error

---

### Finding 2.2: Rate Limiting Per-Second Enforcement (Not Burst-Friendly)

**Trust Score**: TIER 2 - High-Quality Community (Official docs + community reports)
**Source**: [Cloudflare Docs - Limits](https://developers.cloudflare.com/browser-rendering/limits/)
**Date**: 2025
**Verified**: Official documentation
**Impact**: HIGH
**Already in Skill**: Partially (mentions rate limiting, not the per-second enforcement detail)

**Description**:
Rate limits are enforced with a **fixed per-second fill rate**, NOT as a burst allowance. For example:
- 180 requests/min = 3 requests/sec (spread evenly)
- You CANNOT send all 180 requests at once, even if you haven't used any quota

This is a major gotcha for batch processing scenarios.

**Example**:
```typescript
// ❌ WRONG - This will fail even if you haven't used quota
const urls = [...100 URLs];
await Promise.all(urls.map(url => {
  // All 100 requests sent at once → rate limit error
  return renderScreenshot(url);
}));

// ✅ CORRECT - Throttle to per-second rate
const urls = [...100 URLs];
for (const url of urls) {
  await renderScreenshot(url);
  await new Promise(resolve => setTimeout(resolve, 334)); // ~3/sec
}
```

**Community Validation**:
- Documented in official limits page
- Community reports of unexpected 429 errors
- Similar to Cloudflare D1 rate limiting behavior

**Cross-Reference**:
- Skill mentions rate limiting but doesn't emphasize per-second enforcement
- Should add throttling example to "Known Issues Prevention"

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Bot Detection on Own Zones Requires Enterprise Plan

**Trust Score**: TIER 3 - Community Consensus (Multiple sources, official FAQ confirms)
**Source**: [FAQ](https://developers.cloudflare.com/browser-rendering/faq/), Web search results
**Date**: 2025
**Verified**: Cross-referenced official docs
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions WAF skip rule, not Enterprise requirement)

**Description**:
Browser Rendering is ALWAYS identified as bot traffic by Cloudflare. To allowlist it on your own Cloudflare zones, you need:
1. Enterprise plan (for Bot Management access)
2. WAF skip rule with custom header

Free/Pro/Business plans CANNOT bypass bot detection even on their own sites.

**Solution**:
```typescript
// Enterprise plan customers only:
// 1. Create WAF skip rule with custom header in dashboard
// 2. Pass header in requests
await page.setExtraHTTPHeaders({
  'X-Custom-Auth': 'your-secret-token'
});
```

**Consensus Evidence**:
- Official FAQ states "Enterprise-only allowlist"
- Multiple community sources confirm Enterprise requirement
- ScrapeOps and ZenRows tutorials confirm detection unavoidable without Enterprise

**Recommendation**: Add to "Known Issues Prevention" with clear Enterprise plan requirement

---

### Finding 3.2: Memory Consumption Causes 422 Errors

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Official FAQ](https://developers.cloudflare.com/browser-rendering/faq/), Community reports
**Date**: 2025
**Verified**: Official documentation mentions
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions 422 errors, not specific memory cause)

**Description**:
422 Unprocessable Entity errors often occur when pages consume too much memory during rendering. This includes:
- Heavy JavaScript frameworks
- Large images or videos
- Infinite scroll pages
- Pages with memory leaks

**Solution**:
```typescript
// Reduce memory usage
await page.setJavaScriptEnabled(false); // If you only need HTML/CSS
await page.setRequestInterception(true);
page.on('request', (req) => {
  if (['image', 'stylesheet', 'font'].includes(req.resourceType())) {
    req.abort(); // Block heavy resources
  } else {
    req.continue();
  }
});
```

**Consensus Evidence**:
- Official FAQ lists "memory consumption" as 422 cause
- Community reports of 422 on heavy pages
- Workarounds widely shared

**Recommendation**: Add memory optimization patterns to skill

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: puppeteer.connect() WebSocket Error

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #9792](https://github.com/cloudflare/workers-sdk/issues/9792)
**Date**: 2025-06-29 (closed)
**Verified**: No - Reporter couldn't reproduce

**Why Flagged**:
- [x] Single source only
- [x] Cannot reproduce (OP tried and failed)
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
User reported `puppeteer.connect()` throwing "ws does not work in the browser. Browser clients must use the native WebSocket object" error when connecting to external Browserless container (not Cloudflare Browser Rendering).

**Recommendation**: DO NOT add - this was user error (connecting to external browser, not using Cloudflare binding correctly). Issue closed as cannot reproduce.

---

### Finding 4.2: Vite Plugin indexOf Error

**Trust Score**: TIER 4 - Low Confidence (Fixed with version updates)
**Source**: [GitHub Issue #9589](https://github.com/cloudflare/workers-sdk/issues/9589)
**Date**: 2025-06-13 (closed 2025-08-04)
**Verified**: Fixed with Vite 7 + latest plugin versions

**Why Flagged**:
- [ ] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [x] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
Using `@cloudflare/vite-plugin` with Playwright caused "Cannot read properties of undefined (reading 'indexOf')" error. Fixed by updating to Vite 7 and latest plugin versions.

**Recommendation**: DO NOT add - transient version conflict, resolved with updates. Not a persistent Browser Rendering issue.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| XPath not supported | Known Issues #1 | Fully covered with workaround |
| Browser binding not passed | Known Issues #2 | Fully covered |
| Browser timeout (60s default) | Known Issues #3 | Fully covered with keep_alive |
| Concurrency limits | Known Issues #4 | Partially covered - needs limit update (10→30) |
| Local dev 1MB limit | Known Issues #5 | Fully covered with remote: true |
| Bot protection | Known Issues #6 | Partially covered - needs Enterprise plan detail |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.2 page.evaluate() __name error | Known Issues Prevention | Add as Issue #7 with workaround |
| 1.7 waitForSelector timeout fix | Common Patterns | Note behavior change in waitForSelector usage |
| 1.12 Limit increases (30 concurrent paid) | Pricing & Limits | Update from 10→30 concurrent, 10→30/min for paid |
| 2.2 Rate limiting per-second enforcement | Pricing & Limits | Add throttling example, clarify no burst |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.1 browser.close() hang | Known Issues Prevention | Add historical note + fix date |
| 1.3 interceptedRequest.respond() hang | Known Issues Prevention | Add historical note (fixed) |
| 1.4 Screenshot viewport bug | Known Issues Prevention | Add historical note (fixed) |
| 1.6 Screenshot default viewport change | Pricing & Limits | Call out breaking change from 800x600 |
| 1.8 Debug logging default changed | Configuration | Add debug logging control section |
| 1.9 JSON endpoint rawAiResponse | REST API section | Add if REST API coverage exists |
| 1.11 Stagehand support | AI Integration | Add new section or note under Workers AI |
| 2.1 Fetcher type confusion | Quick Start | Add TypeScript type explanation |
| 3.1 Enterprise plan for bot allowlist | Known Issues #6 | Add Enterprise requirement explicitly |
| 3.2 Memory causes 422 errors | Error Handling | Add memory optimization patterns |

### Priority 3: Update Existing Content

| Finding | Current Content | Update To |
|---------|----------------|-----------|
| 1.10 Playwright version | v1.0.0 | v1.1.0 (Playwright v1.57) |
| 1.12 Paid plan limits | 10 concurrent, 10/min | 30 concurrent, 30/min |
| 1.6 Screenshot default | Mentions 1920x1080 | Note breaking change from 800x600 |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "puppeteer" in workers-sdk | 15 | 5 |
| "playwright" in workers-sdk | 14 | 4 |
| "screenshot" in cloudflare/puppeteer | 7 | 3 |
| Recent releases | 10 | 10 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare browser rendering puppeteer 2024 2025" | 0 | N/A |
| "cloudflare puppeteer screenshot gotcha 2024 2025" | ~10 | Mixed (mostly bypass articles) |

### Official Sources

| Source | Notes |
|--------|-------|
| [Browser Rendering FAQ](https://developers.cloudflare.com/browser-rendering/faq/) | Comprehensive edge cases and limitations |
| [Browser Rendering Limits](https://developers.cloudflare.com/browser-rendering/limits/) | Detailed limit values and timeout info |
| [Changelog](https://developers.cloudflare.com/browser-rendering/changelog/) | Complete 2024-2026 update history |

### Community Sources

| Source | Notes |
|--------|-------|
| [ScrapeOps Puppeteer Guide](https://scrapeops.io/puppeteer-web-scraping-playbook/nodejs-puppeteer-bypass-cloudflare/) | Bot detection insights |
| [ZenRows Bypass Guide](https://www.zenrows.com/blog/puppeteer-cloudflare-bypass) | Detection mechanisms |
| [Browserless Blog](https://www.browserless.io/blog/bypass-cloudflare-with-puppeteer) | 2025 detection updates |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `WebSearch` for Stack Overflow and official docs
- `WebFetch` for FAQ, limits, and changelog pages

**Limitations**:
- GitHub rate limit hit on playwright repo (403 error)
- Stack Overflow had limited recent content specifically about Cloudflare Browser Rendering (most content is about bypassing Cloudflare on other sites)
- Focus was on official sources given limited community discussion

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that finding 1.12 (limit increases to 30) matches current official documentation. Cross-reference all changelog dates.

**For api-method-checker**: Verify `process.env.DEBUG` is available in Workers environment for finding 1.8 debug logging.

**For code-example-validator**: Validate code examples in findings 1.2 (page.evaluate workaround) and 2.2 (throttling example) before adding to skill.

**For skill-findings-applier**: Apply priority 1 and 2 findings to SKILL.md with proper sourcing and examples.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

```markdown
### Issue #7: page.evaluate() Function Name Injection (__name Error)

**Error**: `ReferenceError: __name is not defined`
**Source**: [GitHub Issue #7107](https://github.com/cloudflare/workers-sdk/issues/7107)
**Why It Happens**: esbuild minification injects `__name()` calls in arrow functions with nested declarations, but these run in browser context where the helper doesn't exist
**Prevention**: Keep page.evaluate() functions simple - avoid nested function declarations
**Applies to**: wrangler 3.80.1+ (fixed in 3.83.0+)

**Solution:**
```typescript
// ❌ Avoid nested function declarations
const data = await page.evaluate(async () => {
  function toNumber(str) { /* ... */ }  // May trigger __name injection
  return toNumber('123');
});

// ✅ Inline the logic without nested functions
const data = await page.evaluate(async () => {
  const str = '123.456';
  const num = typeof str === 'string' ? str.replaceAll('.', '').match(/[+-]?([0-9]*[.])?[0-9]+/) : false;
  return num ? Number(num[0]) : undefined;
});
```
```

### Updating Pricing & Limits Section

```markdown
## Pricing & Limits

**Billing GA**: August 20, 2025

**Free Tier**: 10 min/day, 3 concurrent, 3 launches/min, 60s timeout
**Paid Tier**: 10 hrs/month included ($0.09/hr after), 30 concurrent ($2.00/browser after), 30 launches/min, 60s-10min timeout

**Concurrency Calculation**: Monthly average of daily peak usage (e.g., 15 browsers avg = (15 - 10 included) × $2.00 = $10.00/mo)

**Rate Limiting**: Enforced per-second (not burst). 30 req/min = 1 req every 2 seconds. You CANNOT send all 30 at once.

**Example - Throttling for Rate Limits**:
```typescript
// ❌ WRONG - Bursts all requests at once
await Promise.all(urls.map(url => renderScreenshot(url)));

// ✅ CORRECT - Throttle to per-second rate (3/sec for paid)
for (const url of urls) {
  await renderScreenshot(url);
  await new Promise(resolve => setTimeout(resolve, 334)); // ~3/sec
}
```
```

---

**Research Completed**: 2026-01-21 20:45 UTC
**Next Research Due**: After next major Browser Rendering release or quarterly (April 2026)

---

## Sources

- [Puppeteer Guide - How To Bypass Cloudflare with Puppeteer | ScrapeOps](https://scrapeops.io/puppeteer-web-scraping-playbook/nodejs-puppeteer-bypass-cloudflare/)
- [Puppeteer · Cloudflare Browser Rendering docs](https://developers.cloudflare.com/browser-rendering/platform/puppeteer/)
- [How to Bypass Cloudflare With Puppeteer: 2 Working Methods - ZenRows](https://www.zenrows.com/blog/puppeteer-cloudflare-bypass)
- [Bypass Cloudflare with Puppeteer (2025 Guide) – Scrape Protected Sites](https://www.browserless.io/blog/bypass-cloudflare-with-puppeteer)
- [Changelog · Cloudflare Browser Rendering docs](https://developers.cloudflare.com/browser-rendering/changelog/)
- [Browser Rendering now supports local development · Changelog](https://developers.cloudflare.com/changelog/2025-07-22-br-local-dev/)
- [Browser Rendering Playwright GA, Stagehand support (Beta), and higher limits · Changelog](https://developers.cloudflare.com/changelog/2025-09-25-br-playwright-ga-stagehand-limits/)
- [Increased Browser Rendering limits! · Changelog](https://developers.cloudflare.com/changelog/2025-01-30-browser-rendering-more-instances/)
- [Limits · Cloudflare Browser Rendering docs](https://developers.cloudflare.com/browser-rendering/limits/)
- [Frequently asked questions about Cloudflare Browser Rendering · Cloudflare Browser Rendering docs](https://developers.cloudflare.com/browser-rendering/faq/)
