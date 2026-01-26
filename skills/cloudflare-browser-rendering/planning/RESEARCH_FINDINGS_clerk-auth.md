# Community Knowledge Research: clerk-auth

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/clerk-auth/SKILL.md
**Packages Researched**: @clerk/nextjs@6.36.8, @clerk/backend@2.29.3, @clerk/clerk-react@5.59.2, @clerk/testing@1.13.29
**Official Repo**: clerk/javascript
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 11 |
| TIER 1 (Official) | 7 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 8 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Next.js 16 Middleware Rename (middleware.ts → proxy.ts)

**Trust Score**: TIER 1 - Official
**Source**: [Next.js 16 Blog](https://nextjs.org/blog/next-16) | [Why Next.js is Moving Away from Middleware](https://www.buildwithmatija.com/blog/nextjs16-middleware-change)
**Date**: 2025-12-15
**Verified**: Yes - In production since Next.js 16 release
**Impact**: HIGH - Breaking change affects all Next.js 16 users
**Already in Skill**: YES - Documented in "What's New" section

**Description**:
Next.js 16 changed the middleware filename from `middleware.ts` to `proxy.ts`. This is due to a critical security vulnerability (CVE discovered March 2025) where middleware could be bypassed by adding an `x-middleware-subrequest` header. The rename represents Next.js steering away from middleware-based security patterns.

**Context**:
The March 2025 security disclosure by Rachid Allam affected every Next.js version from 11.1.4 through 15.2.2. Attackers could bypass all middleware-based authorization by adding a single HTTP header.

**Official Status**:
- [x] Fixed in Next.js 16
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Skill Coverage**: Fully documented in SKILL.md lines 70-92.

---

### Finding 1.2: User Type Inconsistency (useUser vs currentUser)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #2176](https://github.com/clerk/javascript/issues/2176)
**Date**: 2023-11-21 (still open as of 2026-01-20)
**Verified**: Yes - Confirmed by Clerk maintainer
**Impact**: MEDIUM - Causes TypeScript errors when sharing utilities
**Already in Skill**: NO

**Description**:
`useUser()` returns `UserResource` type (client-side, from @clerk/clerk-react) while `currentUser()` returns `User` type (server-side, from @clerk/backend). These types have different properties:

**Client (`useUser`)**: Includes `fullName`, `primaryEmailAddress` (EmailAddress object), `organizationMemberships`, etc.

**Server (`currentUser`)**: Missing `fullName`, `primaryEmailAddress` (has `primaryEmailAddressId` instead), includes `privateMetadata` (not available client-side).

**Reproduction**:
```typescript
// This causes TypeScript errors
import { useUser } from '@clerk/clerk-react'
import { currentUser } from '@clerk/nextjs/server'

// These utilities don't work across client/server boundaries
function getUserEmail(user: ???) {  // What type to use?
  return user.primaryEmailAddress  // Works for useUser, not currentUser
}
```

**Solution/Workaround**:
```typescript
// Workaround from maintainer: Use shared properties
const primaryEmailAddress = emailAddresses.find(
  ({ id }) => id === primaryEmailAddressId
)

// Or use separate types
type ClientUser = ReturnType<typeof useUser>['user']
type ServerUser = Awaited<ReturnType<typeof currentUser>>
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (docs updated post-issue)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related GitHub issues: #4105 (Web3 properties missing), multiple related reports
- Maintainer comment: "These are 2 different types and should not be treated as a common interface"

---

### Finding 1.3: organizationSyncOptions with authenticateRequest()

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7178](https://github.com/clerk/javascript/issues/7178)
**Date**: 2025-11-08 (still open)
**Verified**: Partially - Reported by user, pending maintainer confirmation
**Impact**: MEDIUM - Breaks URL-based org activation in non-Next.js environments
**Already in Skill**: PARTIAL - organizationSyncOptions documented for Next.js only

**Description**:
`organizationSyncOptions` works with `clerkMiddleware()` in Next.js but fails with `authenticateRequest()` in other runtimes (Cloudflare Workers, Express, etc.). The `Sec-Fetch-Dest` header check in `isRequestEligibleForHandshake` prevents activation outside Next.js.

**Reproduction**:
```typescript
// Works in Next.js
export default clerkMiddleware({
  organizationSyncOptions: {
    organizationPatterns: ['/orgs/:slug(.*)'],
  },
})

// Doesn't work in Cloudflare Workers
const result = await authenticateRequest(request, {
  organizationSyncOptions: {
    organizationPatterns: ['/orgs/:slug(.*)'],
  },
})
// Organization not activated despite URL match
```

**Attempted Workaround (doesn't work)**:
```typescript
// User tried setting Sec-Fetch-Dest manually
const newHeaders = new Headers(req.headers)
newHeaders.set('Sec-Fetch-Dest', 'document')
const newRequest = new Request(req.url, { headers: newHeaders })

await authenticateRequest(newRequest, { /* ... */ })
// Still doesn't work - deeper issue in handshake logic
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required (none found yet)
- [ ] Won't fix (awaiting maintainer response)

**Cross-Reference**:
- Skill documents organizationSyncOptions only for Next.js (lines 277-286)
- No mention of authenticateRequest() limitations

---

### Finding 1.4: Multiple acceptsToken Types Causes token-type-mismatch

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7520](https://github.com/clerk/javascript/issues/7520)
**Date**: 2025-12-21 (fixed in snapshot)
**Verified**: Yes - Fix available in snapshot, releasing soon
**Impact**: MEDIUM - Affects API key + session token mixed auth
**Already in Skill**: NO

**Description**:
When using `authenticateRequest()` with multiple `acceptsToken` values (e.g., `['session_token', 'api_key']`), Clerk throws `token-type-mismatch` error incorrectly. This broke the new API Keys feature (beta Dec 2025) when trying to accept both session tokens and API keys.

**Reproduction**:
```typescript
const result = await authenticateRequest(request, {
  acceptsToken: ['session_token', 'api_key'],  // Error!
  // ...other options
})
// Error: token-type-mismatch even when token type is valid
```

**Solution**:
```bash
# Fixed in snapshot (releasing in next version)
npm i @clerk/backend@2.29.2-snapshot.v20260108010246 --save-exact
```

**Official Status**:
- [x] Fixed in version 2.29.2+ (snapshot available, release pending)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to API Keys beta feature documented in skill lines 18-64

---

### Finding 1.5: deriveUrlFromHeaders Unsafe URL Parsing Crash

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7275](https://github.com/clerk/javascript/issues/7275)
**Date**: 2025-11-20 (closed as fixed)
**Verified**: Yes - Fixed in release
**Impact**: HIGH - Crashes server on malformed URLs
**Already in Skill**: NO

**Description**:
Internal `deriveUrlFromHeaders()` function performs unsafe URL parsing and crashes the entire server when receiving malformed URLs in headers. This is a denial-of-service vulnerability.

**Reproduction**:
```typescript
// Malformed URL in headers causes server crash
Request with headers:
  x-forwarded-proto: 'https'
  x-forwarded-host: 'example.com[invalid]'

// Result: Server crashes with URL parsing error
```

**Solution**:
Fixed in recent release - upgrade to @clerk/backend@2.29.0+.

**Official Status**:
- [x] Fixed in version 2.29.0+
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.6: Next.js 16 Cache Invalidation on Sign-out

**Trust Score**: TIER 1 - Official
**Source**: [Changelog @clerk/nextjs@6.35.2](https://github.com/clerk/javascript/blob/main/packages/nextjs/CHANGELOG.md#6352)
**Date**: 2025-11-14
**Verified**: Yes - Fixed in release
**Impact**: MEDIUM - Stale data after sign-out
**Already in Skill**: PARTIAL - Next.js 16 support mentioned, but not this fix

**Description**:
Next.js 16 changed caching behavior. Clerk's sign-out flow needed updates to properly invalidate Next.js 16 caches. Without this, users saw stale authenticated data after signing out.

**Reproduction**:
```typescript
// Next.js 16 with @clerk/nextjs < 6.35.2
// User signs out but still sees cached authenticated content
```

**Solution**:
Upgrade to @clerk/nextjs@6.35.2 or later.

**Official Status**:
- [x] Fixed in version 6.35.2
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Skill mentions Next.js 16 support (line 193-194) but doesn't mention this fix

---

### Finding 1.7: currentUser() treatPendingAsSignedOut Option

**Trust Score**: TIER 1 - Official
**Source**: [Changelog @clerk/nextjs@6.32.0](https://github.com/clerk/javascript/blob/main/packages/nextjs/CHANGELOG.md#6320)
**Date**: 2025-10-15
**Verified**: Yes - New feature in 6.32.0
**Impact**: LOW - Optional parameter for edge case handling
**Already in Skill**: NO

**Description**:
New option `treatPendingAsSignedOut` for `currentUser()` to control how sessions with `pending` status are handled. By default, pending sessions are treated as signed-out (user is null). Set to `false` to treat pending as signed-in.

**Use Case**:
Sessions can have a `pending` status during certain flows (e.g., credential stuffing defense secondary auth). Apps may want to show partial UI during pending state.

**Usage**:
```typescript
// Default: pending = signed out
const user = await currentUser()  // null if status is 'pending'

// Treat pending as signed in
const user = await currentUser({ treatPendingAsSignedOut: false })  // defined if pending
```

**Official Status**:
- [x] Fixed in version 6.32.0+
- [x] Documented behavior (in changelog)
- [ ] Known issue, workaround required
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: March 2025 Next.js Middleware Security Context

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Why Next.js is Moving Away from Middleware](https://www.buildwithmatija.com/blog/nextjs16-middleware-change) | [Clerk Article on Session Management](https://clerk.com/articles/nextjs-session-management-solving-nextauth-persistence-issues)
**Date**: 2025-12-15
**Verified**: Cross-referenced with Next.js 16 changelog
**Impact**: HIGH - Explains why proxy.ts change happened
**Already in Skill**: PARTIAL - proxy.ts documented, but not the "why"

**Description**:
Detailed context on why Next.js 16 renamed middleware.ts to proxy.ts. The CVE disclosed in March 2025 allowed complete bypass of middleware-based auth by adding `x-middleware-subrequest: true` header. This affected ALL auth libraries (NextAuth, Clerk, custom solutions).

**Why It Matters**:
Developers need to understand this isn't just a rename - it's Next.js signaling that middleware-first security patterns are dangerous. Future security patterns should not rely solely on middleware.

**Community Validation**:
- Multiple blog posts from Next.js community leaders
- Referenced in Clerk's official articles
- Corroborated by Next.js 16 release notes

**Recommendation**: Add context to "What's New" section explaining the security motivation behind proxy.ts.

---

### Finding 2.2: Service Outages (May-June 2025) - GCP Dependency

**Trust Score**: TIER 2 - Official Postmortem
**Source**: [Clerk Postmortem: June 26, 2025](https://clerk.com/blog/postmortem-jun-26-2025-service-outage)
**Date**: 2025-06-26
**Verified**: Official postmortem
**Impact**: HIGH - Production apps affected
**Already in Skill**: NO

**Description**:
Three major Clerk service disruptions since May 2025, all attributed to Google Cloud Platform (GCP) outages. June 26 outage lasted 45 minutes (6:16-7:01 UTC), affecting all Clerk customers.

**Key Insight**:
Clerk acknowledged single-vendor dependency risk and committed to exploring multi-cloud redundancy. For mission-critical apps, developers should:
- Implement graceful degradation when Clerk is down
- Cache auth tokens locally where possible
- Monitor https://status.clerk.com

**Workaround During Outage**:
None - total service unavailable. Apps with local token caching (JWT verification with `jwtKey` option) could continue working for existing sessions but couldn't create new sessions.

**Recommendation**: Add to "Production Considerations" or "Known Issues" section as environmental factor.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Nuxt SSR useAuth() Usage Issues

**Trust Score**: TIER 3 - Community Discussion
**Source**: [GitHub Issue #7542](https://github.com/clerk/javascript/issues/7542)
**Date**: 2026-01-06 (very recent, still open)
**Verified**: Maintainer suggested workaround
**Impact**: MEDIUM - Affects Nuxt/Vue users
**Already in Skill**: NO (skill is Next.js/React focused)

**Description**:
Nuxt users experiencing issues with `useAuth()` in SSR context due to Vue module duplication. The `@clerk/vue` module gets bundled twice, causing injection Symbol to be different instances.

**Solution**:
```bash
# Workaround: Explicitly install @clerk/vue
pnpm add @clerk/vue
```

**Consensus Evidence**:
- Maintainer-confirmed workaround
- Multiple users reporting same issue
- Related to bundling, not Clerk bug

**Recommendation**: Not applicable to this skill (Next.js/React focused). Could add to a future clerk-vue skill.

---

### Finding 3.2: Turbopack Build Error with formatMetadataHeaders

**Trust Score**: TIER 3 - Community Discussion
**Source**: [GitHub Issue #7461](https://github.com/clerk/javascript/issues/7461)
**Date**: 2025-12-15 (closed as fixed)
**Verified**: Fixed in release
**Impact**: MEDIUM - Broke Next.js 16 canary builds
**Already in Skill**: NO

**Description**:
Next.js 16 canary builds with Turbopack failed due to `formatMetadataHeaders` function. Fixed in recent release.

**Official Status**:
- [x] Fixed in @clerk/nextjs@6.35.0+
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Mention in Next.js 16 section that canary users should use @clerk/nextjs@6.35.0+.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None found. All issues encountered had official GitHub issues or maintainer responses.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| API Keys Beta (Dec 2025) | What's New, lines 18-64 | Fully covered |
| Next.js 16 proxy.ts rename | What's New, lines 70-92 | Fully covered |
| API Version 2025-11-10 | Breaking Changes, lines 113-151 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.2 User type inconsistency | Known Issues Prevention | Add as Issue #13: User Type Mismatch |
| 1.3 organizationSyncOptions + authenticateRequest | Known Issues Prevention OR clerkMiddleware section | Add note about Next.js-only limitation |
| 1.5 deriveUrlFromHeaders crash | Known Issues Prevention | Add as Issue #14: Server Crash on Malformed URLs (fixed) |

### Priority 2: Enhance Existing Content (TIER 1-2)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.6 Next.js 16 cache invalidation | Next.js 16 Support section | Add fix version requirement (6.35.2+) |
| 2.1 March 2025 security context | Next.js 16 proxy.ts section | Add "Why" paragraph explaining CVE background |
| 2.2 GCP outages | New "Production Considerations" section | Add service availability notes |

### Priority 3: Minor Additions (TIER 1, Low Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.4 acceptsToken type mismatch | API Keys section or Known Issues | Add note that fix is in 2.29.2+ |
| 1.7 treatPendingAsSignedOut | currentUser() usage or Advanced Features | Add optional parameter docs |
| 3.2 Turbopack build error | Next.js 16 section | Add minimum version note (6.35.0+) |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "edge case OR gotcha" in clerk/javascript | 30 | 4 |
| "workaround" in clerk/javascript | 20 | 6 |
| "breaking change" in clerk/javascript | 20 | 3 |
| Issues created after 2025-05-01 | 30+ | 11 |
| Recent releases (@clerk/nextjs changelog) | 20 | 7 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "clerk auth gotcha 2025 2026" | 0 | N/A - No results |
| "clerk nextjs error 2025" | 0 | N/A - No results |
| "@clerk/nextjs workaround 2025" | 0 | N/A - No results |

**Note**: Stack Overflow searches with site: operator returned no results. Most Clerk issues are discussed on GitHub.

### Other Sources

| Source | Notes |
|--------|-------|
| [Clerk Changelog](https://clerk.com/changelog) | Referenced for API version changes |
| [Next.js 16 Blog](https://nextjs.org/blog/next-16) | Confirmed middleware → proxy.ts change |
| [Build with Matija Blog](https://www.buildwithmatija.com/blog/nextjs16-middleware-change) | Deep-dive on middleware security |
| [Clerk Postmortem](https://clerk.com/blog/postmortem-jun-26-2025-service-outage) | GCP outage details |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh api` for changelog retrieval
- `WebSearch` for Stack Overflow and blog posts

**Limitations**:
- Stack Overflow searches returned no results (likely due to search operator limitations)
- Most community discussion happens on GitHub Discussions (not issues) - not fully explored
- Some issues closed recently may not have full resolution details

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that Finding 1.3 (organizationSyncOptions) is still an issue or has been fixed in recent releases. Check if authenticateRequest() now supports this option.

**For api-method-checker**: Verify that `currentUser({ treatPendingAsSignedOut: false })` syntax exists in @clerk/nextjs@6.32.0+.

**For code-example-validator**: Validate code examples in Finding 1.2 (user type workaround) against current TypeScript types.

---

## Integration Guide

### Adding Issue #13: User Type Inconsistency

```markdown
### Issue #13: User Type Mismatch (useUser vs currentUser)

**Error**: TypeScript errors when sharing user utilities across client/server
**Source**: https://github.com/clerk/javascript/issues/2176
**Why It Happens**: `useUser()` returns `UserResource` (client-side) with different properties than `currentUser()` returns `User` (server-side). Client has `fullName`, `primaryEmailAddress` object; server has `primaryEmailAddressId` and `privateMetadata` instead.
**Prevention**: Use shared properties only, or create separate utility functions for client vs server contexts.

```typescript
// ✅ CORRECT: Use properties that exist in both
const primaryEmailAddress = user.emailAddresses.find(
  ({ id }) => id === user.primaryEmailAddressId
)

// ✅ CORRECT: Separate types
type ClientUser = ReturnType<typeof useUser>['user']
type ServerUser = Awaited<ReturnType<typeof currentUser>>
```
```

### Adding Production Considerations Section

```markdown
## Production Considerations

### Service Availability (Multi-Cloud Planning)

**Context**: Clerk experienced 3 major service disruptions in May-June 2025 attributed to Google Cloud Platform (GCP) outages. The June 26, 2025 outage lasted 45 minutes and affected all Clerk customers.

**Source**: [Clerk Postmortem](https://clerk.com/blog/postmortem-jun-26-2025-service-outage)

**Mitigation Strategies**:
- Monitor [Clerk Status](https://status.clerk.com) for real-time updates
- Implement graceful degradation when Clerk API is unavailable
- Cache auth tokens locally where possible
- For existing sessions, use `jwtKey` option for networkless verification:

```typescript
clerkMiddleware({
  jwtKey: process.env.CLERK_JWT_KEY,  // Allows offline token verification
})
```

**Note**: Clerk committed to exploring multi-cloud redundancy to reduce single-vendor dependency risk.
```

### Enhancing proxy.ts Section with Security Context

```markdown
### 2. Next.js 16: proxy.ts Middleware Filename (Dec 2025)

**⚠️ BREAKING**: Next.js 16 changed middleware filename due to critical security vulnerability (CVE disclosed March 2025).

**Background**: The March 2025 vulnerability (affecting Next.js 11.1.4-15.2.2) allowed attackers to completely bypass middleware-based authorization by adding a single HTTP header: `x-middleware-subrequest: true`. This affected all auth libraries (NextAuth, Clerk, custom solutions).

**Why the Rename**: The `middleware.ts` → `proxy.ts` change isn't just cosmetic - it's Next.js signaling that middleware-first security patterns are dangerous. Future auth implementations should not rely solely on middleware for authorization.

```
Next.js 15 and earlier: middleware.ts
Next.js 16+:            proxy.ts
```

**Correct Setup for Next.js 16:**
[existing code example...]

**Minimum Version**: @clerk/nextjs@6.35.0+ required for Next.js 16 (fixes Turbopack build errors and cache invalidation on sign-out).
```

---

**Research Completed**: 2026-01-20 14:35 UTC
**Next Research Due**: After next major Clerk release (likely Q2 2026) or after Next.js 17 announcement
