# Community Knowledge Research: Cloudflare Agents SDK

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-agents/SKILL.md
**Packages Researched**: agents@0.3.6, @modelcontextprotocol/sdk@latest
**Official Repo**: cloudflare/agents
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 9 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 3 |
| Recommended to Add | 12 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: WebSocket Payload Size Limit (1MB) Causes Connection Failures

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #119](https://github.com/cloudflare/agents/issues/119)
**Date**: 2025-04-XX (exact date from issue)
**Verified**: Yes - Open issue with maintainer acknowledgment
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When tool call responses exceed approximately 1 MB, WebSocket connections fail with "internal error" messages. This occurs because all messages—including large tool results—are streamed back to the client and LLM for continued conversations, causing cumulative payload growth. After 5-6 calls with large responses (e.g., Elasticsearch queries), the payload exceeds 1 MB and crashes.

**Error Messages**:
```
Error: internal error; reference = [reference ID]
Override onError(connection, error) to handle websocket connection errors
```

**Reproduction**:
```typescript
// Agent with tool that returns large data
export class SearchAgent extends AIChatAgent<Env> {
  tools = {
    searchDatabase: tool({
      // Returns ~200KB per call
      execute: async () => {
        const results = await elasticsearchQuery(); // Large dataset
        return JSON.stringify(results); // 200KB+ response
      }
    })
  };
}

// After 5-6 calls, cumulative payload > 1MB → connection crashes
```

**Workaround**:
```typescript
// Client-side: Prune message history to stay under 950KB
function pruneMessages(messages: Message[]): Message[] {
  let totalSize = 0;
  const pruned = [];

  // Keep recent messages until we hit size limit
  for (let i = messages.length - 1; i >= 0; i--) {
    const msgSize = JSON.stringify(messages[i]).length;
    if (totalSize + msgSize > 950_000) break; // 950KB limit
    pruned.unshift(messages[i]);
    totalSize += msgSize;
  }

  return pruned;
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to WebSockets API section in skill
- Not currently documented in Known Issues

---

### Finding 1.2: Duplicate Assistant Messages with `needsApproval` Tools

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #790](https://github.com/cloudflare/agents/issues/790)
**Date**: 2026-01-20
**Verified**: Yes - Open issue
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `needsApproval: true` on tools, the system creates duplicate assistant messages instead of updating the original one. Two separate messages persist with identical `toolCallId`:

1. **Server-generated message**: ID format `assistant_1768917665170_4mub00d32`, state `"input-available"`
2. **Client-generated message**: ID `oFwQwEpvLd8f1Gwd`, state `"approval-responded"` with approval data

The original message never transitions from `input-available` to `approval-responded` state.

**Reproduction**:
```typescript
// Define tool with needsApproval
export class MyAgent extends AIChatAgent<Env> {
  tools = {
    sensitiveAction: tool({
      needsApproval: true,
      execute: async (args) => {
        return { result: "action completed" };
      }
    })
  };
}

// User approves via client
await addToolApprovalResponse(toolCallId, approval);

// Result: Two messages with same toolCallId, original stuck in "input-available"
```

**Expected Behavior**:
The original message should be updated to `approval-responded` state, not create a duplicate.

**Environment**:
- `@cloudflare/ai-chat`: 0.0.3
- `agents`: 0.3.3
- `ai`: 6.0.12

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.3: WorkerTransport ClientCapabilities Lost After Hibernation

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #777](https://github.com/cloudflare/agents/issues/777) + [PR #783](https://github.com/cloudflare/agents/pull/783)
**Date**: 2026-01-13 (closed)
**Verified**: Yes - Fixed in agents@0.3.5+
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `WorkerTransport` with MCP servers in serverless environments (Cloudflare Workers), client capabilities fail to persist across Durable Object hibernation cycles, breaking form elicitation features.

**Root Cause**:
The `TransportState` interface only stored `sessionId` and `initialized` status. The `_clientCapabilities` property was set during initial handshake on the `Server` instance but not persisted to storage. When a new serverless function instance handled subsequent requests (like tool calls triggering elicitation), capabilities were unavailable.

**Error**:
```
Error: Client does not support form elicitation at Server.elicitInput
```

**Reproduction**:
```typescript
// MCP server with elicitation
const server = new McpServer({ name: "MyMCP" });

server.tool("getData", "Fetch data", {
  // Tool that triggers elicitation
}, async (args) => {
  // During tool execution, if DO hibernated:
  await server.elicitInput({ /* form */ }); // ❌ Error: capabilities lost
});

// Client advertised elicitation capability during handshake,
// but after hibernation, capability info is gone
```

**Solution** (Fixed in agents@0.3.5):
```typescript
// TransportState now includes clientCapabilities
interface TransportState {
  sessionId: string;
  initialized: boolean;
  clientCapabilities?: ClientCapabilities; // ✅ Now persisted
}
```

**Official Status**:
- [x] Fixed in version 0.3.5+
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Add to Known Issues with note that it's fixed in 0.3.5+

---

### Finding 1.4: Duplicate Messages with Client-Side Tool Execution (OpenAI Reasoning)

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #728](https://github.com/cloudflare/agents/issues/728)
**Date**: 2025-12-10 (closed)
**Verified**: Yes - Fixed in agents@0.2.31+
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `useAgentChat` with client-side tools lacking server-side execute functions, the agents library creates duplicate assistant messages sharing identical reasoning IDs. This triggers OpenAI API rejection: `"Duplicate item found with id rs_xxx"`.

**Root Cause**:
When client-side tool executes and calls `addToolResult()` + `sendMessage()`, the server's `_reply()` method generates a new assistant message. This new message contains reasoning parts with identical `providerMetadata.openai.itemId` values as the previous message, causing duplicate IDs.

**Inconsistent Behavior**:
- **Server-side tools**: Update existing tool parts in-place (`input-available` → `output-available`)
- **Client-side tools**: Create new messages, leaving original stuck in incomplete state

**Error**:
```
OpenAI API Error: Duplicate item found with id rs_xxx
```

**Environment**:
- agents: 0.2.31
- ai: 5.0.0
- Affects: OpenAI reasoning models (e.g., GPT-5)

**Official Status**:
- [x] Fixed in version 0.2.31+ (via PRs #729, #733)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Add to Known Issues with note about the fix

---

### Finding 1.5: Async Querying Cache TTL Not Honored

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #725](https://github.com/cloudflare/agents/issues/725)
**Date**: 2025-12-09 (closed)
**Verified**: Yes - Fixed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The `useAgent` hook has a caching problem where the queryPromise is computed once per `cacheKey` and kept forever, even after the TTL expires. This causes authentication failures when using short-lived credentials (e.g., JWTs expiring in ~1 minute).

**How It Manifests**:
Even with `cacheTtl` specified, the memoization prevents query re-execution when dependencies haven't changed. Upon reconnection after token expiration, the system keeps sending the original (now-expired) token, resulting in 401 errors.

**Root Cause**:
The implementation relies on `useMemo` with dependencies that don't include time, so TTL is never enforced. The internal `queryCache` checks TTL only during promise creation, but since `useMemo` doesn't re-run without dependency changes, expired cached values persist indefinitely.

**Reproduction**:
```typescript
// Client with short-lived JWT
const { state } = useAgent({
  agent: 'my-agent',
  name: 'session-123',
  query: async () => ({
    token: await getJWT() // Expires in 60 seconds
  }),
  cacheTtl: 60_000, // 60 seconds - NOT respected
});

// After 60 seconds:
// - Token expired
// - useMemo doesn't re-run (deps unchanged)
// - Cached query still returns old token
// - Reconnection fails with 401
```

**Workaround** (before fix):
```typescript
// Force cache invalidation by including token in queryDeps
const [tokenVersion, setTokenVersion] = useState(0);

const { state } = useAgent({
  query: async () => ({
    token: await getJWT()
  }),
  queryDeps: [tokenVersion], // ✅ Force new cache key
  cacheTtl: 60_000,
});

// Manually refresh token before expiry
useEffect(() => {
  const interval = setInterval(() => {
    setTokenVersion(v => v + 1);
  }, 50_000); // Refresh every 50s
  return () => clearInterval(interval);
}, []);
```

**Official Status**:
- [x] Fixed in version (check release notes)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.6: jsonSchemaValidator Breaks After DO Hibernation

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #663](https://github.com/cloudflare/agents/issues/663)
**Date**: 2025-11-19 (closed)
**Verified**: Yes - Fixed
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When a Durable Object hibernates and restores, the Agents SDK serializes MCP connection options using `JSON.stringify()`. This converts class instances like `CfWorkerJsonSchemaValidator` into plain objects without methods. Upon restoration via `JSON.parse()`, the validator instance loses its `getValidator()` method, causing tool discovery to fail with TypeError.

**Root Cause**:
Attempting to serialize non-serializable objects. The SDK serialized MCP connection options to SQL, converting the validator class instance into a plain object `{}` without methods.

**Error**:
```
TypeError: validator.getValidator is not a function
```

**Reproduction** (before fix):
```typescript
import { CfWorkerJsonSchemaValidator } from '@modelcontextprotocol/sdk/cloudflare-worker';

const mcpAgent = new McpAgent({
  client: {
    jsonSchemaValidator: new CfWorkerJsonSchemaValidator(), // ❌ Gets serialized
  }
});

// After DO hibernation:
// - Validator serialized to {}
// - Methods lost
// - Tool discovery fails
```

**Resolution**:
The SDK now provides the validator as a built-in default. Users no longer need to pass it explicitly:

```typescript
// ✅ Now automatic - no manual validator needed
const mcpAgent = new McpAgent({
  // SDK handles validator internally
});
```

**Official Status**:
- [x] Fixed in version (validator now built-in)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.7: Schedules Fail on Long AI Requests (blockConcurrencyWhile Timeout)

**Trust Score**: TIER 1 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #600](https://github.com/cloudflare/agents/issues/600) + [PR #653](https://github.com/cloudflare/agents/pull/653)
**Date**: 2025-10-27 (closed)
**Verified**: Yes - Fixed
**Impact**: HIGH
**Already in Skill**: Partially (mentions 30s limit but not the root cause)

**Description**:
When using the schedule feature to debounce async workflows, executions fail with timeout errors when AI requests exceed 30 seconds. The root cause was that scheduled callbacks were wrapped in `blockConcurrencyWhile`, which enforces a 30-second limit.

**Errors**:
```
IoContext timed out due to inactivity; waitUntil tasks were canceled without completing.

A call to blockConcurrencyWhile() in a Durable Object waited for too long.
The call was canceled and the Durable Object was reset.
```

**Root Cause**:
Developers had to `void` promises instead of `await`ing them in scheduled functions, otherwise the `blockConcurrencyWhile` constraint caused failures during long-running AI requests exceeding 30 seconds.

**Reproduction** (before fix):
```typescript
export class MyAgent extends Agent<Env> {
  async onRequest(request: Request) {
    // Schedule an AI task
    await this.schedule(60, "processAIRequest", { query: "..." });
  }

  async processAIRequest(data: { query: string }) {
    // This would timeout after 30s due to blockConcurrencyWhile
    const result = await streamText({
      model: openai('gpt-4o'),
      messages: [{ role: 'user', content: data.query }]
    }); // ❌ Fails if takes > 30s
  }
}
```

**Solution**:
The fix removed the `blockConcurrencyWhile` wrapper from schedule callback execution (PR #653). Schedule callbacks can now run for their full duration without artificial 30-second constraints.

**Official Status**:
- [x] Fixed in version 0.2.x (check PR #653 merge date)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Recommendation**: Update existing Issue #7 in skill to mention this was caused by blockConcurrencyWhile and is now fixed

---

### Finding 1.8: Cannot Enable SQLite on Existing Deployed Class

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Durable Objects Migrations](https://developers.cloudflare.com/durable-objects/reference/durable-objects-migrations/)
**Date**: 2025 (current)
**Verified**: Yes - Official limitation
**Impact**: HIGH
**Already in Skill**: Yes (Issue #2)

**Description**:
You cannot enable a SQLite storage backend on an existing, deployed Durable Object class. Attempting to set `new_sqlite_classes` in later migrations (after v1) will fail. This is already documented in the skill as Known Issue #2.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (design limitation)
- [ ] Known issue, workaround required
- [ ] Won't fix (future migration tooling planned)

**Cross-Reference**: Already covered in skill as Issue #2

---

### Finding 1.9: Resumable Streaming Support (NEW FEATURE)

**Trust Score**: TIER 1 - Official Changelog
**Source**: [Agents SDK v0.2.24 Changelog](https://developers.cloudflare.com/changelog/2025-11-26-agents-resumable-streaming/)
**Date**: 2025-11-26
**Verified**: Yes - Official feature
**Impact**: MEDIUM (feature enhancement)
**Already in Skill**: No

**Description**:
AIChatAgent now supports resumable streaming in agents@0.2.24+, enabling clients to reconnect and continue receiving streamed responses without data loss.

**Problems It Solves**:
- Long-running AI responses
- Users on unreliable networks
- Users switching between devices mid-conversation
- Background tasks where users navigate away and return
- Real-time collaboration where multiple clients need to stay in sync

**Key Capability**:
Streams persist across page refreshes, broken connections, and sync across open tabs and devices.

**Implementation**:
```typescript
// Built into AIChatAgent - automatic
export class ChatAgent extends AIChatAgent<Env> {
  async onChatMessage(onFinish) {
    return streamText({
      model: openai('gpt-4o-mini'),
      messages: this.messages,
      onFinish
    }).toTextStreamResponse();

    // ✅ Stream automatically resumable
    // - Client disconnects? Stream preserved
    // - Page refresh? Stream continues
    // - Multiple tabs? All stay in sync
  }
}
```

**Official Status**:
- [x] Feature available in v0.2.24+
- [x] Documented in changelog
- [ ] Known issue
- [ ] Won't fix

**Recommendation**: Add to "What's New" or feature section in skill

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: State Management Type Safety Gotcha

**Trust Score**: TIER 2 - Official Documentation Note
**Source**: [Store and sync state](https://developers.cloudflare.com/agents/api-reference/store-and-sync-state/)
**Date**: 2025 (current docs)
**Verified**: Yes - Official warning
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Providing a type parameter to state methods does NOT validate that the result matches your type definition. In TypeScript, properties (fields) that do not exist or conform to the type you provided will be dropped silently.

**Gotcha**:
```typescript
interface MyState {
  count: number;
  name: string;
}

export class MyAgent extends Agent<Env, MyState> {
  initialState = { count: 0, name: "default" };

  async increment() {
    // TypeScript allows this, but runtime may differ
    const currentState = this.state; // Type is MyState

    // If state was corrupted/modified externally:
    // { count: "invalid", otherField: 123 }
    // TypeScript still shows it as MyState
    // count field doesn't match (string vs number)
    // otherField is dropped silently
  }
}
```

**Prevention**:
```typescript
// Validate state shape at runtime
function validateState(state: unknown): state is MyState {
  return (
    typeof state === 'object' &&
    state !== null &&
    'count' in state &&
    typeof (state as MyState).count === 'number' &&
    'name' in state &&
    typeof (state as MyState).name === 'string'
  );
}

async increment() {
  if (!validateState(this.state)) {
    console.error('State validation failed', this.state);
    // Reset to valid state
    await this.setState(this.initialState);
    return;
  }

  // Safe to use
  const newCount = this.state.count + 1;
  await this.setState({ ...this.state, count: newCount });
}
```

**Community Validation**:
- Source: Official documentation
- Clear warning about type safety limitations

**Recommendation**: Add to State Management section with runtime validation pattern

---

### Finding 2.2: MCP Protocol Version Support Updated (2025-11-25)

**Trust Score**: TIER 2 - Official GitHub Issue (Fixed)
**Source**: [GitHub Issue #769](https://github.com/cloudflare/agents/issues/769)
**Date**: 2026-01-06 (closed)
**Verified**: Yes - Fixed
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
MCP WorkerTransport initially rejected protocol version `2025-11-25` due to strict version checking. This was fixed to accept any supported protocol version in request headers and only reject truly unsupported versions.

**Background**:
This aligns with the move by the MCP community to stateless transports. The fix ensures compatibility with newer MCP protocol versions.

**Error** (before fix):
```
Error: Unsupported MCP protocol version: 2025-11-25
```

**Resolution**:
Updated version validation to be more permissive:

```typescript
// Before: Strict version check
if (version !== '2024-11-05') {
  throw new Error(`Unsupported version: ${version}`);
}

// After: Accept any non-ancient version
const SUPPORTED_VERSIONS = ['2024-11-05', '2025-11-25', /* future versions */];
if (!SUPPORTED_VERSIONS.includes(version)) {
  throw new Error(`Unsupported version: ${version}`);
}
```

**Official Status**:
- [x] Fixed in agents@0.3.x
- [ ] Documented behavior
- [ ] Known issue
- [ ] Won't fix

**Recommendation**: Add note to MCP section about protocol version support

---

### Finding 2.3: Callable Methods Can Now Return `this.state`

**Trust Score**: TIER 2 - Official Release Notes
**Source**: [agents@0.3.6 Release](https://github.com/cloudflare/agents/releases/tag/agents%400.3.6)
**Date**: 2026-01-17
**Verified**: Yes - Fixed in 0.3.6
**Impact**: LOW (bug fix)
**Already in Skill**: No

**Description**:
Prior to agents@0.3.6, callable methods could not properly return `this.state` due to a TypeScript typing issue. This is now fixed.

**Before** (broken):
```typescript
export class MyAgent extends Agent<Env, { count: number }> {
  async getState() {
    return this.state; // ❌ Type error or incorrect typing
  }
}

// Calling from another agent
const agent = getAgentByName(env.MyAgent, 'instance-1');
const state = await agent.getState(); // Type was 'never'
```

**After** (fixed in 0.3.6):
```typescript
export class MyAgent extends Agent<Env, { count: number }> {
  async getState() {
    return this.state; // ✅ Works correctly
  }
}

// Calling from another agent
const agent = getAgentByName(env.MyAgent, 'instance-1');
const state = await agent.getState(); // ✅ Correct type: { count: number }
```

**Official Status**:
- [x] Fixed in v0.3.6
- [ ] Documented behavior
- [ ] Known issue
- [ ] Won't fix

**Recommendation**: Minor note in changelog or state management section

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: idFromName() vs newUniqueId() Gotcha

**Trust Score**: TIER 3 - Community-sourced best practice
**Source**: [Cloudflare blog - Building agents with OpenAI](https://blog.cloudflare.com/building-agents-with-openai-and-cloudflares-agents-sdk/)
**Date**: 2025
**Verified**: Cross-referenced with official docs
**Impact**: HIGH
**Already in Skill**: No

**Description**:
If you forget to use `idFromName()` and instead call `newUniqueId()`, you'll get a new agent instance each time, and your memory/state will never persist. This is a common early bug that silently kills statefulness.

**Gotcha**:
```typescript
// ❌ WRONG: Creates new agent every time
export default {
  async fetch(request: Request, env: Env) {
    const id = env.MyAgent.newUniqueId(); // New ID = new instance
    const agent = env.MyAgent.get(id);

    // State never persists - different instance each time
    return agent.fetch(request);
  }
}

// ✅ CORRECT: Same user = same agent = persistent state
export default {
  async fetch(request: Request, env: Env) {
    const userId = getUserId(request);
    const id = env.MyAgent.idFromName(userId); // Same ID for same user
    const agent = env.MyAgent.get(id);

    // State persists across requests for this user
    return agent.fetch(request);
  }
}
```

**Why It Matters**:
- `newUniqueId()`: Generates a random unique ID each call → new agent instance
- `idFromName(string)`: Deterministic ID from string → same agent for same input

**Consensus Evidence**:
- Mentioned in official blog posts
- Common pattern in all official examples
- Aligns with Durable Objects documentation

**Recommendation**: Add to Common Patterns or Critical Rules section

---

### Finding 3.2: Legacy Message Conversion Edge Cases

**Trust Score**: TIER 3 - Official changelog mention
**Source**: [Agents SDK v0.1.0 Changelog](https://developers.cloudflare.com/changelog/2025-09-03-agents-sdk-beta-v5/)
**Date**: 2025-09-03
**Verified**: Mentioned in changelog
**Impact**: LOW
**Already in Skill**: No

**Description**:
When migrating from AI SDK v4 to v5, there are edge cases with legacy message format conversion. The Agents SDK v0.1.0 included automatic message migration to handle this.

**What Changed**:
AI SDK v5 changed message format. Agents SDK added automatic conversion for backwards compatibility, but some edge cases may still occur with very old message formats.

**Recommendation**: Low priority - mainly affects legacy migrations

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Tanstack Start Routing Issue

**Trust Score**: TIER 4 - Insufficient information
**Source**: [GitHub Issue #789](https://github.com/cloudflare/agents/issues/789)
**Date**: 2026-01-19 (open)
**Verified**: No - just opened, no resolution
**Impact**: Unknown

**Why Flagged**:
- [x] Just opened, no investigation yet
- [x] Framework-specific (Tanstack Start)
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] Outdated

**Description**:
Issue titled "Tanstack Start: Cannot route to agents" - insufficient details to determine if this is a real Agents SDK issue or a Tanstack Start configuration problem.

**Recommendation**: Monitor for updates. DO NOT add until root cause identified.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Cannot enable SQLite on existing class | Known Issues #2 | Fully covered |
| Migrations are atomic | Known Issues #1 | Fully covered |
| Agent class must be exported | Known Issues #3 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 WebSocket 1MB payload limit | Known Issues Prevention | Add as Issue #17 |
| 1.2 Duplicate messages with needsApproval | Known Issues Prevention | Add as Issue #18 |
| 1.4 Duplicate messages with client-side tools | Known Issues Prevention | Add as Issue #19 (note: fixed in 0.2.31+) |
| 1.5 Async querying cache TTL not honored | Known Issues Prevention | Add as Issue #20 (note: fixed) |
| 1.7 blockConcurrencyWhile timeout | Known Issues Prevention | Update Issue #7 with root cause |
| 3.1 idFromName() vs newUniqueId() | Critical Rules or Common Patterns | Add clear guidance |
| 2.1 State type safety gotcha | State Management | Add runtime validation pattern |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 WorkerTransport capabilities lost | Known Issues Prevention | Add with "fixed in 0.3.5+" note |
| 1.6 jsonSchemaValidator hibernation bug | Known Issues Prevention | Add with "fixed, now automatic" note |
| 1.9 Resumable streaming | What's New or Features | Feature highlight |
| 2.2 MCP protocol version support | MCP section | Brief note on version support |
| 2.3 Callable methods return state | Changelog | Minor fix note |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 Tanstack Start routing | Insufficient info | Wait for investigation |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| All issues in cloudflare/agents | 50 | 15 |
| Recent issues (2025-2026) | 30 | 12 |
| Closed issues with fixes | 20 | 8 |
| Recent releases | 10 | 3 |

### Cloudflare Documentation

| Source | Findings |
|--------|----------|
| Agents SDK docs | 3 (state management, migrations, resumable streaming) |
| Durable Objects migrations | 1 (SQLite limitation) |
| Changelog entries | 4 (version updates, new features) |

### Community Sources

| Source | Findings |
|--------|----------|
| Cloudflare blog posts | 1 (idFromName gotcha) |
| Stack Overflow | 0 (no relevant results) |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub issue discovery
- `gh issue view` for detailed issue analysis
- `gh api` for release information
- `WebSearch` for documentation and blog posts
- `WebFetch` for detailed content extraction

**Limitations**:
- Stack Overflow has minimal Agents SDK content (package too new)
- Most valuable information found in official GitHub issues and changelog
- Some issues still open/under investigation

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.1 (WebSocket payload limit) against current official documentation to verify if this has been officially documented since the issue was opened.

**For api-method-checker**: Verify that all code examples in findings use currently available APIs, especially for recent fixes in 0.3.x versions.

**For code-example-validator**: Validate all TypeScript code examples in findings 1.1-3.1 before adding to skill.

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

#### For High-Priority Issues (1.1, 1.2, 1.4, 1.5, 1.7):

```markdown
### Issue #17: WebSocket Payload Size Limit (1MB)

**Error**: `Error: internal error; reference = [reference ID]`
**Source**: [GitHub Issue #119](https://github.com/cloudflare/agents/issues/119)
**Why**: WebSocket connections fail when cumulative message payload exceeds ~1 MB. After 5-6 tool calls returning large data (e.g., 200KB+ each), connection crashes.
**Prevention**: Prune message history client-side to stay under 950KB

```typescript
// Workaround: Prune old messages
function pruneMessages(messages: Message[]): Message[] {
  let totalSize = 0;
  const pruned = [];

  for (let i = messages.length - 1; i >= 0; i--) {
    const msgSize = JSON.stringify(messages[i]).length;
    if (totalSize + msgSize > 950_000) break;
    pruned.unshift(messages[i]);
    totalSize += msgSize;
  }

  return pruned;
}
```

**Better Solution** (proposed): Server-side context management, only send summaries to client.
```

#### For Fixed Issues (1.3, 1.6):

```markdown
### Issue #[N]: WorkerTransport ClientCapabilities Lost After Hibernation

**Error**: `Error: Client does not support form elicitation`
**Source**: [GitHub Issue #777](https://github.com/cloudflare/agents/issues/777)
**Fixed In**: agents@0.3.5+
**Why**: ClientCapabilities weren't persisted to storage during DO hibernation
**Prevention**: Update to agents@0.3.5 or later

```typescript
// ✅ Fixed automatically in 0.3.5+
// ClientCapabilities now persisted in TransportState
```
```

#### For Common Patterns (3.1):

```markdown
### Critical Pattern: idFromName() vs newUniqueId()

**Rule**: Always use `idFromName()` for user-specific agents, never `newUniqueId()`

```typescript
// ❌ WRONG: Creates new agent every time (state never persists)
const id = env.MyAgent.newUniqueId();
const agent = env.MyAgent.get(id);

// ✅ CORRECT: Same user = same agent = persistent state
const userId = getUserId(request);
const id = env.MyAgent.idFromName(userId);
const agent = env.MyAgent.get(id);
```

**Why It Matters**: `newUniqueId()` generates random IDs → new instance each time. `idFromName()` is deterministic → same agent for same input.
```

---

**Research Completed**: 2026-01-21
**Next Research Due**: After agents@0.4.0 release or quarterly (April 2026)

---

## Sources

### GitHub Issues

- [Websocket connection error with long tool call responses #119](https://github.com/cloudflare/agents/issues/119)
- [Duplicate assistant messages when using needsApproval tools #790](https://github.com/cloudflare/agents/issues/790)
- [WorkerTransport doesn't persist clientCapabilities #777](https://github.com/cloudflare/agents/issues/777)
- [Client-side tool execution creates duplicate messages #728](https://github.com/cloudflare/agents/issues/728)
- [Async querying has caching bugs #725](https://github.com/cloudflare/agents/issues/725)
- [jsonSchemaValidator breaks after DO hibernation #663](https://github.com/cloudflare/agents/issues/663)
- [Schedules can't process long AI requests #600](https://github.com/cloudflare/agents/issues/600)
- [Support MCP-Protocol-Version 2025-11-25 #769](https://github.com/cloudflare/agents/issues/769)

### Official Documentation

- [Agents SDK](https://developers.cloudflare.com/agents/)
- [Store and sync state](https://developers.cloudflare.com/agents/api-reference/store-and-sync-state/)
- [Using WebSockets](https://developers.cloudflare.com/agents/api-reference/websockets/)
- [Durable Objects migrations](https://developers.cloudflare.com/durable-objects/reference/durable-objects-migrations/)
- [Agents SDK v0.2.24 with resumable streaming](https://developers.cloudflare.com/changelog/2025-11-26-agents-resumable-streaming/)
- [Agents SDK v0.3.0 with AI SDK v6 support](https://developers.cloudflare.com/changelog/2025-12-22-agents-sdk-ai-sdk-v6/)

### Release Notes

- [agents@0.3.6](https://github.com/cloudflare/agents/releases/tag/agents%400.3.6)

### Blog Posts

- [Building agents with OpenAI and Cloudflare's Agents SDK](https://blog.cloudflare.com/building-agents-with-openai-and-cloudflares-agents-sdk/)
- [Making Cloudflare the best platform for building AI Agents](https://blog.cloudflare.com/build-ai-agents-on-cloudflare/)
