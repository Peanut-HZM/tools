# Community Knowledge Research: TanStack Router

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/tanstack-router/SKILL.md
**Packages Researched**: @tanstack/react-router@1.154.0, @tanstack/router-plugin@1.154.0, @tanstack/zod-adapter@1.154.0
**Official Repo**: TanStack/router
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 18 |
| TIER 1 (Official) | 12 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 3 |
| Recommended to Add | 15 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: inputValidator Errors Lose Structure During Serialization

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6428](https://github.com/TanStack/router/issues/6428)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When `inputValidator` fails (e.g., with Zod) in TanStack Start server functions, the validation error is serialized in a way that loses all structure. The Zod issues array is JSON-stringified and stuffed into `error.message`, making it unusable on the client without manual parsing.

**Reproduction**:
```typescript
// Server function
export const myFn = createServerFn({ method: 'POST' })
  .inputValidator(z.object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    age: z.number().min(18, 'Must be 18+'),
  }))
  .handler(async ({ data }) => data)

// Client - send invalid data
mutation.mutate({ data: { name: 'A', age: 15 } })

// Received error (structure lost):
{
  name: "Error",  // Lost ZodError type
  message: '[{"origin":"string","code":"too_small","path":["name"],"message":"Name must be at least 2 characters"},...]',
  // ↑ JSON string, not structured data
}
```

**Solution/Workaround**:
Currently requires manual JSON.parse on client:
```typescript
try {
  await mutation.mutate(data)
} catch (error) {
  // Workaround: parse stringified issues
  if (error.message.startsWith('[')) {
    const issues = JSON.parse(error.message)
    // Now can use structured error data
  }
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: GitHub Issue #2935 (broader error typing issues from server functions)
- Affects: TanStack Start server functions with input validation

---

### Finding 1.2: useParams({ strict: false }) Returns Unparsed Params

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6385](https://github.com/TanStack/router/issues/6385)
**Date**: 2026-01-14
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `useParams({ strict: false })` in v1.147.3+, params are returned unparsed but still typed as if they were parsed. This is caused by `match.params` no longer being parsed. On first render, parsing works correctly, but on navigation, values are stored as strings instead of parsed types.

**Reproduction**:
```typescript
// Route with param parsing
export const Route = createFileRoute('/posts/$postId')({
  params: {
    parse: (params) => ({
      postId: z.coerce.number().parse(params.postId), // Parse string to number
    }),
  },
})

// In component
function Component() {
  // First render: postId is number ✓
  // After navigation: postId is string ✗ (but typed as number)
  const { postId } = useParams({ strict: false })

  // Type says number, runtime is string!
  console.log(typeof postId) // "string"
}
```

**Solution/Workaround**:
Use `strict: true` (default) to get parsed params, or manually parse when using `strict: false`:
```typescript
const params = useParams({ strict: false })
const postId = Number(params.postId) // Manual parsing
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects nested routes where parent params need to be accessed from child
- Most nested match has correct parsing, parent matches store as strings

---

### Finding 1.3: Pathless Route notFoundComponent Not Rendering

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6351](https://github.com/TanStack/router/issues/6351), [GitHub Issue #4065](https://github.com/TanStack/router/issues/4065)
**Date**: 2026-01-10 (duplicate of 2025-04 issue)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`notFoundComponent` on pathless layout routes (e.g., `routes/(authenticated)/route.tsx`) is not rendering. Instead, the `defaultNotFoundComponent` from `main.tsx` is triggered. This has been broken since April 2025 (over 8 months).

**Reproduction**:
```typescript
// routes/(authenticated)/route.tsx - pathless layout
export const Route = createFileRoute('/(authenticated)')({
  beforeLoad: ({ context }) => {
    if (!context.auth) throw redirect({ to: '/login' })
  },
  notFoundComponent: () => <div>Protected 404</div>, // Not rendered!
})

// main.tsx
const router = createRouter({
  routeTree,
  defaultNotFoundComponent: () => <div>Public 404</div>, // This shows instead
})
```

**Solution/Workaround**:
Define `notFoundComponent` on child routes instead of pathless parent:
```typescript
// routes/(authenticated)/dashboard/route.tsx
export const Route = createFileRoute('/(authenticated)/dashboard')({
  notFoundComponent: () => <div>Protected 404</div>, // Works
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.4: Aborted Loader Renders errorComponent with Undefined Error

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6388](https://github.com/TanStack/router/issues/6388)
**Date**: 2026-01-15
**Verified**: Yes (side effect of #4570)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
On rapid param navigation (e.g., clicking through list items quickly), aborted loader requests render the `errorComponent` with `undefined` error. This is a side effect introduced after PR #4570.

**Reproduction**:
```typescript
export const Route = createFileRoute('/posts/$postId')({
  loader: async ({ params, abortController }) => {
    // Slow loader
    await fetch(`/api/posts/${params.postId}`, {
      signal: abortController.signal,
    })
  },
  errorComponent: ({ error }) => {
    console.log(error) // undefined when aborted!
    return <div>Error: {error?.message || 'Unknown'}</div>
  },
})

// User rapidly clicks: Post 1 → Post 2 → Post 3
// Post 1 loader aborts → errorComponent renders with undefined error
```

**Solution/Workaround**:
Check for undefined error in errorComponent:
```typescript
errorComponent: ({ error, reset }) => {
  if (!error) {
    // Aborted request, not a real error
    return null // or loading state
  }
  return <div>Error: {error.message}</div>
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.5: Vitest Cannot Read Properties of Null (useState)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6262](https://github.com/TanStack/router/issues/6262), [GitHub Issue #6246](https://github.com/TanStack/router/issues/6246), [PR #6074](https://github.com/TanStack/router/pull/6074)
**Date**: 2025-12-31
**Verified**: Yes (duplicate)
**Impact**: HIGH (blocks testing)
**Already in Skill**: No

**Description**:
TanStack Start + Vitest causes "Cannot read properties of null (reading 'useState')" error when running tests. The issue is caused by the `tanstackStart()` plugin itself. This is a duplicate of #6246 and has a PR #6074 to address it.

**Reproduction**:
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [tanstackStart(), react()],
  test: { environment: 'jsdom' },
})

// Any test with React hooks
test('component renders', () => {
  render(<MyComponent />) // Error: Cannot read properties of null (reading 'useState')
})
```

**Solution/Workaround**:
Temporarily remove `tanstackStart()` from Vite config when running tests (not ideal):
```typescript
export default defineConfig({
  plugins: [
    // tanstackStart(), // Comment out for tests
    react(),
  ],
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, PR #6074 in progress
- [ ] Won't fix

---

### Finding 1.6: Throwing Error in Route Loader with SSR Streaming Crashes Dev Server

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6200](https://github.com/TanStack/router/issues/6200)
**Date**: 2025-12-23
**Verified**: Yes
**Impact**: HIGH (dev server crash)
**Already in Skill**: No

**Description**:
When using SSR streaming mode, if a route loader throws an error without awaiting (using `void` instead of `await`), the dev server crashes. Using `await` or catching the error within the loader prevents the crash.

**Reproduction**:
```typescript
// routes/posts.tsx
export const Route = createFileRoute('/posts')({
  loader: async () => {
    // This crashes dev server with streaming SSR
    void fetch('/api/posts').then(r => {
      throw new Error('boom')
    })
  },
})

// Error in dev server:
// Worker error: [validation error details]
// TypeError: fetch failed
// SocketError: other side closed
```

**Solution/Workaround**:
Always await or catch errors in loaders:
```typescript
export const Route = createFileRoute('/posts')({
  loader: async () => {
    try {
      const data = await fetch('/api/posts')
      return data
    } catch (error) {
      // Handle error, don't let it escape
      throw error // This is caught by errorComponent
    }
  },
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.7: Page Hard Reloads on Save (HMR Issue)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6339](https://github.com/TanStack/router/issues/6339)
**Date**: 2026-01-09
**Verified**: Yes
**Impact**: MEDIUM (DX issue)
**Already in Skill**: No

**Description**:
When making edits to route files (especially root page file), the page hard reloads instead of using HMR. This doesn't happen when editing external component files referenced by the page.

**Reproduction**:
```typescript
// src/routes/index.tsx - editing this file causes hard reload
export const Route = createFileRoute('/')({
  component: Home,
})

// src/components/Home.tsx - editing this file uses HMR ✓
```

**Solution/Workaround**:
No workaround available. Issue is being tracked for fix.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, needs fix
- [ ] Won't fix

---

### Finding 1.8: Prerender Hangs Indefinitely if Filter Returns Zero Results

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6425](https://github.com/TanStack/router/issues/6425)
**Date**: 2026-01-20
**Verified**: Yes
**Impact**: HIGH (blocks build)
**Already in Skill**: No

**Description**:
When using TanStack Start prerendering, if `prerender.filter` returns zero true results (or no filter is provided), the build step hangs indefinitely.

**Reproduction**:
```typescript
// vite.config.ts
tanstackStart({
  prerender: {
    enabled: true,
    concurrency: 1,
    filter: (route) => false, // Returns no routes → hangs!
  },
})

// Or even without filter:
tanstackStart({
  prerender: {
    enabled: true,
    concurrency: 1,
  },
})
// Hangs at build step
```

**Solution/Workaround**:
Ensure at least one route is returned by filter, or disable prerendering:
```typescript
tanstackStart({
  prerender: {
    enabled: false, // Temporary workaround
  },
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.9: Prerendering Does Not Work in Docker

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6275](https://github.com/TanStack/router/issues/6275), [PR #6305](https://github.com/TanStack/router/pull/6305)
**Date**: 2026-01-02
**Verified**: Yes (has fix PR)
**Impact**: HIGH (blocks Docker deployment)
**Already in Skill**: No

**Description**:
TanStack Start prerendering fails when building in Docker container because the Vite preview server used for prerendering is not accessible in the Docker environment.

**Reproduction**:
```dockerfile
# Dockerfile
FROM node:20
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build # Fails: "Unable to connect" during prerender
```

**Solution/Workaround**:
PR #6305 should fix it. In the meantime, remove nitro plugin and set `preview.host` to `true`:
```typescript
// vite.config.ts
export default defineConfig({
  preview: {
    host: true, // Makes preview server accessible in Docker
  },
  plugins: [
    devtools(),
    // nitro({ preset: "bun" }), // Remove temporarily
    tanstackStart(),
    react(),
  ],
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] PR #6305 in progress
- [ ] Won't fix

---

### Finding 1.10: TanStack Start + Tailwind CSS 4 Hydration Error in Docker

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6315](https://github.com/TanStack/router/issues/6315)
**Date**: 2026-01-06
**Verified**: Partial (needs reproduction project)
**Impact**: HIGH (production deployment)
**Already in Skill**: No

**Description**:
When deploying TanStack Start with Tailwind CSS 4 to Docker, the browser tries to load a CSS asset with a different hash than what exists in `.output/public/assets`. Also causes React error #418 (hydration mismatch).

**Reproduction**:
```bash
# Works locally
bun run preview # CSS loads correctly

# Fails in Docker
docker compose build --no-cache
docker compose up -d
# Browser: 404 for CSS file with wrong hash
# Console: React error #418 - Hydration mismatch
```

**Solution/Workaround**:
No confirmed workaround yet. Issue is being investigated. Potentially related to Docker build cache or Vite manifest generation.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, needs reproduction project
- [ ] Won't fix

---

### Finding 1.11: createLazyFileRoute Auto-Replaced with createFileRoute (Virtual Routes)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6396](https://github.com/TanStack/router/issues/6396)
**Date**: 2026-01-16
**Verified**: Yes
**Impact**: MEDIUM (code splitting disabled)
**Already in Skill**: No

**Description**:
When using virtual file routes, the plugin automatically replaces `createLazyFileRoute` with `createFileRoute`, silently disabling manual code splitting. Virtual file routes don't support manual lazy routes - only automatic code splitting works.

**Reproduction**:
```typescript
// Virtual routes config: routes.ts
export const routes = rootRoute('root.tsx', [
  route('/posts', 'posts.tsx'), // This file uses createLazyFileRoute
])

// posts.tsx
export const Route = createLazyFileRoute('/posts')({ /* ... */ })
// ↑ Plugin replaces this with createFileRoute automatically
```

**Solution/Workaround**:
Use automatic code splitting instead of manual lazy routes:
```typescript
// vite.config.ts
tanstackRouter({
  target: 'react',
  virtualRouteConfig: './routes.ts',
  autoCodeSplitting: true, // Use automatic splitting
})
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (by design)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Note**: Contributor stated this is by design - virtual file routes don't support manual lazy.

---

### Finding 1.12: Route Head Function Can Execute Before Loader Finishes

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #6221](https://github.com/TanStack/router/issues/6221)
**Date**: 2025-12-25
**Verified**: Yes
**Impact**: MEDIUM (incorrect meta tags)
**Already in Skill**: No

**Description**:
The `head()` function can execute before the route `loader()` finishes, causing meta tags to be generated with incomplete or placeholder data.

**Reproduction**:
```typescript
export const Route = createFileRoute('/posts/$postId')({
  loader: async ({ params }) => {
    const post = await fetchPost(params.postId) // Slow
    return { post }
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: loaderData.post.title }, // May not be available yet!
    ],
  }),
})
```

**Solution/Workaround**:
Use Suspense-based approach or add explicit await in head():
```typescript
head: async ({ loaderData }) => {
  // Explicitly await if needed
  await loaderData
  return { meta: [...] }
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: NavigateOptions Type Safety Inconsistency

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [TanStack Blog](https://tkdodo.eu/blog/the-beauty-of-tan-stack-router), [GitHub Discussion](https://github.com/TanStack/router/discussions)
**Date**: 2025
**Verified**: Code Review Only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`NavigateOptions` type doesn't behave the same as the function returned from `useNavigate`. When navigating to a route with required parameters, `NavigateOptions` doesn't throw type errors even though params are required.

**Reproduction**:
```typescript
// Route with required params
export const Route = createFileRoute('/posts/$postId')({ /* ... */ })

// useNavigate enforces params ✓
const navigate = useNavigate()
navigate({ to: '/posts/$postId' }) // TS error: params missing ✓

// But NavigateOptions doesn't ✗
const options: NavigateOptions = {
  to: '/posts/$postId', // No TS error, but params required ✗
}
```

**Community Validation**:
- Multiple users confirm in discussions
- Maintainers acknowledge inconsistency
- Type definitions differ between runtime hook and type helper

**Solution**:
Use `useNavigate()` return type for consistency:
```typescript
const navigate = useNavigate()
type NavigateFn = typeof navigate
// Now type-safe across all usages
```

---

### Finding 2.2: React Transitions Support Limited

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [TkDodo's Blog: The Beauty of TanStack Router](https://tkdodo.eu/blog/the-beauty-of-tan-stack-router)
**Date**: 2025
**Verified**: Analysis from Framework Maintainer
**Impact**: LOW (edge case)
**Already in Skill**: No

**Description**:
While TanStack Router fully supports Suspense, it doesn't have great support for React Transitions. Navigations are wrapped in `startTransition`, but the router stores state outside of React and uses `useSyncExternalStore`, which can cause issues with isPending states.

**Analysis**:
From TkDodo (TanStack Query maintainer):
> "TanStack Router stores state outside of React and syncs it with useSyncExternalStore. This means that while navigations are wrapped in startTransition, the transition's isPending state doesn't always reflect the router's loading state accurately."

**Community Validation**:
- Acknowledged by core team member (TkDodo)
- Not a bug, but architectural limitation
- Affects edge cases with complex transition logic

**Recommendation**: Document as "Known Limitation" rather than actionable issue.

---

### Finding 2.3: Common Mistake - Missing Leading Slash in Route Paths

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [TanStack Docs: How to Debug Router Issues](https://tanstack.com/router/latest/docs/framework/react/how-to/debug-router-issues)
**Date**: Official docs, 2025
**Verified**: Official documentation
**Impact**: HIGH (common mistake)
**Already in Skill**: No

**Description**:
A very common mistake is missing the leading slash when defining routes - using `'about'` instead of `'/about'`. This causes route matching failures.

**Reproduction**:
```typescript
// Wrong - missing leading slash
export const Route = createFileRoute('about')({ /* ... */ })

// Correct
export const Route = createFileRoute('/about')({ /* ... */ })
```

**Official Guidance**:
From TanStack debugging docs: "Ensure your route paths start with `/`"

**Recommendation**: Add to "Common Mistakes" section in skill.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Deno Runtime Compatibility Issue

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #5356](https://github.com/TanStack/router/issues/5356)
**Date**: 2025
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM (Deno users only)
**Already in Skill**: No

**Description**:
When running TanStack Start with virtual routes in Deno runtime, the router generator fails with misleading error about Node.js version compatibility. The error states "This version of Node.js (v24.2.0) does not support module.register()", but the real issue is Deno's Node.js compatibility layer doesn't implement `module.register()` and the generator doesn't detect Deno runtime.

**Consensus Evidence**:
- GitHub issue with reproduction
- Multiple Deno users confirm same error
- Official response acknowledges Deno detection gap

**Recommendation**: Add to "Known Limitations" section with platform caveat.

---

### Finding 3.2: Dev Server Hot Reload Removes Nested Pathless API Routes

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #5862](https://github.com/TanStack/router/issues/5862)
**Date**: 2025-11-13 (closed 2026-01-04)
**Verified**: Fixed in latest
**Impact**: LOW (fixed)
**Already in Skill**: No

**Description**:
During dev server hot reload, nested pathless API routes were erroneously removed. This was fixed in recent versions.

**Official Status**:
- [x] Fixed in v1.145.5+
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Document as "Previously Fixed" or skip (low current relevance).

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: SessionManager Type Not Exported

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #6390](https://github.com/TanStack/router/issues/6390)
**Date**: 2026-01-16
**Verified**: No (no comments, no reproduction)
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [x] Cannot reproduce (no details provided)
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
Issue claims `SessionManager` type is not exported from public API, causing type inference issues. However, no reproduction or code example provided.

**Recommendation**: Manual verification required. DO NOT add to skill without reproduction.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Devtools dependency resolution | Known Issues #1 | Fully covered |
| Vite plugin order critical | Known Issues #2 | Fully covered with CRITICAL flag |
| Memory leak with TanStack Form | Known Issues #5 | Documented as FIXED |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 inputValidator structure loss | Known Issues Prevention | Add as Issue #9 with workaround |
| 1.2 useParams unparsed | Known Issues Prevention | Add as Issue #10 with strict mode guidance |
| 1.3 Pathless notFoundComponent | Known Issues Prevention | Add as Issue #11 with child route workaround |
| 1.4 Aborted loader undefined error | Known Issues Prevention | Add as Issue #12 with null check |
| 1.5 Vitest useState error | Known Issues Prevention | Add as Issue #13 with PR #6074 tracking |
| 1.6 Streaming SSR loader crash | Known Issues Prevention | Add as Issue #14 with await requirement |
| 1.8 Prerender hangs | Known Issues Prevention | Add as Issue #15 with filter guidance |
| 1.9 Docker prerender | Known Issues Prevention | Add as Issue #16 with preview.host workaround |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.7 HMR hard reload | Known Issues | Track for fix, low DX impact |
| 1.10 Docker CSS hydration | Known Issues | Needs more investigation |
| 1.11 Virtual routes lazy | Core Patterns | Document as limitation |
| 1.12 Head before loader | Best Practices | Add await pattern |
| 2.1 NavigateOptions types | Type Safety | Add to type patterns section |
| 2.3 Missing leading slash | Common Mistakes | Add to quick start checklist |

### Priority 3: Monitor (TIER 3-4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 2.2 React Transitions | Known limitation, edge case | Add to Known Limitations section |
| 3.1 Deno compatibility | Platform-specific | Add note in environment requirements |
| 3.2 Dev server API routes | Fixed in latest | Skip (no longer relevant) |
| 4.1 SessionManager type | No reproduction | Wait for details |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "edge case OR gotcha" in TanStack/router | 0 | 0 (no direct matches) |
| "workaround OR breaking change" | 20 | 5 |
| Recent releases (v1.144-v1.154) | 15 | 4 |
| Closed bugs (label:bug) | 30 | 12 |
| Open issues created ≥2025-05-01 | 150+ | 18 |
| "type inference" issues | 20 | 6 |
| "search params" issues | 20 | 3 |
| "code splitting" issues | 15 | 2 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "tanstack router gotcha" | 0 | N/A |
| "tanstack router edge case" | 0 | N/A |
| General "@tanstack/react-router" | Few | Low activity on SO |

**Note**: TanStack Router discussions primarily happen on GitHub Issues/Discussions, not Stack Overflow.

### Other Sources

| Source | Notes |
|--------|-------|
| [TkDodo's Blog](https://tkdodo.eu/blog/the-beauty-of-tan-stack-router) | High-quality analysis from TanStack Query maintainer |
| [TanStack Official Docs](https://tanstack.com/router/latest/docs/framework/react/how-to/debug-router-issues) | Debugging guidance for common issues |
| [GitHub Releases](https://github.com/TanStack/router/releases) | Breaking changes and fixes |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release list` for version tracking
- `WebSearch` for community content (limited results)

**Limitations**:
- Stack Overflow has very little TanStack Router content (community prefers GitHub)
- Most issues are TanStack Start specific (SSR/full-stack), not just router
- Many issues lack complete reproduction code
- Some issues are platform-specific (Docker, Deno, Windows)

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.1, 1.2, 1.3, 1.4 against current official documentation to ensure workarounds are still accurate.

**For api-method-checker**: Verify that `useParams({ strict: false })` API (finding 1.2) exists in current version and behaves as described.

**For code-example-validator**: Validate all code examples in findings 1.1-1.12 before adding to skill. Check that imports, syntax, and patterns are current.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

```markdown
### Issue #9: inputValidator Validation Errors Lose Structure

**Error**: Zod validation errors stringified in `error.message`
**Source**: [GitHub Issue #6428](https://github.com/TanStack/router/issues/6428)
**Why It Happens**: Server function error serialization doesn't preserve Zod error structure
**Prevention**:

```typescript
// Workaround: Parse stringified issues on client
try {
  await serverFn({ data: invalidData })
} catch (error) {
  if (error.message.startsWith('[')) {
    const issues = JSON.parse(error.message)
    // Use structured error data
  }
}
```

**Official Status**: Known issue, tracking PR for fix

---

### Issue #10: useParams({ strict: false }) Returns Unparsed Values

**Error**: Params typed as parsed but returned as strings after navigation
**Source**: [GitHub Issue #6385](https://github.com/TanStack/router/issues/6385)
**Why It Happens**: `match.params` no longer parsed in v1.147.3+, only `_strictParams`
**Prevention**: Use `strict: true` (default) or manually parse when using `strict: false`

```typescript
// Correct: Use strict mode for parsed params
const { postId } = useParams() // Parsed ✓

// Or manual parsing with strict: false
const params = useParams({ strict: false })
const postId = Number(params.postId)
```
```

### Adding Common Mistakes Section

```markdown
## Common Mistakes to Avoid

### 1. Missing Leading Slash in Route Paths

❌ **Wrong**: `createFileRoute('about')({})`
✅ **Correct**: `createFileRoute('/about')({})`

**Source**: [Official Debugging Guide](https://tanstack.com/router/latest/docs/framework/react/how-to/debug-router-issues)

### 2. Using strict: false Without Manual Parsing

❌ **Wrong**: `const { id } = useParams({ strict: false })` (assumes parsed)
✅ **Correct**: `const params = useParams({ strict: false }); const id = Number(params.id)`

### 3. Not Awaiting Errors in SSR Streaming Loaders

❌ **Wrong**: `void fetch().then(() => throw error)` (crashes dev server)
✅ **Correct**: `await fetch()` or `try/catch` to handle errors properly
```

---

**Research Completed**: 2026-01-20 13:45
**Next Research Due**: After v2.0.0 release or April 2026 (quarterly review)

---

## Version History

- **v1.0** (2026-01-20): Initial research covering v1.144-v1.154, focus on post-May 2025 issues
