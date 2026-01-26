# Community Knowledge Research: Cloudflare Queues

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-queues/SKILL.md
**Packages Researched**: wrangler@4.58.0, @cloudflare/workers-types@4.20260109.0
**Official Repo**: cloudflare/workers-sdk
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 3 |
| Recommended to Add | 10 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Multiple Dev Commands - Queues Broken in Local Multi-Worker Setup

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #9795](https://github.com/cloudflare/workers-sdk/issues/9795)
**Date**: 2025-06-30
**Verified**: Yes (Open issue, maintainer response)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When running producer and consumer workers as separate `wrangler dev` processes, queue messages do not flow between them. The virtual queue used by wrangler is in-process/memory, making it impossible to share across separate worker processes.

**Reproduction**:
```bash
# Terminal 1 - Producer
cd producer && wrangler dev

# Terminal 2 - Consumer
cd consumer && wrangler dev

# Producer sends messages successfully, but consumer never receives them
```

**Solution/Workaround**:
```bash
# Option 1: Run both in single dev command
wrangler dev -c producer/wrangler.jsonc -c consumer/wrangler.jsonc

# Option 2: Use vite plugin with auxiliaryWorkers
# In vite.config.ts:
export default defineConfig({
  plugins: [
    cloudflare({
      auxiliaryWorkers: [
        './consumer/wrangler.jsonc'
      ]
    })
  ]
})
```

**Official Status**:
- [x] Known issue, workaround required
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: Maintainer @CarmenPopoviciu confirmed limitation
- Related to: Official docs mention single-instance requirement
- Impact: Multiple users affected, including Vite users (cannot use multi-dev with queues)

---

### Finding 1.2: Queue Producer Binding Causes 500 Errors with `wrangler dev --remote`

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #9642](https://github.com/cloudflare/workers-sdk/issues/9642)
**Date**: 2025-06-18
**Verified**: Yes (Maintainer acknowledged)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When queue producer bindings are configured, ALL routes return 500 Internal Server Error when using `wrangler dev --remote`, even routes that don't use the queue binding. No error details provided even with `--log-level=debug`.

**Reproduction**:
```jsonc
// wrangler.jsonc
{
  "queues": {
    "producers": [{
      "queue": "my-queue",
      "binding": "MY_QUEUE"
    }]
  }
}
```

```bash
wrangler dev --remote
# All routes return 500, even those not using MY_QUEUE
```

**Solution/Workaround**:
Comment out queue producer configuration when using `--remote`:
```jsonc
{
  "queues": {
    // Temporarily disable for remote dev
    // "producers": [{ "queue": "my-queue", "binding": "MY_QUEUE" }]
  }
}
```

**Official Status**:
- [x] Known issue, workaround required
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (warning shown: "Queues are not yet supported in wrangler dev remote mode")
- [ ] Won't fix

**Cross-Reference**:
- Maintainer @penalosa: "This is because Queues do not support `wrangler dev --remote`. However, we should make this a warning rather than a hard error"
- Affects: All routes, not just queue-using routes

---

### Finding 1.3: Queue Name Not Exposed on Producer Bindings

**Trust Score**: TIER 1 - Official Feature Request
**Source**: [GitHub Issue #10131](https://github.com/cloudflare/workers-sdk/issues/10131)
**Date**: 2025-07-30
**Verified**: Yes (Tracked internally MQ-923)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Queue names are only available via `batch.queue` in consumer handlers, not on producer bindings. This creates maintenance issues with dynamic/environment-specific queue names (e.g., `email-queue-staging`, `email-queue-pr-123`) because developers must hardcode queue names or implement complex normalization logic.

**Current Problematic Code**:
```typescript
// ❌ Hardcoded queue names - breaks with dynamic environments
switch (batch.queue) {
  case 'email-queue': // What about email-queue-staging?
  case 'stripe-queue': // What about stripe-queue-pr-123?
}

// ❌ Complex normalization required
function normalizeQueueName(queueName: string): string {
  if (queueName.startsWith('email-queue')) return 'email-queue'
  return queueName
}
```

**Desired Solution**:
```typescript
// ✅ Clean, environment-agnostic
switch (batch.queue) {
  case env.EMAIL_QUEUE.name: // Resolves to actual queue name
  case env.STRIPE_QUEUE.name:
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix
- **Internal Tracking**: [MQ-923](https://jira.cfdata.org/browse/MQ-923)

**Cross-Reference**:
- Use Cases: Multi-environment deployments, PR previews, tenant-specific queues
- Workaround: Maintain separate normalization logic or hardcode names

---

### Finding 1.4: D1 Remote Breaks if Queue Remote is Set

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #11106](https://github.com/cloudflare/workers-sdk/issues/11106)
**Date**: 2025-10-27
**Verified**: Yes (Open issue)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When `remote: true` is set on a queue producer binding, D1 remote bindings stop working. This is a binding conflict issue affecting mixed local/remote development.

**Reproduction**:
```jsonc
{
  "d1_databases": [{
    "binding": "WEB_DB",
    "database_name": "my-db",
    "database_id": "...",
    "remote": true
  }],
  "queues": {
    "producers": [{
      "binding": "MY_QUEUE",
      "queue": "my-queue",
      "remote": true  // ← This breaks D1 remote
    }]
  }
}
```

**Solution/Workaround**:
None provided yet. Issue remains open.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, no workaround
- [ ] Won't fix

**Cross-Reference**:
- Affects: Mixed local/remote bindings (D1 + Queues)
- Related: Issue #9887 (queue consumers with remote bindings)

---

### Finding 1.5: `delivery_delay` Parameter Should Be Removed from Producer Config (Breaking Change)

**Trust Score**: TIER 1 - Official Breaking Change Issue
**Source**: [GitHub Issue #10286](https://github.com/cloudflare/workers-sdk/issues/10286)
**Date**: 2025-08-08
**Verified**: Yes (Open issue)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The `delivery_delay` parameter in producer bindings is incorrect behavior. Workers should not be able to affect queue-level settings. When multiple producers exist, the setting is determined by the last deployed producer, leading to unpredictable behavior.

**Current Incorrect Pattern**:
```jsonc
{
  "queues": {
    "producers": [{
      "queue": "my-queue",
      "binding": "MY_QUEUE",
      "delivery_delay": 300  // ❌ Should not exist at producer level
    }]
  }
}
```

**Correct Pattern**:
Delay should be specified per-message:
```typescript
await env.MY_QUEUE.send({ data }, { delaySeconds: 300 });
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, breaking change planned
- [ ] Won't fix

**Cross-Reference**:
- Breaking change: Will be removed in future wrangler version
- Migration: Use `delaySeconds` in send options instead

---

### Finding 1.6: Pause & Purge APIs (March 2025 - NEW)

**Trust Score**: TIER 1 - Official Changelog
**Source**: [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-03-25-pause-purge-queues/)
**Date**: 2025-03-25
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (documented in SKILL.md)

**Description**:
New queue management capabilities: pause/resume delivery and purge (delete all messages).

**Features**:
```bash
# Pause delivery (queue continues receiving, stops delivering)
npx wrangler queues pause-delivery my-queue

# Resume delivery
npx wrangler queues resume-delivery my-queue

# Purge all messages (DESTRUCTIVE)
npx wrangler queues purge my-queue
```

**Official Status**:
- [x] Fixed in version X.Y.Z
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill under "Wrangler Commands"
- Use case: Pausing during buggy consumer deployments, purging test messages

---

### Finding 1.7: HTTP Publishing to Queues (May 2025 - NEW)

**Trust Score**: TIER 1 - Official Changelog
**Source**: [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-05-09-publish-to-queues-via-http/)
**Date**: 2025-05-09
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
You can now publish messages to Cloudflare Queues directly via HTTP from any service or programming language. Previously, publishing was only possible from within Cloudflare Workers.

**Authentication**:
Requires Cloudflare API token with `Queues Edit` permissions.

**Impact**:
- Enables non-Worker services to publish to queues
- Opens queues to external microservices, cron jobs, webhooks
- No rate limits mentioned in changelog

**Official Status**:
- [x] Fixed in version X.Y.Z
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Not mentioned in current skill
- Significant feature: expands producer options beyond Workers

---

### Finding 1.8: Event Subscriptions for Queues (August 2025 - NEW)

**Trust Score**: TIER 1 - Official Changelog
**Source**: [Cloudflare Changelog](https://developers.cloudflare.com/changelog/2025-08-19-event-subscriptions/)
**Date**: 2025-08-19
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Subscribe to events from Cloudflare services (R2, Workers KV, Workers AI, Vectorize, etc.) and consume them via Queues. Enables building custom workflows and integrations triggered by account activity.

**Supported Event Sources**:
- R2
- Workers KV
- Workers AI
- Workers Builds
- Vectorize
- Super Slurper
- Workflows

**Configuration**:
```bash
npx wrangler queues subscription create my-queue --source r2 --events bucket.created
```

**Event Structure**:
```typescript
{
  type: 'r2.bucket.created',
  source: 'r2',
  payload: { bucketName: 'my-bucket', location: 'us-east-1' },
  metadata: { accountId: '...', timestamp: '...' }
}
```

**Official Status**:
- [x] Fixed in version X.Y.Z
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Not mentioned in current skill
- Major feature: event-driven architectures without custom webhooks

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Queue Consumer Not Executing with `type = "http_pull"` Configuration

**Trust Score**: TIER 2 - GitHub Issue with Resolution
**Source**: [GitHub Issue #6619](https://github.com/cloudflare/workers-sdk/issues/6619)
**Date**: 2024-09-03
**Verified**: Partial (issue closed, workaround confirmed)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When configuring a queue consumer with `type = "http_pull"` in wrangler.toml, the consumer does not execute. Messages queue successfully but the `queue()` handler is never called in production. The issue was resolved by correcting environment declarations in wrangler.toml.

**Reproduction**:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "offline-sales-queue",
      "retry_delay": 60,
      "type": "http_pull",  // ❌ Misconfiguration
      "max_retries": 3,
      "max_batch_size": 10,
      "max_batch_timeout": 3
    }]
  }
}
```

**Solution/Workaround**:
Remove `type = "http_pull"` for push-based Workers consumers:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "offline-sales-queue",
      "max_retries": 3,
      "max_batch_size": 10,
      "max_batch_timeout": 3
      // No "type" field - defaults to push-based Worker consumer
    }]
  }
}
```

**Community Validation**:
- Reported by multiple users
- Resolution: "environments were declared in a wrong way in wrangler.toml"
- Additional note: `max_batch_timeout` can prevent local consumer execution

**Cross-Reference**:
- HTTP pull consumers are for external HTTP-based consumers, not Worker-based consumers
- Skill mentions pull consumers but doesn't warn about this misconfiguration

---

### Finding 2.2: `max_batch_timeout` Prevents Local Consumer Execution

**Trust Score**: TIER 2 - Community Comment
**Source**: [GitHub Issue #6619 Comment](https://github.com/cloudflare/workers-sdk/issues/6619#issuecomment-2396888227)
**Date**: 2024-10-06
**Verified**: Single user report
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Setting `max_batch_timeout` in consumer configuration can prevent the queue consumer from working in local development (`wrangler dev`).

**Reproduction**:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "my-queue",
      "max_batch_size": 10,
      "max_batch_timeout": 3  // ❌ May break local dev
    }]
  }
}
```

**Solution/Workaround**:
Remove `max_batch_timeout` for local development:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "my-queue",
      "max_batch_size": 10
      // Omit max_batch_timeout in local dev
    }]
  }
}
```

**Community Validation**:
- Single report by @gregory
- Not corroborated by maintainers
- May be version-specific or edge case

**Recommendation**: Add to Community Tips section with verification flag

---

### Finding 2.3: TLS Disconnect Error with `https: true` in Miniflare

**Trust Score**: TIER 2 - GitHub Issue
**Source**: [GitHub Issue #8221](https://github.com/cloudflare/workers-sdk/issues/8221)
**Date**: 2025-02-22
**Verified**: Yes (Open issue)
**Impact**: LOW
**Already in Skill**: No

**Description**:
When using Miniflare with `https: true` and calling the `queue()` method, workerd produces a TLS disconnect error. The error appears unrelated to functionality - queues work correctly despite the error.

**Reproduction**:
```javascript
const mf = new Miniflare({
  scriptPath: './worker.js',
  modules: true,
  https: true,  // ← Triggers TLS error
});

const worker = await mf.getWorker();
await worker.queue('ok', [
  {id: 'a', timestamp: new Date(0), attempts: 1, body: {foo: 1}},
]);

// Error: disconnected: peer disconnected without gracefully ending TLS session
```

**Solution/Workaround**:
Error is cosmetic and can be ignored. Alternatively, use `https: false` for local testing if TLS is not required.

**Community Validation**:
- Single user report
- No maintainer response yet
- Issue remains open

**Recommendation**: Monitor for updates, low priority (cosmetic error)

---

### Finding 2.4: Queue Consumer Bindings Missing with Mixed Local/Remote Bindings

**Trust Score**: TIER 2 - GitHub Issue
**Source**: [GitHub Issue #9887](https://github.com/cloudflare/workers-sdk/issues/9887)
**Date**: 2025-07-08
**Verified**: Yes (Closed with partial resolution)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using mixed local/remote bindings (e.g., remote AI binding + queue consumer), the queue consumer binding does not appear in the worker's available bindings. Messages sent to the queue are never received.

**Reproduction**:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "my-queue-dev",
      "max_batch_size": 1
    }]
  },
  "ai": {
    "binding": "AI",
    "experimental_remote": true  // ← Mixed remote binding
  }
}
```

```bash
wrangler dev --x-remote-bindings
# Queue consumer binding (MY_QUEUE) is missing
# Only AI binding shows as remote
```

**Solution/Workaround**:
Maintainer confirmed: "Queues do work in local development" - but requires all-local or all-remote approach. Mixed bindings not supported.

```bash
# Option 1: All local (no remote AI)
wrangler dev

# Option 2: All remote (queues not supported)
wrangler dev --remote  # ❌ Queues not supported

# Option 3: Use Vite plugin with remoteBindings
# (but queues still require all-local setup)
```

**Community Validation**:
- Multiple users affected
- Maintainer @jamesopstad confirmed limitation
- Related to Finding 1.1 (multi-worker setup)

**Cross-Reference**:
- Affects: Any worker using queues + remote bindings (AI, Vectorize)
- Workaround: Separate workers for queue processing vs AI operations

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Messages Not Moving to Dead Letter Queue After Max Retries

**Trust Score**: TIER 3 - Community Forum
**Source**: [Cloudflare Community](https://community.cloudflare.com/t/messages-not-moving-to-dead-letter-queue-after-max-retries/708750)
**Date**: 2024-09 (approximate)
**Verified**: Forum discussion (blocked, could not retrieve full content)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Messages that reach `max_retries` are not appearing in the configured Dead Letter Queue, even with proper configuration.

**Expected Configuration**:
```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "my-queue",
      "max_retries": 3,
      "dead_letter_queue": "my-dlq"
    }]
  }
}
```

**Consensus Evidence**:
- Community forum discussion (403 error prevented full retrieval)
- Known topic in Cloudflare community

**Recommendation**: Needs verification. Flagged for manual testing or official docs check.

---

### Finding 3.2: Single Queue Consumer Limitation

**Trust Score**: TIER 3 - Web Search Summary
**Source**: Web search results (multiple mentions)
**Date**: 2025
**Verified**: Cross-referenced with docs
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Each queue can only have one consumer Worker connected to it. Attempting to connect multiple consumers to the same queue causes an error when publishing the Worker.

**Solution**:
Use separate queues for different consumers, or implement routing logic within a single consumer.

**Consensus Evidence**:
- Mentioned in web search results
- Consistent with Cloudflare's architecture (single consumer per queue)

**Recommendation**: Verify against official docs and add if confirmed.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Implicit Batch Retry Behavior

**Trust Score**: TIER 4 - Web Search Summary
**Source**: Web search results
**Date**: Unknown
**Verified**: Partial (mentioned in official docs)
**Impact**: HIGH

**Why Flagged**:
- [x] Already documented in skill
- [ ] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
"By default, messages within a batch are treated as all or nothing when determining retries - if the last message in a batch fails to be processed, the entire batch will be retried."

**Recommendation**: Already covered in skill under "Critical Consumer Patterns" - no action needed.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Pause & Purge APIs (1.6) | Wrangler Commands | Fully covered |
| Implicit batch retry | Critical Consumer Patterns | Fully covered |
| Dead letter queue setup | Dead Letter Queue (DLQ) section | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Multi-dev limitation | Known Issues Prevention | Add as Issue #9 with workaround |
| 1.2 Remote dev 500 errors | Known Issues Prevention | Add as Issue #10 with workaround |
| 1.4 D1 remote conflict | Known Issues Prevention | Add as Issue #11 (no workaround yet) |
| 1.7 HTTP Publishing | Producer API | Add new section for HTTP-based publishing |
| 1.8 Event Subscriptions | New Section | Add "Event Subscriptions" section with examples |
| 2.4 Mixed bindings issue | Known Issues Prevention | Add as Issue #12 with workaround |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 Queue name exposure | Feature Request | Document limitation in Producer API section |
| 1.5 delivery_delay deprecation | Breaking Changes | Add warning about upcoming removal |
| 2.1 http_pull misconfiguration | Common Errors | Add to error handling section |
| 2.2 max_batch_timeout local dev | Community Tips | Add with "Community-sourced" flag |

### Priority 3: Monitor (TIER 3-4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 DLQ not working | Could not verify (403 error) | Manual testing or contact Cloudflare support |
| 3.2 Single consumer limit | Needs official docs verification | Check official limits documentation |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "queues" issues in cloudflare/workers-sdk | 30 | 8 |
| "queues" with bug label | 30 | 3 |
| "queues" created >2025-05-01 | 30 | 6 |
| "queues edge case OR gotcha" | 0 | 0 |
| "queues workaround OR breaking change" | 0 | 0 |

### Cloudflare Official

| Source | Notes |
|--------|-------|
| [Cloudflare Queues Changelog](https://developers.cloudflare.com/queues/platform/changelog/) | 3 major features in 2025 |
| [Cloudflare Blog](https://blog.cloudflare.com/) | 2 relevant posts |
| [Official Docs](https://developers.cloudflare.com/queues/) | Primary reference |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare queues" gotcha 2024 2025 | 0 | N/A |
| "cloudflare workers queues" error 2025 2026 | 0 | N/A |

**Note**: Very limited Stack Overflow activity for Cloudflare Queues. Most community discussion happens on GitHub Issues and Cloudflare Community forums.

### Community Forums

| Source | Notes |
|--------|-------|
| [Cloudflare Community](https://community.cloudflare.com/) | 1 relevant thread (DLQ issue), blocked by 403 |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue retrieval
- `WebSearch` for Stack Overflow, blogs, and official docs
- `WebFetch` for changelog and official documentation

**Limitations**:
- Cloudflare Community forum returned 403 Forbidden (could not verify Finding 3.1)
- Very limited Stack Overflow activity for Cloudflare Queues
- Most knowledge concentrated in GitHub Issues and official docs
- No access to internal Cloudflare JIRA (MQ-923 mentioned but not accessible)

**Time Spent**: ~12 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify Finding 1.7 (HTTP Publishing) and 1.8 (Event Subscriptions) against current official documentation
- Cross-reference Finding 3.2 (single consumer limit) with official limits page

**For api-method-checker**:
- Verify that HTTP publishing API is documented
- Check if `env.QUEUE.name` property exists (Finding 1.3)

**For code-example-validator**:
- Validate event subscription examples from Finding 1.8
- Test HTTP publishing examples when adding to skill

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### New Section: HTTP Publishing (Finding 1.7)

Add after "Producer API" section:

```markdown
## HTTP Publishing (External Services)

**New in May 2025**: Publish messages to queues via HTTP from any service.

**Authentication**: Requires Cloudflare API token with `Queues Edit` permissions.

```bash
curl -X POST "https://api.cloudflare.com/client/v4/accounts/{account_id}/queues/{queue_name}/messages" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"body": {"userId": "123", "action": "process-order"}}
    ]
  }'
```

**Use Cases**:
- Publishing from external microservices
- Cron jobs outside Cloudflare
- Webhook receivers
- Legacy systems integration
```

#### New Section: Event Subscriptions (Finding 1.8)

Add new section after "HTTP Publishing":

```markdown
## Event Subscriptions (August 2025)

**New in August 2025**: Subscribe to events from Cloudflare services and consume via Queues.

**Supported Event Sources**:
- R2 (bucket.created, object.uploaded, etc.)
- Workers KV
- Workers AI
- Vectorize
- Workflows

**Create Subscription**:
```bash
npx wrangler queues subscription create my-queue \
  --source r2 \
  --events bucket.created
```

**Event Structure**:
```typescript
interface CloudflareEvent {
  type: string;           // 'r2.bucket.created'
  source: string;         // 'r2'
  payload: any;           // Event-specific data
  metadata: {
    accountId: string;
    timestamp: string;
  };
}
```

**Consumer**:
```typescript
export default {
  async queue(batch: MessageBatch, env: Env): Promise<void> {
    for (const message of batch.messages) {
      const event = message.body as CloudflareEvent;

      switch (event.type) {
        case 'r2.bucket.created':
          console.log('New bucket:', event.payload.bucketName);
          break;
        case 'kv.namespace.created':
          console.log('New KV namespace:', event.payload.namespaceId);
          break;
      }

      message.ack();
    }
  }
};
```
```

#### Known Issues Section Updates

Add to "Known Issues Prevented" table:

```markdown
| Issue | Description | Prevention |
|-------|-------------|------------|
| **Multiple dev commands broken** | Queue messages don't flow between separate `wrangler dev` processes | Run both producer/consumer in single dev command or use Vite auxiliaryWorkers |
| **Remote dev 500 errors** | All routes return 500 with `--remote` when queue bindings exist | Remove queue bindings for remote dev or use local dev |
| **D1 + Queue remote conflict** | D1 remote breaks when queue producer has `remote: true` | Avoid mixing D1 remote with queue remote (no workaround yet) |
| **Mixed local/remote bindings** | Queue consumer missing when mixing local queues with remote AI/Vectorize | Use all-local or separate workers for queue processing |
| **http_pull misconfiguration** | Setting `type: "http_pull"` on Worker consumer prevents execution | Omit `type` field for push-based Worker consumers |
```

#### Breaking Changes Section

Add new section before "Related Documentation":

```markdown
## Breaking Changes & Deprecations

### delivery_delay in Producer Config (Upcoming)

⚠️ **Breaking Change**: The `delivery_delay` parameter in producer bindings will be removed in a future wrangler version.

```jsonc
// ❌ Will be removed
{
  "queues": {
    "producers": [{
      "binding": "MY_QUEUE",
      "delivery_delay": 300  // Don't use this
    }]
  }
}
```

**Migration**: Use per-message delay instead:
```typescript
// ✅ Correct approach
await env.MY_QUEUE.send({ data }, { delaySeconds: 300 });
```

**Why**: Workers should not affect queue-level settings. With multiple producers, last-deployed wins (unpredictable).
```

### Adding to Community Tips Section (TIER 2)

Create new section after "Critical Rules":

```markdown
## Community Tips

> **Note**: These tips come from community discussions and GitHub issues. Verify against your wrangler version.

### Tip: max_batch_timeout May Break Local Development

**Source**: [GitHub Issue #6619](https://github.com/cloudflare/workers-sdk/issues/6619) | **Confidence**: MEDIUM
**Applies to**: Local development with `wrangler dev`

If your queue consumer doesn't execute locally, try removing `max_batch_timeout`:

```jsonc
{
  "queues": {
    "consumers": [{
      "queue": "my-queue",
      "max_batch_size": 10
      // Remove max_batch_timeout for local dev
    }]
  }
}
```

This appears to be version-specific and may not affect all setups.

### Tip: Queue Name Not Available on Producer Bindings

**Source**: [GitHub Issue #10131](https://github.com/cloudflare/workers-sdk/issues/10131) | **Confidence**: HIGH
**Applies to**: Multi-environment deployments

Queue names are only available in `batch.queue` (consumer), not on producer bindings. For environment-specific queues:

```typescript
// Workaround: Hardcode or use normalization
const queueName = batch.queue.replace(/-staging|-pr-\d+/, '');

switch (queueName) {
  case 'email-queue':
    // Handle email
}
```

Feature request tracked internally: [MQ-923](https://jira.cfdata.org/browse/MQ-923)
```

---

## Sources

### Official Cloudflare Sources

- [Durable Objects aren't just durable, they're fast: a 10x speedup for Cloudflare Queues](https://blog.cloudflare.com/how-we-built-cloudflare-queues/)
- [Making Super Slurper 5x faster with Workers, Durable Objects, and Queues](https://blog.cloudflare.com/making-super-slurper-five-times-faster/)
- [Cloudflare Queues Changelog](https://developers.cloudflare.com/queues/platform/changelog/)
- [Increased limits for Queues pull consumers](https://developers.cloudflare.com/changelog/2025-04-17-pull-consumer-limits/)
- [New Pause & Purge APIs for Queues](https://developers.cloudflare.com/changelog/2025-03-25-pause-purge-queues/)
- [Customize queue message retention periods](https://developers.cloudflare.com/changelog/2025-02-14-customize-queue-retention-period/)
- [Publish messages to Queues directly via HTTP](https://developers.cloudflare.com/changelog/2025-05-09-publish-to-queues-via-http/)
- [Subscribe to events from Cloudflare services with Queues](https://developers.cloudflare.com/changelog/2025-08-19-event-subscriptions/)

### GitHub Issues

- [#9795: Queues broken locally with multiple dev commands](https://github.com/cloudflare/workers-sdk/issues/9795)
- [#9642: Queue producer binding causes 500 errors with --remote](https://github.com/cloudflare/workers-sdk/issues/9642)
- [#10131: Expose Queue Name Property on Queue Bindings](https://github.com/cloudflare/workers-sdk/issues/10131)
- [#11106: D1 remote breaks if queue remote is set](https://github.com/cloudflare/workers-sdk/issues/11106)
- [#10286: Remove delivery_delay parameter (Breaking)](https://github.com/cloudflare/workers-sdk/issues/10286)
- [#9887: Queue Consumer Binding Issue in Local Development](https://github.com/cloudflare/workers-sdk/issues/9887)
- [#6619: Queue Consumer Not Executing in Production](https://github.com/cloudflare/workers-sdk/issues/6619)
- [#8221: Using queue in Miniflare with https: true produces TLS error](https://github.com/cloudflare/workers-sdk/issues/8221)

### Community Forums

- [Messages Not Moving to Dead Letter Queue After Max Retries](https://community.cloudflare.com/t/messages-not-moving-to-dead-letter-queue-after-max-retries/708750) (403 error, could not verify)

---

**Research Completed**: 2026-01-20 10:45 AM
**Next Research Due**: After next major Queues release or wrangler 5.0
