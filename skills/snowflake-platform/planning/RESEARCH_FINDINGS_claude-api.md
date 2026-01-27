# Community Knowledge Research: claude-api

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/claude-api/SKILL.md
**Packages Researched**: @anthropic-ai/sdk@0.71.2
**Official Repo**: anthropics/anthropic-sdk-typescript
**Time Window**: May 2025 - January 2026 (post-training-cutoff focus)

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
| Recommended to Add | 9 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Stream Errors Not Catchable (Fixed in v0.71.2)

**Trust Score**: TIER 1 - Official SDK Fix
**Source**: [GitHub Issue #856](https://github.com/anthropics/anthropic-sdk-typescript/issues/856) | [Release v0.71.2](https://github.com/anthropics/anthropic-sdk-typescript/releases/tag/sdk-v0.71.2)
**Date**: 2025-12-05
**Verified**: Yes - Fixed in SDK
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Prior to SDK v0.71.2, errors thrown during streaming with `.withResponse()` were uncatchable, leading to unhandled promise rejections. The SDK had internal error handling that prevented user code from catching stream errors when using `messages.stream().withResponse()`.

**Reproduction** (pre-v0.71.2):
```typescript
// This would throw uncatchable error
try {
  const stream = anthropic.messages.stream({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 1024,
    messages: [{ role: 'user', content: 'Hello' }]
  }).withResponse();

  await stream;
} catch (error) {
  // This catch block was never reached!
  console.error('This error handler was not called:', error);
}
```

**Solution/Workaround**:
Upgrade to v0.71.2+. For older versions, avoid using `.withResponse()` and use event listeners instead:

```typescript
// Workaround for pre-v0.71.2
const stream = anthropic.messages.stream({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello' }]
});

stream.on('error', (error) => {
  console.error('Stream error:', error);
});
```

**Official Status**:
- [x] Fixed in version 0.71.2
- [x] Documented in changelog

**Cross-Reference**:
- Related to skill section "Streaming Responses (SSE)" but error catchability not mentioned

---

### Finding 1.2: MCP Tool Connections Cause 2-Minute Timeout for Long Requests

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #842](https://github.com/anthropics/anthropic-sdk-typescript/issues/842)
**Date**: 2025-11-11 (ongoing)
**Verified**: Yes - Multiple users confirm
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using MCP (Model Context Protocol) tools with the Claude API, requests consistently fail after ~121 seconds (2 minutes) even if the AI is not actively calling MCP tools. The connection appears to timeout due to MCP server connection management, even though the API should support up to 10 minutes for long-running requests. Dashboard shows error code 499: "Client disconnected".

**Reproduction**:
```typescript
// With MCP server registered
const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  messages: [{ role: 'user', content: 'Long complex task requiring >2 minutes' }],
  // MCP tools configured (even if not used in this request)
  tools: [mcpTools]
});
// Fails at ~121 seconds with "Connection error"
```

**Solution/Workaround**:
1. Remove MCP integration and use direct `toolRunner` with custom functions
2. Ensure MCP server has proper timeout configuration (not confirmed fix)
3. For streaming: Implement proper error handling as errors won't be surfaced

```typescript
// Workaround: Use toolRunner instead of MCP
const message = await anthropic.beta.messages.toolRunner({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  messages: [{ role: 'user', content: 'Long task' }],
  tools: [customTools] // Direct tool definitions, not MCP
});
```

**Official Status**:
- [ ] Known issue, no fix announced
- [ ] Workaround: Don't use MCP for long requests
- [ ] Investigation ongoing

**Cross-Reference**:
- Multiple users confirmed: gustavosizilio, robBowes, xpluscal, jacobweiss2305, dulacp
- Affects both streaming and non-streaming
- Error more severe with 2+ parallel tool calls

---

### Finding 1.3: Structured Outputs Performance Characteristics

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | [Anthropic Blog](https://claude.com/blog/structured-outputs-on-the-claude-developer-platform)
**Date**: 2025-11-14
**Verified**: Yes - Official feature
**Impact**: MEDIUM
**Already in Skill**: Partially (limitations documented, not performance)

**Description**:
Structured outputs use constrained sampling with compiled grammar artifacts. The first request with a specific schema has additional latency while the grammar is compiled (cached for 24 hours). This is not mentioned in the skill despite being a critical performance consideration.

**Performance Impact**:
- First request: +200-500ms latency for grammar compilation
- Subsequent requests (24hr): Normal latency (grammar cached)
- Cache shared only with IDENTICAL schema (small changes = recompilation)

**Solution/Workaround**:
```typescript
// Pre-warm schema compilation during startup for critical paths
const warmupMessage = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 10,
  messages: [{ role: 'user', content: 'warmup' }],
  betas: ['structured-outputs-2025-11-13'],
  output_format: {
    type: 'json_schema',
    json_schema: YOUR_CRITICAL_SCHEMA // Pre-compile on server start
  }
});

// Later requests use cached grammar
```

**Official Status**:
- [x] Documented behavior
- [x] Grammar cache: 24 hours
- [x] Schema must be identical for cache hit

**Cross-Reference**:
- Skill mentions limitations but not performance characteristics
- Should add "Performance Considerations" section

---

### Finding 1.4: Structured Outputs Accuracy Caveat

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Structured Outputs Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
**Date**: 2025-11-14
**Verified**: Yes
**Impact**: HIGH (expectations management)
**Already in Skill**: No

**Description**:
Anthropic explicitly states that structured outputs guarantee format compliance, NOT accuracy. Models can still hallucinate—you get "perfectly formatted incorrect answers." This critical caveat is missing from the skill.

**Example**:
```typescript
// Schema guarantees THIS structure
const schema = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    email: { type: 'string' },
    age: { type: 'number' }
  }
};

// But you might get:
{
  name: "John Doe",
  email: "fake@example.com", // Hallucinated email
  age: 42 // Hallucinated age
}
// Format is valid, content is wrong!
```

**Solution/Workaround**:
Always validate semantic correctness, not just format:

```typescript
const message = await anthropic.messages.create({
  /* structured output config */
});

const data = JSON.parse(message.content[0].text);

// CRITICAL: Validate semantic correctness
if (!isValidEmail(data.email)) {
  throw new Error('Hallucinated email detected');
}
if (data.age < 0 || data.age > 120) {
  throw new Error('Implausible age value');
}
```

**Official Status**:
- [x] Documented caveat in official docs
- [x] Working as intended

---

### Finding 1.5: Haiku 4.5 Prompt Caching Minimum Tokens

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Prompt Caching Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
**Date**: 2025-08-13+
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (documented as 2,048 tokens)

**Description**:
Claude Haiku 4.5 requires 2,048 tokens minimum for prompt caching (double the 1,024 minimum for other models). This is already correctly documented in the skill.

**Official Status**:
- [x] Documented in skill

---

### Finding 1.6: AWS Bedrock Prompt Caching Not Working for Claude 4 Family

**Trust Score**: TIER 1 - GitHub Issue (Bedrock-specific)
**Source**: [GitHub Issue #1347](https://github.com/anthropics/claude-code/issues/1347)
**Date**: 2025-05-XX
**Verified**: Yes - AWS Bedrock limitation
**Impact**: HIGH (for Bedrock users)
**Already in Skill**: No

**Description**:
On AWS Bedrock, prompt caching works for Claude 3.7 Sonnet but NOT for Claude 4 family (Opus 4, Sonnet 4.5). All cache reads/writes show 0, making Claude 4 "completely unusable for coding" on Bedrock due to high costs and latency.

**Reproduction** (AWS Bedrock only):
```typescript
// Works on Claude 3.7 Sonnet
const message37 = await client.messages.create({
  model: 'anthropic.claude-3-7-sonnet',
  system: [{
    type: 'text',
    text: LARGE_CODEBASE,
    cache_control: { type: 'ephemeral' }
  }],
  messages: [...]
});
// Shows cache_read_input_tokens > 0

// Fails on Claude 4 family
const message4 = await client.messages.create({
  model: 'anthropic.claude-sonnet-4-5',
  system: [{
    type: 'text',
    text: LARGE_CODEBASE,
    cache_control: { type: 'ephemeral' }
  }],
  messages: [...]
});
// Always shows cache_read_input_tokens: 0
```

**Solution/Workaround**:
Use direct Anthropic API instead of AWS Bedrock for Claude 4 family with prompt caching.

**Official Status**:
- [ ] AWS Bedrock platform limitation
- [ ] No fix announced
- [ ] Workaround: Use native API

---

### Finding 1.7: `.parsed` Property Deprecation (v0.71.1)

**Trust Score**: TIER 1 - Official SDK Change
**Source**: [Release v0.71.1](https://github.com/anthropics/anthropic-sdk-typescript/releases/tag/sdk-v0.71.1)
**Date**: 2025-12-04
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
SDK v0.71.1 added deprecation warnings for accessing `.parsed` property on structured outputs. The property naming was corrected, and direct access now triggers warnings.

**Changes**:
- Bug fix: Use correct naming for parsed text blocks
- `.parsed` property made non-enumerable
- Deprecation warnings added for `.parsed` access

**Solution/Workaround**:
Update code to avoid direct `.parsed` access (check SDK docs for new API).

**Official Status**:
- [x] Deprecated in v0.71.1
- [x] Migration path in release notes

---

### Finding 1.8: Claude Opus 4.5 Release (v0.71.0)

**Trust Score**: TIER 1 - Official Release
**Source**: [Release v0.71.0](https://github.com/anthropics/anthropic-sdk-typescript/releases/tag/sdk-v0.71.0)
**Date**: 2025-11-24
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (updated 2026-01-18)

**Description**:
Claude Opus 4.5 (`claude-opus-4-5-20251101`) was released with advanced capabilities. The skill has been updated to reflect this.

**Official Status**:
- [x] Documented in skill

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Web Search Tool Content Block Index Reuse (Streaming)

**Trust Score**: TIER 2 - GitHub Issue (Not Confirmed by Maintainers)
**Source**: [GitHub Issue #879](https://github.com/anthropics/anthropic-sdk-typescript/issues/879)
**Date**: 2026-01-14
**Verified**: Partial - User report only
**Impact**: HIGH (if confirmed)
**Already in Skill**: No

**Description**:
When using the web_search tool with streaming, `content_block_start` events reuse indices after `web_search_tool_results` blocks are returned. This causes index mismatches and "text part X not found" errors.

**Reproduction**:
```typescript
// Using web_search_20250305 with streamText
const stream = anthropic.messages.stream({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  tools: [{ name: 'web_search', /* ... */ }],
  messages: [{ role: 'user', content: 'Search for X' }]
});

stream.on('content_block_start', (event) => {
  // Index might be reused after web_search_tool_results
  console.log('Block index:', event.index); // May duplicate!
});
```

**Community Validation**:
- GitHub issue open
- Related to issue #880 (web search with streamText errors)
- No maintainer response yet

**Recommendation**: Monitor issue for official response. Flag as known limitation if confirmed.

---

### Finding 2.2: U+2028 LINE SEPARATOR in MCP Tool Results Causes JSON Parsing Failures

**Trust Score**: TIER 2 - GitHub Issue (Recent)
**Source**: [GitHub Issue #882](https://github.com/anthropics/anthropic-sdk-typescript/issues/882)
**Date**: 2026-01-18
**Verified**: Partial - User report
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When MCP tool results contain Unicode line separator character (U+2028), JSON parsing fails because U+2028 is valid in JSON but not in JavaScript string literals. This causes silent failures or parse errors.

**Reproduction**:
```typescript
const toolResult = {
  type: 'tool_result',
  tool_use_id: 'toolu_123',
  content: 'Text with\u2028line separator' // U+2028 character
};

// This may fail when processed by SDK
messages.push({
  role: 'user',
  content: [toolResult]
});
```

**Solution/Workaround**:
Sanitize tool results before passing to SDK:

```typescript
function sanitizeToolResult(content: string): string {
  return content
    .replace(/\u2028/g, '\n') // LINE SEPARATOR to newline
    .replace(/\u2029/g, '\n'); // PARAGRAPH SEPARATOR to newline
}

const toolResult = {
  type: 'tool_result',
  tool_use_id: block.id,
  content: sanitizeToolResult(result)
};
```

**Community Validation**:
- Issue open
- No maintainer response yet
- Known JavaScript/JSON edge case

**Recommendation**: Add to "Tool Use" section with sanitization example.

---

### Finding 2.3: Streaming Idle Timeout Proposal

**Trust Score**: TIER 2 - GitHub Issue Discussion
**Source**: [GitHub Issue #867](https://github.com/anthropics/anthropic-sdk-typescript/issues/867)
**Date**: 2025-12-19
**Verified**: Partial - Community proposal
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Proposal for adding configurable streaming idle timeout to prevent indefinite hangs when streams stall without completing. Currently, streams can hang indefinitely if the connection doesn't fully close but stops sending data.

**Proposed Solution**:
```typescript
const stream = anthropic.messages.stream({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello' }],
  // Proposed option
  streamingIdleTimeout: 30000 // 30 seconds
});
```

**Community Validation**:
- Open discussion
- No official response
- Community workaround: Implement timeout wrapper

**Recommendation**: Monitor for official implementation. Document workaround if becomes common issue.

---

### Finding 2.4: Vercel AI SDK + Anthropic Provider PDF URL Issue

**Trust Score**: TIER 2 - GitHub Issue (External Library)
**Source**: [GitHub Issue #11685](https://github.com/vercel/ai/issues/11685)
**Date**: 2026-01-XX
**Verified**: Yes - Vercel AI SDK issue
**Impact**: LOW (Vercel AI SDK specific)
**Already in Skill**: No

**Description**:
When using the Anthropic provider with Vercel AI SDK, PDF URLs are unnecessarily downloaded because the provider's `supportedUrls` config only includes `image/*` patterns, missing `application/pdf`. Anthropic's API natively supports PDF URLs via `type: "document"`.

**Workaround**:
```typescript
// Vercel AI SDK usage
import { anthropic } from '@ai-sdk/anthropic';

const result = await generateText({
  model: anthropic('claude-sonnet-4-5-20250929'),
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: 'Analyze this PDF' },
      { type: 'file', url: 'https://example.com/doc.pdf' }
    ]
  }],
  experimental_download: async (downloads) => downloads.map(() => null)
});
```

**Community Validation**:
- Reported in Vercel AI SDK repo
- Affects Anthropic provider specifically
- Workaround confirmed

**Recommendation**: Not relevant to claude-api skill (Vercel AI SDK specific). Skip.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Extended Thinking Token Consumption

**Trust Score**: TIER 3 - Best Practices Documentation
**Source**: Multiple blog posts and guides
**Date**: 2025-2026
**Verified**: Cross-referenced
**Impact**: MEDIUM (cost optimization)
**Already in Skill**: Mentioned but could expand

**Description**:
Multiple community sources emphasize that extended thinking mode significantly increases token costs because thinking tokens are billed. The skill mentions this but could provide more specific guidance on when to use it selectively.

**Consensus Evidence**:
- [Claude API Guide 2025](https://www.spurnor.com/en/blogs/claude-api-guide): "turn it on selectively"
- [Collabnix Guide](https://collabnix.com/claude-api-integration-guide-2025): "you pay for extra thinking tokens"
- Official docs confirm billing

**Recommendation**: Already covered in skill. Consider adding cost comparison example.

---

### Finding 3.2: System Prompt Verbosity Affects Costs

**Trust Score**: TIER 3 - Best Practices Consensus
**Source**: Multiple community guides
**Date**: 2025-2026
**Verified**: Common knowledge
**Impact**: LOW (optimization tip)
**Already in Skill**: No

**Description**:
Overly detailed system prompts or repetitive instructions cause longer outputs and higher token costs. Community consensus recommends brief, precise prompts.

**Best Practice**:
```typescript
// Verbose (higher cost)
const message = await anthropic.messages.create({
  system: 'You are a helpful assistant. Always be polite. Always format...',
  // 200+ token system prompt

// Concise (lower cost)
const message = await anthropic.messages.create({
  system: 'Respond concisely and format as JSON.',
  // 10 token system prompt
```

**Consensus Evidence**:
- Multiple guides mention this
- General best practice, not Claude-specific

**Recommendation**: Add to "Best Practices" or "Cost Optimization" section.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Databricks Prompt Caching Not Supported

**Trust Score**: TIER 4 - Platform-Specific Limitation
**Source**: [Databricks Community Post](https://community.databricks.com/t5/generative-ai/how-to-implement-prompt-caching-using-claude-models/td-p/129766)
**Date**: 2025
**Verified**: Databricks-specific
**Impact**: N/A (not relevant to claude-api skill)

**Why Flagged**:
- [x] Platform-specific (Databricks)
- [x] Not relevant to direct API usage

**Recommendation**: Skip. Not relevant to @anthropic-ai/sdk users.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Claude 4 model support | Active Models table | Fully covered |
| Prompt caching minimum tokens | Prompt Caching section | Fully covered (1,024 for Sonnet, 2,048 for Haiku) |
| Structured outputs beta | What's New section | Fully covered |
| Extended thinking compatibility | Extended Thinking Mode | Fully covered |
| Streaming error handling | Streaming Responses | Partially covered (pre-v0.71.2 issue missing) |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Stream errors not catchable | Known Issues Prevention | Add as Issue #13 with version note (fixed in 0.71.2) |
| 1.2 MCP 2-minute timeout | Known Issues Prevention | Add as Issue #14 with workaround |
| 1.3 Structured outputs performance | Structured Outputs section | Add "Performance Characteristics" subsection |
| 1.4 Structured outputs accuracy caveat | Structured Outputs section | Add prominent warning about hallucinations |
| 1.6 AWS Bedrock caching limitation | Prompt Caching section | Add platform-specific note |
| 1.7 `.parsed` deprecation | Structured Outputs section | Add migration note |

### Priority 2: Consider Adding (TIER 2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.2 U+2028 character issue | Tool Use section | Add sanitization example |
| 2.1 Web search index reuse | Monitor issue | Add if confirmed by maintainers |

### Priority 3: Monitor (Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 2.3 Streaming idle timeout | Proposal only | Wait for official implementation |
| 2.1 Web search streaming bug | No maintainer confirmation | Wait for official response |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Recent issues (post-May 2025) | 30 | 12 |
| "bug" label closed | 20 | 3 |
| Release notes v0.69.0-v0.71.2 | 4 releases | 8 findings |
| CHANGELOG.md | 300+ lines | 6 findings |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "claude api" best practices 2025 | 10 | 4 high-quality guides |
| Structured outputs edge cases | 8 | 2 official + 2 community |
| Prompt caching not working | 7 | 2 platform-specific issues |

### Other Sources

| Source | Notes |
|--------|-------|
| [Official Docs](https://platform.claude.com/docs) | Primary reference for verification |
| [Anthropic Blog](https://claude.com/blog) | Structured outputs announcement |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh release list` for recent releases
- `gh issue view` for detailed issue content
- `WebSearch` for community guides and Stack Overflow

**Limitations**:
- Stack Overflow had no results for "claude api edge case gotcha" (niche topic)
- Some GitHub issues lack maintainer responses (flagged as TIER 2)
- MCP-specific issues may evolve rapidly

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference finding 1.3 (structured outputs performance) against current official documentation
- Verify finding 1.4 (accuracy caveat) is prominently stated in official docs

**For api-method-checker**:
- Verify the workaround in finding 1.2 (toolRunner vs MCP) uses currently available APIs
- Check if `.parsed` deprecation (1.7) has replacement API

**For code-example-validator**:
- Validate code examples in findings 1.1, 2.2 before adding to skill
- Test MCP workaround (finding 1.2) if possible

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### Issue #13: Stream Errors Not Catchable (Pre-v0.71.2)

```markdown
### Issue #13: Stream Errors Not Catchable with .withResponse() (Fixed in v0.71.2)

**Error**: Unhandled promise rejection when using `messages.stream().withResponse()`
**Source**: https://github.com/anthropics/anthropic-sdk-typescript/issues/856
**Why It Happens**: SDK internal error handling prevented user catch blocks from working
**Prevention**: Upgrade to v0.71.2 or use event listeners instead

**Fixed in v0.71.2+**:
```typescript
try {
  const stream = await anthropic.messages.stream({
    model: 'claude-sonnet-4-5-20250929',
    max_tokens: 1024,
    messages: [{ role: 'user', content: 'Hello' }]
  }).withResponse();
} catch (error) {
  // Now properly catchable in v0.71.2+
  console.error('Stream error:', error);
}
```

**Workaround for pre-v0.71.2**:
```typescript
const stream = anthropic.messages.stream({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 1024,
  messages: [{ role: 'user', content: 'Hello' }]
});

stream.on('error', (error) => {
  console.error('Stream error:', error);
});
```
```

#### Issue #14: MCP Tools Cause 2-Minute Timeout for Long Requests

```markdown
### Issue #14: MCP Tool Connections Cause 2-Minute Timeout

**Error**: `Connection error` / `499 Client disconnected` after ~121 seconds
**Source**: https://github.com/anthropics/anthropic-sdk-typescript/issues/842
**Why It Happens**: MCP server connection management conflicts with long-running requests, even when MCP tools are not actively used
**Prevention**: Use direct toolRunner instead of MCP for requests >2 minutes

**Symptoms**:
- Request works fine without MCP
- Fails at exactly ~121 seconds with MCP registered
- Dashboard shows: "Client disconnected (code 499)"
- Multiple users confirmed across streaming and non-streaming

**Workaround**:
```typescript
// Don't use MCP for long requests
const message = await anthropic.beta.messages.toolRunner({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  messages: [{ role: 'user', content: 'Long task >2 min' }],
  tools: [customTools] // Direct tool definitions, not MCP
});
```

**Note**: This is a known limitation with no official fix. Consider architecture changes if long-running requests with tools are required.
```

#### Structured Outputs Performance Section

```markdown
## Structured Outputs (v0.69.0, Nov 14, 2025) - CRITICAL ⭐

**Guaranteed JSON schema conformance** - Claude's responses strictly follow your JSON schema with two modes:

[... existing content ...]

### Performance Characteristics

**First Request Latency**: The first time you use a specific schema, there will be +200-500ms additional latency while the grammar is compiled. This grammar artifact is cached for 24 hours.

**Cache Behavior**:
- Grammar is cached for 24 hours
- Cache is shared ONLY with IDENTICAL schemas
- Small schema changes = recompilation required

**Pre-warming Critical Schemas**:
```typescript
// Pre-compile schemas during server startup
const warmupMessage = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 10,
  messages: [{ role: 'user', content: 'warmup' }],
  betas: ['structured-outputs-2025-11-13'],
  output_format: {
    type: 'json_schema',
    json_schema: YOUR_CRITICAL_SCHEMA
  }
});

// Later requests use cached grammar (no extra latency)
```

### Accuracy Caveat ⚠️

**CRITICAL**: Structured outputs guarantee format compliance, NOT accuracy. Models can still hallucinate—you get "perfectly formatted incorrect answers."

```typescript
// Schema guarantees format but not accuracy
const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  messages: [{ role: 'user', content: 'Extract contact info: John Doe' }],
  betas: ['structured-outputs-2025-11-13'],
  output_format: {
    type: 'json_schema',
    json_schema: contactSchema
  }
});

const contact = JSON.parse(message.content[0].text);

// ✅ Format is guaranteed valid
// ❌ Content may be hallucinated

// ALWAYS validate semantic correctness
if (!isValidEmail(contact.email)) {
  throw new Error('Hallucinated email detected');
}
if (contact.age < 0 || contact.age > 120) {
  throw new Error('Implausible age value');
}
```
```

---

**Research Completed**: 2026-01-20 15:30
**Next Research Due**: After next major SDK release (v0.72.0+) or March 2026

**Sources**:

- [Streaming Messages - Claude Docs](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Errors - Claude Docs](https://platform.claude.com/docs/en/api/errors)
- [Structured outputs - Claude Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Prompt caching - Claude Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Claude API Guide: Build AI Agents & Chatbots (2025)](https://www.spurnow.com/en/blogs/claude-api-guide)
- [Claude API Integration Guide 2025 - Collabnix](https://collabnix.com/claude-api-integration-guide-2025-complete-developer-tutorial-with-code-examples/)
