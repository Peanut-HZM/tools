# Community Knowledge Research: Cloudflare Durable Objects

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-durable-objects/SKILL.md
**Packages Researched**: @cloudflare/workers-types@4.20260109.0, wrangler@4.59.2, @cloudflare/actors@0.x (beta)
**Official Repo**: cloudflare/workers-sdk, cloudflare/workerd, cloudflare/actors
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 13 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 5 |
| Recommended to Add | 8 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: JavaScript Booleans Bound as Strings in SQLite (Not Integers)

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #9964](https://github.com/cloudflare/workers-sdk/issues/9964)
**Date**: 2025-07-15
**Verified**: Yes, confirmed by Cloudflare team
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When binding JavaScript boolean values to SQLite queries in Durable Objects, the values are serialized as the string `"true"` or `"false"` instead of integers `0`/`1` as they are in D1. This inconsistency between D1 and DO SQLite backends can cause unexpected behavior.

**Reproduction**:
```typescript
// Durable Object SQLite
this.sql.exec('INSERT INTO test (bool_col) VALUES (?)', true);
const result = this.sql.exec('SELECT bool_col FROM test').one();
console.log(result.bool_col); // "true" (string)

// Expected (D1 behavior):
console.log(result.bool_col); // 1 (integer)
```

**Solution/Workaround**:
```typescript
// Manually convert booleans to integers
this.sql.exec('INSERT INTO test (bool_col) VALUES (?)', value ? 1 : 0);

// Or use STRICT tables to catch type mismatches early
this.sql.exec(`
  CREATE TABLE IF NOT EXISTS test (
    id INTEGER PRIMARY KEY,
    bool_col INTEGER NOT NULL
  ) STRICT;
`);
```

**Official Status**:
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required (STOR-4509 tracked internally)
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Cloudflare team comment (penalosa, alsuren)
- Related to: Skill section on SQL API (line 162-161)
- Note: Planned as backwards-incompatible change requiring careful rollout

---

### Finding 1.2: RPC ReadableStream Cancel Logs False Network Errors

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #11071](https://github.com/cloudflare/workers-sdk/issues/11071)
**Date**: 2025-10-23
**Verified**: Yes, confirmed reproducible by maintainer
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Canceling a ReadableStream returned from a Durable Object via RPC and proxied by a Worker results in Wrangler dev logs showing "Network connection lost" almost immediately, followed later (~1 minute) by an "IoContext" message. This occurs despite the stream's cancel being invoked correctly in both the Worker and the DO, making it look like an actual network fault during normal cancellation.

**Reproduction**:
```typescript
// Durable Object
export class MyDO extends DurableObject {
  async rpc() {
    return new ReadableStream({
      async start(controller) {
        for await (const value of dataSource) {
          controller.enqueue(new TextEncoder().encode(String(value)));
        }
      },
      cancel() {
        console.log('CANCELLED'); // This logs correctly
      },
    });
  }
}

// Worker
const stream = await stub.rpc();
request.signal.addEventListener('abort', () => {
  console.log('CLIENT ABORTED REQUEST');
  stream.cancel(); // Triggers false error logs
});
return new Response(stream, { headers: { 'Content-Type': 'application/octet-stream' } });
```

**Solution/Workaround**:
No workaround available. The cancellation works correctly, but the error logs are misleading. This appears to be a Wrangler/Miniflare presentation issue rather than a runtime behavior problem.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Documented behavior
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Maintainer petebacondarwin confirmed reproduction
- Related to: Skill section on RPC vs HTTP Fetch (line 309-348)
- Note: Issue isolated to Wrangler dev, not present in workerd-only setup

---

### Finding 1.3: blockConcurrencyWhile Does Not Block in Local Dev (Vite Plugin)

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #8686](https://github.com/cloudflare/workers-sdk/issues/8686)
**Date**: 2025-03-26 (Closed, fixed in PR #9023)
**Verified**: Yes, confirmed and fixed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
blockConcurrencyWhile in Durable Object constructor does not block requests in local dev (wrangler dev / @cloudflare/vite-plugin). However, in production it blocks correctly. This causes a mismatch between local testing and production behavior, potentially hiding race conditions during development.

**Reproduction**:
```typescript
export class MyDO extends DurableObject {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);

    // This should block concurrent requests until complete
    ctx.blockConcurrencyWhile(async () => {
      await new Promise(resolve => setTimeout(resolve, 5000));
      this.ready = true;
    });
  }

  async fetch(request: Request) {
    console.log('Ready:', this.ready); // May log false in local dev, true in production
    return new Response('OK');
  }
}
```

**Solution/Workaround**:
Upgrade to @cloudflare/vite-plugin v1.3.1+ and wrangler v4.18.0+ where this is fixed.

**Official Status**:
- [x] Fixed in version 1.3.1 (@cloudflare/vite-plugin)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Multiple users (aroman, zegevlier, grocco)
- Fixed by: PR #9023
- Related to: Skill section on Constructor Rules (line 105-111)

---

### Finding 1.4: deleteAll() in Alarm Handler Causes Internal Error (SQLite)

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #2993 (workerd)](https://github.com/cloudflare/workerd/issues/2993)
**Date**: 2024-10-24 (Closed, fixed and rolled out)
**Verified**: Yes, confirmed and fixed
**Impact**: HIGH
**Already in Skill**: Partially (mentions deleteAll atomic behavior, not alarm interaction)

**Description**:
Calling deleteAll in an alarm handler in SQLite-backed Durable Objects causes an internal error, which means the alarm handler fails and keeps getting retried indefinitely. This creates an alarm retry loop that cannot be escaped.

**Reproduction**:
```typescript
export class MyDO extends DurableObject {
  async alarm(info: { retryCount: number }): Promise<void> {
    // This causes internal error and retry loop
    await this.ctx.storage.deleteAll();
  }
}
```

**Solution/Workaround**:
```typescript
// Call deleteAlarm() BEFORE deleteAll()
async alarm(info: { retryCount: number }): Promise<void> {
  await this.ctx.storage.deleteAlarm();
  await this.ctx.storage.deleteAll(); // Now works correctly
}
```

**Official Status**:
- [x] Fixed in runtime version (rolled out after PR merge)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Cloudflare team (joshthoward, jclee)
- Related to: Skill section on Alarms API (line 266-303) and Known Issue #9 (line 664-668)
- Note: Some users still experiencing issues with variations (stayallive comment)

---

### Finding 1.5: Outgoing WebSocket Connections Prevent Hibernation

**Trust Score**: TIER 1 - Official GitHub Feature Request
**Source**: [GitHub Issue #4864 (workerd)](https://github.com/cloudflare/workerd/issues/4864)
**Date**: 2025-08-22
**Verified**: Yes, confirmed limitation
**Impact**: HIGH
**Already in Skill**: Partially (mentions "outgoing WebSocket cannot hibernate" in Known Issue #7)

**Description**:
Durable Objects that maintain persistent connections to external WebSocket services using new WebSocket('some-url') cannot hibernate and will remain pinned in memory indefinitely. This prevents cost optimization during idle periods and limits scalability benefits of hibernation.

**Current Behavior**:
- ✅ Hibernation works for **incoming** WebSocket connections via ctx.acceptWebSocket(socket)
- ❌ Hibernation does **not work** for **outgoing** WebSocket connections created via new WebSocket(url)

**Use Cases Affected**:
- Real-time database subscriptions (Supabase, Firebase)
- Message brokers (Redis Streams, Apache Kafka)
- WebSocket connections to external real-time services
- Inter-service communication

**Solution/Workaround**:
No workaround available. This is a fundamental limitation. Redesign architecture to avoid outgoing WebSocket connections from Durable Objects if hibernation is required.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, feature request open
- [x] Documented behavior
- [ ] Won't fix

**Cross-Reference**:
- Related to: Skill section on Known Issue #7 (line 652-657) - expand with specific use cases
- Related to: WebSocket Hibernation API section (line 190-262)

---

### Finding 1.6: RPC to Durable Objects Fails Across Multiple wrangler dev Sessions

**Trust Score**: TIER 1 - Official GitHub Feature Request
**Source**: [GitHub Issue #11944](https://github.com/cloudflare/workers-sdk/issues/11944)
**Date**: 2026-01-15
**Verified**: Yes, confirmed limitation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Accessing a Durable Object over RPC in multiple wrangler dev instances (e.g., separate Workers in a monorepo) causes error: "Cannot access MyDurableObject#myMethod as Durable Object RPC is not yet supported between multiple wrangler dev sessions."

This makes local development of multi-worker systems with shared Durable Objects difficult.

**Reproduction**:
```bash
# Terminal 1: Worker A
wrangler dev

# Terminal 2: Worker B (shares DO with Worker A)
wrangler dev

# Error when Worker B calls DO RPC:
# "Cannot access MyDurableObject#myMethod as Durable Object RPC is not yet supported..."
```

**Solution/Workaround**:
Use wrangler dev -c config1 -c config2 to run multiple workers in a single session, or use HTTP fetch instead of RPC for cross-worker DO communication during local development.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, feature in consideration
- [x] Documented behavior
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Team comment (emily-shen)
- Related to: Skill section on RPC vs HTTP Fetch (line 309-348)

---

### Finding 1.7: state.id.name Undefined in Constructor (vitest-pool-workers Regression)

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #11580](https://github.com/cloudflare/workers-sdk/issues/11580)
**Date**: 2025-12-09 (Closed)
**Verified**: Yes, regression in vitest-pool-workers 0.8.71
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using @cloudflare/vitest-pool-workers version 0.8.71, DurableObjectState.id.name is undefined in the Durable Object constructor, even when the ID was created using idFromName. This breaks code that relies on the name in the constructor. Worked correctly in 0.8.38.

**Reproduction**:
```typescript
export class MyDO extends DurableObject {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    console.log(ctx.id.name); // undefined in vitest 0.8.71, works in 0.8.38
  }
}

// Test
const id = env.MY_DO.idFromName('test-name');
const stub = env.MY_DO.get(id);
await stub.fetch(...);
```

**Solution/Workaround**:
Downgrade to @cloudflare/vitest-pool-workers@0.8.38 or wait for fix in newer version.

**Official Status**:
- [x] Fixed in later version (issue closed)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: Testing with Durable Objects
- Note: Vitest-specific issue, not production runtime

---

### Finding 1.8: @cloudflare/actors Library Beta Issues

**Trust Score**: TIER 1 - Official GitHub Issues
**Source**: [GitHub cloudflare/actors](https://github.com/cloudflare/actors/issues)
**Date**: 2025-06-27 to 2025-12-05 (Ongoing)
**Verified**: Yes, multiple open issues
**Impact**: MEDIUM
**Already in Skill**: Mentioned briefly (line 19)

**Description**:
The @cloudflare/actors library (beta, released June 2025) has several open issues that developers should be aware of:

1. **@Persist state returns RpcStub objects when returned via RPC** (#99, 2025-12-05) - Serialization issue with persisted state
2. **Alarms runs setName which doesn't exist** (#90, 2025-11-04) - If Alarms class used independently of Actor class
3. **Actor this.identifier not available during blockConcurrencyWhile** (#60, 2025-08-31) - Property access limitation
4. **Unable to use with vitest in integration tests** (#49, 2025-08-10) - Testing integration issues
5. **Proper instance not being removed with .destroy()** (#23, 2025-06-27, bug) - Memory management issue
6. **DurableObjectStub obscures the type of sql method** (#22, 2025-06-26, bug) - TypeScript typing issue

**Recommendation**:
Skill should add note that @cloudflare/actors is in beta and has active issues. Link to GitHub issues page. Recommend testing thoroughly before production use.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issues, beta library
- [ ] Documented behavior
- [ ] Won't fix

**Cross-Reference**:
- Related to: Skill section mentioning @cloudflare/actors (line 19)
- Add: Beta stability warning, link to issues page

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: WebSocket Hibernation State Loss Pattern (Common Pitfall)

**Trust Score**: TIER 2 - High-Quality Community Blog + GitHub Discussions
**Sources**:
- [Debugging WebSocket Hibernation Blog](https://thomasgauvin.com/writing/how-cloudflare-durable-objects-websocket-hibernation-works/)
- [DO Hibernate Not Working - Cloudflare Community](https://community.cloudflare.com/t/do-hibernate-not-working-when-sending-message-through-websocket/691197)
- [Hono Issue #3206](https://github.com/honojs/hono/issues/3206)

**Date**: 2024-2025
**Verified**: Cross-referenced across multiple sources
**Impact**: HIGH
**Already in Skill**: Yes (Known Issue #6, line 637-650)

**Description**:
Community sources highlight a common pitfall: developers expect in-memory state to persist across hibernation without explicitly serializing it. This is already well-documented in the skill, but community discussions reveal:

1. **Constructor gets called on every wake** - The pool of connections stored in this.sessions = new Map gets wiped clean
2. **Framework integration issues** - Triplit's createTriplitHonoServer was using server.accept instead of ctx.acceptWebSocket(server), preventing hibernation
3. **Documentation vs. reality gap** - Code copied from docs sometimes doesn't work as expected (though Cloudflare notes many people use it successfully)

**Community Validation**:
- Multiple blog posts explaining the pattern
- GitHub issues across frameworks (tRPC, Hono, Triplit)
- Cloudflare Community forum discussions

**Cross-Reference**:
- Already covered in skill Known Issue #6 (line 637-650)
- Could expand with framework-specific integration notes

---

### Finding 2.2: SQLite STRICT Tables Catch Type Mismatches Early

**Trust Score**: TIER 2 - Official Comment + Community Practice
**Source**: [GitHub Issue #9964 Comment](https://github.com/cloudflare/workers-sdk/issues/9964#issuecomment-2644697068)
**Date**: 2025-07-15
**Verified**: Recommended by Cloudflare team member (alsuren)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Use SQLite STRICT tables to catch type mismatches and implicit conversions early during development. This is especially important given the boolean binding issue (Finding 1.1).

**Solution**:
```typescript
// Add STRICT keyword to table definitions
this.sql.exec(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    is_read INTEGER NOT NULL,  -- Explicit integer for boolean
    created_at INTEGER NOT NULL
  ) STRICT;
`);

// STRICT mode enforces type affinity strictly
// Regular SQLite allows flexible types, STRICT requires exact matches
```

**Community Validation**:
- Recommended by Cloudflare team member
- SQLite official feature: https://www.sqlite.org/stricttables.html

**Recommendation**: Add to SQL API section as best practice

---

### Finding 2.3: WebSocket Message Size Increased to 32 MiB (Oct 2025)

**Trust Score**: TIER 2 - Official Changelog
**Source**: [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-10-31-increased-websocket-message-size-limit/)
**Date**: 2025-10-31
**Verified**: Yes, official announcement
**Impact**: MEDIUM
**Already in Skill**: Yes (line 196, line 239)

**Description**:
Workers WebSocket message size limit increased from 1 MiB to 32 MiB on October 31, 2025. This allows handling use cases requiring large message sizes, such as processing Chrome DevTools Protocol messages. Applies to Workers, Durable Objects, and Browser Rendering.

**Official Status**:
- [x] Documented in changelog
- Already updated in skill (line 196, 239)

**Cross-Reference**:
- Already documented in skill
- No action needed

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Horizontal Scaling Pattern for 10GB Storage Limit

**Trust Score**: TIER 3 - Community Consensus + Official Docs
**Sources**:
- [Cloudflare Docs - Limits](https://developers.cloudflare.com/durable-objects/platform/limits/)
- [Blog: Unlimited Graph Databases](https://boristane.com/blog/durable-objects-graph-databases/)
- [Community Forum - Best Practices](https://community.cloudflare.com/t/durable-objects-workers-new-best-practices-guide-for-durable-objects/868986)

**Date**: 2024-2025
**Verified**: Cross-referenced official docs + community practice
**Impact**: MEDIUM
**Already in Skill**: Mentioned (line 686)

**Description**:
Community best practice for working around the 10GB per-object SQLite storage limit is horizontal scaling across multiple Durable Objects. Design pattern: create one Durable Object per logical unit (chat room, game session, user, tenant) rather than a global singleton.

**Pattern**:
```typescript
// Don't: Single global DO that hits 10GB limit
const globalDO = env.MY_DO.idFromName('global-singleton');

// Do: One DO per logical unit (unlimited total)
const userDO = env.USER_DATA.idFromName(`user:${userId}`);
const roomDO = env.CHAT_ROOM.idFromName(`room:${roomId}`);
```

**Consensus Evidence**:
- Official docs recommend this pattern
- Multiple community blogs demonstrate it
- Cloudflare team promotes "atom of coordination" design

**Recommendation**: Already documented, could add more specific examples

---

### Finding 3.2: Framework Integration Patterns (Hono, tRPC)

**Trust Score**: TIER 3 - Community Consensus
**Sources**:
- [Hono Docs - Durable Objects](https://hono.dev/examples/cloudflare-durable-objects)
- [tRPC Discussion #4400](https://github.com/trpc/trpc/discussions/4400)
- [DEV.to - Hono WebSocket Tutorial](https://dev.to/fiberplane/creating-a-websocket-server-in-hono-with-durable-objects-4ha3)

**Date**: 2024-2025
**Verified**: Multiple community sources
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Community has developed integration patterns for popular frameworks with Durable Objects:

**Hono Pattern** (compatibility date 2024-04-03+):
- Use Hono as router in Worker
- Call RPC to Durable Objects
- WebSocket upgrade requires ctx.acceptWebSocket not server.accept

**tRPC Pattern**:
- tRPC over WebSockets requires rewriting applyWSSHandler into multiple methods to work with hibernation API
- Not straightforward integration

**Recommendation**: Consider adding "Framework Integration" section with these patterns

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| WebSocket hibernation state loss | Known Issue #6 (line 637-650) | Fully covered |
| Partial deleteAll on KV backend | Known Issue #9 (line 664-668) | Covered, could link to alarm interaction |
| Outgoing WebSocket limitation | Known Issue #7 (line 652-657) | Mentioned, could expand use cases |
| WebSocket 32 MiB message size | Line 196, 239 | Fully documented |
| 10GB SQLite storage limit | Line 186, 686 | Documented with limit increase form |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Boolean binding issue | Known Issues Prevention | Add as Issue #16 |
| 1.2 RPC stream cancel logs | Known Issues Prevention | Add as Issue #17 |
| 1.3 blockConcurrencyWhile local dev | Known Issues Prevention | Add as Issue #18 (Fixed) |
| 1.4 deleteAll alarm interaction | Known Issue #9 expansion | Expand with alarm handler conflict |
| 1.5 Outgoing WebSocket expansion | Known Issue #7 expansion | Add specific use cases affected |
| 1.6 RPC multi-session limitation | Known Issues Prevention | Add as Issue #19 |
| 1.8 @cloudflare/actors beta warning | Recent Updates section | Add beta stability note |
| 2.2 STRICT tables best practice | SQL API section | Add as best practice |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 3.2 Framework integration | New section | Hono + tRPC patterns |
| 3.1 Horizontal scaling expansion | Common Patterns | More specific examples |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "durable objects" bugs (2025-05-01+) | 14 | 8 |
| "durable objects alarm" | 7 | 2 |
| "durable objects migration" | 7 | 2 |
| "durable objects RPC" | 6 | 3 |
| "durable objects blockConcurrencyWhile" | 2 | 2 |
| cloudflare/actors issues | 10+ | 6 |
| cloudflare/workerd DO issues | 2 | 2 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| Cloudflare durable objects 2025 | 0 | N/A - no results |
| Durable objects gotcha/edge case 2024-2025 | 0 | N/A - no results |

**Note**: Stack Overflow has very limited recent Durable Objects content. Most community discussion happens on GitHub issues and Cloudflare Community forums.

### Other Sources

| Source | Notes |
|--------|-------|
| [Cloudflare Changelog](https://developers.cloudflare.com/changelog/) | WebSocket message size increase |
| [Thomas Gauvin Blog](https://thomasgauvin.com/writing/how-cloudflare-durable-objects-websocket-hibernation-works/) | Detailed hibernation walkthrough |
| [Boris Tane Blog](https://boristane.com/blog/durable-objects-graph-databases/) | Graph database pattern |
| [Cloudflare Community Forums](https://community.cloudflare.com/) | Hibernation issues, best practices |
| [Hono Docs](https://hono.dev/examples/cloudflare-durable-objects) | Framework integration |

---

## Methodology Notes

**Tools Used**:
- gh search issues for GitHub discovery in cloudflare/workers-sdk, cloudflare/workerd, cloudflare/actors
- gh issue view for detailed issue content
- WebSearch for community blogs, forums, and Stack Overflow
- gh release list for recent breaking changes

**Limitations**:
- Stack Overflow has minimal recent Durable Objects content (no results for 2024-2025 queries)
- Most community knowledge is on GitHub issues and official Cloudflare Community forums
- Some cloudflare/actors issues lack detailed reproduction steps (beta library)
- Several vitest-pool-workers issues are testing-specific, not production issues

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that Finding 1.1 (boolean binding) is still current behavior and not fixed in recent versions.

**For code-example-validator**: Validate code examples in findings 1.1, 1.4, 2.2 before adding to skill.

---

**Research Completed**: 2026-01-20 14:40
**Next Research Due**: After next major Durable Objects release or every 6 months (July 2026)
