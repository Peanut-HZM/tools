# Community Knowledge Research: Next.js

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/nextjs/SKILL.md
**Packages Researched**: next@16.1.4, react@19.2.3
**Official Repo**: vercel/next.js
**Time Window**: December 2025 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 14 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 11 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Client-Side Navigation Fails with Multiple Redirects (Middleware + Server Component)

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #87245](https://github.com/vercel/next.js/issues/87245)
**Date**: 2026-01-19
**Verified**: Yes (reproduction available)
**Impact**: HIGH - Breaks production navigation
**Already in Skill**: No

**Description**:
When using `proxy.ts` (or `middleware.ts`) that performs a redirect to add query params, AND a Server Component also calls `redirect()` to add different query params, client-side navigation via `<Link>` fails in production builds. The browser console shows: "Throttling navigation to prevent the browser from hanging."

This is a **regression from Next.js 14 → 16**. The same pattern worked correctly in Next.js 14.

**Key Observations**:
- ✅ Works in `next dev` (development mode)
- ✅ Works with direct URL access (full page load)
- ❌ Fails with client-side navigation via `<Link>` in production build
- ❌ Prefetch causes infinite redirect loop

**Reproduction**:
```typescript
// proxy.ts (Middleware/Proxy)
export function proxy(request: NextRequest) {
  const url = new URL(request.url);
  if (!url.searchParams.has("proxy-params")) {
    url.searchParams.set("proxy-params", "my-proxy");
    return NextResponse.redirect(url.toString());
  }
  return NextResponse.next();
}

// app/my-internal-redirect/page.tsx (Server Component)
export default async function MyInternalRedirectPage({ searchParams }: Props) {
  const params = await searchParams;
  if (!params["internal-params"]) {
    const currentParams = new URLSearchParams(params);
    currentParams.set("internal-params", "my-params");
    redirect(`/my-internal-redirect?${currentParams.toString()}`);
  }
  return <div>...</div>;
}

// Navigation (fails in production)
<Link href="/my-internal-redirect">
  Go to Internal Redirect Page →
</Link>
```

**Solution/Workaround**:
```typescript
// WORKAROUND: Disable prefetch
<Link href="/my-internal-redirect" prefetch={false}>
  Go to Internal Redirect Page →
</Link>
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Real-world use case: Middleware maintains global query params (tracking, session), pages maintain page-specific params (filters, state)
- Affects migration from Next.js 14 to 16

---

### Finding 1.2: Cache Components Fail with Localized Dynamic Segments

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #86870](https://github.com/vercel/next.js/issues/86870)
**Date**: 2025-12-18
**Verified**: Yes (reproduction available)
**Impact**: HIGH - Breaks i18n with cache components
**Already in Skill**: No

**Description**:
Cache components (`"use cache"` directive) do NOT work on dynamic segments when using internationalization (i18n) frameworks like `intlayer`, `next-intl`, or `lingui`. The reason is that accessing `params` forces the route to be dynamic, even with `generateStaticParams` at the layout level.

This affects ALL major React Server Component i18n frameworks.

**Key Issue**:
- Every i18n framework requires accessing `params` to get the locale
- Accessing `params` is an async call in Next.js 16
- This opts the entire page out of caching, making it dynamic
- Result: **Translated server components cannot be cached**

**Reproduction**:
```typescript
// app/[locale]/layout.tsx
export async function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'fr' }, { locale: 'de' }];
}

export default async function Layout({ params, children }: Props) {
  const { locale } = await params; // ← This makes the route dynamic

  return (
    <IntlayerProvider locale={locale}> {/* All i18n libs need this */}
      {children}
    </IntlayerProvider>
  );
}

// app/[locale]/page.tsx
'use cache' // ← This DOESN'T work because params are accessed in layout

export default async function Page({ params }: Props) {
  const { locale } = await params;
  // Cache component doesn't cache because route is dynamic
  return <div>...</div>;
}
```

**Solution/Workaround**:
```typescript
// Add generateStaticParams at EACH dynamic segment level
// app/[locale]/[id]/page.tsx
export async function generateStaticParams() {
  return [
    { locale: 'en', id: '1' },
    { locale: 'en', id: '2' },
    // ... all combinations
  ];
}

'use cache'

export default async function Page({ params }: Props) {
  // Now caching works
}
```

**Additional Context**:
- `[...not-found]` catch-all routes also trigger this issue
- The `[locale]` dynamic segment receives invalid values like `_next` during compilation
- This causes `new Intl.Locale('_next')` → `RangeError: Incorrect locale information provided`
- Provider tree fails to initialize, breaking context providers (NuqsAdapter, QueryClient, etc.)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (but unclear in docs)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to Next.js not-found.tsx limitation with multiple root layouts ([#55191](https://github.com/vercel/next.js/issues/55191), [#59180](https://github.com/vercel/next.js/issues/59180))

---

### Finding 1.3: Turbopack External Module Hash Mismatch with Different node_modules Structures

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #87737](https://github.com/vercel/next.js/issues/87737)
**Date**: 2025-12-20
**Verified**: Yes
**Impact**: HIGH - Breaks production builds
**Already in Skill**: No

**Description**:
Turbopack generates external module references with hashes that don't match installed packages when `node_modules` structure differs (e.g., monorepo, pnpm, yarn workspaces). This causes module resolution failures in production builds.

**Symptoms**:
- Build succeeds locally but fails in CI/CD
- "Module not found" errors for packages that ARE installed
- Hash mismatches between bundled references and actual module files

**Reproduction**:
```bash
# Monorepo with pnpm workspaces
packages/
  app/
    node_modules/ (symlinks to root node_modules)
  shared/
    node_modules/ (symlinks to root node_modules)
node_modules/ (hoisted dependencies)

# Turbopack generates hash based on local structure
# Deployed environment has different structure → hash mismatch → error
```

**Solution/Workaround**:
```typescript
// next.config.ts
const config: NextConfig = {
  experimental: {
    // Explicitly externalize packages to avoid hashing issues
    serverExternalPackages: ['package-name'],
  },
};
```

**Official Status**:
- [x] Partially fixed in Next.js 16.1 (improved serverExternalPackages handling)
- [x] Known issue in complex monorepo setups
- [ ] Won't fix

**Cross-Reference**:
- Related to finding about Turbopack + Bun compatibility (#86866)
- Affects pnpm, yarn workspaces, and Turborepo users

---

### Finding 1.4: Turbopack + Prisma Compatibility Issues

**Trust Score**: TIER 1 - Official Discussion
**Source**: [GitHub Discussion #77721](https://github.com/vercel/next.js/discussions/77721)
**Date**: 2025-11-15
**Verified**: Yes (multiple user reports)
**Impact**: HIGH - Breaks Prisma users
**Already in Skill**: No

**Description**:
Turbopack production builds fail with Prisma ORM (tested on v6.5.0 and v6.6.0). Error: "The 'path' argument must be of type string." This affects both the `prisma-client-js` generator and Prisma Accelerate.

**Reproduction**:
```bash
npm run build # With Turbopack default in Next.js 16
# Error: The 'path' argument must be of type string
```

**Solution/Workaround**:
```bash
# Opt out of Turbopack for production builds
npm run build -- --webpack
```

Or in `next.config.ts`:
```typescript
const config: NextConfig = {
  experimental: {
    // Disable Turbopack for production
    turbo: false,
  },
};
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required (use webpack)
- [ ] Won't fix

**Cross-Reference**:
- Skill documents Turbopack as stable, but should note Prisma incompatibility
- Related to serverExternalPackages configuration

---

### Finding 1.5: Turbopack Source Maps Expose Source Code in Production

**Trust Score**: TIER 1 - Official Discussion
**Source**: [GitHub Discussion #77721](https://github.com/vercel/next.js/discussions/77721)
**Date**: 2025-11-15
**Verified**: Yes
**Impact**: MEDIUM - Security concern
**Already in Skill**: No

**Description**:
Turbopack currently **always builds production source maps for the browser**. This will include project source code if deployed to production, which is a security/IP concern.

**Current Behavior**:
```bash
next build # With Turbopack
# Generates .map files that include full source code
# These are deployed to production by default
```

**Solution/Workaround**:
```typescript
// next.config.ts
const config: NextConfig = {
  productionBrowserSourceMaps: false, // Disable source maps
};
```

Or exclude `.map` files in deployment:
```bash
# .vercelignore or similar
*.map
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (will be improved)
- [ ] Won't fix

**Cross-Reference**:
- Security implication not mentioned in skill's Turbopack section

---

### Finding 1.6: `instanceof` Check Fails for Custom Error Classes in Server Components

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #87614](https://github.com/vercel/next.js/issues/87614)
**Date**: 2025-12-17
**Verified**: Yes
**Impact**: MEDIUM - Breaks error handling patterns
**Already in Skill**: No

**Description**:
`instanceof` checks fail for custom error classes in Server Components due to suspected module duplication. Custom error classes are loaded twice, creating different prototypes.

**Reproduction**:
```typescript
// lib/errors.ts
export class CustomError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CustomError';
  }
}

// app/page.tsx (Server Component)
import { CustomError } from '@/lib/errors';

export default async function Page() {
  try {
    throw new CustomError('Test error');
  } catch (error) {
    console.log(error instanceof CustomError); // ❌ false (should be true)
    console.log(error.name === 'CustomError'); // ✅ true (works)
  }
}
```

**Solution/Workaround**:
```typescript
// Don't use instanceof, use error.name or error.constructor.name
try {
  throw new CustomError('Test error');
} catch (error) {
  if (error instanceof Error && error.name === 'CustomError') {
    // Handle CustomError
  }
}

// Or use error.constructor.name
if (error.constructor.name === 'CustomError') {
  // Handle CustomError
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue (module duplication in RSC)
- [ ] Won't fix

**Cross-Reference**:
- Related to Server Component module loading
- Should be added to Common Errors section

---

### Finding 1.7: Dev-only RangeError with Large Prisma Queries in App Router

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #87772](https://github.com/vercel/next.js/issues/87772)
**Date**: 2025-12-21
**Verified**: Yes
**Impact**: LOW - Dev-only, specific to large datasets
**Already in Skill**: No

**Description**:
Development server throws `RangeError` in App Router async traversal when large Prisma MSSQL queries resolve (~10k rows). This only happens in `next dev`, not production builds.

**Reproduction**:
```typescript
// app/page.tsx
export default async function Page() {
  const data = await prisma.table.findMany({
    take: 10000, // Large dataset
  });

  return <div>{data.length}</div>;
  // RangeError in dev server during RSC payload serialization
}
```

**Solution/Workaround**:
```typescript
// 1. Paginate queries
const data = await prisma.table.findMany({
  take: 100, // Smaller batches
  skip: 0,
});

// 2. Use cursor-based pagination
const data = await prisma.table.findMany({
  take: 100,
  cursor: { id: lastId },
});

// 3. Production builds work fine, so only affects dev workflow
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue (dev-only)
- [ ] Won't fix

**Cross-Reference**:
- Specific to Prisma + MSSQL + large datasets
- Low priority (dev-only)

---

### Finding 1.8: TypeScript Plugin Doesn't Catch Non-Serializable Props to Client Components

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #86748](https://github.com/vercel/next.js/issues/86748)
**Date**: 2025-12-13
**Verified**: Yes
**Impact**: MEDIUM - Silent runtime errors
**Already in Skill**: No

**Description**:
The Next.js TypeScript plugin doesn't catch non-serializable props being passed from Server Components to Client Components. This causes runtime errors that are not detected at compile time.

**Reproduction**:
```typescript
// components/ClientComponent.tsx
'use client';

interface Props {
  user: {
    name: string;
    getProfile: () => void; // ❌ Function not serializable
  };
}

export default function ClientComponent({ user }: Props) {
  return <div>{user.name}</div>;
}

// app/page.tsx (Server Component)
export default function Page() {
  const user = {
    name: 'John',
    getProfile: () => console.log('profile'), // ❌ Not serializable
  };

  // TypeScript doesn't error, but runtime fails
  return <ClientComponent user={user} />;
}
```

**Solution/Workaround**:
```typescript
// 1. Only pass serializable props
interface SerializableUser {
  name: string;
  email: string;
  // No functions, no class instances, no Symbols
}

// 2. Use Zod or similar for runtime validation
import { z } from 'zod';

const UserSchema = z.object({
  name: z.string(),
  email: z.string(),
});

type User = z.infer<typeof UserSchema>;

// 3. Create functions in Client Component
'use client';

export default function ClientComponent({ user }: { user: { name: string } }) {
  const getProfile = () => console.log('profile'); // Define in client
  return <div onClick={getProfile}>{user.name}</div>;
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known limitation of TypeScript plugin
- [ ] Won't fix

**Cross-Reference**:
- Should be added to Server/Client Component best practices
- Related to "Common Errors & Solutions" section in skill

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Next.js 15/16 Caching Behavior Changed - Default to Dynamic

**Trust Score**: TIER 2 - High-Quality Community + Official Docs
**Source**: [DEV Community Article](https://dev.to/pockit_tools/why-your-nextjs-cache-isnt-working-and-how-to-fix-it-in-2026-10pp) | [Next.js Docs](https://nextjs.org/docs/app/guides/caching)
**Date**: 2025-12
**Verified**: Cross-referenced with official docs
**Impact**: HIGH - Fundamental behavior change
**Already in Skill**: Partially (Cache Components section exists)

**Description**:
Next.js 15/16 introduced major caching default changes that break assumptions from Next.js 14:

| Feature | Next.js 14 | Next.js 15/16 |
|---------|-----------|---------------|
| **fetch() requests** | Cached by default | NOT cached by default |
| **Router Cache (dynamic pages)** | Cached on client | NOT cached by default |
| **Router Cache (static pages)** | Cached | Still cached |
| **Route Handlers (GET)** | Cached | Dynamic by default |

**Community Insights**:
- "Default to dynamic in Next.js 15/16. Start with no caching and add it where beneficial, rather than debugging unexpected cache hits."
- "Always test with production builds. The development server lies about caching behavior."
- Router Cache bug: Every navigation before 30 seconds increases cache time by another 30 seconds

**Solution/Workaround**:
```typescript
// Opt-in to caching explicitly
'use cache'

export async function getData() {
  const response = await fetch('/api/data', {
    cache: 'force-cache', // Explicit caching
  });
  return response.json();
}

// OR use Cache Components
'use cache'

export async function CachedComponent() {
  const data = await getData();
  return <div>{data}</div>;
}
```

**Community Validation**:
- Multiple sources confirm (DEV Community, TrackJS blog, Web Dev Simplified)
- Corroborated by official Next.js docs migration guide

**Cross-Reference**:
- Skill documents Cache Components but should emphasize default behavior change
- Add to migration guide section

---

### Finding 2.2: Async Params Migration - Codemod Misses 20% of Cases

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Michael Pilgram Blog](https://michaelpilgram.co.uk/blog/migrating-to-nextjs-16) | [Vivek Asia Blog](https://vivek.asia/blog/next-js/nextjs-16-vs-15-differences/)
**Date**: 2025-12
**Verified**: Multiple developer reports
**Impact**: MEDIUM - Migration pain point
**Already in Skill**: Partially (async params documented)

**Description**:
The official Next.js codemod (`npx @next/codemod@canary upgrade latest`) handles ~80% of async API migrations automatically, but misses edge cases:

**Codemod Misses**:
- Async APIs accessed in custom hooks
- Conditional logic accessing params
- Components imported from external packages
- Complex server actions with multiple async calls
- Layouts with multiple params

**Community Reports**:
- "Most teams spend 4 to 8 hours migrating from Next.js 15 to 16, not because it's complicated, but because breaking changes are spread across your entire codebase."
- "Builds may succeed but throw runtime errors until you properly migrate every async API call."
- Components throw "Promise is not defined" errors when you forget to await

**Solution/Workaround**:
```typescript
// 1. Run the codemod first
npx @next/codemod@canary upgrade latest

// 2. Search for @next-codemod-error comments
// These mark places codemod couldn't auto-fix

// 3. Manually fix edge cases
// BEFORE (missed by codemod)
function useLocale() {
  const params = useParams(); // ❌ Hook not handled
  return params.locale;
}

// AFTER
function useLocale() {
  const params = useParams();
  const locale = React.use(params).locale; // Use React.use() in client
  return locale;
}

// 4. For client components, use React.use()
'use client';

export default function ClientComponent({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params); // Unwrap Promise
  return <div>{id}</div>;
}
```

**Community Validation**:
- Multiple blog posts confirm (Michael Pilgram, Vivek Asia, DEV Community)
- Developer forums report same 80/20 split

**Cross-Reference**:
- Add to "Async Route Parameters" section with codemod limitations
- Add manual migration patterns for edge cases

---

### Finding 2.3: Hydration Mismatches - Default to Server Components Principle

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Medium Article](https://medium.com/@juandadotdev/server-components-in-next-js-15-what-i-got-wrong-and-right-07915e3a04ce) | [Medium Article 2](https://medium.com/@Saroj_bist/client-vs-server-components-in-next-js-what-goes-where-74badf8c5620)
**Date**: 2025-12
**Verified**: Multiple sources agree
**Impact**: MEDIUM - Common mistake
**Already in Skill**: Partially (Server/Client composition documented)

**Description**:
Community consistently identifies hydration mismatches as the #1 Server Component mistake. The core principle is: **"Default to Server Components, move to Client only when necessary."**

**Common Mistakes**:
1. Defaulting to Client Components instead of Server Components
2. Not understanding what can stay on server vs must move to client
3. Passing non-serializable props between Server and Client
4. Importing Server Component into Client Component (auto-conversion misconception)

**Best Practices**:
```typescript
// ✅ Server Component (default)
export default async function Page() {
  const data = await fetch('/api/data').then(r => r.json());

  return (
    <div>
      <StaticHeader data={data} /> {/* Server */}
      <InteractiveButton /> {/* Client */}
    </div>
  );
}

// ✅ Client Component (only for interactivity)
'use client';

export function InteractiveButton() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}

// ❌ Wrong: Making everything client
'use client'; // Unnecessary

export default function Page() {
  // Now entire page is client-side, lose Server Component benefits
}
```

**When to Use Client Components** (from community consensus):
- State and event handlers (`onClick`, `onChange`)
- Lifecycle logic (`useEffect`)
- Browser-only APIs (`localStorage`, `window`, `Navigator.geolocation`)

**Community Validation**:
- Multiple Medium articles (Juanda Martinez, Saroj Bist, Hassan Ibrahim)
- Next.js official docs align with this principle

**Cross-Reference**:
- Add to "Server Components Patterns" section
- Emphasize "default to server" principle more prominently

---

### Finding 2.4: Parallel Routes + default.js - Hard Navigation/Refresh 404 Issues

**Trust Score**: TIER 2 - High-Quality Community + GitHub Issues
**Source**: [GitHub Issue #48090](https://github.com/vercel/next.js/issues/48090) | [GitHub Issue #73939](https://github.com/vercel/next.js/issues/73939)
**Date**: 2024-12 (ongoing in 2025)
**Verified**: Multiple user reports
**Impact**: MEDIUM - Parallel routes edge case
**Already in Skill**: Partially (default.js requirement documented)

**Description**:
Even WITH `default.js` files, hard navigating or refreshing routes with parallel routes can return 404 errors. The workaround is adding a reference to Catch All Segments when the route does not exist outside of the slot's folder.

**Reproduction**:
```typescript
// Structure
app/
├── @modal/
│   ├── login/page.tsx
│   └── default.tsx  // ← Present, but still 404 on refresh
├── page.tsx

// Problem: Hard refresh on /login → 404
```

**Solution/Workaround**:
```typescript
// Add catch-all route to handle unmatched slots
// app/@modal/[...catchAll]/page.tsx
export default function CatchAll() {
  return null;
}

// OR use catch-all in default.tsx
// app/@modal/default.tsx
export default function ModalDefault({ params }: { params: { catchAll?: string[] } }) {
  return null; // Handles all unmatched routes
}
```

**Community Validation**:
- Multiple GitHub issues report this (48090, 73939, 58796)
- Workaround confirmed by multiple developers

**Cross-Reference**:
- Add to "Parallel Routes" section
- Note this as advanced edge case beyond just having default.js

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Performance Mistakes - Misusing SSR and Caching

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Medium Article](https://medium.com/@sureshdotariya/10-performance-mistakes-in-next-js-16-that-are-killing-your-app-and-how-to-fix-them-2facfab26bea)
**Date**: 2025-12
**Verified**: Cross-referenced patterns
**Impact**: MEDIUM - Performance optimization
**Already in Skill**: No

**Description**:
Common performance mistakes identified across community sources:

1. **Over-using Client Components** - Defaulting to client when server would work
2. **Not using Streaming/Suspense** - Blocking entire page for slow data
3. **Caching mistakes** - Not understanding new Next.js 16 opt-in caching
4. **Image optimization neglect** - Not using `next/image` properly
5. **Bundle size issues** - Not code-splitting large dependencies

**Consensus Evidence**:
- Multiple sources agree (Medium, DEV Community, official docs)
- Aligned with official Next.js performance best practices

**Recommendation**: Add to "Performance Patterns" section with community-sourced flag

---

### Finding 3.2: Turbopack Bundle Size Differences from Webpack

**Trust Score**: TIER 3 - Community Consensus + Official Acknowledgment
**Source**: [GitHub Discussion #77721](https://github.com/vercel/next.js/discussions/77721)
**Date**: 2025-11
**Verified**: Official team acknowledges
**Impact**: LOW - Expected difference
**Already in Skill**: No

**Description**:
Bundle sizes built with Turbopack may differ from webpack builds. This is expected and will be improved as Turbopack matures.

**Consensus Evidence**:
- Official team comment: "It is expected that your bundle size might be different from `next build` with webpack."
- Community reports varying bundle sizes (sometimes larger, sometimes smaller)

**Recommendation**: Add note to Turbopack section that bundle size differences are expected and being optimized

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Async params/searchParams/cookies() | Breaking Changes #1, Errors #1-3 | Fully covered |
| Parallel routes require default.js | Breaking Changes #3, Error #4 | Fully covered |
| revalidateTag() requires 2 arguments | Cache Components, Error #5 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Client-side nav with redirects | Common Errors #19 | Add new error with workaround |
| 1.2 Cache + i18n dynamic segments | Common Errors #20 | Add new error with generateStaticParams solution |
| 1.3 Turbopack external module hash | Common Errors #21 | Add to Turbopack section |
| 1.4 Turbopack + Prisma incompatibility | Turbopack section | Add note about Prisma, workaround |
| 1.5 Turbopack source maps security | Turbopack section | Add security warning |
| 1.6 instanceof fails in Server Components | Common Errors #22 | Add error handling pattern |
| 2.1 Caching default changes | Migration Guide | Emphasize behavior change |
| 2.2 Async params codemod limitations | Breaking Changes #1 | Add codemod limitations and manual patterns |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.7 Dev RangeError with large queries | Community Tips | Dev-only, low priority |
| 1.8 TypeScript plugin non-serializable | Server/Client Patterns | Add to best practices |
| 2.3 Hydration - default to server | Server Components Patterns | Emphasize principle more |
| 2.4 Parallel routes catch-all | Parallel Routes section | Advanced edge case |
| 3.1 Performance mistakes | Performance section | Add community tips subsection |
| 3.2 Turbopack bundle size | Turbopack section | Add note about expected differences |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| N/A | No TIER 4 findings | — |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "server component" in vercel/next.js (Dec 2025+) | 20 | 8 |
| "edge case OR gotcha" in vercel/next.js | 30 | 0 (no results) |
| "workaround OR known issue" in vercel/next.js | 20 | 0 (no results) |
| Open bugs (recent) | 30 | 10 |
| Releases (v16.1.0-v16.1.4) | 5 | 4 |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| Next.js cache behavior 2025 | 10 | 3 high-quality articles |
| Next.js 16 async params migration | 10 | 4 migration guides |
| Next.js server components mistakes | 10 | 5 best practice articles |
| Next.js parallel routes default.js | 10 | 2 GitHub discussions |
| Next.js turbopack production issues | 10 | 2 official discussions |

### Other Sources

| Source | Notes |
|--------|-------|
| [Next.js 16.1 Blog](https://nextjs.org/blog/next-16-1) | Official release notes |
| [Next.js Security Update](https://nextjs.org/blog/security-update-2025-12-11) | CVE disclosures |
| [updateTag vs revalidateTag Discussion](https://github.com/vercel/next.js/discussions/84805) | Official clarification |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh release list/view` for release notes
- `WebSearch` for Stack Overflow and blog posts
- Cross-referencing official docs

**Limitations**:
- GitHub search didn't return results for "edge case OR gotcha" queries (possibly too restrictive)
- Stack Overflow search returned no results with 2025-2026 date filter
- Focused on recent issues (Dec 2025 - Jan 2026) due to time constraints
- Some older ongoing issues may have been missed

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference finding 1.2 (cache + i18n) against official Cache Components documentation
- Verify finding 2.1 (caching defaults) matches current Next.js 16.1 behavior

**For api-method-checker**:
- Verify `React.use()` pattern in finding 2.2 is current React 19 API
- Check if `updateTag()` and `revalidateTag()` signatures match current Next.js 16.1

**For code-example-validator**:
- Validate code examples in findings 1.1, 1.2, 1.6, 2.2
- Test Prisma workaround in finding 1.4
- Test instanceof workaround in finding 1.6

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

```markdown
### Issue #19: Client-side navigation fails with multiple redirects

**Error**: `Throttling navigation to prevent the browser from hanging`
**Source**: [GitHub Issue #87245](https://github.com/vercel/next.js/issues/87245)
**Why It Happens**: When `proxy.ts` (or `middleware.ts`) performs a redirect AND a Server Component also calls `redirect()`, prefetch causes infinite redirect loop in production builds.
**Prevention**: Disable prefetch on links that navigate to pages with redirect logic.

```typescript
// ✅ Workaround: Disable prefetch
<Link href="/my-route" prefetch={false}>
  Navigate
</Link>
```

**Status**: Regression from Next.js 14. Works in dev, fails in production.
```

### Adding to Turbopack Section

```markdown
## Turbopack Production Considerations (NEW)

**Known Limitations** (as of Next.js 16.1):

### Prisma Incompatibility
Turbopack production builds fail with Prisma ORM (v6.5+).

**Workaround**:
```bash
npm run build -- --webpack
```

### Source Maps Security
Turbopack always generates production source maps, exposing source code.

**Workaround**:
```typescript
// next.config.ts
export default {
  productionBrowserSourceMaps: false,
};
```

### External Module Hash Mismatches
Monorepos with different `node_modules` structures may experience hash mismatches.

**Workaround**:
```typescript
export default {
  experimental: {
    serverExternalPackages: ['package-name'],
  },
};
```
```

---

**Research Completed**: 2026-01-21 10:30
**Next Research Due**: After Next.js 17 release or quarterly (April 2026)

---

## Summary for Skill Maintainer

**High-Value Findings**:
1. **Client-side navigation + redirects** - Production-breaking regression (TIER 1)
2. **Cache + i18n** - Breaks all major i18n frameworks (TIER 1)
3. **Turbopack limitations** - Prisma, source maps, monorepos (TIER 1)
4. **Caching defaults changed** - Fundamental behavior shift from 14→16 (TIER 2)
5. **Async params codemod misses** - 20% manual work required (TIER 2)

**Quick Wins**:
- Add 5 new errors to "Common Errors & Solutions"
- Expand Turbopack section with production considerations
- Emphasize caching behavior change in migration guide
- Add codemod limitations to async params section
- Add "default to server" principle to Server Components patterns

**Low Priority**:
- Dev-only RangeError (finding 1.7)
- Performance tips (finding 3.1) - already well-documented
- Bundle size differences (finding 3.2) - expected behavior

Sources:
- [Next.js Caching Guide](https://nextjs.org/docs/app/guides/caching)
- [Next.js Cache Components](https://nextjs.org/docs/app/getting-started/cache-components)
- [Caching Deep Dive Discussion](https://github.com/vercel/next.js/discussions/54075)
- [Fixing Caching Bug - Ziyi Li](https://www.ziyili.dev/blog/fix-nextjs-caching-bug)
- [Next.js Cache Mastery - Web Dev Simplified](https://blog.webdevsimplified.com/2024-01/next-js-app-router-cache/)
- [Why Cache Isn't Working - DEV Community](https://dev.to/pockit_tools/why-your-nextjs-cache-isnt-working-and-how-to-fix-it-in-2026-10pp)
- [Data Caching - Leapcell](https://leapcell.io/blog/understanding-data-caching-and-revalidation-in-next-js-app-router)
- [Common Caching Errors - TrackJS](https://trackjs.com/blog/common-errors-in-nextjs-caching/)
- [Caching with App Router - ProNext.js](https://www.pronextjs.dev/workshops/next-js-react-server-component-rsc-architecture-jbvxk/caching-with-the-next-js-app-router-dtpj1)
- [Next.js 16 Upgrade Guide](https://nextjs.org/docs/app/guides/upgrading/version-16)
- [Next.js 16 Blog](https://nextjs.org/blog/next-16)
- [Migrating to Next.js 16 - Michael Pilgram](https://michaelpilgram.co.uk/blog/migrating-to-nextjs-16)
- [Next.js 16 Features - Strapi](https://strapi.io/blog/next-js-16-features)
- [Next.js 16 vs 15 - Vivek Asia](https://vivek.asia/blog/next-js/nextjs-16-vs-15-differences/)
- [What's New in Next.js 16 - Trevor Lasn](https://www.trevorlasn.com/blog/whats-new-in-nextjs-16)
- [Parallel Routes File Conventions](https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes)
- [Parallel Routes Discussion](https://github.com/vercel/next.js/discussions/68528)
- [Missing default.js Error](https://nextjs.org/docs/messages/slot-missing-default)
- [default.js Documentation](https://nextjs.org/docs/app/api-reference/file-conventions/default)
- [Turbopack in 2026 - DEV Community](https://dev.to/pockit_tools/turbopack-in-2026-the-complete-guide-to-nextjss-rust-powered-bundler-oda)
- [Turbopack Stable](https://nextjs.org/blog/turbopack-for-development-stable)
- [Next.js 16.1 Blog](https://nextjs.org/blog/next-16-1)
- [Turbopack Build Feedback](https://github.com/vercel/next.js/discussions/77721)
- [revalidateTag Documentation](https://nextjs.org/docs/app/api-reference/functions/revalidateTag)
- [updateTag vs revalidateTag Discussion](https://github.com/vercel/next.js/discussions/84805)
- [updateTag Documentation](https://nextjs.org/docs/app/api-reference/functions/updateTag)
- [10 Performance Mistakes - Medium](https://medium.com/@sureshdotariya/10-performance-mistakes-in-next-js-16-that-are-killing-your-app-and-how-to-fix-them-2facfab26bea)
- [Server Components Complete Guide - Medium](https://medium.com/@hassan.webtech/understanding-server-components-in-next-js-a-complete-guide-46cbb653068d)
- [Server Components What I Got Wrong - Medium](https://medium.com/@juandadotdev/server-components-in-next-js-15-what-i-got-wrong-and-right-07915e3a04ce)
- [Client vs Server Components - Medium](https://medium.com/@Saroj_bist/client-vs-server-components-in-next-js-what-goes-where-74badf8c5620)
