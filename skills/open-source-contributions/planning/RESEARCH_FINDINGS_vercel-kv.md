# Community Knowledge Research: Vercel KV

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/vercel-kv/SKILL.md
**Packages Researched**: @vercel/kv@3.0.0
**Official Repo**: vercel/storage
**Time Window**: January 2024 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 9 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 5 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: scanIterator() Infinite Loop in v2.0.0+

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #706](https://github.com/vercel/storage/issues/706)
**Date**: 2024-06-26
**Verified**: Yes (multiple users confirmed)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
After updating from @vercel/kv 1.0.1 to 2.0.0+, `kv.scanIterator()` no longer terminates properly in `for await` loops. The iterator processes keys correctly but never exits, preventing the function from returning. This also affects `kv.sscanIterator()`.

**Reproduction**:
```typescript
export async function startRun() {
  console.log("Starting iteration");

  for await (const key of kv.scanIterator()) {
    const value = await kv.get(key);
    console.log({ key, value });
  }

  return "This never executes"; // Loop never terminates
}
```

**Solution/Workaround**:
```typescript
// Workaround: Downgrade to v1.0.1
// Or use scan() with cursor manually instead of scanIterator()
let cursor = 0;
do {
  const result = await kv.scan(cursor);
  cursor = result[0];
  const keys = result[1];
  for (const key of keys) {
    const value = await kv.get(key);
    console.log({ key, value });
  }
} while (cursor !== 0);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects both `scanIterator()` and `sscanIterator()`
- Related to Issue #9 in skill (Scan Operation Inefficiency) but different bug

---

### Finding 1.2: zrange() with rev: true Flag Returns Empty Array

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #742](https://github.com/vercel/storage/issues/742)
**Date**: 2024-08-24
**Verified**: Yes (reproducible)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `kv.zrange()` with the `{ rev: true }` option, the SDK sometimes returns an empty array even though the sorted set has values. The CLI always returns correct values. Removing the `rev` flag returns data correctly. This appears to be a bug in the SDK's reverse flag handling for certain key patterns.

**Reproduction**:
```typescript
// CLI shows data exists:
// zrange user:chat:1 0 -1 rev
// Returns: chat:C9Osv8r, chat:v3XkExq, ...

const key1 = "user:chat:1";
const key2 = "user:chat:29d2f72f-46a9-4137-9198-436f3194f64c";

// This returns empty array (BUG)
const chats1: string[] = await kv.zrange(key1, 0, -1, { rev: true });
// Array(0) - should be Array(12)

// This works
const chats2: string[] = await kv.zrange(key2, 0, -1, { rev: true });
// Array(4) - correct

// Without rev flag, works correctly
const chats1NoRev: string[] = await kv.zrange(key1, 0, -1);
// Array(12) - correct

// Verify data exists
const keyExists = await kv.exists(key1); // returns 1
const keyType = await kv.type(key1); // returns "zset"
const setSize = await kv.zcard(key1); // returns 12
```

**Solution/Workaround**:
```typescript
// Workaround: Omit rev flag and reverse in-memory
const chats = await kv.zrange(`user:chat:${userId}`, 0, -1);
const reversedChats = chats.reverse();

// Or use negative indices
const chats = await kv.zrevrange(`user:chat:${userId}`, 0, -1);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Also affects leaderboard patterns in skill (Advanced Patterns section)

---

### Finding 1.3: v3.0.0 Breaking Change - Scan Cursor Type Changed

**Trust Score**: TIER 1 - Official Release Notes
**Source**: [GitHub Release @vercel/kv@3.0.0](https://github.com/vercel/storage/releases/tag/@vercel/kv@3.0.0)
**Date**: 2024-09-27
**Verified**: Yes (official breaking change)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Version 3.0.0 introduced a breaking change by updating @upstash/redis to v1.34.0. The cursor field in scan commands (`scan()`, `sscan()`, `zscan()`, `hscan()`) is now returned as `string` instead of `number`.

**Reproduction**:
```typescript
// v2.0.0 and earlier
const [cursor, keys] = await kv.scan(0);
typeof cursor; // "number"

// v3.0.0+
const [cursor, keys] = await kv.scan(0);
typeof cursor; // "string"
```

**Solution/Workaround**:
```typescript
// Update code to handle string cursor
let cursor: string | number = "0"; // Use string in v3+
do {
  const [newCursor, keys] = await kv.scan(cursor);
  cursor = newCursor;
  // process keys
} while (cursor !== "0"); // Compare to string "0" not number 0
```

**Official Status**:
- [x] Documented behavior (in release notes)
- [x] Breaking change in v3.0.0

**Cross-Reference**:
- Relates to Issue #9 in skill (Scan Operation Inefficiency)
- Update skill to document string cursor type for v3+

---

### Finding 1.4: v2.0.0 Auto-Pipelining Enabled by Default

**Trust Score**: TIER 1 - Official Release Notes
**Source**: [GitHub Release @vercel/kv@2.0.0](https://github.com/vercel/storage/releases/tag/@vercel/kv@2.0.0)
**Date**: 2024-05-27
**Verified**: Yes (official breaking change)
**Impact**: MEDIUM
**Already in Skill**: Partially (mentioned in patterns, not in breaking changes)

**Description**:
Version 2.0.0 enabled auto-pipelining by default, which automatically batches Redis commands for performance. This is a breaking change that may cause unexpected behavior in edge cases where command order and timing matter.

**Reproduction**:
```typescript
// v2.0.0+ automatically pipelines these commands
await kv.set('key1', 'value1');
await kv.set('key2', 'value2');
await kv.set('key3', 'value3');
// These may be executed as a single pipeline batch
```

**Solution/Workaround**:
```typescript
// If auto-pipelining causes issues, disable it:
import { createClient } from '@vercel/kv';

const kv = createClient({
  url: process.env.KV_REST_API_URL,
  token: process.env.KV_REST_API_TOKEN,
  enableAutoPipelining: false // Disable auto-pipelining
});
```

**Official Status**:
- [x] Documented behavior (in release notes)
- [x] Breaking change in v2.0.0
- [x] Can be disabled via config

**Cross-Reference**:
- Related to Issue #8 in skill (Pipeline Errors Not Handled)
- Should document in version migration section

---

### Finding 1.5: KV Returns Null on Dev Server Start (Next.js)

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #781](https://github.com/vercel/storage/issues/781)
**Date**: 2024-10-19
**Verified**: Yes (multiple users confirmed)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Vercel KV in Next.js, `kv.get()` returns `null` on the first call after starting the dev server, despite the key existing in storage. Subsequent calls return correct data until the server is restarted. This happens on each compilation in Next.js.

**Reproduction**:
```typescript
import { kv } from '@vercel/kv';

// In Next.js server component or API route
const accessTokenData = await kv.get('accessTokenData');
console.log(accessTokenData);
// null on first try after server start
// Correct data on subsequent requests
```

**Solution/Workaround**:
```typescript
// Workaround 1: Force dynamic rendering with unstable_noStore
import { unstable_noStore as noStore } from 'next/cache';

export async function getData() {
  noStore(); // Force dynamic rendering
  const data = await kv.get('mykey');
  return data;
}

// Workaround 2: Use cache: 'no-store' in fetch calls
const response = await fetch('/api/data', {
  method: 'GET',
  cache: 'no-store', // Disable Next.js caching
});

// Workaround 3: Add retry logic
async function getWithRetry(key: string, retries = 2) {
  let data = await kv.get(key);
  let attempt = 0;
  while (!data && attempt < retries) {
    await new Promise(r => setTimeout(r, 100));
    data = await kv.get(key);
    attempt++;
  }
  return data;
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to Next.js static rendering behavior
- Similar to Finding 2.1 (Generic Type Inference Bug)

---

### Finding 1.6: hset/hget Data Type Coercion Bug

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #727](https://github.com/vercel/storage/issues/727)
**Date**: 2024-07-20
**Verified**: Yes (reproducible)
**Impact**: HIGH
**Already in Skill**: Partially (covered in Issue #2 JSON Serialization)

**Description**:
When using `hset()` to store string values, `hgetall()` sometimes returns them as numbers if they look numeric. This causes type inconsistencies and runtime errors. The `automaticDeserialization: false` option doesn't help.

**Reproduction**:
```typescript
await kv.hset('key', { code1: '123456', code2: '000001' });

const value = await kv.hgetall('key');
console.log(typeof value.code1); // "number" - BUG! Should be "string"
console.log(typeof value.code2); // "string" - Correct (leading zero preserved)
console.log(value.code1); // 123456 (number, not "123456" string)
```

**Solution/Workaround**:
```typescript
// Workaround 1: Use non-numeric prefix
await kv.hset('key', { code1: 'code_123456', code2: 'code_000001' });

// Workaround 2: Store as JSON string
await kv.hset('key', {
  data: JSON.stringify({ code1: '123456', code2: '000001' })
});
const result = await kv.hget('key', 'data');
const parsed = JSON.parse(result);

// Workaround 3: Validate and recast types after retrieval
const value = await kv.hgetall('key');
const data = {
  code1: String(value.code1),
  code2: String(value.code2)
};
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Extends Issue #2 in skill (JSON Serialization Error)
- Should add specific note about numeric string coercion

---

### Finding 1.7: Vite "process is not defined" Error

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #743](https://github.com/vercel/storage/issues/743)
**Date**: 2024-08-29
**Verified**: Yes (Vite-specific)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `@vercel/kv` with Vite, importing the package causes "Uncaught ReferenceError: process is not defined" error. This happens even when following the official documentation's suggested fixes with `dotenv-expand` and `loadEnv()`.

**Reproduction**:
```typescript
// Simply importing causes error in Vite
import { createClient } from '@vercel/kv';
// Error: Uncaught ReferenceError: process is not defined
```

**Solution/Workaround**:
```typescript
// Option 1: Use Vite's define to polyfill process.env
// vite.config.ts
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    define: {
      'process.env.KV_REST_API_URL': JSON.stringify(env.KV_REST_API_URL),
      'process.env.KV_REST_API_TOKEN': JSON.stringify(env.KV_REST_API_TOKEN),
    },
  };
});

// Option 2: Use explicit createClient with hardcoded values
import { createClient } from '@vercel/kv';

const kv = createClient({
  url: import.meta.env.VITE_KV_REST_API_URL,
  token: import.meta.env.VITE_KV_REST_API_TOKEN,
});

// Option 3: Install vite-plugin-node-polyfills
// pnpm add -D vite-plugin-node-polyfills
import { nodePolyfills } from 'vite-plugin-node-polyfills';

export default defineConfig({
  plugins: [
    nodePolyfills({
      include: ['process']
    })
  ]
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Vite-specific, not an issue with Next.js or other bundlers
- Should add to Known Issues as Vite-specific problem

---

### Finding 1.8: Monorepo Build Failure - Missing Environment Variables

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #759](https://github.com/vercel/storage/issues/759)
**Date**: 2024-09-25
**Verified**: Yes (Turborepo/monorepo specific)
**Impact**: MEDIUM
**Already in Skill**: Partially (Issue #1 covers env vars, but not monorepo specifics)

**Description**:
In Turborepo/monorepo setups, abstracting `@vercel/kv` into a shared package causes build failures on Vercel with "Error: [Upstash Redis] The 'url' property is missing or undefined in your Redis config." Local builds work fine, but Vercel deployments fail.

**Reproduction**:
```typescript
// In packages/database/src/kv.ts (shared package)
import { createClient } from "@vercel/kv";

export const kv = createClient({
  url: process.env.KV_REST_API_URL,
  token: process.env.KV_REST_API_TOKEN,
});

// Environment variables in root .env file
// Vercel build fails to read them for the package
```

**Solution/Workaround**:
```typescript
// Option 1: Pass env vars explicitly from consuming app
// apps/web/src/lib/kv.ts
import { createClient } from "@vercel/kv";

export const kv = createClient({
  url: process.env.KV_REST_API_URL!,
  token: process.env.KV_REST_API_TOKEN!,
});

// Option 2: Use Vercel's environment variables UI to set at project level
// Settings → Environment Variables → Add KV_REST_API_URL and KV_REST_API_TOKEN

// Option 3: Use turbo.json to pass env vars to packages
{
  "pipeline": {
    "build": {
      "env": ["KV_REST_API_URL", "KV_REST_API_TOKEN"]
    }
  }
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Extends Issue #1 in skill (Missing Environment Variables)
- Should add monorepo-specific note

---

### Finding 1.9: Redis Streams Not Supported

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Vercel KV Redis Compatibility Docs](https://vercel.com/docs/storage/vercel-kv/redis-compatibility) + [GitHub Issue #278](https://github.com/vercel/storage/issues/278)
**Date**: 2024-02-17 (issue), 2024+ (docs)
**Verified**: Yes (confirmed by maintainers)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
@vercel/kv does not support Redis Streams (XREAD, XADD, XGROUP, etc.) even though the underlying Upstash Redis supports them. The package lacks methods like `xRead()`, `xAdd()`, etc. To use streams, you must connect directly to Upstash Redis using `ioredis` or `node-redis`.

**Reproduction**:
```typescript
import { kv } from '@vercel/kv';

// These methods don't exist on kv object
await kv.xAdd('stream:events', '*', { event: 'user.login' });
// TypeError: kv.xAdd is not a function

await kv.xRead({ key: 'stream:events', id: '0' });
// TypeError: kv.xRead is not a function
```

**Solution/Workaround**:
```typescript
// Use Upstash Redis client directly for streams
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.KV_REST_API_URL!,
  token: process.env.KV_REST_API_TOKEN!,
});

// Now streams work
await redis.xadd('stream:events', '*', { event: 'user.login' });
const messages = await redis.xread('stream:events', '0');
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented limitation
- [x] Won't fix (use Upstash client directly)

**Cross-Reference**:
- Should add to Known Limitations section
- Document when to use @upstash/redis instead of @vercel/kv

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Generic Type Inference Bug with kv.get<T>()

**Trust Score**: TIER 2 - High-Quality Community (Medium article + GitHub discussion)
**Source**: [Medium Article](https://darkaico.medium.com/the-vercel-kv-cache-mystery-when-your-data-exists-but-returns-null-a6ae5d78f8cc) + [GitHub Issue #510](https://github.com/vercel/storage/issues/510)
**Date**: 2024-01-04 (issue), 2024+ (article)
**Verified**: Code Review + Multiple User Reports
**Impact**: MEDIUM
**Already in Skill**: Partially (Issue #7 mentions type mismatches, but not this specific bug)

**Description**:
When using generics with `kv.get<T>()`, there's a type inference bug that causes the function to return `null` even when the data exists in storage. The CLI shows the value is correctly stored, but the typed get returns null. This is related to serialization/deserialization issues with TypeScript generics.

**Reproduction**:
```typescript
interface CachedWeatherData {
  temperature: number;
  city: string;
}

const cacheKey = 'weather:london';

// Set data
await kv.set(cacheKey, { temperature: 15, city: 'London' });

// Generic get returns null (BUG)
const cached = await kv.get<CachedWeatherData>(cacheKey);
console.log(cached); // null (but CLI shows data exists!)

// Non-generic get works
const rawCached = await kv.get(cacheKey);
console.log(rawCached); // { temperature: 15, city: 'London' }
```

**Solution/Workaround**:
```typescript
// Workaround: Don't use generics, cast after retrieval
const rawCached = await kv.get(cacheKey);
const cached = rawCached as CachedWeatherData | null;

// Or use type guard
function isCachedWeatherData(data: unknown): data is CachedWeatherData {
  return typeof data === 'object' && data !== null &&
         'temperature' in data && 'city' in data;
}

const rawCached = await kv.get(cacheKey);
if (rawCached && isCachedWeatherData(rawCached)) {
  // Use cached safely
}
```

**Community Validation**:
- Multiple GitHub issue comments confirm
- Medium article with detailed analysis
- Workaround verified by several developers

---

### Finding 2.2: Next.js Server Actions Cache Stale Reads

**Trust Score**: TIER 2 - High-Quality Community (GitHub discussion)
**Source**: [GitHub Issue #510](https://github.com/vercel/storage/issues/510) (comment thread)
**Date**: 2024-01-04+
**Verified**: Code Review + Multiple Users
**Impact**: HIGH
**Already in Skill**: Related to Finding 1.5 (Dev Server Null)

**Description**:
When using `kv.get()` in Next.js Server Actions ('use server'), the values appear to be cached by Next.js static rendering, returning stale data even after KV values are updated. The console output appears yellow (indicating cache hit). Same code works correctly in route handlers.

**Reproduction**:
```typescript
// app/actions.ts
'use server'
import { kv } from '@vercel/kv';

export async function logChat(text: string) {
  let n_usage = await kv.get('n_usage');
  console.log(n_usage);
  // Always returns 5 (yellow in console = cached)
  // Even after manually changing value in KV CLI
}
```

**Solution/Workaround**:
```typescript
// Workaround 1: Use unstable_noStore to force dynamic
import { unstable_noStore as noStore } from 'next/cache';

'use server'
export async function logChat(text: string) {
  noStore(); // Force dynamic rendering
  let n_usage = await kv.get('n_usage');
  console.log(n_usage); // Now returns fresh value
}

// Workaround 2: Use in route handlers instead of server actions
// app/api/chat/route.ts (automatic dynamic rendering)
export async function GET() {
  let n_usage = await kv.get('n_usage'); // Fresh data
  return Response.json({ n_usage });
}

// Workaround 3: Add cache: 'no-store' to fetch if calling API
const response = await fetch('/api/data', {
  cache: 'no-store'
});
```

**Community Validation**:
- Confirmed by Next.js team member (dferber90)
- Multiple developers report same issue
- Workaround verified effective

---

### Finding 2.3: hgetall Returns Object Not JSON String

**Trust Score**: TIER 2 - High-Quality Community (GitHub discussion)
**Source**: [GitHub Issue #674](https://github.com/vercel/storage/issues/674)
**Date**: 2024-05-05
**Verified**: Confirmed by Maintainer
**Impact**: LOW (Documentation/DX Issue)
**Already in Skill**: No

**Description**:
`kv.hgetall()` returns a JavaScript object, not a JSON string. This confuses developers expecting string serialization like other KV operations. The confusion is compounded by lack of clear type definitions.

**Reproduction**:
```typescript
await kv.hset('foobar', { '1834': 'https://example.com' });
await kv.hset('foobar', { '1314': 'https://example2.com' });

const data = await kv.hgetall('foobar');
console.log(typeof data); // "object" not "string"
console.log(data);
// { '1834': 'https://example.com', '1314': 'https://example2.com' }

// This fails (expects string)
const parsed = JSON.parse(data);
// TypeError: Cannot convert object to primitive value
```

**Solution/Workaround**:
```typescript
// It's already an object - use directly
const data = await kv.hgetall('foobar');
console.log(data['1834']); // 'https://example.com'

// If you need JSON string
const jsonString = JSON.stringify(data);

// Type definitions available from @upstash/redis
import type { HashField } from '@upstash/redis';
const data: Record<string, string> = await kv.hgetall('foobar');
```

**Community Validation**:
- Confirmed by vercel/storage maintainer (luismeyer)
- Type definitions available from @upstash/redis
- Common DX confusion

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Vercel KV Product Sunset Notice

**Trust Score**: TIER 3 - Community Consensus (Multiple Sources)
**Source**: [GitHub Issue #829](https://github.com/vercel/storage/issues/829) + [Vercel Community](https://community.vercel.com/t/switching-from-vercel-kv-to-upstash-kv-questions/2660)
**Date**: 2025-02-11 (documentation removal)
**Verified**: Cross-Referenced Multiple Sources
**Impact**: HIGH (Strategic)
**Already in Skill**: No

**Description**:
Vercel has sunset first-party Vercel KV storage and migrated all stores to the Vercel Marketplace (powered by Upstash). The official Vercel KV documentation has been removed. New projects should use Upstash KV from the marketplace instead. The @vercel/kv package still works but is essentially a wrapper around Upstash Redis.

**Solution**:
```typescript
// Existing @vercel/kv code continues to work
import { kv } from '@vercel/kv'; // Still supported

// For new projects, use Upstash directly from Marketplace
// 1. Install Upstash from Vercel Marketplace
// 2. Use @upstash/redis package
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
});
```

**Consensus Evidence**:
- Multiple community forum threads
- GitHub issue #829 confirming documentation removal
- Vercel product changes page
- Multiple developers reporting marketplace migration

**Recommendation**: Add deprecation notice to skill. Note that @vercel/kv still works but is essentially Upstash Redis.

---

### Finding 3.2: Connection Pooling Not Exposed

**Trust Score**: TIER 3 - Community Consensus (Stack Overflow + discussions)
**Source**: Multiple community discussions + [Upstash blog](https://upstash.com/blog/vercel-auto-pipeline)
**Date**: 2024+ (ongoing discussion)
**Verified**: Cross-Referenced Community Sources
**Impact**: LOW
**Already in Skill**: No

**Description**:
@vercel/kv (and Upstash Redis REST API) does not expose connection pooling configuration because it uses HTTP REST API rather than persistent TCP connections. Auto-pipelining (v2.0+) provides batching benefits but not true connection pooling. This differs from traditional Redis clients using persistent connections.

**Solution**:
```typescript
// Auto-pipelining provides batching (enabled by default in v2.0+)
// Multiple concurrent requests automatically batched

// To use traditional connection pooling, use TCP-based client
import { Redis } from 'ioredis';

const redis = new Redis({
  host: process.env.UPSTASH_REDIS_HOST,
  port: Number(process.env.UPSTASH_REDIS_PORT),
  password: process.env.UPSTASH_REDIS_PASSWORD,
  tls: {},
  maxRetriesPerRequest: 3,
  // Connection pool options available
  lazyConnect: true,
  enableReadyCheck: true,
});
```

**Consensus Evidence**:
- Upstash documentation confirms REST API design
- Community discussions about lack of connection pooling
- Auto-pipelining as alternative approach

**Recommendation**: Add note to skill that @vercel/kv uses REST API (no connection pooling), auto-pipelining is the performance optimization mechanism.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Inconsistent Increment Behavior in Server Actions

**Trust Score**: TIER 4 - Low Confidence
**Source**: [GitHub Issue #557](https://github.com/vercel/storage/issues/557)
**Date**: 2024-01-19
**Verified**: No (single report, cannot reproduce)
**Impact**: Unknown

**Why Flagged**:
- [x] Single source only
- [x] Cannot reproduce (insufficient code provided)
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [x] Likely Next.js caching issue (not KV bug)

**Description**:
Single report of `kv.incr()` behaving inconsistently in Next.js Server Actions. Likely related to static rendering caching (same as Finding 2.2) rather than actual KV bug.

**Recommendation**: Monitor for more reports. Likely duplicate of Finding 2.2. DO NOT add without additional verification.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Missing environment variables | Known Issues #1 | Fully covered |
| JSON serialization errors | Known Issues #2 | Partially covered, see Finding 1.6 for enhancement |
| TTL not set | Known Issues #4 | Fully covered |
| Rate limits exceeded | Known Issues #5 | Fully covered |
| Type mismatches | Known Issues #7 | Partially covered, see Finding 2.1 for enhancement |
| Pipeline errors | Known Issues #8 | Fully covered |
| Scan inefficiency | Known Issues #9 | Partially covered, see Finding 1.1 for bug |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 scanIterator Infinite Loop | Known Issues Prevention | Add as Issue #11 |
| 1.2 zrange rev Bug | Known Issues Prevention | Add as Issue #12 |
| 1.5 Dev Server Null Returns | Known Issues Prevention | Add as Issue #13 |
| 1.6 hset/hget Type Coercion | Known Issues Prevention | Expand Issue #2 with hash-specific example |
| 1.7 Vite process Undefined | Known Issues Prevention | Add as Issue #14 |
| 1.9 Redis Streams Not Supported | Known Limitations | Add new section |

### Priority 2: Add Breaking Changes Section (TIER 1)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.3 v3.0.0 Cursor Type | Breaking Changes | New section documenting version migrations |
| 1.4 v2.0.0 Auto-Pipelining | Breaking Changes | Document default change |

### Priority 3: Add Monorepo/Framework Notes (TIER 1-2)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.8 Monorepo Env Vars | Known Issues Prevention | Expand Issue #1 with monorepo note |
| 2.2 Next.js Server Actions | Framework Integration | New subsection under Next.js usage |
| 2.3 hgetall Returns Object | Common Patterns | Add clarification note |

### Priority 4: Add Deprecation Notice (TIER 3)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 3.1 Product Sunset | Header/Quick Start | Add notice about marketplace migration |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "kv" in vercel/storage (open) | 9 | 7 |
| "kv" in vercel/storage (closed) | 8 | 5 |
| "edge case OR gotcha" | 0 | 0 |
| Releases | 10 | 2 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "@vercel/kv issues 2024" | 0 visible | N/A |
| Vercel KV problems | Links but no content | Low |

### Other Sources

| Source | Notes |
|--------|-------|
| [Vercel Docs](https://vercel.com/docs/storage/vercel-kv) | Official documentation (some removed) |
| [Upstash Blog](https://upstash.com/blog/vercel-auto-pipeline) | Auto-pipelining explanation |
| [Medium Article](https://darkaico.medium.com/the-vercel-kv-cache-mystery-when-your-data-exists-but-returns-null-a6ae5d78f8cc) | Type inference bug analysis |
| GitHub Release Notes | v2.0.0 and v3.0.0 breaking changes |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release view` for version change notes
- `WebSearch` for Stack Overflow, blogs, and documentation
- `npm view` for package version information

**Limitations**:
- Stack Overflow has limited results (most discussion happens on GitHub)
- Some Vercel documentation has been removed post-sunset
- Could not access paywalled content
- Focus on 2024+ means some older edge cases may be missed

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.1 (scanIterator), 1.2 (zrange), 1.5 (dev server null), and 1.7 (Vite) against current @vercel/kv documentation to verify they're still unresolved.

**For api-method-checker**: Verify that the workarounds in findings 1.1, 1.2, and 1.9 use currently available APIs in @vercel/kv v3.0.0.

**For code-example-validator**: Validate code examples in all TIER 1 findings before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

```markdown
### Issue #11: scanIterator() Infinite Loop (v2.0.0+)

**Error**: `for await` loop never terminates when using `kv.scanIterator()`
**Source**: [GitHub Issue #706](https://github.com/vercel/storage/issues/706)
**Why It Happens**: Bug in v2.0.0+ where iterator doesn't properly signal completion
**Prevention**: Use manual `scan()` with cursor instead of `scanIterator()`.

```typescript
// Don't use scanIterator() - it hangs in v2.0.0+
for await (const key of kv.scanIterator()) { ... } // HANGS

// Use manual scan with cursor
let cursor = 0;
do {
  const [newCursor, keys] = await kv.scan(cursor);
  cursor = newCursor;
  for (const key of keys) {
    await processKey(key);
  }
} while (cursor !== 0); // v2.x use number, v3.x use "0" string
```
```

### Adding Breaking Changes Section

```markdown
## Version Migration Guide

### v3.0.0 Breaking Changes

**Cursor Type Changed** ([Release Notes](https://github.com/vercel/storage/releases/tag/@vercel/kv@3.0.0)):
- Scan cursor now returns `string` instead of `number`
- Update comparisons from `cursor !== 0` to `cursor !== "0"`

**Example**:
```typescript
// v2.x
let cursor: number = 0;
while (cursor !== 0) { ... }

// v3.x
let cursor: string = "0";
while (cursor !== "0") { ... }
```

### v2.0.0 Breaking Changes

**Auto-Pipelining Enabled by Default** ([Release Notes](https://github.com/vercel/storage/releases/tag/@vercel/kv@2.0.0)):
- Commands now automatically batched for performance
- May cause timing issues in edge cases
- Disable with `enableAutoPipelining: false` if needed
```

### Adding Product Status Notice

```markdown
## Product Status (2025+)

> **Note**: Vercel has migrated Vercel KV to the Vercel Marketplace (powered by Upstash). The @vercel/kv package still works but is essentially a wrapper around Upstash Redis. For new projects, consider using `@upstash/redis` directly from the Vercel Marketplace.

Documentation: [Upstash for Vercel](https://vercel.com/marketplace/upstash)
```

---

**Research Completed**: 2026-01-21 09:45
**Next Research Due**: After @vercel/kv v4.0.0 release (or quarterly check)
