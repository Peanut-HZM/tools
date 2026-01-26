# Community Knowledge Research: better-auth

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/better-auth/SKILL.md
**Packages Researched**: better-auth@1.4.10-1.4.16, @better-auth/expo@1.4.16
**Official Repo**: better-auth/better-auth
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

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Expo Client Crashes with fromJSONSchema Regression

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7491](https://github.com/better-auth/better-auth/issues/7491)
**Date**: 2026-01-20
**Verified**: Yes (maintainer confirmed regression)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
After PR #6933 (cookie-based OAuth state fix for Expo), upgrading from continuous build at commit `f4a9f15` to any subsequent release (including v1.4.16) causes a runtime crash when importing `expoClient` from `@better-auth/expo/client`. The error is `TypeError: Cannot read property 'fromJSONSchema' of undefined`.

**Reproduction**:
```typescript
// Crashes on v1.4.16, works on f4a9f15
import { expoClient } from '@better-auth/expo/client'

// Error: TypeError: Cannot read property 'fromJSONSchema' of undefined
```

**Solution/Workaround**:
- **Temporary**: Downgrade to continuous build at commit `f4a9f15`
- **Permanent**: Wait for fix (issue is open as of 2026-01-20)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to PR #6933 (cookie-based OAuth state for Expo)
- Regression introduced in one of 3 commits after f4a9f15

---

### Finding 1.2: additionalFields with string[] Returns Stringified JSON

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7440](https://github.com/better-auth/better-auth/issues/7440)
**Date**: 2026-01-17
**Verified**: Yes (maintainer confirmed, root cause identified)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
After upgrading from v1.4.4 → v1.4.12+, `additionalFields` defined with `type: 'string[]'` no longer return arrays. Instead, values are returned as stringified JSON arrays (e.g., `'["a","b"]'`), breaking code that expects native arrays.

**Root Cause**: In Drizzle adapter, `string[]` fields are stored with `mode: 'json'`, which expects arrays. But better-auth v1.4.4+ passes strings to Drizzle, causing double-stringification. When querying **directly via Drizzle**, the value is a string (double-stringify), but when using **better-auth `internalAdapter`**, a transformer correctly returns an array.

**Reproduction**:
```typescript
// Config
additionalFields: {
  notificationTokens: {
    type: 'string[]',
    required: true,
    input: true,
  },
}

// Create user
notificationTokens: ['token1', 'token2']

// Result in DB (when querying via Drizzle directly)
// '["token1","token2"]' (string, not array)
```

**Solution/Workaround**:
1. **Change Drizzle schema** to use `.jsonb()` instead of `.text()` for string[] fields
2. **Use better-auth `internalAdapter`** instead of querying Drizzle directly (transformer handles conversion)
3. **Manually parse** stringified arrays until fixed

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to issue #6779 (migration to JSONB for Postgres arrays)

---

### Finding 1.3: additionalFields "returned" Property Doesn't Work

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7489](https://github.com/better-auth/better-auth/issues/7489)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `returned: false` property on `additionalFields` (intended to prevent field from being returned in API responses) also prevents the field from being **saved to the database** when using the API. The `input: true` property should control write access, but `returned: false` blocks both read AND write.

**Reproduction**:
```typescript
// Organization plugin config
additionalFields: {
  secretField: {
    type: 'string',
    required: true,
    input: true,      // Should allow API writes
    returned: false,  // Should only block reads, but blocks writes too
  },
}

// API request to create organization
// secretField is never saved to database
```

**Solution/Workaround**:
- Don't use `returned: false` if you need to write via API
- Write field through server-side methods (`auth.api.*`) instead of client API

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.4: CORS Issues with Cloudflare Workers + Hono

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7434](https://github.com/better-auth/better-auth/issues/7434)
**Date**: 2026-01-16
**Verified**: Yes (resolved by user)
**Impact**: MEDIUM
**Already in Skill**: Partially (CORS mentioned in Issue #5)

**Description**:
When deploying better-auth on Cloudflare Workers with Hono, CORS middleware must be configured correctly with matching frontend origin in both Hono CORS config AND better-auth `trustedOrigins`. Common mistake: typo in origin URL (trailing slash, http vs https, wrong port).

**Reproduction**:
```typescript
// Frontend: http://localhost:5173
// Backend: http://localhost:5174

// WRONG - mismatched origins
app.use("/api/auth/*", cors({ origin: "http://localhost:5174" }))
auth = betterAuth({ trustedOrigins: ["http://localhost:5173"] })

// CORRECT - both match frontend origin
app.use("/api/auth/*", cors({ origin: "http://localhost:5173" }))
auth = betterAuth({ trustedOrigins: ["http://localhost:5173"] })
```

**Solution/Workaround**:
1. Ensure CORS `origin` matches frontend URL exactly (no trailing slash, correct protocol/port)
2. Set same origin in `trustedOrigins`
3. Include `credentials: true` in CORS config
4. Ensure CORS middleware is registered BEFORE auth routes

**Official Status**:
- [x] Fixed in version X.Y.Z (resolved by user config)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Skill Issue #5 already covers CORS, but could expand with this specific Hono pattern

---

### Finding 1.5: Kysely CamelCasePlugin Breaks Join Parsing

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7136](https://github.com/better-auth/better-auth/issues/7136)
**Date**: 2026-01-05
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Partially (CamelCasePlugin mentioned in SKILL.md lines 119-120)

**Description**:
Using Kysely's `CamelCasePlugin` breaks better-auth's join parsing in the adapter. The plugin converts database column names from `snake_case` to `camelCase`, but better-auth's `processJoinedResults` expects keys like `_joined_user_user_id` (snake_case). When the plugin transforms these to `_joinedUserUserId`, the join fields are not recognized, causing `user` to be null in session queries.

**Reproduction**:
```typescript
// Config with CamelCasePlugin
const db = new Kysely({
  dialect: new LibsqlDialect({ url: "file:./data/local.db" }),
  plugins: [new CamelCasePlugin()],
})

export const auth = betterAuth({
  database: { db, type: "sqlite" },
  // ... config
})

// Result: auth.api.getSession() returns null even though session exists
```

**Solution/Workaround**:
**Use separate Kysely instance without CamelCasePlugin for better-auth**:
```typescript
// DB for better-auth (no CamelCasePlugin)
const authDb = new Kysely({
  dialect: new LibsqlDialect({ url: "file:./data/local.db" }),
})

// DB for app queries (with CamelCasePlugin)
const appDb = new Kysely({
  dialect: new LibsqlDialect({ url: "file:./data/local.db" }),
  plugins: [new CamelCasePlugin()],
})

export const auth = betterAuth({
  database: { db: authDb, type: "sqlite" },
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Skill already mentions CamelCasePlugin but doesn't document this breaking issue
- Update Issue #3 or add new issue for join parsing failure

---

### Finding 1.6: freshAge Does Not Use Last Activity

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7472](https://github.com/better-auth/better-auth/issues/7472)
**Date**: 2026-01-19
**Verified**: Yes (maintainer confirmed: "A fresh session is determined by when the session was created, not by when it was active")
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `session.freshAge` configuration is based on session creation time (`createdAt`), NOT recent activity. Even if a session is actively used, it becomes "not fresh" after `freshAge` elapses from creation, causing "fresh session required" endpoints to reject valid active sessions.

**Why It Happens**: The `freshSessionMiddleware` checks `Date.now() - (session.updatedAt || session.createdAt)`, but `updatedAt` only changes when the session is refreshed based on `updateAge`. If `updateAge > freshAge`, the session becomes "not fresh" before `updatedAt` is bumped.

**Reproduction**:
```typescript
// Config
session: {
  expiresIn: 60 * 60 * 24 * 7,    // 7 days
  freshAge: 60 * 60 * 24,          // 24 hours
  updateAge: 60 * 60 * 24 * 3,     // 3 days (> freshAge!)
}

// Timeline:
// T+0h: User signs in (createdAt = now)
// T+12h: User makes requests (session active, still fresh)
// T+25h: User makes request (session active, BUT NOT FRESH - freshAge elapsed)
// Result: "Fresh session required" endpoints reject active session
```

**Solution/Workaround**:
1. **Set `updateAge <= freshAge`** to ensure session freshness is updated before expiry
2. **Avoid "fresh session required" gating** for long-lived sessions
3. **Document clearly**: `freshAge` is strictly time-since-creation, not activity-based

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (maintainer clarified this is by design)
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.7: OAuth/OIDC Token Endpoints Return Wrapped JSON

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7355](https://github.com/better-auth/better-auth/issues/7355)
**Date**: 2026-01-14
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
OAuth 2.1 and OIDC token endpoints (`/oauth2/token`, OIDC4VCI `/credential`) return JSON wrapped as `{ "response": { ...actual_oauth_fields... } }` instead of spec-compliant top-level fields. OAuth/OIDC clients expect `access_token`, `token_type`, `c_nonce`, etc. at the root level, causing authentication failures (e.g., `Bearer undefined`).

**Root Cause**: The endpoint pipeline returns `{ response, headers, status }` for internal use, which gets serialized directly for HTTP requests. This breaks OAuth/OIDC spec requirements.

**Reproduction**:
```typescript
// Expected (spec-compliant)
{ "access_token": "...", "token_type": "bearer", "expires_in": 3600 }

// Actual (wrapped)
{ "response": { "access_token": "...", "token_type": "bearer", "expires_in": 3600 } }

// Result: OAuth clients fail to parse, send `Bearer undefined`
```

**Solution/Workaround**:
- **Temporary**: Manually unwrap `.response` field on client side
- **Permanent**: Wait for fix (proposed in issue, open to contributions as of 2026-01-14)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required (fix proposed)
- [ ] Won't fix

---

### Finding 1.8: listSessions Missing ID Field with Redis secondaryStorage

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #7454](https://github.com/better-auth/better-auth/issues/7454)
**Date**: 2026-01-18
**Verified**: Yes (closed as fixed)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Redis as `secondaryStorage` for sessions, the `listSessions` endpoint returns session objects without the `id` field, breaking client-side session management that relies on session IDs.

**Reproduction**:
```typescript
// Config with Redis secondaryStorage
secondaryStorage: {
  get: async (key) => redis.get(key),
  set: async (key, value, ttl) => redis.setex(key, ttl, value),
  delete: async (key) => redis.del(key),
}

// Call listSessions
const sessions = await auth.api.listSessions({ headers })

// Result: sessions[0].id is undefined
```

**Solution/Workaround**:
- **Fixed in v1.4.15+** (issue closed on 2026-01-18)
- If on older version, upgrade to v1.4.15+

**Official Status**:
- [x] Fixed in version 1.4.15
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Cloudflare Workers DB Binding Constraints

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Medium Article](https://medium.com/@dasfacc/sveltekit-better-auth-using-cloudflare-d1-and-drizzle-91d9d9a6d0b4), [AnswerOverflow](https://www.answeroverflow.com/m/1416707955423711363)
**Date**: 2025-2026
**Verified**: Multiple sources agree
**Impact**: MEDIUM
**Already in Skill**: Partially (mentioned in worker setup)

**Description**:
In Cloudflare Workers, D1 database bindings are only available inside the context of an inbound request (the `fetch()` function). You cannot initialize Drizzle/better-auth outside the request handler. This creates architectural challenges when setting up better-auth, as the auth instance must be created per-request.

**Community Validation**:
- Multiple blog posts confirm this pattern
- Official Hono example uses this approach
- Community consensus on Discord

**Reproduction**:
```typescript
// ❌ WRONG - DB binding not available outside request
const db = drizzle(env.DB, { schema }) // env.DB doesn't exist here
export const auth = betterAuth({ database: drizzleAdapter(db, { provider: "sqlite" }) })

// ✅ CORRECT - Create auth instance per-request
export default {
  fetch(request, env, ctx) {
    const db = drizzle(env.DB, { schema })
    const auth = betterAuth({ database: drizzleAdapter(db, { provider: "sqlite" }) })
    return auth.handler(request)
  }
}
```

**Solution**:
Use factory function pattern to create auth instance per-request:
```typescript
function createAuth(env: Env) {
  const db = drizzle(env.DB, { schema })
  return betterAuth({
    database: drizzleAdapter(db, { provider: "sqlite" }),
    // ... config
  })
}

export default {
  fetch(request, env, ctx) {
    return createAuth(env).handler(request)
  }
}
```

**Recommendation**: Add to Known Issues or Configuration section with "Cloudflare Workers-specific" flag

---

### Finding 2.2: TanStack Start Session Object Always Exists (Nullability Issue)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #7494](https://github.com/better-auth/better-auth/issues/7494)
**Date**: 2026-01-20
**Verified**: Closed (user resolved)
**Impact**: LOW
**Already in Skill**: No

**Description**:
When using better-auth with TanStack Start, `useSession()` returns a session object even when the user is not logged in. The outer `session` object exists, but `session.user` and `session.session` are `null`. This can cause confusion when checking `if (session)` instead of `if (session?.user)`.

**Reproduction**:
```typescript
const { data: session } = authClient.useSession()

// When NOT logged in:
console.log(session) // { user: null, session: null }
console.log(!!session) // true (unexpected!)

// Correct check:
if (session?.user) {
  // User is logged in
}
```

**Solution**:
- Always check `session?.user` or `session?.session`, not just `session`
- This is expected behavior (session object container always exists)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (expected nullability pattern)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Add to TanStack Start integration section as "Important Note"

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: SvelteKit Route Detection Issue

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Medium Article](https://medium.com/@dasfacc/sveltekit-better-auth-using-cloudflare-d1-and-drizzle-91d9d9a6d0b4)
**Date**: 2025
**Verified**: Cross-referenced with SvelteKit + Workers patterns
**Impact**: LOW
**Already in Skill**: No

**Description**:
When deploying SvelteKit apps with better-auth to Cloudflare Workers, the `/api/auth` route may not be detected by Wrangler because the `svelteKitHandler` does programmatic route checks. This can cause 404 errors for auth endpoints.

**Solution**:
```typescript
// src/hooks.server.ts
export const handle = sequence(
  // Add explicit auth handler before SvelteKit handler
  ({ event, resolve }) => {
    if (event.url.pathname.startsWith('/api/auth')) {
      return auth.handler(event.request)
    }
    return resolve(event)
  },
  svelteKitHandler
)
```

**Consensus Evidence**:
- Blog post with working implementation
- Community discussions on Discord mention this pattern

**Recommendation**: Add to SvelteKit integration examples (if skill expands framework coverage)

---

### Finding 3.2: baseURL Requirement When trustedOrigins Is Set

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #7502](https://github.com/better-auth/better-auth/issues/7502)
**Date**: 2026-01-20
**Verified**: Issue closed as question/clarification
**Impact**: LOW
**Already in Skill**: No

**Description**:
Confusion about whether `baseURL` is required when `trustedOrigins` is configured. Community question suggests some users think `trustedOrigins` replaces `baseURL`, but they serve different purposes.

**Clarification**:
- `baseURL`: The auth server's own URL (for callbacks, email links, etc.)
- `trustedOrigins`: Client origins allowed to make requests (CORS-like)

**Both are needed** when frontend and backend are on different origins.

**Recommendation**: Add to Configuration section as FAQ or Common Mistake

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| D1 adapter doesn't exist (use Drizzle/Kysely) | Issue #1, Line 24-30 | Fully covered |
| CORS configuration for SPA | Issue #5 | Fully covered |
| CamelCasePlugin usage | Lines 119-120, Issue #3 | Mentioned but not the breaking join parsing issue |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Expo fromJSONSchema crash | Known Issues (new #18) | Add with regression warning for v1.4.16 |
| 1.2 string[] stringified arrays | Known Issues (new #19) | Add with Drizzle schema workaround |
| 1.3 additionalFields returned property | Known Issues (new #20) | Add with input/returned clarification |
| 1.5 Kysely CamelCasePlugin breaks joins | Known Issues (expand #3) | Expand existing CamelCasePlugin note with join parsing failure |
| 1.6 freshAge not activity-based | Known Issues (new #21) | Add with configuration guidance (updateAge <= freshAge) |
| 1.7 OAuth token wrapped JSON | Known Issues (new #22) | Add for OAuth 2.1 Provider plugin users |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.4 Hono CORS configuration | Known Issues (expand #5) | Expand with specific Hono pattern |
| 1.8 listSessions missing ID (fixed) | Migration Notes | Note fixed in v1.4.15 |
| 2.1 Cloudflare Workers binding constraints | Cloudflare Workers section | Add factory function pattern |
| 2.2 TanStack Start session nullability | TanStack Start section | Add as "Important Note" |

### Priority 3: Monitor (TIER 3, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 SvelteKit route detection | Framework-specific, low impact | Monitor for more reports |
| 3.2 baseURL vs trustedOrigins confusion | Clarification issue, not a bug | Add to FAQ if more questions arise |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Issues created after 2025-05-01 | 30 | 12 |
| Labeled "bug" post-cutoff | 30 | 8 |
| Recent releases | 10 | 3 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "better-auth gotcha" | 0 | N/A |
| "better-auth edge case" | 0 | N/A |

**Note**: better-auth has minimal Stack Overflow presence, likely because community uses GitHub Issues and Discord.

### Other Sources

| Source | Notes |
|--------|-------|
| [Medium - SvelteKit D1 Guide](https://medium.com/@dasfacc/sveltekit-better-auth-using-cloudflare-d1-and-drizzle-91d9d9a6d0b4) | 1 relevant pattern (Workers binding) |
| [AnswerOverflow](https://www.answeroverflow.com) | 3 Discord discussions archived |
| [Hono Examples](https://hono.dev/examples/better-auth-on-cloudflare) | Official Cloudflare Workers pattern |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `WebSearch` for Stack Overflow and blogs
- Manual cross-referencing between issues

**Limitations**:
- Stack Overflow has very few better-auth questions (most activity on GitHub)
- Some issues lack maintainer response (marked as TIER 2-3 until confirmed)
- Expo issue (#7491) is still open, workaround may change

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.6 (freshAge) and 1.7 (OAuth token wrapping) against current official documentation to ensure these are not addressed in recent docs updates.

**For api-method-checker**: Verify that the workarounds in findings 1.2 (string[] arrays) and 1.5 (CamelCasePlugin) use currently available APIs.

**For code-example-validator**: Validate code examples in findings 1.5, 2.1 before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

**For High-Impact Bugs (Findings 1.1, 1.2, 1.7)**:

```markdown
### Issue #18: Expo Client fromJSONSchema Crash (v1.4.16)

**Problem**: Importing `expoClient` from `@better-auth/expo/client` crashes with `TypeError: Cannot read property 'fromJSONSchema' of undefined` on v1.4.16.

**Symptoms**: Runtime crash immediately when importing expoClient in React Native/Expo apps.

**Solution**:
- **Temporary**: Use continuous build at commit `f4a9f15` (pre-regression)
- **Permanent**: Wait for fix (issue #7491 open as of 2026-01-20)

**Source**: [GitHub Issue #7491](https://github.com/better-auth/better-auth/issues/7491)

---

### Issue #19: additionalFields string[] Returns Stringified JSON

**Problem**: After v1.4.12, `additionalFields` with `type: 'string[]'` return stringified arrays (`'["a","b"]'`) instead of native arrays when querying via Drizzle directly.

**Symptoms**: `user.notificationTokens` is a string, not an array. Code expecting arrays breaks.

**Solution**:
1. **Use better-auth `internalAdapter`** instead of querying Drizzle directly (has transformer)
2. **Change Drizzle schema** to `.jsonb()` for string[] fields
3. **Manually parse** JSON strings until fixed

**Source**: [GitHub Issue #7440](https://github.com/better-auth/better-auth/issues/7440)

---

### Issue #20: additionalFields "returned" Property Blocks Input

**Problem**: Setting `returned: false` on `additionalFields` prevents field from being saved via API, even with `input: true`.

**Symptoms**: Field never saved to database when creating/updating via API endpoints.

**Solution**:
- Don't use `returned: false` if you need API write access
- Write via server-side methods (`auth.api.*`) instead

**Source**: [GitHub Issue #7489](https://github.com/better-auth/better-auth/issues/7489)

---

### Issue #21: freshAge Based on Creation Time, Not Activity

**Problem**: `session.freshAge` checks time-since-creation, NOT recent activity. Active sessions become "not fresh" after `freshAge` elapses, even if used constantly.

**Symptoms**: "Fresh session required" endpoints reject valid active sessions.

**Why**: `updatedAt` only changes when session is refreshed (based on `updateAge`). If `updateAge > freshAge`, freshness expires before session updates.

**Solution**:
1. **Set `updateAge <= freshAge`** to ensure freshness is updated before expiry
2. **Avoid "fresh session required"** gating for long-lived sessions
3. **Accept as design**: freshAge is strictly time-since-creation (maintainer confirmed)

**Source**: [GitHub Issue #7472](https://github.com/better-auth/better-auth/issues/7472)

---

### Issue #22: OAuth Token Endpoints Return Wrapped JSON

**Problem**: OAuth 2.1 and OIDC token endpoints return `{ "response": { ...tokens... } }` instead of spec-compliant top-level JSON. OAuth clients expect `{ "access_token": "...", "token_type": "bearer" }` at root.

**Symptoms**: OAuth clients fail with `Bearer undefined` or `invalid_token`.

**Solution**:
- **Temporary**: Manually unwrap `.response` field on client
- **Permanent**: Wait for fix (issue #7355 open, accepting contributions)

**Source**: [GitHub Issue #7355](https://github.com/better-auth/better-auth/issues/7355)
```

### Expanding Existing Issues

**For Issue #3 (CamelCasePlugin) - Add Join Parsing Detail**:

```markdown
### Issue 3: CamelCase vs snake_case Column Mismatch

**Problem**: Database has `email_verified` but better-auth expects `emailVerified`.

**Symptoms**: Session reads fail, user data missing fields.

**⚠️ CRITICAL (v1.4.10+)**: Using Kysely's `CamelCasePlugin` **breaks join parsing** in better-auth adapter. The plugin converts join keys like `_joined_user_user_id` to `_joinedUserUserId`, causing user data to be null in session queries.

**Solution for Drizzle**:
[existing Drizzle solution]

**Solution for Kysely with CamelCasePlugin**:
Use **separate Kysely instance** without CamelCasePlugin for better-auth:

```typescript
// DB for better-auth (no CamelCasePlugin)
const authDb = new Kysely({
  dialect: new D1Dialect({ database: env.DB }),
})

// DB for app queries (with CamelCasePlugin)
const appDb = new Kysely({
  dialect: new D1Dialect({ database: env.DB }),
  plugins: [new CamelCasePlugin()],
})

export const auth = betterAuth({
  database: { db: authDb, type: "sqlite" },
})
```

**Source**: [GitHub Issue #7136](https://github.com/better-auth/better-auth/issues/7136)
```

---

**Research Completed**: 2026-01-21 14:30
**Next Research Due**: After v1.5.0 stable release (currently in beta)
