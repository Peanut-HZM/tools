# Community Knowledge Research: TypeScript MCP SDK

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/typescript-mcp/SKILL.md
**Packages Researched**: @modelcontextprotocol/sdk@1.25.3
**Official Repo**: modelcontextprotocol/typescript-sdk
**Time Window**: Dec 2025 - Jan 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 14 |
| TIER 1 (Official) | 10 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 11 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Server.connect() Silently Overwrites Transport

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1405](https://github.com/modelcontextprotocol/typescript-sdk/issues/1405)
**Date**: 2026-01-19
**Verified**: Yes
**Impact**: CRITICAL
**Already in Skill**: No

**Description**:
When using `StreamableHTTPServerTransport` with multiple concurrent HTTP sessions, calling `Server.connect(transport)` for a second transport silently overwrites `this._transport` without warning. This breaks the first transport's ability to receive responses, causing `AbortError: This operation was aborted`.

This is a major footgun because:
- No error is thrown at `connect()` time
- The first session works fine until the second connects
- Error messages don't indicate the root cause

**Reproduction**:
```typescript
const server = new McpServer({ name: 'test', version: '1.0.0' });

// Session A connects
const transportA = new StreamableHTTPServerTransport({ sessionIdGenerator: () => 'session-a' });
await server.connect(transportA);  // Works

// Session B connects
const transportB = new StreamableHTTPServerTransport({ sessionIdGenerator: () => 'session-b' });
await server.connect(transportB);  // Also "works" - but silently breaks transportA

// Now any request through transportA will fail with AbortError
```

**Solution/Workaround**:
```typescript
// CRITICAL: Create a new McpServer instance for each HTTP session
app.post('/mcp', async (c) => {
  // ✅ CORRECT - Fresh server per session
  const server = new McpServer({ name: 'my-server', version: '1.0.0' });

  // Register tools/resources/prompts
  server.registerTool(...);

  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true
  });

  c.res.raw.on('close', () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(c.req.raw, c.res.raw, await c.req.json());
  return c.body(null);
});

// ❌ WRONG - Reusing server instance across sessions
const sharedServer = new McpServer(...);
app.post('/mcp', async (c) => {
  await sharedServer.connect(transport); // Breaks previous connections
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to: #1400 (reconnection error), #1278 (confusion about McpServer sharing)
- Corroborated by: SDK examples use `getServer()` function to create fresh instances per request

---

### Finding 1.2: Invalid Types for sessionIdGenerator in 1.25.2

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1397](https://github.com/modelcontextprotocol/typescript-sdk/issues/1397)
**Date**: 2026-01-16
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
SDK 1.25.2 introduced strict types that break projects using `sessionIdGenerator: undefined` with TypeScript's `exactOptionalPropertyTypes: true` compiler option. The types incorrectly require `sessionIdGenerator?: () => string` instead of `sessionIdGenerator?: (() => string) | undefined`.

**Reproduction**:
```typescript
// With exactOptionalPropertyTypes: true in tsconfig.json
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,  // ❌ Type error in 1.25.2
  enableJsonResponse: true
});

// Error: Type 'undefined' is not assignable to type '() => string'
```

**Solution/Workaround**:
```typescript
// Option 1: Omit the property instead of setting to undefined
const transport = new StreamableHTTPServerTransport({
  // sessionIdGenerator omitted entirely
  enableJsonResponse: true
});

// Option 2: Provide a no-op function (not recommended)
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: () => crypto.randomUUID(),
  enableJsonResponse: true
});

// Option 3: Disable exactOptionalPropertyTypes (not recommended)
// tsconfig.json: "exactOptionalPropertyTypes": false
```

**Official Status**:
- [ ] Fixed in version 1.25.3+
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Root cause: PR #1326 changed optional property types
- Also affects `Transport.onclose` property

---

### Finding 1.3: Global fetch Pollution from Hono (v1.25.0+)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1376](https://github.com/modelcontextprotocol/typescript-sdk/issues/1376), [PR #1411](https://github.com/modelcontextprotocol/typescript-sdk/pull/1411)
**Date**: 2026-01-12
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
SDK v1.25.0+ includes `@hono/node-server` which globally overwrites `global.fetch`, breaking code that depends on the native Node.js fetch implementation. This is because Hono's server code modifies the global fetch to disable compression handling.

**Reproduction**:
```typescript
// Before importing SDK
console.log(global.fetch); // [Function: fetch]

// After importing SDK (v1.25.0+)
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
console.log(global.fetch); // [Function: anonymous] - CHANGED!

// This breaks libraries that expect native fetch behavior
```

**Solution/Workaround**:
```typescript
// Workaround: Save native fetch before importing SDK
const nativeFetch = global.fetch;

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

// Restore if needed
global.fetch = nativeFetch;

// Or use explicit fetch reference
const response = await nativeFetch('https://api.example.com');
```

**Official Status**:
- [x] Fixed in version 1.25.3 (PR #1411)
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Fixed in v1.25.3 via commit 67ba7ad
- Root cause: `@hono/node-server/dist/globals.js` modifies global.fetch

---

### Finding 1.4: Task Error Wrapping Masks Validation Errors

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1385](https://github.com/modelcontextprotocol/typescript-sdk/issues/1385)
**Date**: 2026-01-14
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When a task-augmented tool call fails due to input validation or other errors before task creation, the SDK incorrectly wraps the error as a tool error result (`{content: [...], isError: true}`). This then fails `CreateTaskResultSchema` validation, producing a confusing error message that completely hides the actual underlying error.

**Reproduction**:
```typescript
server.experimental.tasks.registerToolTask(
  'batch_process',
  {
    inputSchema: z.object({
      itemCount: z.number().min(1).max(10),
      processingTimeMs: z.number().min(500).max(5000).optional(),
    })
  },
  {
    createTask: async (args, extra) => {
      // Handler code
    }
  }
);

// Call with invalid input (processingTimeMs too small)
// Request: { "itemCount": 5, "processingTimeMs": 100, "task": { "ttl": 60000 } }
```

**Expected Error**:
```json
{
  "error": {
    "code": -32602,
    "message": "Invalid arguments for tool batch_process: Too small: expected number to be >=500"
  }
}
```

**Actual Error** (confusing):
```json
{
  "error": {
    "code": -32602,
    "message": "MCP error -32602: Invalid task creation result: [{\"expected\":\"object\",\"code\":\"invalid_type\",\"path\":[\"task\"],\"message\":\"Invalid input: expected object, received undefined\"}]"
  }
}
```

**Solution/Workaround**:
Currently no workaround. SDK needs fix to re-throw validation errors for task-augmented requests instead of wrapping them.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, SDK fix needed
- [ ] Won't fix

**Cross-Reference**:
- Reproducible in MCP Inspector: https://glama.ai/mcp/inspector

---

### Finding 1.5: Tool Schema with All Optional Fields Causes InvalidParams

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #400](https://github.com/modelcontextprotocol/typescript-sdk/issues/400)
**Date**: 2025-04-24
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When registering a tool with a schema where all fields are optional, some LLM clients (e.g., Windsurf) will call the tool without supplying the `arguments` field in the request. The SDK's validation fails because the Zod object created is non-optional, even though all its properties are optional.

**Reproduction**:
```typescript
server.registerTool(
  "fetch-records",
  {
    description: "Fetches database records",
    inputSchema: z.object({
      limit: z.number().optional().describe("The number of records to fetch. Default is 20.")
    })
  },
  ({ limit }) => {
    return {
      content: [{ type: "text", text: `Fetched ${limit ?? 20} records` }],
    };
  }
);

// Some clients call without arguments field
// Request: { "method": "tools/call", "params": { "name": "fetch-records" } }
// Error: "expected": "object", "received": "undefined"
```

**Solution/Workaround**:
```typescript
// Workaround 1: Use .nullable() on the schema (less idiomatic)
inputSchema: z.object({
  limit: z.number().optional()
}).nullable()

// Workaround 2: Always include at least one required field
inputSchema: z.object({
  action: z.literal("fetch").default("fetch"),  // Required field
  limit: z.number().optional()
})

// Workaround 3: Use empty object as valid input
inputSchema: z.object({}).passthrough()
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Discussion: https://github.com/orgs/modelcontextprotocol/discussions/366
- Affects Windsurf and potentially other clients

---

### Finding 1.6: Bulk Tool Registration Triggers EventEmitter Memory Leak Warnings

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #842](https://github.com/modelcontextprotocol/typescript-sdk/issues/842)
**Date**: 2025-08-05
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When registering 80+ tools dynamically in a loop, the SDK triggers `MaxListenersExceededWarning` from Node.js EventEmitter. This happens because each `server.tool()` call automatically triggers `sendToolListChanged()`, and rapid notifications overwhelm the stdout buffer in `StdioServerTransport`, causing multiple `'drain'` listeners to accumulate.

**Reproduction**:
```typescript
const tools = [...]; // Array of 80+ tool definitions

for (const tool of tools) {
  server.registerTool(tool.name, tool.schema, tool.handler);
}

// Warning: Possible EventEmitter memory leak detected. 11 drain listeners added to [Socket]
```

**Solution/Workaround**:
```typescript
// Workaround 1: Increase maxListeners before bulk registration
process.stdout.setMaxListeners(100);

for (const tool of tools) {
  server.registerTool(tool.name, tool.schema, tool.handler);
}

// Workaround 2: Use a registration wrapper (future SDK feature?)
// Not yet available, but proposed as registerTools(tools[]) with single notification
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Common in dynamic, context-aware servers (XcodeBuildMCP, etc.)
- Community suggests this is expected behavior for 80+ tools
- Proposed solution: Batch registration API

---

### Finding 1.7: Some Transport Errors Silently Swallowed

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1395](https://github.com/modelcontextprotocol/typescript-sdk/issues/1395)
**Date**: 2026-01-16
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Transport errors can be silently swallowed if the transport's `onerror` callback is not set. This makes debugging connection issues extremely difficult as errors vanish without logs.

**Reproduction**:
```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
  enableJsonResponse: true
});

// Error occurs in transport but no onerror handler set
await server.connect(transport);
// Errors are silently swallowed - no logs, no exceptions
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - Always set onerror handler
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
  enableJsonResponse: true
});

transport.onerror = (error) => {
  console.error('Transport error:', error);
  // Handle error appropriately
};

await server.connect(transport);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to missing error handling in protocol layer

---

### Finding 1.8: listTools() Fails with $defs References (SDK 1.22.0-1.22.x)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1175](https://github.com/modelcontextprotocol/typescript-sdk/issues/1175)
**Date**: 2025-11-26
**Verified**: Yes
**Impact**: HIGH (but fixed)
**Already in Skill**: No

**Description**:
SDK 1.22.0 introduced a regression in `cacheToolOutputSchemas` that broke `listTools()` when servers return tool schemas with `$defs` references. AJV fails to compile schemas with error "can't resolve reference #/$defs/..." This affected AWS MCP servers and others using complex JSON Schema with `$defs` blocks.

**Reproduction**:
```typescript
// This worked in 1.19.1, failed in 1.22.0
const client = new Client({ name: 'test', version: '1.0.0' });
const transport = new StdioClientTransport({
  command: 'uvx',
  args: ['awslabs.aws-api-mcp-server@latest'],
  env: { AWS_REGION: 'us-east-1' }
});

await client.connect(transport);
await client.listTools(); // ❌ Error in 1.22.0
```

**Solution/Workaround**:
```typescript
// Solution: Update to SDK 1.23.0 or later
// No workaround in 1.22.0 - must upgrade or downgrade to 1.19.1
```

**Official Status**:
- [x] Fixed in version 1.23.0
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Forced AWS Toolkit for VS Code to pin SDK to 1.19.1 temporarily
- Root cause: `cacheToolOutputSchemas` method added in 1.22.0

---

### Finding 1.9: DoS via qs arrayLimit Bypass

**Trust Score**: TIER 1 - Official (Security)
**Source**: [GitHub Issue #1368](https://github.com/modelcontextprotocol/typescript-sdk/issues/1368)
**Date**: 2026-01-07
**Verified**: Yes
**Impact**: HIGH (Security)
**Already in Skill**: No

**Description**:
The `qs` library's `arrayLimit` can be bypassed using bracket notation, allowing DoS attacks via memory exhaustion. Attackers can send query strings with bracket syntax like `?foo[99999999]=bar` to allocate massive arrays.

**Reproduction**:
```typescript
// Malicious query string
// ?items[99999999]=value
// Bypasses arrayLimit and allocates huge array, exhausting memory
```

**Solution/Workaround**:
```typescript
// Solution: Update qs library to patched version
// Or use alternative query string parser with proper array limits

// For MCP servers, validate query parameters
app.post('/mcp', async (c) => {
  const queryParams = c.req.query();

  // Validate query string doesn't contain malicious patterns
  if (Object.keys(queryParams).some(key => /\[\d{6,}\]/.test(key))) {
    return c.json({ error: 'Invalid query parameters' }, 400);
  }

  // ... handle request
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z (depends on qs library update)
- [ ] Documented behavior
- [x] Known security issue, validation required
- [ ] Won't fix

**Cross-Reference**:
- Security vulnerability in qs dependency
- Affects all SDK versions using qs

---

### Finding 1.10: Request Handlers Not Cancelled on Transport Close

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #611](https://github.com/modelcontextprotocol/typescript-sdk/issues/611)
**Date**: 2025-06-11
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When a transport connection closes unexpectedly (client disconnect, network error), request handlers continue executing instead of being cancelled. This wastes resources and can cause issues if handlers try to send responses after the connection is closed.

**Reproduction**:
```typescript
server.registerTool(
  'long-running-task',
  { inputSchema: z.object({ duration: z.number() }) },
  async ({ duration }) => {
    // Long-running task (e.g., 30 seconds)
    await new Promise(resolve => setTimeout(resolve, duration * 1000));
    return { content: [{ type: 'text', text: 'Done' }] };
  }
);

// Client disconnects after 5 seconds
// Handler continues running for full 30 seconds instead of being cancelled
```

**Solution/Workaround**:
```typescript
// Workaround: Use AbortController pattern manually
server.registerTool(
  'long-running-task',
  { inputSchema: z.object({ duration: z.number() }) },
  async ({ duration }, extra) => {
    const abortController = new AbortController();

    // Listen for transport close
    extra.transport?.onclose = () => {
      abortController.abort();
    };

    try {
      await longRunningTask(duration, abortController.signal);
      return { content: [{ type: 'text', text: 'Done' }] };
    } catch (error) {
      if (error.name === 'AbortError') {
        // Task cancelled due to connection close
        return { content: [{ type: 'text', text: 'Cancelled' }], isError: true };
      }
      throw error;
    }
  }
);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, manual cancellation required
- [ ] Won't fix

**Cross-Reference**:
- Related to transport lifecycle management
- Affects all transports (stdio, HTTP, SSE)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Streamable HTTP Recommended for Production over SSE

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Blog Post](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/), [Official SDK Docs](https://github.com/modelcontextprotocol/typescript-sdk)
**Date**: 2025-06-06
**Verified**: Cross-referenced with official docs
**Impact**: HIGH
**Already in Skill**: Partially (mentions StreamableHTTP but not deprecation context)

**Description**:
Streamable HTTP was introduced in MCP specification v2025-03-26 as a replacement for SSE (Server-Sent Events). SDK v1.10.0+ supports Streamable HTTP as the recommended production transport. SSE support remains for backwards compatibility only.

Key improvements in Streamable HTTP over SSE:
- Better handling of bidirectional communication
- Improved error recovery
- Simpler deployment (no need for separate SSE endpoint)
- Better support for HTTP/2 and HTTP/3

**Solution**:
```typescript
// ✅ RECOMMENDED - Use StreamableHTTPServerTransport
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';

const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
  enableJsonResponse: true
});

// ❌ DEPRECATED - SSE transport (backwards compatibility only)
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
```

**Community Validation**:
- Official MCP spec update: 2025-03-26
- SDK support added: v1.10.0 (April 17, 2025)
- Multiple production deployments confirmed

**Recommendation**: Update skill to explicitly note SSE deprecation and recommend Streamable HTTP for all new projects.

---

### Finding 2.2: v2 Release Timeline and Migration Planning

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [InfoQ Article](https://www.infoq.com/news/2026/01/azure-functions-mcp-support/), Official SDK releases
**Date**: 2026-01-XX
**Verified**: Cross-referenced with official releases
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
SDK v2.0 is anticipated in Q1 2026. v1.x will continue to receive bug fixes and security updates for at least 6 months after v2 ships. This gives production users time to plan migration.

Key points:
- v1.x is stable and recommended for production until v2 is released
- v1.25.x is latest stable (as of Jan 2026)
- Breaking changes expected in v2 (details TBD)
- Migration window: 6+ months after v2 release

**Recommendation**: Update skill to note version stability and upcoming v2 timeline.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: HTTP Transport Required for Production Deployments

**Trust Score**: TIER 3 - Community Consensus
**Source**: Multiple sources ([SDK README](https://github.com/modelcontextprotocol/typescript-sdk), community discussions)
**Date**: 2025-2026
**Verified**: Multiple sources agree
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions HTTP but not stdio limitation)

**Description**:
Stdio transport is only suitable for local development and cannot be deployed to production. HTTP transport (StreamableHTTP or SSE) is required for any production deployment, including edge/serverless environments.

**Consensus Evidence**:
- Official SDK README states stdio is for "connecting to local servers"
- Community discussions consistently mention HTTP requirement
- Example servers use HTTP for production deployments

**Recommendation**: Add explicit warning about stdio transport limitations to skill.

---

### Finding 3.2: CORS Configuration Essential for Browser Clients

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #143](https://github.com/modelcontextprotocol/typescript-sdk/issues/143), production deployments
**Date**: 2025-02-03
**Verified**: Multiple deployments confirm
**Impact**: MEDIUM
**Already in Skill**: Yes (Issue #5)

**Description**:
Better CORS defaults needed for HTTP transports. The skill already covers CORS configuration (Issue #5), but community feedback suggests this is one of the most common deployment issues.

**Recommendation**: No action needed - already well-covered in skill.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| CORS misconfiguration | Issue #5 | Fully covered with Hono middleware example |
| Unclosed transport connections | Issue #2 | Fully covered with c.res.raw.on('close') pattern |
| Export syntax errors | Issue #1 | Fully covered (direct export vs object wrapper) |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, Critical/High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Server.connect() overwrites transport | Known Issues Prevention | Add as Issue #11 - CRITICAL for concurrent HTTP |
| 1.2 sessionIdGenerator type error | Known Issues Prevention | Add as Issue #12 - TypeScript strict mode |
| 1.3 Global fetch pollution | Known Issues Prevention | Add as Issue #13 - Note fixed in 1.25.3 |
| 1.4 Task error wrapping | Known Issues Prevention | Add as Issue #14 - Tasks feature |
| 1.7 Silent transport errors | Error Handling | Add onerror handler to templates |
| 1.9 DoS via qs arrayLimit | Security section | Add validation pattern |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.5 All-optional schema bug | Common Patterns | Add to tool registration section |
| 1.6 Bulk registration warnings | Performance Tips | Add as community tip with workaround |
| 1.10 Handler cancellation | Advanced Patterns | Add AbortController pattern |
| 2.1 SSE deprecation | Quick Start | Note Streamable HTTP is recommended |
| 2.2 v2 timeline | Version info | Add migration timeline note |

### Priority 3: Monitor (Low Impact or Fixed)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 1.8 $defs schema bug | Fixed in 1.23.0 | Update minimum version recommendation |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "transport" in modelcontextprotocol/typescript-sdk | 30 | 8 |
| "edge case OR gotcha" in repo | 0 | 0 |
| "workaround OR breaking change" in repo | 0 | 0 |
| Recent issues (Dec 2025 - Jan 2026) | 30 | 10 |
| Open error/fail issues | 20 | 7 |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "MCP typescript sdk StreamableHTTP production" | 10 | High (official + blog posts) |
| "modelcontextprotocol typescript-sdk site:stackoverflow.com" | 0 | N/A |

### Official Sources

| Source | Notes |
|--------|-------|
| [TypeScript SDK Repository](https://github.com/modelcontextprotocol/typescript-sdk) | Primary source for issues |
| [MCP Specification](https://spec.modelcontextprotocol.io/) | Transport recommendations |
| [Release Notes](https://github.com/modelcontextprotocol/typescript-sdk/releases) | v1.25.3 latest |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release list/view` for release information
- `WebSearch` for community content and blogs

**Limitations**:
- Stack Overflow has minimal MCP TypeScript SDK coverage yet (very new technology)
- Most community knowledge is in GitHub issues and official sources
- Some issues are version-specific (1.22.0 bug, 1.25.0-1.25.2 bugs)

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.1, 1.4, and 1.9 against current official documentation before adding.

**For api-method-checker**: Verify that workarounds in findings 1.5 and 1.6 use currently available APIs in SDK 1.25.3.

**For code-example-validator**: Validate code examples in findings 1.1, 1.7, and 1.10 before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

**For Finding 1.1 (Server.connect() overwrites transport)**:

```markdown
### Issue #11: Server Instance Reuse Breaks Concurrent HTTP Sessions

**Error**: `AbortError: This operation was aborted`
**Source**: [GitHub Issue #1405](https://github.com/modelcontextprotocol/typescript-sdk/issues/1405)
**Why It Happens**: Calling `Server.connect(transport)` silently overwrites the previous transport without warning
**Prevention**:
```typescript
// ✅ CORRECT - Create fresh McpServer per HTTP session
app.post('/mcp', async (c) => {
  const server = new McpServer({ name: 'my-server', version: '1.0.0' });
  server.registerTool(...); // Register tools per request

  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true
  });

  c.res.raw.on('close', () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(c.req.raw, c.res.raw, await c.req.json());
  return c.body(null);
});

// ❌ WRONG - Reusing server instance
const sharedServer = new McpServer(...);
app.post('/mcp', async (c) => {
  await sharedServer.connect(transport); // Breaks previous sessions
});
```
```

**For Finding 1.7 (Silent transport errors)**:

Add to all template files:
```typescript
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
  enableJsonResponse: true
});

// CRITICAL: Set onerror handler to catch transport errors
transport.onerror = (error) => {
  console.error('MCP transport error:', error);
};
```

---

**Research Completed**: 2026-01-21 12:30
**Next Research Due**: After SDK v2.0 release (anticipated Q1 2026)
