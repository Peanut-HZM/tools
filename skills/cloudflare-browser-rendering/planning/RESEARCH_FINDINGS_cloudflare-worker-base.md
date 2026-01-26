# Community Knowledge Research: cloudflare-worker-base

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-worker-base/SKILL.md
**Packages Researched**: @cloudflare/workers-types@4.20260103.0, wrangler@4.59.2, @cloudflare/vite-plugin@1.21.0
**Official Repo**: cloudflare/workers-sdk
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 9 |

**Key Themes**:
- Vite 8 compatibility issues (post-May 2025)
- Auto-provisioning beta edge cases (Oct 2025+)
- Vite plugin regressions with `base` option (Jan 2026)
- SSR module duplication with React (resolved)
- New `--x-autoconfig` feature for framework detection (Dec 2025)

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Vite 8 Breaks nodejs_compat with require() Calls

**Trust Score**: TIER 1 - Official (Active Issue)
**Source**: [workers-sdk #11948](https://github.com/cloudflare/workers-sdk/issues/11948)
**Date**: 2026-01-16
**Verified**: Yes - Maintainer confirmed investigating
**Impact**: HIGH (Breaking change for Vite 8 users)
**Already in Skill**: No

**Description**:
When using Vite 8 with `@cloudflare/vite-plugin` and `nodejs_compat` flag, `require()` calls to Node built-in modules fail. Vite 8 uses Rolldown bundler which doesn't convert external `require` to `import` to avoid semantics changes. Since Workers don't expose `require()`, the bundled code throws: `Calling require for "buffer" in an environment that doesn't expose the require function`.

**Reproduction**:
```typescript
// Vite 8 output breaks:
var __require = /* @__PURE__ */ ((x) =>
  typeof require !== "undefined" ? require :
  typeof Proxy !== "undefined" ? new Proxy(x, {
    get: (a, b) => (typeof require !== "undefined" ? require : a)[b]
  }) : x
)(function(x) {
  if (typeof require !== "undefined") return require.apply(this, arguments);
  throw Error("Calling `require` for \"" + x + "\" in an environment that doesn't expose the `require` function.");
});
```

**Solution/Workaround**:
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import { cloudflare } from '@cloudflare/vite-plugin'
import { esmExternalRequirePlugin } from 'vite'
import { builtinModules } from 'node:module'

export default defineConfig({
  plugins: [
    cloudflare(),
    esmExternalRequirePlugin({
      external: [/^node:/, ...builtinModules],
    }),
  ],
})
```

**Official Status**:
- [x] Known issue, workaround required
- [ ] Fix in progress (Vite team opened PR: https://github.com/vitejs/vite/pull/21452)
- [ ] Tests skipped in workers-sdk for Vite 8

**Cross-Reference**:
- Affects: Vite 8.x with @cloudflare/vite-plugin 1.21.0+
- Related: nodejs_compat flag in wrangler.jsonc
- Maintainer @jamesopstad confirmed investigating (2026-01-16)

---

### Finding 1.2: Vite Plugin Regression with base Option for SPAs

**Trust Score**: TIER 1 - Official (Confirmed Regression)
**Source**: [workers-sdk #11857](https://github.com/cloudflare/workers-sdk/issues/11857)
**Date**: 2026-01-10
**Verified**: Yes - Maintainer confirmed intentional change
**Impact**: HIGH (Breaks SPA routing with base path)
**Already in Skill**: No

**Description**:
Since `@cloudflare/vite-plugin@1.13.8`, using Vite's `base` option breaks SPA serving in development. Prior to 1.13.8, Vite stripped the base path before passing to Asset Worker. Now the full URL (with base) is passed, causing 404s. Platform support for `assets.base` is planned for Q1 2026.

**Reproduction**:
```typescript
// vite.config.ts
export default {
  base: "/prefix",
  plugins: [cloudflare()],
}

// Dev server:
// curl http://localhost:5173/prefix → 404 (broken since 1.13.8)
// curl http://localhost:5173/prefix -H 'Sec-Fetch-Mode: navigate' → 200 (workaround)
```

**Solution/Workaround**:
```typescript
// worker.ts - Strip base path manually in dev mode
if (import.meta.env.DEV) {
  url.pathname = url.pathname.replace(import.meta.env.BASE_URL, '');
  if (url.pathname === '/') {
    return this.env.ASSETS.fetch(request);
  }
  request = new Request(url, request);
}
```

**Official Status**:
- [x] Documented behavior change (dev now matches prod)
- [ ] Platform feature needed: `assets.base` option ([workers-sdk #9885](https://github.com/cloudflare/workers-sdk/issues/9885))
- [ ] Will be worked on Q1 2026

**Cross-Reference**:
- Introduced in: @cloudflare/vite-plugin@1.13.8 (PR #10593)
- Related issue: [workers-sdk #9885](https://github.com/cloudflare/workers-sdk/issues/9885)
- Maintainer note: "Actually an improvement, brings dev into line with prod"

---

### Finding 1.3: Auto-Provisioning Prefers Binding Over database_name

**Trust Score**: TIER 1 - Official (Confirmed Bug)
**Source**: [workers-sdk #11870](https://github.com/cloudflare/workers-sdk/issues/11870)
**Date**: 2026-01-12
**Verified**: Yes - Maintainer opened issue
**Impact**: MEDIUM (Confusing behavior, not breaking)
**Already in Skill**: Partially (auto-provisioning documented, not this edge case)

**Description**:
When using auto-provisioning (wrangler 4.45+), if you provide only `binding` without `database_name`, Wrangler auto-creates the database using the binding name. The docs state `database_name` is required, but auto-provisioner doesn't enforce this. This causes confusion because `wrangler dev` and `d1` subcommands prefer `database_id` → `database_name` → `binding`, so you get fresh local databases on first provision.

**Reproduction**:
```jsonc
// wrangler.jsonc - This works but shouldn't according to docs
{
  "d1_databases": [
    { "binding": "DB" }  // No database_name provided
  ]
}

// wrangler deploy → creates database named "DB" (uses binding name)
// wrangler dev → creates local database with different behavior
```

**Solution/Workaround**:
Always provide `database_name` explicitly:
```jsonc
{
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "my-app-db"  // ✅ Explicit name
    }
  ]
}
```

**Official Status**:
- [x] Known issue (filed by maintainer)
- [ ] Fix planned: Make database_name required with actionable warning
- [ ] Subcommands will prefer: database_id → database_name → binding

**Cross-Reference**:
- Related PR: [workers-sdk #11804](https://github.com/cloudflare/workers-sdk/pull/11804)
- Affects: Wrangler 4.45+ with auto-provisioning
- Also applies to: R2 buckets (`bucket_name` vs `binding`)

---

### Finding 1.4: Response Already Sent Error in Dev (.wrangler Cache Corruption)

**Trust Score**: TIER 1 - Official (Community-Reported, Common Issue)
**Source**: [workers-sdk #11932](https://github.com/cloudflare/workers-sdk/issues/11932)
**Date**: 2026-01-15
**Verified**: Yes - Multiple user confirmations
**Impact**: MEDIUM (Development only, fixable by cache clear)
**Already in Skill**: No

**Description**:
During `wrangler dev`, users encounter random "The response has already been sent" errors during normal GET requests. Only happens in full Workers mode (not Cloudflare Pages). The error is sporadic and affects navigation/page loads.

**Reproduction**:
```bash
# Happens randomly during development
[wrangler:info] GET /plan 200 OK (6ms)
✘ [ERROR] Uncaught Error: ResponseSentError: The response has already been sent to the browser and cannot be altered.
```

**Solution/Workaround**:
```bash
# Delete cache directories
rm -rf .wrangler dist node_modules/.vite

# Recreate local D1 databases if needed
wrangler d1 execute DB --local --file schema.sql
```

**Official Status**:
- [x] Community-reported pattern
- [ ] Root cause unclear (suspected: stale cache or state corruption)
- [ ] Workaround reliable: clearing .wrangler fixes it

**Cross-Reference**:
- Similar to: HMR race conditions ([workers-sdk #9518](https://github.com/cloudflare/workers-sdk/issues/9518))
- May be related to: Workerd state management in local dev

---

### Finding 1.5: Wrangler 4.55+ Auto-Config for Frameworks

**Trust Score**: TIER 1 - Official (New Feature)
**Source**: [Cloudflare Changelog 2025-12-16](https://developers.cloudflare.com/changelog/2025-12-16-wrangler-autoconfig/)
**Date**: 2025-12-16
**Verified**: Yes - Official feature launch
**Impact**: LOW (Quality of life improvement)
**Already in Skill**: No

**Description**:
Wrangler 4.55+ includes experimental `--x-autoconfig` flag that automatically detects framework and configures wrangler.jsonc for deployment. Supports static sites (HTML, Jekyll, Hugo) and frameworks (React, Vue, Waku, TanStack Start). Detects assets directory and build commands automatically.

**Usage**:
```bash
# Automatic framework detection and deployment
npx wrangler deploy --x-autoconfig

# Works from any web app directory
cd my-react-app && npx wrangler deploy --x-autoconfig

# Also works with wrangler setup
npx wrangler setup
```

**Supported Frameworks** (as of 4.59.0):
- Static sites: HTML, Jekyll, Hugo
- React (Vite)
- Vue (Vite)
- Waku (updated for 0.12.5-1.0.0-alpha.1-0 in wrangler@4.59.0)
- TanStack Start

**Official Status**:
- [x] Experimental feature (--x- prefix)
- [x] Released in Wrangler 4.55.0
- [x] Actively maintained (Waku support updated Jan 2026)

**Cross-Reference**:
- Related skill sections: Quick Start (could mention this as alternative)
- See also: `wrangler setup` command for project initialization

---

### Finding 1.6: ESM Package Crashes Wrangler (uuid@11)

**Trust Score**: TIER 1 - Official (Under Investigation)
**Source**: [workers-sdk #11957](https://github.com/cloudflare/workers-sdk/issues/11957)
**Date**: 2026-01-17
**Verified**: Partial - Maintainer cannot reproduce, user confirms consistently
**Impact**: LOW (Package-specific, workarounds available)
**Already in Skill**: No

**Description**:
Using `uuid@11` (ESM) in Workers causes runtime crash with "fileURLToPath undefined". The issue is inconsistent - maintainer cannot reproduce, but user reports consistent failure. `uuid@11` uses Node-specific `fileURLToPath` from `node:url`, which should be supported by `nodejs_compat` flag.

**Reproduction** (user report):
```typescript
// ESM Worker with uuid@11
import { v4 as uuidv4 } from 'uuid';

// Runtime crash (not build time):
// "fileURLToPath undefined" in uuid/dist/esm/native.js
```

**Solution/Workaround**:
```typescript
// Option 1: Use Web Crypto API instead
const uuid = crypto.randomUUID(); // ✅ Native Workers API

// Option 2: Downgrade to uuid@9
npm install uuid@9
```

**Official Status**:
- [x] Awaiting minimal reproduction
- [ ] `fileURLToPath` should work with nodejs_compat (maintainer confused)
- [ ] May be environment-specific (Debian 13, Node 20)

**Cross-Reference**:
- Related: nodejs_compat flag support for Node APIs
- Alternative: Web Crypto `crypto.randomUUID()` (native Workers API)
- Note: crypto.randomUUID() is already production-ready for UUIDs

---

### Finding 1.7: Wrangler Detects AI Coding Agents (Analytics Feature)

**Trust Score**: TIER 1 - Official (New Feature)
**Source**: [wrangler@4.59.0 Release Notes](https://github.com/cloudflare/workers-sdk/releases/tag/wrangler@4.59.0)
**Date**: 2026-01-13
**Verified**: Yes - Official feature release
**Impact**: LOW (Analytics only, no behavior change)
**Already in Skill**: No

**Description**:
Wrangler 4.59.0 includes AI agent detection using the `am-i-vibing` library. When commands are executed by AI coding agents (Claude Code, Cursor, GitHub Copilot), the agent ID is included in analytics events. This helps Cloudflare understand AI-assisted development patterns.

**Implementation**:
```typescript
// Analytics event includes agent property
{
  command: "deploy",
  agent: "claude-code" | "cursor-agent" | null,
  // ... other analytics
}
```

**Detected Agents**:
- claude-code (Claude Code CLI)
- cursor-agent (Cursor AI)
- github-copilot (GitHub Copilot)
- null (no agent detected)

**Privacy Note**: Only agent type is sent, no code or project data.

**Official Status**:
- [x] Released in wrangler@4.59.0 (2026-01-13)
- [x] Uses am-i-vibing library
- [x] Opt-out: Same as existing analytics opt-out

**Cross-Reference**:
- Related: Wrangler telemetry settings
- No user action needed (passive detection)

---

### Finding 1.8: Bundler Breaks Durable Objects with discord.js

**Trust Score**: TIER 1 - Official (Active Issue)
**Source**: [workers-sdk #11790](https://github.com/cloudflare/workers-sdk/issues/11790)
**Date**: 2026-01-04
**Verified**: Yes - Reproduction provided
**Impact**: MEDIUM (Specific to discord.js, workaround exists)
**Already in Skill**: No

**Description**:
When a Durable Object imports from a module that imports `discord.js`, Wrangler's bundler fails with "Super expression must either be null or a function". This appears to be an esbuild bundling issue with discord.js's class inheritance patterns in Workers context.

**Reproduction**:
```typescript
// Durable Object
export class MyDO {
  constructor(state, env) {
    // Imports module that uses discord.js
    const { someFunc } = await import('./helpers');
  }
}

// helpers.ts
import { Client } from 'discord.js';
// Bundler fails: Super expression must either be null or a function
```

**Solution/Workaround**:
```typescript
// Option 1: Don't use discord.js in Durable Objects
// Use REST API instead
const response = await fetch('https://discord.com/api/v10/...', {
  headers: { 'Authorization': `Bot ${env.DISCORD_TOKEN}` }
});

// Option 2: External discord.js (if feasible)
// vite.config.ts
export default {
  build: {
    rollupOptions: {
      external: ['discord.js']
    }
  }
}
```

**Official Status**:
- [x] Issue open with reproduction
- [ ] Root cause: esbuild class inheritance transform
- [ ] No fix timeline yet

**Cross-Reference**:
- Related: esbuild bundling of complex class hierarchies
- Alternative: Use Discord REST API instead of discord.js library
- See: [Discord API Docs](https://discord.com/developers/docs/intro)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: vite-tsconfig-paths v6 Breaks React SSR (Resolved)

**Trust Score**: TIER 2 - High-Quality Community (Resolved)
**Source**: [workers-sdk #11825](https://github.com/cloudflare/workers-sdk/issues/11825) (closed)
**Date**: 2026-01-07
**Verified**: Yes - Maintainer confirmed root cause, user confirmed fix
**Impact**: MEDIUM (Resolved by downgrade)
**Already in Skill**: No

**Description**:
Using `vite-tsconfig-paths@6.x` with `@cloudflare/vite-plugin` causes "Invalid hook call" errors in React SSR. The plugin doesn't follow path aliases during dependency scan, causing modules to be discovered late and creating duplicate React instances. Downgrading to `vite-tsconfig-paths@5.1.4` fixes it.

**Reproduction**:
```typescript
// Using vite-tsconfig-paths@6.x
import viteTsconfigPaths from 'vite-tsconfig-paths'

export default {
  plugins: [
    viteTsconfigPaths(),
    cloudflare({ viteEnvironment: { name: 'ssr' } }),
  ]
}

// Error: Invalid hook call. Hooks can only be called inside of the body of a function component.
// TypeError: Cannot read properties of null (reading 'useContext')
```

**Solution/Workaround**:
```bash
# Downgrade to v5.1.4
npm install vite-tsconfig-paths@5.1.4
```

**Community Validation**:
- Reported by: @mengxi-ream
- Diagnosed by: @jamesopstad (Cloudflare maintainer)
- Root cause: [vite-tsconfig-paths PR #200](https://github.com/aleclarson/vite-tsconfig-paths/pull/200)
- User confirmed fix works

**Cross-Reference**:
- Related: React duplicate instance patterns
- Note: Not a vite-plugin bug, but worth documenting as common issue
- Status: Resolved by using vite-tsconfig-paths@5.1.4

---

### Finding 2.2: Wrangler 4 Breaking Changes Summary (March 2025)

**Trust Score**: TIER 2 - High-Quality Community (Official Docs)
**Source**: [Cloudflare Workers Changelog - Wrangler v4](https://developers.cloudflare.com/workers/wrangler/migration/update-v3-to-v4/)
**Date**: 2025-03-13 (Wrangler v4 release)
**Verified**: Yes - Official migration guide
**Impact**: HIGH (Major version breaking changes)
**Already in Skill**: Partially (some already documented)

**Description**:
Wrangler v4 breaking changes summary (already in skill, but good to validate completeness):

**Breaking Changes**:
1. **Node.js 16 dropped** - Minimum Node.js 18+
2. **esbuild v0.17.19 → v0.24** - May affect dynamic imports
3. **Local mode by default** - All commands require `--remote` flag for API calls
4. **Removed features**:
   - `--legacy-assets` (use Workers Static Assets)
   - `--node-compat` (use `nodejs_compat` flag)
   - `wrangler version` (use `wrangler --version`)
   - `getBindingsProxy()` (use `getPlatformProxy()`)

**Solution**:
```bash
# Migration checklist
# 1. Update Node.js
node --version  # Must be 18+

# 2. Replace legacy assets
# wrangler.jsonc
{
  "assets": {
    "directory": "./public/"
  }
}

# 3. Use nodejs_compat flag
{
  "compatibility_flags": ["nodejs_compat"]
}

# 4. Update API calls
# Old: wrangler kv get → queries remote
# New: wrangler kv get → queries local (add --remote for API)

# 5. Update imports
// Old: import { getBindingsProxy } from 'wrangler'
// New: import { getPlatformProxy } from 'wrangler'
```

**Official Status**:
- [x] Released March 2025
- [x] Wrangler v3 supported until Q1 2027
- [x] Official migration guide available

**Cross-Reference**:
- Already in skill: Recent Updates section mentions Wrangler v4
- Could add: Specific migration checklist
- See: [Migration Guide](https://developers.cloudflare.com/workers/wrangler/migration/update-v3-to-v4/)

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Higher Asset Count Limits (100K) for Pages

**Trust Score**: TIER 3 - Community Consensus (Official Feature, Limited Rollout)
**Source**: [wrangler@4.59.0 Release Notes](https://github.com/cloudflare/workers-sdk/releases/tag/wrangler@4.59.0)
**Date**: 2026-01-13
**Verified**: Yes - Official feature, per-account basis
**Impact**: LOW (Only affects large static sites)
**Already in Skill**: No

**Description**:
Wrangler can now read asset count limits from JWT claims during Pages deployments, allowing selected accounts to upload up to 100,000 assets (up from default 20,000). This is enabled on a per-account basis by Cloudflare.

**Usage**:
```bash
# No configuration needed - automatic if enabled for your account
wrangler pages deploy ./dist

# If you have >20k assets and it's not working:
# Contact Cloudflare support to enable higher limits
```

**Consensus Evidence**:
- Official feature in wrangler@4.59.0
- Opt-in per account (not automatic)
- Default remains 20,000 assets

**Recommendation**: Add to Advanced Topics section as optional scaling feature

**Cross-Reference**:
- Related: Static Assets deployment
- Target users: Large monorepos, design systems
- Note: May have additional costs (verify with Cloudflare)

---

### Finding 3.2: Wrangler Types --check Flag for CI/CD

**Trust Score**: TIER 3 - Community Consensus (Official Feature)
**Source**: [wrangler@4.59.0 Release Notes](https://github.com/cloudflare/workers-sdk/releases/tag/wrangler@4.59.0)
**Date**: 2026-01-13
**Verified**: Yes - Official feature
**Impact**: LOW (Quality of life for CI/CD)
**Already in Skill**: No

**Description**:
Wrangler 4.59.0 adds `--check` flag to `wrangler types` command. Verifies generated types are up-to-date without regenerating. Useful for pre-commit hooks and CI pipelines to ensure types are committed after config changes.

**Usage**:
```bash
# In CI/CD pipeline
wrangler types --check
# Exit code 0: Types up-to-date
# Exit code 1: Types out-of-date

# Example GitHub Actions
jobs:
  check-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install
      - run: npx wrangler types --check
```

**Consensus Evidence**:
- Official feature in wrangler@4.59.0
- Community-requested (PR #11852)
- Solves CI/CD pain point

**Recommendation**: Add to CI/CD section or Quick Tips

**Cross-Reference**:
- Related: TypeScript setup, pre-commit hooks
- See also: `wrangler types` command in docs

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Static Assets routing conflicts (run_worker_first) | Known Issues #2 | Fully covered with issue #8879 |
| Export syntax (`export default app` vs `{ fetch }`) | Known Issues #1 | Fully covered with hono #3955 |
| Auto-provisioning basics (Wrangler 4.45+) | Auto-Provisioning section | Covered, but could expand edge cases |
| Wrangler v4 release (March 2025) | Recent Updates | Mentioned, could add migration checklist |
| Free tier 429 errors with run_worker_first | Known Issues #8 | Fully covered with docs link |
| HMR race condition | Known Issues #4 | Covered (fixed in vite-plugin@1.13.13+) |
| Gradual rollouts asset mismatch | Known Issues #7 | Fully covered with docs link |
| Service Worker → ES Module migration | Known Issues #6 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Vite 8 nodejs_compat breaks | Known Issues Prevention | Add as Issue #9 with workaround |
| 1.2 Vite plugin base option regression | Known Issues Prevention | Add as Issue #10 with dev-mode workaround |
| 1.3 Auto-provisioning binding preference | Auto-Provisioning section | Expand with edge case: always specify database_name |
| 1.4 Response already sent cache bug | Common Troubleshooting | Add to troubleshooting section |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.5 --x-autoconfig feature | Quick Start | Alternative setup method (1 command deploy) |
| 1.8 discord.js bundler issue | Known Issues or Community Tips | Package-specific, but common library |
| 2.1 vite-tsconfig-paths v6 SSR | Community Tips | Resolved, but worth documenting |
| 2.2 Wrangler v4 migration checklist | Recent Updates | Add explicit migration steps |

### Priority 3: Monitor (TIER 3, Low Priority)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.6 uuid@11 ESM crash | Watch for resolution | Cannot reproduce, user-specific? |
| 1.7 AI agent detection | Ignore | Analytics only, no user impact |
| 3.1 100K asset limit | Advanced Topics | Opt-in feature, niche use case |
| 3.2 --check flag for types | Quick Tips | Nice to have, low priority |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Issues created after 2025-05-01 | 50 | 12 |
| "static assets" issues | 20 | 3 |
| "wrangler 4" issues | 20 | 2 |
| Latest releases (wrangler@4.59.0+) | 15 | 4 |

### Cloudflare Docs & Changelogs

| Source | Notes |
|--------|-------|
| [Workers Changelog](https://developers.cloudflare.com/workers/platform/changelog/) | Wrangler v4 breaking changes |
| [Wrangler Migration Guide](https://developers.cloudflare.com/workers/wrangler/migration/update-v3-to-v4/) | Official v3→v4 migration |
| [Changelog - Autoconfig](https://developers.cloudflare.com/changelog/2025-12-16-wrangler-autoconfig/) | --x-autoconfig feature |
| [Changelog - Auto-provisioning](https://developers.cloudflare.com/changelog/2025-10-24-automatic-resource-provisioning/) | KV/R2/D1 auto-provisioning beta |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare workers" Stack Overflow 2025-2026 | 0 | N/A (no recent SO posts with "gotcha" keyword) |
| "wrangler 4 breaking changes" | 6 | HIGH (official docs + changelog) |
| "@cloudflare/vite-plugin" issues 2025-2026 | 10 | HIGH (GitHub issues + docs) |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery (cloudflare/workers-sdk)
- `gh issue view` for detailed issue content
- `gh release list` for version tracking
- `WebSearch` for Cloudflare docs and community content

**Focus Areas**:
- Post-May 2025 issues (training cutoff)
- Breaking changes in Wrangler 4.45+ (auto-provisioning era)
- Vite plugin regressions (1.13.8+, 1.21.0+)
- SSR and bundling edge cases

**Limitations**:
- Stack Overflow has minimal recent Workers content (most activity on GitHub)
- Some issues awaiting reproduction (uuid@11 crash)
- Auto-provisioning is beta, edge cases still emerging

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify finding 1.2 (vite base option) against latest docs - is `assets.base` shipped yet?
- Cross-reference finding 1.3 (auto-provisioning) with current wrangler.jsonc schema docs
- Check if finding 2.2 (Wrangler v4 migration) matches official migration guide exactly

**For api-method-checker**:
- Verify `esmExternalRequirePlugin` API exists in Vite 8 (finding 1.1)
- Confirm `getPlatformProxy()` API signature matches docs (finding 2.2)

**For code-example-validator**:
- Test Vite 8 workaround code (finding 1.1) in actual Vite 8 project
- Validate dev-mode base path stripping code (finding 1.2)
- Test cache clear commands (finding 1.4) don't break local D1

---

## Integration Guide

### Adding to Known Issues Section

```markdown
### Issue #9: Vite 8 Breaks nodejs_compat with require()

**Error**: `Calling require for "buffer" in an environment that doesn't expose the require function`
**Source**: [workers-sdk #11948](https://github.com/cloudflare/workers-sdk/issues/11948)
**Affected Versions**: Vite 8.x with @cloudflare/vite-plugin 1.21.0+
**Why It Happens**: Vite 8 uses Rolldown bundler which doesn't convert `require()` to `import` for external modules. Workers don't expose `require()` function.

**Prevention**:
```typescript
// vite.config.ts - Add esmExternalRequirePlugin
import { esmExternalRequirePlugin } from 'vite'
import { builtinModules } from 'node:module'

export default defineConfig({
  plugins: [
    cloudflare(),
    esmExternalRequirePlugin({
      external: [/^node:/, ...builtinModules],
    }),
  ],
})
```

**Status**: Workaround available. Vite team working on fix ([vitejs/vite#21452](https://github.com/vitejs/vite/pull/21452)).

---

### Issue #10: Vite base Option Breaks SPA Routing (1.13.8+)

**Error**: `curl http://localhost:5173/prefix` returns 404 instead of index.html
**Source**: [workers-sdk #11857](https://github.com/cloudflare/workers-sdk/issues/11857)
**Affected Versions**: @cloudflare/vite-plugin 1.13.8+
**Why It Happens**: Plugin now passes full URL with base path to Asset Worker (matching prod behavior). Platform support for `assets.base` not yet available.

**Prevention** (dev-mode workaround):
```typescript
// worker.ts - Strip base path in development
if (import.meta.env.DEV) {
  url.pathname = url.pathname.replace(import.meta.env.BASE_URL, '');
  if (url.pathname === '/') {
    return this.env.ASSETS.fetch(request);
  }
  request = new Request(url, request);
}
```

**Status**: Intentional change to align dev with prod. Platform feature `assets.base` planned for Q1 2026 ([workers-sdk #9885](https://github.com/cloudflare/workers-sdk/issues/9885)).
```

### Adding to Auto-Provisioning Section

```markdown
## Auto-Provisioning (Wrangler 4.45+)

**Default Behavior**: Wrangler automatically provisions R2 buckets, D1 databases, and KV namespaces when deploying.

**Critical: Always Specify Resource Names**

⚠️ **Edge Case**: If you provide only `binding` without `database_name`, Wrangler uses the binding name as the database name. This causes confusing behavior with `wrangler dev` and `d1` subcommands, which prefer `database_id` → `database_name` → `binding`.

```jsonc
// ❌ DON'T: Binding-only creates database named "DB"
{
  "d1_databases": [{ "binding": "DB" }]
}

// ✅ DO: Explicit names prevent confusion
{
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "my-app-db"  // Always specify!
    }
  ]
}
```

**Source**: [workers-sdk #11870](https://github.com/cloudflare/workers-sdk/issues/11870)
```

### Adding to Quick Start (Alternative Method)

```markdown
## Quick Start Option 2: Auto-Config (Wrangler 4.55+)

For supported frameworks, use one-command automatic setup:

```bash
# Automatic framework detection and deployment
cd my-web-app
npx wrangler deploy --x-autoconfig

# Detects: React, Vue, Waku, TanStack Start, static HTML
# Configures: Assets directory, build commands, wrangler.jsonc
# Deploys: Immediately to Cloudflare Workers
```

**Supported**:
- Static sites (HTML, Jekyll, Hugo)
- React + Vite
- Vue + Vite
- Waku
- TanStack Start

**Source**: [Wrangler Auto-Config Changelog](https://developers.cloudflare.com/changelog/2025-12-16-wrangler-autoconfig/)
```

---

## Community Tips Section (New)

Add new section to SKILL.md for community-sourced tips:

```markdown
## Community Tips

> **Note**: These tips come from community discussions. Verify against your version.

### Tip: Clear Cache on Weird Development Errors

**Source**: [workers-sdk #11932](https://github.com/cloudflare/workers-sdk/issues/11932) | **Confidence**: HIGH

If you get random "The response has already been sent" errors or other unexplained issues in `wrangler dev`:

```bash
# Nuclear option: clear all caches
rm -rf .wrangler dist node_modules/.vite

# Rebuild
npm run build

# Recreate local D1 if needed
wrangler d1 execute DB --local --file schema.sql
```

**Applies to**: Wrangler 4.x development mode

---

### Tip: Avoid vite-tsconfig-paths v6 with SSR

**Source**: [workers-sdk #11825](https://github.com/cloudflare/workers-sdk/issues/11825) | **Confidence**: HIGH

If using React SSR with `@cloudflare/vite-plugin`, pin to `vite-tsconfig-paths@5.1.4`:

```bash
npm install vite-tsconfig-paths@5.1.4
```

Version 6.x doesn't follow path aliases during dependency scan, causing duplicate React instances.

**Applies to**: Projects using TypeScript path aliases with React SSR
```

---

**Research Completed**: 2026-01-20 13:45 PST
**Next Research Due**: After Wrangler 5.0 release or Q2 2026 (whichever comes first)

**High-Priority Tracking**:
- [ ] Watch workers-sdk #11948 (Vite 8 fix PR merged)
- [ ] Watch workers-sdk #9885 (assets.base platform feature)
- [ ] Monitor auto-provisioning beta graduation to stable
- [ ] Track Wrangler v4→v5 migration timeline (if planned)
