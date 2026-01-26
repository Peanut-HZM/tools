# Community Knowledge Research: Cloudflare Workflows

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-workflows/SKILL.md
**Packages Researched**: cloudflare:workers (Workflows API), wrangler@4.58.0, @cloudflare/workers-types@4.20260109.0
**Official Repo**: cloudflare/workers-sdk
**Time Window**: January 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 11 |
| TIER 1 (Official) | 6 |
| TIER 2 (High-Quality Community) | 1 |
| TIER 3 (Community Consensus) | 1 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 5 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: waitForEvent Skips Events After Timeout in Local Development

**Trust Score**: TIER 1 - Official (Maintainer Confirmed)
**Source**: [GitHub Issue #11740](https://github.com/cloudflare/workers-sdk/issues/11740)
**Date**: 2025-12-22
**Verified**: Yes (Maintainer comment confirms bug)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `waitForEvent()` in local development (`wrangler dev`), if a `waitForEvent()` call times out, subsequent `waitForEvent()` calls in the same workflow instance cannot receive events. The events are sent but never captured. **This bug only occurs in local development, not production.**

This was fixed in production on May 13, 2025 (per Discord discussion), but the fix was **not ported to miniflare/wrangler dev**.

**Reproduction**:
```typescript
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    // Loop through 3 iterations
    for (let i = 0; i < 3; i++) {
      try {
        const evt = await step.waitForEvent(`wait-${i}`, {
          type: 'user-action',
          timeout: '5 seconds'
        });
        console.log(`Iteration ${i}: Received event`);
      } catch {
        console.log(`Iteration ${i}: Timeout`);
      }
    }
  }
}
// In wrangler dev:
// - Iteration 1: ✅ receives event
// - Iteration 2: ⏱️ times out (expected)
// - Iteration 3: ❌ does not receive event (BUG - event is sent but ignored)
```

**Solution/Workaround**:
No workaround available. **Must test waitForEvent with timeouts in production environment** until fix is ported to miniflare.

**Official Status**:
- [ ] Fixed in miniflare
- [x] Fixed in production only (May 13, 2025)
- [x] Known issue, no workaround
- [ ] Won't fix

**Additional Notes**:
Maintainer @pombosilva confirmed fixing this after the report. Also revealed: **Nesting steps is NOT advised** (e.g., calling `step.waitForEvent()` inside `step.do()` is discouraged). Documentation on bad behaviors coming shortly.

---

### Finding 1.2: getPlatformProxy() Fails With Workflow Bindings

**Trust Score**: TIER 1 - Official (Maintainer Confirmed)
**Source**: [GitHub Issue #9402](https://github.com/cloudflare/workers-sdk/issues/9402)
**Date**: 2025-05-29
**Verified**: Yes (Maintainer assigned)
**Impact**: HIGH (Blocks Next.js integration, local testing)
**Already in Skill**: No

**Description**:
Using `getPlatformProxy()` from `wrangler` package fails when workflows are defined in `wrangler.jsonc`. The error states that the workflow binding refers to a service with a named entrypoint, but the service has no such entrypoint.

This blocks:
- Next.js apps using `opennextjs-cloudflare`
- Any local script using `getPlatformProxy()` for bindings
- CI/CD pipelines that rely on proxy access

**Error Message**:
```
Worker "workflows:workflows-starter-dev"'s binding "USER_WORKFLOW" refers to service
"core:user:[PROJECT_NAME]" with a named entrypoint "MyWorkflow", but
"core:user:[PROJECT_NAME]" has no such named entrypoint.

MiniflareCoreError [ERR_RUNTIME_FAILURE]: The Workers runtime failed to start.
```

**Workaround**:
1. **Temporary**: Comment out workflows from `wrangler.jsonc` when using `getPlatformProxy()`
2. **Alternative**: Create a minimal `wrangler.cli.jsonc` without workflow bindings for CLI scripts
3. **Long-term**: Awaiting maintainer fix (similar to Durable Objects warning pattern)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
Maintainer @petebacondarwin assigned, planning to filter out all Workflow bindings in `getPlatformProxy()` similar to how Durable Objects are handled (show warning, don't crash). Fix was delayed due to complexity.

---

### Finding 1.3: Workflows Fail to Execute After Redirect in Local Dev

**Trust Score**: TIER 1 - Official (Maintainer Confirmed + Fixed)
**Source**: [GitHub Issue #10806](https://github.com/cloudflare/workers-sdk/issues/10806)
**Date**: 2025-09-29
**Verified**: Yes (Fix merged)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When a Worker creates a workflow instance and immediately returns a redirect response, the workflow ID is generated but the instance never actually executes in local development. The instance shows as `not_found` when queried. **Works fine in production.**

Root cause: The redirect causes the current request to "soft abort" execution of the Workflow before it completes initialization. This happens because `wrangler dev` uses a single thread, whereas production handles async workflow creation differently.

**Reproduction**:
```typescript
// FAILS in wrangler dev - workflow ID returned but instance never created
export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const workflow = await env.WORKFLOW.create({ params: { userId: '123' } });
    console.log('Created workflow:', workflow.id);

    return Response.redirect('/dashboard', 302);
    // Later: await env.WORKFLOW.get(workflow.id) throws "instance.not_found"
  }
};
```

**Solution/Workaround**:
Add `ctx.waitUntil(workflow.status())` before the redirect to ensure initialization completes:

```typescript
export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const workflow = await env.WORKFLOW.create({ params: { userId: '123' } });

    // ✅ Ensure workflow initialization completes
    ctx.waitUntil(workflow.status());

    return Response.redirect('/dashboard', 302);
  }
};
```

**Official Status**:
- [x] Fixed by @pombosilva (merged)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Impact Timeline**:
Bug existed for months (per reporter) before fix was merged. Affects any workflow creation followed by immediate redirect.

---

### Finding 1.4: NonRetryableError Behaves Differently in Dev vs Production

**Trust Score**: TIER 1 - Official (Confirmed Bug)
**Source**: [GitHub Issue #10113](https://github.com/cloudflare/workers-sdk/issues/10113)
**Date**: 2025-07-29
**Verified**: Yes (Maintainer confirmed)
**Impact**: MEDIUM
**Already in Skill**: YES (Partially - needs expansion)

**Description**:
Throwing `new NonRetryableError('')` with an empty message causes retries in `wrangler dev`, but works correctly in production (exits without retry). When a non-empty message is provided, behavior is consistent across environments.

**Reproduction**:
```typescript
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    await step.do('validate', async () => {
      // ❌ Retries in dev, exits in prod
      throw new NonRetryableError('');

      // ✅ Exits in both environments
      // throw new NonRetryableError('Validation failed');
    });
  }
}
```

**Solution/Workaround**:
**Always provide a message to NonRetryableError** (as already documented in skill).

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (workaround known)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
Already documented in skill at line 498-507, but could emphasize this is a dev mode specific bug, not just best practice.

---

### Finding 1.5: Vitest Pool Workers Unreliable in CI

**Trust Score**: TIER 1 - Official (Tracked)
**Source**: [GitHub Issue #10600](https://github.com/cloudflare/workers-sdk/issues/10600)
**Date**: 2025-09-10
**Verified**: Yes (Internal tracking)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
`@cloudflare/vitest-pool-workers` does not run tests against workflows reliably in CI environments (GitLab, GitHub Actions). Tests pass locally but timeout or fail in CI with cryptic errors.

This appears to be a resource constraint issue in CI containers, not workflow-specific, but affects workflow testing more than other worker types.

**Error Message**:
```
Error: [vitest-worker]: Timeout calling "resolveId" with
"["/builds/xxx/cf-workers/packages/xxx/tests/workflow/index.ts",null,"ssr"]"
```

**Workaround**:
1. Increase `testTimeout` in vitest config (e.g., `testTimeout: 60_000`)
2. Check CI resource constraints (CPU/memory)
3. Use `isolatedStorage: false` if not testing storage isolation
4. Consider running workflow tests against deployed instances instead of vitest

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, investigating (Internal: WOR-945)
- [ ] Won't fix

**Additional Notes**:
Affects Durable Objects as well, suggesting underlying vitest-pool-workers issue rather than workflow-specific bug.

---

### Finding 1.6: Instance restart() and terminate() Not Implemented in Local Dev

**Trust Score**: TIER 1 - Official (Confirmed)
**Source**: [GitHub Issue #11312](https://github.com/cloudflare/workers-sdk/issues/11312)
**Date**: 2025-11-17
**Verified**: Yes
**Impact**: LOW (Development convenience only)
**Already in Skill**: No

**Description**:
Calling `instance.restart()` or `instance.terminate()` in local development (`wrangler dev`) throws `Error: Not implemented yet`. These methods work in production.

Additionally, instance status shows `running` even when workflow is sleeping, making local debugging harder.

**Reproduction**:
```typescript
const instance = await env.MY_WORKFLOW.get(instanceId);

// ❌ Fails in wrangler dev
await instance.restart();  // Error: Not implemented yet
await instance.terminate(); // Error: Not implemented yet

// Status also incorrect during sleep
console.log(await instance.status()); // Shows "running" even during step.sleep()
```

**Workaround**:
Test instance lifecycle management (pause/resume/terminate) in production or staging environment until local dev support is added.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented in local dev limitations
- [x] Known limitation
- [ ] Won't fix

**Recommendation**:
Add to skill's "Troubleshooting" or "Local Development" section noting that instance management APIs are production-only for now.

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: State Persistence Rules Not Obvious (Official Docs)

**Trust Score**: TIER 2 - High-Quality (Official Docs but Edge Case)
**Source**: [Cloudflare Workflows Rules](https://developers.cloudflare.com/workflows/build/rules-of-workflows/)
**Date**: Accessed 2026-01-20
**Verified**: Official documentation
**Impact**: HIGH (Common mistake)
**Already in Skill**: Partially (serialization covered, but not hibernation details)

**Description**:
The official "Rules of Workflows" documentation reveals several non-obvious edge cases that could cause state loss or unexpected behavior:

1. **In-memory state loss on hibernation**: Workflows may hibernate and lose all in-memory state when the engine detects no pending work. Variables declared outside `step.do()` won't persist even if previous steps succeeded.

2. **Non-deterministic step names break caching**: Using `Date.now()`, `Math.random()`, or other non-deterministic values in step names causes steps to re-run unnecessarily because step names act as cache keys.

3. **Promise.race/any outside steps causes inconsistency**: Wrapping `Promise.race()` or `Promise.any()` outside a `step.do()` causes unpredictable caching—the first-to-resolve promise may not match the cached result on restart.

4. **Side effects repeat on restart**: Code outside steps (logging, instance creation) executes multiple times if the engine restarts mid-workflow.

5. **Event mutation doesn't persist**: Changes to the incoming `event` object aren't preserved across steps or restarts.

6. **Non-idempotent operations can repeat**: Steps retry individually, meaning API calls that modify state (charges, database writes) could execute multiple times if the destination service commits but crashes before responding.

**Code Examples**:
```typescript
// ❌ BAD - In-memory state lost on hibernation
let counter = 0;
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    await step.do('increment', async () => {
      counter++; // ❌ Lost on hibernation
    });
    await step.sleep('wait', '1 hour'); // Hibernates here
    console.log(counter); // ❌ Will be 0, not 1!
  }
}

// ✅ GOOD - State from steps persists
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    const counter = await step.do('get counter', async () => {
      return 1;
    });
    await step.sleep('wait', '1 hour');
    console.log(counter); // ✅ Still 1
  }
}

// ❌ BAD - Non-deterministic step name
await step.do(`process-${Date.now()}`, async () => { /* work */ });
// Cache key changes every run → step always re-executes

// ✅ GOOD - Deterministic step name
await step.do('process', async () => { /* work */ });

// ❌ BAD - Non-idempotent operation without check
await step.do('charge customer', async () => {
  await stripe.charges.create({ amount: 1000, customer: customerId });
  // If this succeeds but step times out before returning,
  // retry will charge customer AGAIN!
});

// ✅ GOOD - Check before non-idempotent operation
await step.do('charge customer', async () => {
  const existing = await stripe.charges.list({ customer: customerId });
  if (existing.data.length > 0) return existing.data[0];
  return await stripe.charges.create({ amount: 1000, customer: customerId });
});
```

**Community Validation**:
Official Cloudflare documentation, comprehensive coverage of edge cases.

**Recommendation**:
Add "State Persistence & Caching Rules" section to skill with these gotchas. Current skill covers serialization but not hibernation/restart behavior.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Step Nesting Discouraged (Maintainer Comment)

**Trust Score**: TIER 3 - Community (Maintainer comment, not yet documented)
**Source**: [GitHub Issue #11740 Comment](https://github.com/cloudflare/workers-sdk/issues/11740)
**Date**: 2025-12-22
**Verified**: Maintainer statement only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Maintainer @pombosilva stated: "We don't advise nesting steps (and there should be documentation regarding these bad behaviors coming out shortly)."

"Nesting steps" means calling `step.do()`, `step.sleep()`, or `step.waitForEvent()` inside another `step.do()` callback.

**Example**:
```typescript
// ❌ Discouraged - nesting waitForEvent inside step.do
await step.do('wait for approval', async () => {
  const event = await step.waitForEvent('approval', { type: 'approved' });
  return event;
});

// ✅ Recommended - call step methods at top level
const event = await step.waitForEvent('approval', { type: 'approved' });
await step.do('process approval', async () => {
  // Use event data
  return processApproval(event);
});
```

**Consensus Evidence**:
- Maintainer statement in issue comment
- Official documentation "coming out shortly" (as of Dec 2025)
- No conflicting information found

**Recommendation**:
Monitor for official documentation on step nesting. Once published, add to skill as official guidance.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| I/O must be inside step.do() | Troubleshooting (line 468-489) | Fully covered with examples |
| NonRetryableError requires message | Troubleshooting (line 492-507) | Covered, but could add dev mode note |
| Serialization limits | State Persistence (line 334-365) | Fully covered |
| Step retry configuration | WorkflowStepConfig (line 188-220) | Comprehensive |
| waitForEvent timeout handling | step.waitForEvent (line 176-184) | Example provided |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 waitForEvent timeout skip | Known Issues Prevention | Add as Issue #13 |
| 1.2 getPlatformProxy() failure | Known Issues Prevention | Add as Issue #14 |
| 1.3 Redirect causes instance loss | Known Issues Prevention | Add as Issue #15 (with ctx.waitUntil workaround) |
| 1.5 Vitest CI unreliability | Testing section | Add note about CI resource constraints |
| 1.6 restart()/terminate() not in dev | Local Development section | Add to limitations |

### Priority 2: Expand Existing (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.4 NonRetryableError dev bug | Troubleshooting | Add note that this is dev-specific bug |
| 2.1 State persistence rules | Add new section | "State Persistence & Caching Rules" with hibernation gotchas |

### Priority 3: Monitor (TIER 3, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 Step nesting discouraged | Awaiting official docs | Check Cloudflare docs monthly for publication |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "workflows" in workers-sdk (2025+) | 22 | 6 |
| "workflows edge case OR gotcha" | 0 | 0 |
| "workflows workaround" | 0 | 0 |
| Recent workflow issues reviewed | 30 | 8 |
| Issue deep dives | 6 | 6 |

**Key Issues Reviewed**:
- #11740: waitForEvent timeout skip (HIGH IMPACT)
- #10600: Vitest CI unreliability (MEDIUM)
- #9402: getPlatformProxy() failure (HIGH IMPACT)
- #10806: Redirect causes instance loss (FIXED)
- #11312: restart()/terminate() not implemented (LOW)
- #10113: NonRetryableError dev bug (ALREADY IN SKILL)

### Cloudflare Official Docs

| Source | Notes |
|--------|-------|
| [Rules of Workflows](https://developers.cloudflare.com/workflows/build/rules-of-workflows/) | Comprehensive edge cases (TIER 2) |
| [Jan 15, 2025 Changelog](https://developers.cloudflare.com/changelog/2025-01-15-workflows-more-steps/) | Queueing improvements |
| [April 7, 2025 GA Changelog](https://developers.cloudflare.com/changelog/2025-04-07-workflows-ga/) | waitForEvent release, CPU limits |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare workflows" 2025 | 0 | N/A |
| "cloudflare workflows edge case" | 0 | N/A |

**Note**: Cloudflare Workflows is relatively new (GA April 2025), limited Stack Overflow discussion.

### Community Forums

Community forum link (Cloudflare Community #807343) returned 403 error, unable to access content.

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `WebSearch` for Stack Overflow and community forums
- `WebFetch` for official documentation

**Limitations**:
- Community forum content inaccessible (403 errors)
- Stack Overflow has minimal Workflows content (new feature)
- Focus shifted to GitHub issues as primary source (high quality)
- Some local dev issues may not be reported (developers assume it's expected)

**Time Spent**: ~25 minutes

**Search Strategy**:
Started with broad searches, narrowed to specific areas (waitForEvent, serialization, local dev). GitHub issues proved most valuable due to maintainer engagement and reproduction cases.

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify Finding 2.1 state persistence rules against current official documentation to ensure no changes since last access.

**For code-example-validator**: Validate code examples in findings 1.1, 1.3, 2.1 for syntax correctness before adding to skill.

**For skill-findings-applier**: Prioritize findings 1.1, 1.2, 1.3 (high impact, production blockers for some users). Add comprehensive "State Persistence & Caching Rules" section from finding 2.1.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Issue #13: waitForEvent Skips Events After Timeout (Local Dev Only)

```markdown
### Issue #13: waitForEvent Skips Events After Timeout in Local Dev

**Error**: Events sent after a `waitForEvent()` timeout are ignored in subsequent `waitForEvent()` calls
**Environment**: Local development (`wrangler dev`) only - works correctly in production
**Source**: [GitHub Issue #11740](https://github.com/cloudflare/workers-sdk/issues/11740)

**Why It Happens**: Bug in miniflare that was fixed in production (May 2025) but not ported to local emulator. After a timeout, the event queue becomes corrupted for that instance.

**Workaround**:
- **Test waitForEvent timeout scenarios in production/staging**, not local dev
- Avoid chaining multiple `waitForEvent()` calls where timeouts are expected

**Status**: Known bug, fix pending for miniflare.
```

#### Issue #14: getPlatformProxy() Fails With Workflow Bindings

```markdown
### Issue #14: getPlatformProxy() Fails With Workflow Bindings

**Error**: `MiniflareCoreError [ERR_RUNTIME_FAILURE]: The Workers runtime failed to start`
**Message**: Worker's binding refers to service with named entrypoint, but service has no such entrypoint
**Source**: [GitHub Issue #9402](https://github.com/cloudflare/workers-sdk/issues/9402)

**Why It Happens**: `getPlatformProxy()` from `wrangler` package doesn't support Workflow bindings (similar to how it handles Durable Objects).

**Prevention**:
- **Option 1**: Comment out workflow bindings when using `getPlatformProxy()`
- **Option 2**: Create separate `wrangler.cli.jsonc` without workflows for CLI scripts
- **Option 3**: Access workflow bindings directly via deployed worker, not proxy

```typescript
// Workaround: Separate config for CLI scripts
// wrangler.cli.jsonc (no workflows)
{
  "name": "my-worker",
  "main": "src/index.ts",
  "compatibility_date": "2025-01-20"
  // workflows commented out
}

// Use in script:
import { getPlatformProxy } from 'wrangler';
const { env } = await getPlatformProxy({ configPath: './wrangler.cli.jsonc' });
```

**Status**: Known limitation, fix planned (filter workflows similar to DOs).
```

#### Issue #15: Workflow Fails to Execute After Immediate Redirect (Local Dev)

```markdown
### Issue #15: Workflow Instance Lost After Immediate Redirect (Local Dev Only)

**Error**: Instance ID returned but `instance.not_found` when queried
**Environment**: Local development (`wrangler dev`) only - works correctly in production
**Source**: [GitHub Issue #10806](https://github.com/cloudflare/workers-sdk/issues/10806)

**Why It Happens**: Returning a redirect immediately after `workflow.create()` causes request to "soft abort" before workflow initialization completes (single-threaded execution in dev).

**Prevention**: Use `ctx.waitUntil()` to ensure workflow initialization completes before redirect:

```typescript
export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const workflow = await env.MY_WORKFLOW.create({ params: { userId: '123' } });

    // ✅ Ensure workflow initialization completes
    ctx.waitUntil(workflow.status());

    return Response.redirect('/dashboard', 302);
  }
};
```

**Status**: Fixed in recent wrangler versions (post-Sept 2025), but workaround still recommended for compatibility.
```

### New Section: State Persistence & Caching Rules

```markdown
## State Persistence & Caching Rules

**CRITICAL**: Understanding when state persists vs when it's lost is essential for reliable workflows.

### Rule 1: Workflows Hibernate and Lose In-Memory State

Workflows may hibernate when the engine detects no pending work (e.g., during `step.sleep()`). **All in-memory state is lost during hibernation**.

```typescript
// ❌ BAD - In-memory variable lost on hibernation
let counter = 0;
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    counter = await step.do('increment', async () => counter + 1);
    await step.sleep('wait', '1 hour'); // ← Hibernates here, in-memory state lost
    console.log(counter); // ❌ Will be 0, not 1!
  }
}

// ✅ GOOD - State from step.do() return values persists
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    const counter = await step.do('increment', async () => 1);
    await step.sleep('wait', '1 hour');
    console.log(counter); // ✅ Still 1
  }
}
```

**Rule**: Only state returned from `step.do()` persists across hibernation/restart. Everything else is ephemeral.

---

### Rule 2: Step Names Are Cache Keys - Must Be Deterministic

Step names act as cache keys. Non-deterministic names (using `Date.now()`, `Math.random()`) cause steps to re-run unnecessarily.

```typescript
// ❌ BAD - Non-deterministic step name
await step.do(`fetch-data-${Date.now()}`, async () => {
  return await fetchExpensiveData();
});
// Every execution creates new cache key → step always re-runs

// ✅ GOOD - Deterministic step name
await step.do('fetch-data', async () => {
  return await fetchExpensiveData();
});
// Same cache key → result reused on restart/retry
```

**Rule**: Use static, deterministic step names. If you need unique identifiers, pass them as parameters to the callback, not in the name.

---

### Rule 3: Promise.race/any Must Be Inside step.do()

Wrapping `Promise.race()` or `Promise.any()` outside `step.do()` causes unpredictable caching—the first-to-resolve promise may differ on restart.

```typescript
// ❌ BAD - Race outside step
const fastest = await Promise.race([fetchA(), fetchB()]);
await step.do('use result', async () => fastest);
// On restart: race runs again, different promise might win

// ✅ GOOD - Race inside step
const fastest = await step.do('fetch fastest', async () => {
  return await Promise.race([fetchA(), fetchB()]);
});
// On restart: cached result used, consistent behavior
```

**Rule**: Keep all non-deterministic logic (races, random, time-based) inside `step.do()` callbacks.

---

### Rule 4: Side Effects Repeat on Restart

Code outside `step.do()` executes multiple times if the workflow restarts mid-execution.

```typescript
// ❌ BAD - Side effect outside step
console.log('Workflow started'); // ← Logs multiple times on restart
await step.do('work', async () => { /* work */ });

// ✅ GOOD - Side effects inside step
await step.do('log start', async () => {
  console.log('Workflow started'); // ← Logs once (cached)
});
```

**Rule**: Put logging, metrics, and other side effects inside `step.do()` to avoid duplication.

---

### Rule 5: Event Object Is Immutable

Changes to the incoming `event` object aren't preserved across steps or restarts.

```typescript
// ❌ BAD - Mutating event
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    event.payload.status = 'processing'; // ❌ Not persisted
    await step.sleep('wait', '1 hour');
    console.log(event.payload.status); // ❌ Original value restored
  }
}

// ✅ GOOD - Store state in step.do() return values
export class MyWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    const status = await step.do('set status', async () => 'processing');
    await step.sleep('wait', '1 hour');
    console.log(status); // ✅ Still 'processing'
  }
}
```

**Rule**: Treat `event` as read-only. Store derived state in `step.do()` return values.

---

### Rule 6: Guard Non-Idempotent Operations

Steps retry individually. If an API call succeeds but the step times out before returning, the retry will call the API again.

```typescript
// ❌ BAD - Charge customer without check
await step.do('charge', async () => {
  return await stripe.charges.create({ amount: 1000, customer: customerId });
});
// If step times out after charge succeeds, retry charges AGAIN!

// ✅ GOOD - Check for existing charge first
await step.do('charge', async () => {
  const existing = await stripe.charges.list({ customer: customerId, limit: 1 });
  if (existing.data.length > 0) return existing.data[0]; // Idempotent
  return await stripe.charges.create({ amount: 1000, customer: customerId });
});
```

**Rule**: For non-idempotent operations (payments, database writes), check if operation already succeeded before executing.

---

**Source**: [Cloudflare Workflows Rules](https://developers.cloudflare.com/workflows/build/rules-of-workflows/)
```

### Update to Vitest Testing Section

Add after line 560 (after test modifiers list):

```markdown
### Known Issue: CI Reliability

**Vitest tests may be unreliable in CI environments** (GitLab, GitHub Actions) due to resource constraints. Tests pass locally but timeout in CI.

**Symptoms**:
- Timeout errors: `[vitest-worker]: Timeout calling "resolveId"`
- Tests work locally but fail in CI
- Inconsistent failures across runs

**Workarounds**:
1. Increase `testTimeout` in vitest config:
   ```typescript
   export default defineWorkersConfig({
     test: {
       testTimeout: 60_000 // Default: 5000ms
     }
   });
   ```
2. Check CI resource limits (CPU/memory)
3. Use `isolatedStorage: false` if not testing storage isolation
4. Consider testing against deployed instances instead of vitest for critical workflows

**Source**: [GitHub Issue #10600](https://github.com/cloudflare/workers-sdk/issues/10600)
```

### Update to Local Development Section

Add new section after Testing:

```markdown
## Local Development Limitations

Some Workflow features are not yet implemented in `wrangler dev` (miniflare):

### Instance Management APIs

```typescript
const instance = await env.MY_WORKFLOW.get(instanceId);

// ❌ Not implemented in wrangler dev
await instance.restart();    // Error: Not implemented yet
await instance.terminate();  // Error: Not implemented yet

// ✅ Works in production
```

**Workaround**: Test instance lifecycle management in production or staging environment.

### Instance Status During Sleep

Instance status shows `running` even when workflow is sleeping (`step.sleep()`, `step.sleepUntil()`), making debugging harder.

**Workaround**: Use step names and logs to track workflow state in dev.

**Source**: [GitHub Issue #11312](https://github.com/cloudflare/workers-sdk/issues/11312)
```

---

## Research Completed: 2026-01-20 15:45
**Next Research Due**: After next major Workflows release (check quarterly)

**Key Monitoring Targets**:
- GitHub milestones for Workflows
- Cloudflare changelog for workflow updates
- Step nesting documentation (Finding 3.1)
- getPlatformProxy() fix (Finding 1.2)
