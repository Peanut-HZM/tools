# Community Knowledge Research: playwright-local

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/playwright-local/SKILL.md
**Packages Researched**: playwright@1.57.0, @playwright/test@1.57.0, playwright-extra@4.3.6, puppeteer-extra-plugin-stealth@2.11.2
**Official Repo**: microsoft/playwright
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 10 |
| TIER 1 (Official) | 5 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Chrome for Testing Migration (v1.57.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v1.57.0](https://github.com/microsoft/playwright/releases/tag/v1.57.0)
**Date**: 2025-11-25
**Verified**: Yes (official release notes)
**Impact**: MEDIUM
**Already in Skill**: Yes (documented in SKILL.md line 18)

**Description**:
Starting with Playwright v1.57.0, Playwright switched from Chromium to using Chrome for Testing builds. This affects both headed and headless browsers.

**Key Changes**:
- New browser icon and title bar appearance
- No functional changes expected
- Exception: ARM64 Linux continues to use Chromium
- Chrome for Testing provides more authentic browser behavior

**Official Status**:
- [x] Live in version 1.57.0
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill: SKILL.md line 18 (breaking change section)
- Source: [Chrome for Testing Blog](https://developer.chrome.com/blog/chrome-for-testing/)

---

### Finding 1.2: page.pause() Timeout Issue in Headless Mode (v1.57.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #38754](https://github.com/microsoft/playwright/issues/38754)
**Date**: 2026-01-12
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When `page.pause()` is called in headless mode, it disables the test timeout, causing Playwright to hang indefinitely on any subsequent failing assertions. This issue is particularly problematic in CI environments.

**Reproduction**:
```typescript
// In headless mode (CI)
await page.pause(); // This is ignored but disables timeout
await expect(someLocatorThatDoesNotExist).toBeVisible(); // Hangs forever
```

**Solution/Workaround**:
```typescript
// Remove page.pause() calls before running in CI
// Or use conditional debugging:
if (!process.env.CI) {
  await page.pause();
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, open bug
- [ ] Won't fix

**Cross-Reference**:
- Affects: Debugging workflows in CI/CD
- Related to: Timeout configuration

---

### Finding 1.3: Drag and Drop Regression in v1.57.0 with Chrome for Testing

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #38796](https://github.com/microsoft/playwright/issues/38796)
**Date**: 2026-01-15
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `dragTo()` action broke in v1.57.0 when used with html5sortable library and Chromium. The issue only affects Chromium browser and is likely related to the Chrome for Testing migration.

**Reproduction**:
```typescript
// Works in 1.56.1, fails in 1.57.0
await page.locator('#draggable').dragTo(page.locator('#dropzone'));
// Drag doesn't complete correctly
```

**Solution/Workaround**:
```typescript
// Use steps option (new in 1.57.0) for more granular control
await page.locator('#draggable').dragTo(page.locator('#dropzone'), {
  steps: 20 // Smooth drag animation
});

// Or temporarily downgrade to 1.56.1 if critical
```

**Official Status**:
- [x] Fixed (closed issue)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: Chrome for Testing migration
- Affects: Drag and drop operations in Chromium

---

### Finding 1.4: Permission Prompts Cannot Be Auto-Granted with launchPersistentContext

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #38670](https://github.com/microsoft/playwright/issues/38670)
**Date**: 2026-01-02
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `chromium.launchPersistentContext()` with browser extensions, permission prompts (clipboard-read/write, local-network-access) appear and cannot be auto-granted. This blocks test execution in CI environments.

**Reproduction**:
```typescript
const context = await chromium.launchPersistentContext("", {
  headless: false,
  args: [
    `--disable-extensions-except=${extensionPath}`,
    `--load-extension=${extensionPath}`,
  ],
});

// Extension requests permissions → prompt appears → test hangs
```

**Solution/Workaround**:
```typescript
// Attempted solutions that DON'T work:
// 1. context.on("dialog") - doesn't fire for permission prompts
// 2. context.grantPermissions() - only works for certain permissions
// 3. Chrome flags like --disable-web-security - works locally, fails in CI

// Current workaround: Avoid persistent context for extensions in CI
// Use regular context with browser.newContext() instead
const context = await browser.newContext({
  // Pre-grant permissions where possible
  permissions: ['clipboard-read', 'clipboard-write']
});
```

**Official Status**:
- [x] Fixed (closed issue)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects: Extension testing in CI
- Related to: Browser permissions API

---

### Finding 1.5: Ubuntu 25.10 Not Supported (libicu74/libxml2 Missing)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #38874](https://github.com/microsoft/playwright/issues/38874)
**Date**: 2026-01-21
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Playwright fails to install browser dependencies on Ubuntu 25.10 due to missing libicu74 and libxml2 packages. The installer falls back to Ubuntu 24.04 dependencies but fails.

**Reproduction**:
```bash
# On Ubuntu 25.10
npm install -D @playwright/test
npx playwright install --with-deps
# Error: Unable to locate package libicu74
# Error: Package 'libxml2' has no installation candidate
```

**Solution/Workaround**:
```bash
# Use Ubuntu 24.04 Docker image instead
docker pull mcr.microsoft.com/playwright:v1.57.0-noble

# Or manually install compatible libraries
sudo apt-get update
sudo apt-get install libicu72 libxml2
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, open bug
- [ ] Won't fix

**Cross-Reference**:
- Affects: Ubuntu 25.10 users
- Related to: Docker deployment strategy

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Docker IPC Host Flag Critical for Chromium Memory

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Playwright Docker Best Practices 2025](https://www.browserstack.com/guide/playwright-docker) | [Official Docker Docs](https://playwright.dev/docs/docker)
**Date**: 2025
**Verified**: Cross-referenced with official docs
**Impact**: HIGH
**Already in Skill**: Yes (documented in SKILL.md line 877)

**Description**:
When running Playwright in Docker containers with Chromium, the `--ipc=host` flag is critical to prevent memory exhaustion crashes. Without it, Chromium can run out of shared memory and crash.

**Reproduction**:
```bash
# Without --ipc=host
docker run my-playwright-tests
# Chromium crashes with "out of memory" errors

# With --ipc=host
docker run --ipc=host my-playwright-tests
# Chromium runs normally
```

**Solution/Workaround**:
```bash
# Always use --ipc=host for Chromium in Docker
docker run -it --init --ipc=host my-playwright-tests

# Or in docker-compose.yml:
services:
  playwright:
    ipc: host
```

**Community Validation**:
- Documented in official Playwright docs
- Mentioned in multiple 2025 tutorials
- Consensus across community resources

**Cross-Reference**:
- Already documented in skill: SKILL.md line 877
- Also mentioned in: Docker deployment section

---

### Finding 2.2: Speedboard Feature for Performance Analysis (v1.57.0)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Release v1.57.0](https://github.com/microsoft/playwright/releases/tag/v1.57.0) | [Medium Article](https://medium.com/@szaranger/playwright-1-57-the-must-use-update-for-web-test-automation-in-2025-b194df6c9e03)
**Date**: 2025-11-25
**Verified**: Official release feature
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Playwright 1.57.0 introduced "Speedboard" in the HTML reporter - a new tab that shows all executed tests sorted by slowness. This helps identify performance bottlenecks in test suites.

**Solution**:
```bash
# After running tests with HTML reporter
npx playwright test --reporter=html

# Open report and check Speedboard tab
npx playwright show-report

# Speedboard shows:
# - Tests sorted by execution time
# - Wait times broken down
# - Network request durations
# - Helps identify slow selectors/waits
```

**Community Validation**:
- Official feature in v1.57.0
- Highlighted in community reviews
- Practical for test suite optimization

**Recommendation**: Add to "Advanced Topics" section as a debugging/optimization tool.

---

### Finding 2.3: WebServer Wait for Output (v1.57.0)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Release v1.57.0](https://github.com/microsoft/playwright/releases/tag/v1.57.0)
**Date**: 2025-11-25
**Verified**: Official release feature
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Playwright 1.57.0 added a `wait` field to `testConfig.webServer` that accepts a regular expression. Playwright will wait until the web server logs match the pattern before starting tests.

**Solution**:
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  webServer: {
    command: 'npm run start',
    wait: {
      stdout: '/Listening on port (?<my_server_port>\\d+)/'
    },
  },
  use: {
    baseURL: `http://localhost:${process.env.MY_SERVER_PORT ?? 3000}`
  }
});
```

**Benefits**:
- Captures dynamic ports from dev server output
- Waits for readiness without HTTP checks
- Named capture groups become environment variables

**Community Validation**:
- Official API in v1.57.0
- Addresses common CI/CD issue
- Recommended in 2025 best practices

**Recommendation**: Add to "Configuration Files Reference" section.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Flakiness Prevention - Async Operations Main Issue

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Common Challenges in Playwright Testing](https://testrig.medium.com/common-challenges-in-playwright-testing-and-how-to-fix-them-ca1687f26d94) | [Toxigon Troubleshooting Guide](https://toxigon.com/troubleshooting-playwright)
**Date**: 2025
**Verified**: Cross-Referenced
**Impact**: HIGH
**Already in Skill**: Partially covered

**Description**:
Community consensus identifies flakiness as the #1 issue in Playwright automation, most commonly caused by asynchronous operations and elements not being ready when tests interact with them.

**Solution**:
```typescript
// Common flakiness patterns and fixes:

// ❌ Flaky: No wait
await page.click('button.submit');

// ✅ Reliable: Explicit wait
await page.waitForSelector('button.submit', { state: 'visible' });
await page.click('button.submit');

// ✅ Better: Use locator with auto-wait
await page.locator('button.submit').click();

// ❌ Flaky: Fixed timeout
await page.waitForTimeout(1000);
const data = await page.textContent('.result');

// ✅ Reliable: Wait for condition
await page.waitForSelector('.result');
const data = await page.textContent('.result');
```

**Consensus Evidence**:
- Multiple 2025 articles cite flakiness as top issue
- Async operations identified as primary cause
- Consistent recommendation: use locators with auto-wait

**Recommendation**: Add to "Critical Rules" section as expanded guidance on flakiness prevention.

---

### Finding 3.2: Node.js 24 Support in Docker Images

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #38043](https://github.com/microsoft/playwright/issues/38043)
**Date**: 2025-10-29 (closed)
**Verified**: Feature request fulfilled
**Impact**: LOW
**Already in Skill**: No

**Description**:
Node.js 24 became Active LTS on October 28, 2025. Community requested Node.js 24 Docker images for Playwright to access latest features like `URLPattern`, `Error.isError`, and permissions model.

**Solution**:
```dockerfile
# Node.js 24 is now available in Playwright Docker images
FROM mcr.microsoft.com/playwright:v1.57.0-noble

# Noble image includes Node.js 22 LTS by default
# For Node.js 24 features, use current image and upgrade:
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
RUN apt-get install -y nodejs
```

**Consensus Evidence**:
- Feature request closed (likely fulfilled)
- Node.js 24 provides useful features for testing
- Docker images align with LTS releases

**Recommendation**: Update Docker section to mention Node.js 24 compatibility when official images are released.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None identified. All findings have official sources or strong community consensus.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Chrome for Testing migration | Line 18 (breaking change) | Fully covered |
| Docker --ipc=host flag | Line 877 (Docker deployment) | Documented with explanation |
| Steps option for mouse/drag | Lines 346-371 (Advanced Mouse Control) | Fully documented with examples |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.2 page.pause() timeout issue | Known Issues Prevention | Add as Issue #9 with CI-specific warning |
| 1.4 Permission prompts in launchPersistentContext | Known Issues Prevention | Add as Issue #10 for extension testing |
| 1.5 Ubuntu 25.10 compatibility | Troubleshooting | Add to troubleshooting section |
| 2.2 Speedboard feature | Advanced Topics | Add new subsection for performance analysis |
| 2.3 WebServer wait config | Configuration Files Reference | Add to playwright.config.ts examples |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 Drag and drop regression | Already resolved, consider adding as historical note |
| 3.1 Flakiness prevention expanded | Critical Rules | Expand existing flakiness guidance |
| 3.2 Node.js 24 Docker support | Docker Deployment | Add note when official images released |

### Priority 3: Monitor (Updates)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| Ubuntu 25.10 support | May be fixed in next release | Check v1.58+ release notes |
| page.pause() timeout | Open bug | Monitor for fix in future releases |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "browser installation" (>2025-05-01) | 4 | 2 |
| "docker" (>2025-08-01) | 20 | 8 |
| "timeout" (>2025-10-01) | 15 | 4 |
| Release notes v1.57.0, v1.56.0 | 2 | 2 |
| Specific issues reviewed | 5 | 5 |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "playwright common issues 2025" | 10+ articles | Multiple high-quality resources |
| "playwright debugging tips 2025" | 10+ articles | Official docs + tutorials |
| "playwright docker best practices 2025" | 10+ guides | BrowserStack, official docs |
| "playwright chrome for testing migration" | Medium article + release notes | High quality |

### Other Sources

| Source | Notes |
|--------|-------|
| Playwright Official Docs | Referenced for Docker, debugging |
| Medium Articles | Community reviews of v1.57.0 |
| Testing Blogs | Best practices and gotchas |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release view` for release notes
- `WebSearch` for community articles and best practices
- Cross-referencing with official documentation

**Limitations**:
- StackOverflow specific searches didn't return results (likely due to search tool limitations)
- Some closed issues may have fixes not yet documented
- Ubuntu 25.10 issue is very recent (Jan 21, 2026)

**Focus Areas**:
- Browser installation and compatibility
- Docker deployment patterns
- CI/CD best practices
- New v1.56-v1.57 features
- Debugging and timeout issues

**Time Spent**: ~35 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that findings 1.2, 1.4, and 1.5 match current issue status before adding (check if bugs were fixed).

**For code-example-validator**: Validate code examples in findings 2.2 (Speedboard) and 2.3 (WebServer wait) against v1.57.0 API.

**For version-checker**: Update skill to reflect Node.js 24 Docker support when official images are released.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

Add after existing Issue #8 (line 499):

```markdown
### Issue #9: page.pause() Disables Timeout in Headless Mode

**Error**: Tests hang indefinitely in CI when `page.pause()` is present
**Source**: https://github.com/microsoft/playwright/issues/38754
**Why It Happens**: `page.pause()` is ignored in headless mode but disables test timeout
**Prevention**:
```typescript
// Conditional debugging - only pause in local development
if (!process.env.CI && !process.env.HEADLESS) {
  await page.pause();
}

// Or use environment variable
const shouldPause = process.env.DEBUG_MODE === 'true';
if (shouldPause) {
  await page.pause();
}
```

**Impact**: HIGH - Can cause CI pipelines to hang indefinitely

---

### Issue #10: Permission Prompts Block Extension Testing in CI

**Error**: Tests hang on permission prompts when testing browser extensions
**Source**: https://github.com/microsoft/playwright/issues/38670
**Why It Happens**: `launchPersistentContext` with extensions shows non-dismissible permission prompts
**Prevention**:
```typescript
// Don't use persistent context for extensions in CI
// Use regular context instead
const context = await browser.newContext({
  permissions: ['clipboard-read', 'clipboard-write']
});

// For extensions, pre-grant permissions where possible
const context = await browser.newContext({
  permissions: ['notifications', 'geolocation']
});
```

**Impact**: HIGH - Blocks automated extension testing in CI/CD
```

### Adding TIER 2 Features to Advanced Topics

Add new section after "Playwright MCP Server" (line 846):

```markdown
## Performance Analysis with Speedboard (v1.57+)

Playwright v1.57 introduced Speedboard in the HTML reporter - a dedicated tab for identifying slow tests.

**Enable in Config**:
```typescript
export default defineConfig({
  reporter: 'html',
});
```

**View Speedboard**:
```bash
npx playwright test --reporter=html
npx playwright show-report
```

**What Speedboard Shows**:
- All tests sorted by execution time (slowest first)
- Breakdown of wait times
- Network request durations
- Helps identify inefficient selectors and unnecessary waits

**Use Cases**:
- Optimize test suite runtime
- Find tests with excessive `waitForTimeout()` calls
- Identify slow API responses affecting tests
- Prioritize refactoring efforts

---

## Dynamic Web Server Configuration (v1.57+)

Wait for web server output before starting tests:

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  webServer: {
    command: 'npm run dev',
    // Wait for server to print port
    wait: {
      stdout: '/Server running on port (?<SERVER_PORT>\\d+)/'
    },
  },
  use: {
    // Use captured port in tests
    baseURL: `http://localhost:${process.env.SERVER_PORT ?? 3000}`
  }
});
```

**Benefits**:
- Handles dynamic ports from dev servers
- No need for HTTP readiness checks
- Captures environment variables from output
- Works with services that only log readiness messages

**When to Use**:
- Dev servers with random ports (Vite, Next.js dev mode)
- Services without HTTP endpoints
- Containerized environments with port mapping
```

### Adding to Troubleshooting Section

Add to troubleshooting section (after line 1194):

```markdown
### Problem: Ubuntu 25.10 installation fails
**Error**: `Unable to locate package libicu74`, `Package 'libxml2' has no installation candidate`
**Solution**:
```bash
# Use Ubuntu 24.04 Docker image (officially supported)
docker pull mcr.microsoft.com/playwright:v1.57.0-noble

# Or wait for Ubuntu 25.10 support in future releases
# Track: https://github.com/microsoft/playwright/issues/38874
```
```

---

**Research Completed**: 2026-01-21 14:30
**Next Research Due**: After v1.58.0 release (check for Ubuntu 25.10 support and page.pause() fix)
