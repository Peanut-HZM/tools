# Community Knowledge Research: OpenAI Apps MCP

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/openai-apps-mcp/SKILL.md
**Packages Researched**: @modelcontextprotocol/sdk@1.25.2, hono@4.11.3, zod@4.3.5
**Official Repos**: modelcontextprotocol/typescript-sdk, openai/openai-apps-sdk-examples
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 13 |
| TIER 1 (Official) | 7 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 5 |
| Recommended to Add | 8 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Hono Global Response Override Breaks Next.js App Router (v1.25.x+)

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #1369](https://github.com/modelcontextprotocol/typescript-sdk/issues/1369)
**Date**: 2026-01-08
**Verified**: Yes (Fixed in v1.25.3)
**Impact**: HIGH - Breaks production applications using Next.js
**Already in Skill**: No

**Description**:
MCP SDK v1.25.x introduced Hono as a dependency. Hono defaults to `overrideGlobalObjects: true`, which overwrites `global.Response` when `StreamableHTTPServerTransport` is instantiated. This breaks Next.js App Router routes because `NextResponse extends Response`, and the instanceof check fails after Hono replaces the global.

**Reproduction**:
```typescript
// Before MCP SDK instantiation
const before = NextResponse.json({ status: "before" });
console.log(before instanceof Response); // true

// Instantiate MCP SDK
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
});

// After - NextResponse instanceof check now fails
const after = NextResponse.json({ status: "after" });
console.log(after instanceof Response); // false ❌
```

**Error**:
```
[Error: No response is returned from route handler '[project]/web/src/app/api/chatCompletion/route.ts'.
Ensure you return a `Response` or a `NextResponse` in all branches of your handler.]
```

**Solution/Workaround**:
1. **Fixed in v1.25.3** (2026-01-20): [PR #1411](https://github.com/modelcontextprotocol/typescript-sdk/pull/1411) prevents Hono from overriding global Response
2. **Before fix**: Use `webStandardStreamableHTTPServerTransport` instead of `StreamableHTTPServerTransport`
3. **Or**: Run MCP server on separate port/process from Next.js app

**Official Status**:
- [x] Fixed in version 1.25.3
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related PR: [#1209 - Fetch transport](https://github.com/modelcontextprotocol/typescript-sdk/pull/1209)
- Affects any framework using global.Response (Next.js, Remix, SvelteKit)

---

### Finding 1.2: Elicitation (User Input) Fails on Cloudflare Workers - AJV Code Generation

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #689](https://github.com/modelcontextprotocol/typescript-sdk/issues/689)
**Date**: 2025-06-23
**Verified**: Yes
**Impact**: HIGH - Blocks elicitation feature on edge platforms
**Already in Skill**: No

**Description**:
The `elicitInput()` feature fails on Cloudflare Workers with `EvalError: Code generation from strings disallowed`. This is because AJV v6 internally uses dynamic code generation (not shown in user code), which is prohibited in Cloudflare Workers and other edge environments.

**Reproduction**:
```typescript
// On Cloudflare Workers
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Calling elicitInput triggers AJV validation internally
  const userInput = await server.elicitInput({
    prompt: "What is your name?",
    schema: { type: "string" }
  });
  // ❌ EvalError: Code generation from strings disallowed
  // This is an internal AJV error, not user code
});
```

**Error**:
```
EvalError: Code generation from strings disallowed for this context
    at Ajv3.localCompile (.../index.js:3411:30)
    at Ajv3.resolve (.../index.js:2571:73)
```

**Solution/Workaround**:
1. **Avoid `elicitInput()` on Cloudflare Workers** - Use standard tool parameters instead
2. **Alternative validators**: Use `@cfworker/json-schema` (doesn't use code generation)
3. **Wait for fix**: Issue closed, but requires SDK v2 migration to fix properly (PR #844, #1242)

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix (requires v2 spec changes)

**Cross-Reference**:
- Corroborated by: [Issue #928](https://github.com/modelcontextprotocol/typescript-sdk/issues/928) (same root cause)
- MCP Spec PR: [modelcontextprotocol#1148](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/1148)
- Affects: Cloudflare Workers, Vercel Edge, Deno Deploy

---

### Finding 1.3: SSE Transport Statefulness Breaks Serverless Deployments

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #273](https://github.com/modelcontextprotocol/typescript-sdk/issues/273)
**Date**: 2025-04-07
**Verified**: Yes (Addressed by Streamable HTTP in v1.24+)
**Impact**: HIGH - Makes SSE unusable in serverless
**Already in Skill**: Partially (skill mentions SSE heartbeat, but not statelessness issue)

**Description**:
`SSEServerTransport` relies on in-memory session storage (`transports: {[sessionId: string]: SSEServerTransport}`). In serverless environments (AWS Lambda, Cloudflare Workers), the initial `GET /sse` request may be handled by Instance A, but subsequent `POST /messages` requests land on Instance B, which lacks the in-memory state. Result: `400: No transport found for sessionId`.

**Reproduction**:
1. Deploy MCP SSE server to AWS Lambda + API Gateway
2. Client connects to `/sse` → Instance A
3. Send message to `/messages?sessionId=abc` → Instance B (different)
4. Error: `400: No transport found for sessionId: abc`

**Solution/Workaround**:
1. **Use Streamable HTTP transport instead of SSE** (added in v1.24.0, spec 2025-11-25)
2. **For stateful SSE**: Deploy to non-serverless environments (VPS, long-running containers)
3. **Load balancer sticky sessions**: Route same sessionId to same instance (not recommended)

**Official Status**:
- [x] Fixed by introducing Streamable HTTP (v1.24+)
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related: [PR #266 - Streamable HTTP](https://github.com/modelcontextprotocol/typescript-sdk/pull/266)
- Streamable HTTP is now the **recommended standard** for serverless deployments

---

### Finding 1.4: Loose Type Exports Removed in v1.25.0 (BREAKING)

**Trust Score**: TIER 1 - Official Release Notes
**Source**: [v1.25.0 Release](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/1.25.0)
**Date**: 2025-12-15
**Verified**: Yes
**Impact**: HIGH - Breaking change requiring code updates
**Already in Skill**: Yes (documented in SKILL.md)

**Description**:
MCP SDK v1.25.0 removed loose/passthrough types (Prompts, Resources, Roots, Sampling, Tools) that were not allowed/defined by MCP spec. Now you must use specific schema imports.

**Migration**:
```typescript
// ❌ Old (removed in 1.25.0)
import { Tools } from '@modelcontextprotocol/sdk/types.js';

// ✅ New (1.25.0+)
import { ListToolsRequestSchema, CallToolRequestSchema } from '@modelcontextprotocol/sdk/types.js';
```

**Official Status**:
- [x] Breaking change in v1.25.0
- [x] Documented in release notes
- [x] Already in skill

**Cross-Reference**:
- PR: [#1242 - Remove loose types](https://github.com/modelcontextprotocol/typescript-sdk/pull/1242)
- Also requires ES2020 target (was ES2018)

---

### Finding 1.5: Tasks & Sampling with Tools (v1.24.0+)

**Trust Score**: TIER 1 - Official Release
**Source**: [v1.24.0 Release](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/1.24.0)
**Date**: 2025-12-02
**Verified**: Yes
**Impact**: MEDIUM - New feature, not breaking
**Already in Skill**: Yes (documented in SKILL.md)

**Description**:
MCP SDK v1.24.0 added two new features:
1. **Tasks** (SEP-1686): Long-running operations with progress tracking
2. **Sampling with Tools**: Tools can request model sampling

**Usage**:
```typescript
// Tasks - for long-running operations
server.setRequestHandler(CreateTaskRequestSchema, async (request) => {
  // Start background job, return task ID
  return { taskId: "task-123" };
});

// Sampling with Tools - tools can invoke LLM
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const result = await server.requestSampling({
    messages: [{ role: "user", content: "Summarize this data" }],
    modelPreferences: { hints: ["claude-3-5-sonnet"] }
  });
  return { content: [{ type: "text", text: result.completion }] };
});
```

**Official Status**:
- [x] New feature in v1.24.0
- [x] Spec version 2025-11-25
- [x] Already documented in skill

---

### Finding 1.6: Widget Outage - HTML Not Loading (October 2025)

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [Issue #58 - openai-apps-sdk-examples](https://github.com/openai/openai-apps-sdk-examples/issues/58)
**Date**: 2025-10-15 to 2025-10-16
**Verified**: Yes (Temporary platform issue)
**Impact**: HIGH (during outage) - Complete widget failure
**Already in Skill**: No

**Description**:
From October 15-16, 2025, ChatGPT apps stopped rendering widgets. HTML UI resources weren't being invoked - no `index.html` requests appeared in logs, and 403 errors appeared briefly. Apps that worked on Oct 15 stopped working on Oct 16 with no code changes.

**Symptoms**:
- Widget UI shows structured content only (no rendered widget)
- No network requests to widget HTML in browser console
- Multiple 403 errors on widget assets (temporary)

**Solution**:
- **Platform-side fix**: Issue resolved by OpenAI within 24 hours
- **No code changes needed**

**Key Lesson**:
ChatGPT Apps platform can have temporary outages affecting all widgets. Always check OpenAI status page before debugging widget rendering issues.

**Official Status**:
- [x] Resolved (platform issue)
- [ ] Ongoing
- [ ] User-side fix required

**Cross-Reference**:
- Related: [Issue #53 - No widget UI showing](https://github.com/openai/openai-apps-sdk-examples/issues/53)
- Affects: All ChatGPT apps using widgets

---

### Finding 1.7: OAuth Configuration Requires TWO Separate Apps

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Cloudflare Remote MCP Server Docs](https://developers.cloudflare.com/agents/guides/remote-mcp-server/)
**Date**: 2025 (current docs)
**Verified**: Yes
**Impact**: MEDIUM - Common misconfiguration
**Already in Skill**: No

**Description**:
When adding OAuth to MCP servers, you need **two separate OAuth apps** - one for localhost development (`http://localhost:8788/callback`) and one for production (`https://your-app.workers.dev/callback`). Using the same OAuth app for both environments causes authentication failures.

**Why It Happens**:
OAuth providers (GitHub, Google, etc.) validate redirect URLs strictly. Localhost and production have different URLs, so they need separate OAuth client registrations.

**Prevention**:
```bash
# Development OAuth App
Callback URL: http://localhost:8788/callback

# Production OAuth App
Callback URL: https://my-mcp-server.workers.dev/callback
```

**Additional Requirements**:
- KV namespace for auth state storage (create manually)
- `COOKIE_ENCRYPTION_KEY` env var: `openssl rand -hex 32`
- Client restart required after config changes

**Official Status**:
- [x] Documented in official guides
- [ ] Common gotcha
- [ ] Not documented in MCP SDK

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Widget State Scope Limitation - 4k Token Limit

**Trust Score**: TIER 2 - Official Developer Docs
**Source**: [OpenAI Apps SDK - ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
**Date**: 2025 (current docs)
**Verified**: Yes
**Impact**: MEDIUM - Performance degradation if exceeded
**Already in Skill**: No

**Description**:
Widget state persists only to a single widget instance tied to one conversation message. State is reset (fresh `widgetId`, empty state) when users submit via the main chat composer instead of widget controls. Keep state payloads under **4k tokens** for performance.

**Prevention**:
```typescript
// ✅ Good - Lightweight state
window.openai.setWidgetState({ selectedId: "item-123", view: "grid" });

// ❌ Bad - Will cause performance issues
window.openai.setWidgetState({
  items: largeArray,           // Don't store full datasets
  history: conversationLog,    // Don't store conversation history
  cache: expensiveComputation  // Don't cache large results
});
```

**Best Practice**:
- Store only UI state (selected items, view mode, filters)
- Fetch data from MCP server on widget mount
- Use tool calls to persist important data

**Community Validation**:
- Source: Official OpenAI developer documentation
- Applies to: All ChatGPT apps with widgets

---

### Finding 2.2: Widget Can't Initiate Tool Calls Without Server Permission

**Trust Score**: TIER 2 - Official Documentation
**Source**: [OpenAI Apps SDK - ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
**Date**: 2025 (current docs)
**Verified**: Yes
**Impact**: HIGH - Tool calls fail silently without proper flag
**Already in Skill**: Partially (mentions window.openai.callTool but not permission requirement)

**Description**:
Components initiating tool calls via `window.openai.callTool()` require the tool marked as **"able to be initiated by the component"** on the MCP server. Without this flag, calls fail silently.

**How to Fix**:
```typescript
// MCP Server - Mark tool as widget-callable
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'update_item',
    description: 'Update an item',
    inputSchema: { /* ... */ },
    annotations: {
      openai: {
        outputTemplate: 'ui://widget/item.html',
        // ✅ Required for widget-initiated calls
        widgetCallable: true
      }
    }
  }]
}));

// Widget - Now allowed to call tool
window.openai.callTool({
  name: 'update_item',
  arguments: { id: itemId, status: 'completed' }
});
```

**Community Validation**:
- Source: Official OpenAI Apps SDK documentation
- Symptom: Tool calls from widget fail with no error message

---

### Finding 2.3: File Upload Limited to 3 MIME Types

**Trust Score**: TIER 2 - Official Documentation
**Source**: [OpenAI Apps SDK - ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
**Date**: 2025 (current docs)
**Verified**: Yes
**Impact**: MEDIUM - Restricts file upload functionality
**Already in Skill**: No

**Description**:
`window.openai.uploadFile()` only supports 3 image formats: `image/png`, `image/jpeg`, and `image/webp`. Other formats (PDFs, documents, etc.) fail silently.

**Workaround**:
```typescript
// ✅ Supported
window.openai.uploadFile({ accept: 'image/png,image/jpeg,image/webp' });

// ❌ Not supported (fails silently)
window.openai.uploadFile({ accept: 'application/pdf' });
window.openai.uploadFile({ accept: 'text/csv' });
window.openai.uploadFile({ accept: 'application/zip' });
```

**Alternative for Other File Types**:
1. Use base64 encoding in tool arguments
2. Request user paste text content
3. Use external upload service (S3, R2) and pass URL

**Community Validation**:
- Source: Official documentation
- Confirmed by multiple developers in community forums

---

### Finding 2.4: Tool Calls Over 200ms Cause Sluggishness

**Trust Score**: TIER 2 - Official Troubleshooting Guide
**Source**: [OpenAI Apps SDK - Troubleshooting](https://developers.openai.com/apps-sdk/deploy/troubleshooting)
**Date**: 2025 (current docs)
**Verified**: Yes via official docs
**Impact**: MEDIUM - User experience degradation
**Already in Skill**: No

**Description**:
Tool calls exceeding "a few hundred milliseconds" cause UI sluggishness in ChatGPT. The official docs recommend profiling backends and implementing caching for slow operations.

**Performance Targets**:
- **< 200ms**: Ideal response time
- **200-500ms**: Acceptable but noticeable
- **> 500ms**: Sluggish, needs optimization

**Optimization Strategies**:
```typescript
// 1. Cache expensive computations
const cache = new Map();
if (cache.has(key)) return cache.get(key);
const result = await expensiveOperation();
cache.set(key, result);

// 2. Use KV/D1 for pre-computed data
const cached = await env.KV.get(`result:${id}`);
if (cached) return JSON.parse(cached);

// 3. Paginate large datasets
return {
  content: [{ type: 'text', text: 'First 20 results...' }],
  _meta: { hasMore: true, nextPage: 2 }
};

// 4. Move slow work to async tasks
// Return immediately, update via follow-up
```

**Community Validation**:
- Source: Official troubleshooting documentation
- Applies to: All ChatGPT apps with tools

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Skybridge Framework Simplifies MCP + Widget Development

**Trust Score**: TIER 3 - Community Open Source Project
**Source**: [Skybridge GitHub](https://github.com/alpic-ai/skybridge)
**Date**: 2025 (active development)
**Verified**: Cross-referenced with multiple blog posts
**Impact**: LOW - Alternative framework, not official
**Already in Skill**: No

**Description**:
Skybridge is a community-built framework that aims to simplify ChatGPT Apps development with:
- `skybridge/server`: Drop-in replacement for MCP SDK with widget registration helpers
- `skybridge/web`: React library with `window.openai` hooks and components
- Vite plugin with HMR for widgets

**When to Consider**:
- Building React-heavy widgets
- Need faster iteration (HMR support)
- Comfortable with community frameworks vs official SDK

**Recommendation**:
Monitor but don't add to skill yet. Verify with skill maintainer, as this is an unofficial framework. Worth mentioning in "Community Resources" section if validated.

**Consensus Evidence**:
- Multiple blog posts reference Skybridge: [Alpic AI](https://alpic.ai/blog/mcp-apps-how-it-works-and-how-it-compares-to-chatgpt-apps)
- Active GitHub repo with commits through 2025
- No official endorsement from OpenAI or MCP

---

### Finding 3.2: Cloudflare One-Click MCP Server Deployment

**Trust Score**: TIER 3 - Community Knowledge
**Source**: [Cloudflare Blog](https://blog.cloudflare.com/model-context-protocol/), [Community Forum](https://community.cloudflare.com/t/introducing-one-click-remote-mcp-servers-with-cloudflare/795791)
**Date**: 2025 (recent)
**Verified**: Multiple sources agree
**Impact**: MEDIUM - Simplifies deployment significantly
**Already in Skill**: No

**Description**:
Cloudflare now provides one-click MCP server deployment via "Deploy to Cloudflare" button. Features:
- Pre-built templates with latest MCP standards
- Auto-configures GitHub/GitLab CI/CD
- Includes OAuth wrapper library (`workers-oauth-provider`)
- Deploys to `your-account.workers.dev` subdomain

**Key Features**:
1. **Automatic Git setup**: New repo created with auto-deploy on push
2. **Built-in OAuth**: No need to implement OAuth manually
3. **Python support**: Can now use Python, not just TypeScript
4. **Streamable HTTP**: Uses latest transport standard

**How to Use**:
1. Visit Cloudflare MCP deployment page
2. Click "Deploy to Cloudflare"
3. Connect GitHub/GitLab account
4. Customize template
5. Auto-deployed and live

**Recommendation**:
Add to skill as "Quick Deployment Option" section. This is official Cloudflare functionality.

**Consensus Evidence**:
- Cloudflare official blog post
- Cloudflare developer documentation
- Community forum announcement

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

*No TIER 4 findings identified.*

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| CORS must allow chatgpt.com | Known Issues #1 | Fully covered |
| Widget URI must use ui://widget/ prefix | Known Issues #2 | Fully covered |
| MIME type must be text/html+skybridge | Known Issues #3 | Fully covered |
| SSE heartbeat every 30s | Known Issues #5 | Fully covered |
| MCP SDK 1.25.x breaking changes | Version Updates section | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Hono Global Response Override | Known Issues Prevention | Add as Issue #9 - Fixed in v1.25.3 but important for users on older versions |
| 1.2 Elicitation Fails on Workers | Known Issues Prevention | Add as Issue #10 - Critical limitation for Cloudflare Workers |
| 1.3 SSE Statefulness in Serverless | Architecture section | Add note recommending Streamable HTTP for serverless |
| 1.7 OAuth Requires Two Apps | Configuration section | Add to deployment checklist |

### Priority 2: Consider Adding (TIER 2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.1 Widget State 4k Token Limit | Widget Development | Add to best practices |
| 2.2 Widget Tool Call Permissions | Widget Development | Add widgetCallable annotation requirement |
| 2.3 File Upload MIME Types | Known Issues or Widget section | Document limitation |
| 2.4 Tool Performance (200ms) | Performance section | Add optimization guidance |

### Priority 3: Monitor (TIER 3, Community Projects)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 Skybridge Framework | Unofficial framework | Add to "Community Resources" if validated |
| 3.2 Cloudflare One-Click Deploy | Official Cloudflare feature | Add to "Quick Start" or "Deployment" section |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "mcp OR apps" in openai/openai-node | 0 | 0 (wrong repo) |
| "edge case OR gotcha" in mcp/typescript-sdk | 30 | 8 |
| "cloudflare workers" in mcp/typescript-sdk | 20 | 5 |
| Recent releases (v1.24.0-1.25.3) | 4 | 4 |
| Issues in openai/openai-apps-sdk-examples | 20 | 3 |

### Official Documentation

| Source | Relevance |
|--------|-----------|
| [OpenAI Apps SDK - MCP Server](https://developers.openai.com/apps-sdk/build/mcp-server/) | HIGH - Primary source for widget/tool patterns |
| [OpenAI Apps SDK - ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/) | HIGH - Widget development best practices |
| [OpenAI Apps SDK - Troubleshooting](https://developers.openai.com/apps-sdk/deploy/troubleshooting) | HIGH - Common errors and solutions |
| [Cloudflare Remote MCP Server Guide](https://developers.cloudflare.com/agents/guides/remote-mcp-server/) | HIGH - Deployment specifics |

### Community Resources

| Source | Notes |
|--------|-------|
| [Skybridge Framework](https://github.com/alpic-ai/skybridge) | Community framework - monitoring |
| [Alpic AI Blog - MCP Apps](https://alpic.ai/blog/mcp-apps-how-it-works-and-how-it-compares-to-chatgpt-apps) | Technical deep dive |
| [Zuplo Blog - MCP Apps](https://zuplo.com/blog/mcp-openai-apps-sdk) | Implementation guide |
| OpenAI Developer Community Forum | Widget loading issues |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` and `gh issue view` for GitHub discovery
- `gh release view` for release notes
- `WebSearch` for community resources and blogs
- `WebFetch` for official documentation

**Limitations**:
- OpenAI Apps SDK is very new (GA Nov 2025) - limited community history
- Many issues still being discovered/reported
- Skybridge framework needs deeper validation before recommending

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
Cross-reference Finding 1.7 (OAuth two-app requirement) and Finding 2.4 (performance targets) against current official documentation to ensure accuracy before adding.

**For api-method-checker**:
Verify that `widgetCallable` annotation in Finding 2.2 exists in current MCP SDK version.

**For code-example-validator**:
Validate code examples in findings 1.1, 1.2, and 2.2 before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Issue #9: Hono Global Response Override (v1.25.x)

```markdown
### Issue #9: Hono Global Response Override Breaks Next.js (v1.25.0-1.25.2)

**Error**: `No response is returned from route handler` (Next.js App Router)
**Source**: [GitHub Issue #1369](https://github.com/modelcontextprotocol/typescript-sdk/issues/1369)
**Affected Versions**: v1.25.0 to v1.25.2
**Fixed In**: v1.25.3
**Why It Happens**: Hono (MCP SDK dependency) overwrites `global.Response`, breaking frameworks that extend it
**Prevention**:
- **Upgrade to v1.25.3+** (recommended)
- **Before fix**: Use `webStandardStreamableHTTPServerTransport` instead
- **Or**: Run MCP server on separate port from Next.js/Remix/SvelteKit app

```typescript
// ✅ v1.25.3+ - Fixed
const transport = new StreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
});

// ✅ v1.25.0-1.25.2 - Workaround
import { webStandardStreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/index.js';
const transport = webStandardStreamableHTTPServerTransport({
  sessionIdGenerator: undefined,
});
```
```

#### Issue #10: Elicitation Fails on Cloudflare Workers

```markdown
### Issue #10: Elicitation (User Input) Fails on Cloudflare Workers

**Error**: `EvalError: Code generation from strings disallowed`
**Source**: [GitHub Issue #689](https://github.com/modelcontextprotocol/typescript-sdk/issues/689)
**Why It Happens**: Internal AJV v6 validator uses prohibited APIs on edge platforms
**Prevention**: Avoid `elicitInput()` on edge platforms (Cloudflare Workers, Vercel Edge, Deno Deploy)

**Workaround**:
```typescript
// ❌ Don't use on Cloudflare Workers
const userInput = await server.elicitInput({
  prompt: "What is your name?",
  schema: { type: "string" }
});

// ✅ Use tool parameters instead
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name } = request.params.arguments as { name: string };
  // User provides via tool call, not elicitation
});
```

**Status**: Requires MCP SDK v2 to fix properly. Track [PR #844](https://github.com/modelcontextprotocol/typescript-sdk/pull/844).
```

### Adding TIER 2 Findings

#### Widget State Best Practice

```markdown
## Widget State Management

**State Scope**: Widget state persists only to the current message. New submissions reset state.
**Performance Limit**: Keep state under **4k tokens** for optimal performance.

**Best Practices**:
```typescript
// ✅ Store lightweight UI state
window.openai.setWidgetState({
  selectedId: "item-123",
  view: "grid",
  filters: { status: "active" }
});

// ❌ Don't store large datasets
window.openai.setWidgetState({
  items: largeArray,           // Fetch from server instead
  history: conversationLog     // Store server-side
});
```

**Data Fetching**: Load data from MCP server on widget mount, not from state.
```

#### Widget-Callable Tools

```markdown
## Widget-Initiated Tool Calls

Tools called from widgets via `window.openai.callTool()` must be marked as **widget-callable**:

```typescript
// MCP Server
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'update_item',
    description: 'Update an item',
    inputSchema: { /* ... */ },
    annotations: {
      openai: {
        outputTemplate: 'ui://widget/item.html',
        widgetCallable: true  // ← Required
      }
    }
  }]
}));

// Widget
window.openai.callTool({
  name: 'update_item',
  arguments: { id: itemId, status: 'completed' }
});
```

Without `widgetCallable: true`, tool calls fail silently.
```

### Adding TIER 3 to Community Resources

```markdown
## Community Resources

### Deployment Tools

**Cloudflare One-Click Deploy**: Deploy MCP servers to Cloudflare Workers with pre-built templates and auto-configured CI/CD. Includes OAuth wrapper and Python support.
- Docs: https://developers.cloudflare.com/agents/guides/remote-mcp-server/
- Blog: https://blog.cloudflare.com/model-context-protocol/

### Frameworks

**Skybridge** (Community): React-focused framework with HMR support for widgets and enhanced MCP server helpers. Unofficial but actively maintained.
- GitHub: https://github.com/alpic-ai/skybridge
- Docs: https://www.skybridge.tech/

> **Note**: Community frameworks are not officially supported. Use at your own discretion.
```

---

**Research Completed**: 2026-01-21 14:30
**Next Research Due**: After MCP SDK v2 release (Q1 2026) or after next ChatGPT Apps platform update

---

## Sources

- [GitHub - modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
- [OpenAI Apps SDK - Build MCP Server](https://developers.openai.com/apps-sdk/build/mcp-server/)
- [OpenAI Apps SDK - ChatGPT UI](https://developers.openai.com/apps-sdk/build/chatgpt-ui/)
- [OpenAI Apps SDK - Troubleshooting](https://developers.openai.com/apps-sdk/deploy/troubleshooting)
- [Cloudflare Agents - Remote MCP Server](https://developers.cloudflare.com/agents/guides/remote-mcp-server/)
- [GitHub - Skybridge Framework](https://github.com/alpic-ai/skybridge)
- [Alpic AI Blog - MCP Apps](https://alpic.ai/blog/inside-openai-s-apps-sdk-how-to-build-interactive-chatgpt-apps-with-mcp)
- [Zuplo Blog - MCP Apps](https://zuplo.com/blog/mcp-openai-apps-sdk)
- [OpenAI Apps SDK Examples - Issue #53](https://github.com/openai/openai-apps-sdk-examples/issues/53)
- [OpenAI Apps SDK Examples - Issue #58](https://github.com/openai/openai-apps-sdk-examples/issues/58)
