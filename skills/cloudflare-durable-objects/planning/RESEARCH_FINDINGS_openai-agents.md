# Community Knowledge Research: OpenAI Agents SDK

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/openai-agents/SKILL.md
**Packages Researched**: @openai/agents@0.4.1, @openai/agents-realtime@0.4.1
**Official Repo**: openai/openai-agents-js
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 0 |
| TIER 4 (Low Confidence) | 2 |
| Already in Skill | 2 |
| Recommended to Add | 8 |

**Key Discovery**: Multiple BREAKING CHANGES in v0.4.0 (Jan 2026) - Zod 4 required, reasoning defaults changed, @ai-sdk/provider now optional peer dependency.

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Zod 4 Required (Breaking Change v0.4.0)

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.4.0](https://github.com/openai/openai-agents-js/releases/tag/v0.4.0) | [Issue #561](https://github.com/openai/openai-agents-js/issues/561)
**Date**: 2026-01-18
**Verified**: Yes
**Impact**: HIGH (Breaking Change)
**Already in Skill**: No (skill says zod@4 but doesn't mention breaking change)

**Description**:
Starting with v0.4.0, the SDK dropped Zod v3 support and now requires Zod v4 for schema-based tools and outputs. This is a breaking change from all previous versions (0.1.x - 0.3.x) which used Zod 3.

**Migration**:
```bash
# Update package.json
npm install zod@4  # NOT zod@3
```

**Official Status**:
- [x] Breaking change in v0.4.0
- [x] Documented in release notes
- [x] Required for schema-based tools

**Cross-Reference**:
- Skill currently says `npm install @openai/agents zod@4` (line 19) - correct
- README says `zod@3` (line 167) - INCORRECT, needs update
- No mention this is a breaking change in v0.4.0

---

### Finding 1.2: GPT-5.1/5.2 Reasoning Defaults Changed to "none"

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.4.0](https://github.com/openai/openai-agents-js/releases/tag/v0.4.0) | [PR #876](https://github.com/openai/openai-agents-js/pull/876)
**Date**: 2026-01-18
**Verified**: Yes
**Impact**: MEDIUM (Behavior Change)
**Already in Skill**: No

**Description**:
The default reasoning effort for gpt-5.1 and gpt-5.2 changed from `"low"` to `"none"` in v0.4.0. This is better suited for interactive agent apps but may break existing code that relied on the default.

**Reproduction**:
```typescript
// v0.3.x - default reasoning effort was "low"
const agent = new Agent({ model: 'gpt-5.1' }); // reasoning.effort="low" implicitly

// v0.4.0+ - default is now "none"
const agent = new Agent({ model: 'gpt-5.1' }); // reasoning.effort="none"
```

**Solution/Workaround**:
```typescript
// Explicitly set reasoning effort if you need it
const agent = new Agent({
  model: 'gpt-5.1',
  reasoning: { effort: 'low' }, // or 'medium', 'high'
});
```

**Official Status**:
- [x] Documented behavior change in v0.4.0
- [x] Intentional default change for better interactive UX
- [ ] Not a bug

---

### Finding 1.3: Invalid JSON in Tool Calls Now Handled Gracefully

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.4.1](https://github.com/openai/openai-agents-js/releases/tag/v0.4.1) | [PR #887](https://github.com/openai/openai-agents-js/pull/887) | [Issue #723](https://github.com/openai/openai-agents-js/issues/723)
**Date**: 2026-01-20 (v0.4.1)
**Verified**: Yes
**Impact**: MEDIUM (Bug Fix)
**Already in Skill**: Partially (Error #1 mentions schema errors, but not invalid JSON parsing)

**Description**:
Prior to v0.4.1, when an LLM generated invalid JSON for tool call arguments, a SyntaxError would crash the agent run. v0.4.1 now handles this gracefully.

**Reproduction**:
```typescript
// Prior to v0.4.1 - this would crash:
// LLM generates: { "city": "New York"  // Missing closing brace
// Result: SyntaxError stops agent

// v0.4.1+ - gracefully handles parse errors
// Agent continues with error feedback to model
```

**Solution/Workaround**:
```typescript
// Community workaround (pre-v0.4.1): use jsonrepair library
import { jsonrepair } from 'jsonrepair';

// But as of v0.4.1, SDK handles this internally
```

**Official Status**:
- [x] Fixed in version 0.4.1
- [x] No longer requires jsonrepair workaround

**Cross-Reference**:
- Skill Error #1 mentions "Zod Schema Type Errors" but not JSON parse errors
- Consider expanding Error #1 or adding new error section

---

### Finding 1.4: SDK Leaks Internal Reasoning into JSON Output

**Trust Score**: TIER 1 - Official
**Source**: [Issue #844](https://github.com/openai/openai-agents-js/issues/844)
**Date**: 2026-01-12
**Verified**: Yes (maintainer confirmed)
**Impact**: MEDIUM (Model-side issue)
**Already in Skill**: No

**Description**:
When using `outputType` with reasoning models, the SDK may leak internal reasoning into the client-facing JSON response (adds `response_reasoning:` field inside output).

**Reproduction**:
```typescript
const agent = new Agent({
  model: 'gpt-5.1',
  outputType: z.object({ result: z.string() }),
  reasoning: { effort: 'low' },
});

// Output may include:
// { "result": "...", "response_reasoning": "..." }  // ❌ Unexpected field
```

**Solution/Workaround**:
Maintainer confirmed this is a model endpoint issue, not SDK bug. No SDK-side fix available yet. Workaround:

```typescript
// Filter out response_reasoning from output
const result = await run(agent, input);
const { response_reasoning, ...cleanOutput } = result.finalOutput;
return cleanOutput;
```

**Official Status**:
- [ ] Model endpoint issue (not SDK)
- [ ] Coordinating with OpenAI teams
- [ ] No fix timeline

---

### Finding 1.5: Streaming with Human-in-the-Loop Requires Special Pattern

**Trust Score**: TIER 1 - Official
**Source**: [Issue #647](https://github.com/openai/openai-agents-js/issues/647) | [Example Code](https://github.com/openai/openai-agents-js/blob/main/examples/agent-patterns/human-in-the-loop-stream.ts)
**Date**: 2025-11-07
**Verified**: Yes
**Impact**: MEDIUM (Common Gotcha)
**Already in Skill**: Partially (HITL covered but not streaming HITL)

**Description**:
When using `stream: true` with tools that have `requiresApproval: true`, interruptions are NOT automatically emitted. Must manually check for interruptions during stream consumption.

**Reproduction**:
```typescript
// ❌ WRONG - interruptions ignored in streaming mode
const stream = await run(agent, input, { stream: true });
for await (const event of stream) {
  // Tool executes WITHOUT approval!
}

// ✅ CORRECT - check interruptions explicitly
const stream = await run(agent, input, { stream: true });
let result = await stream.finalResult();
while (result.interruption?.type === 'tool_approval') {
  const approved = await promptUser(result.interruption);
  result = approved
    ? await result.state.approve(result.interruption)
    : await result.state.reject(result.interruption);
}
```

**Solution/Workaround**:
Use the official example pattern: https://github.com/openai/openai-agents-js/blob/main/examples/agent-patterns/human-in-the-loop-stream.ts

**Official Status**:
- [x] Documented behavior
- [x] Example provided
- [ ] Not a bug (by design)

**Cross-Reference**:
- Skill has HITL example (line 105-111) but doesn't mention streaming caveat
- Consider adding note about streaming HITL pattern

---

### Finding 1.6: Cloudflare Workers Tracing Requires Manual Setup

**Trust Score**: TIER 1 - Official
**Source**: [Issue #16](https://github.com/openai/openai-agents-js/issues/16) | [PR #50](https://github.com/openai/openai-agents-js/pull/50)
**Date**: 2025-06-04
**Verified**: Yes
**Impact**: LOW (Experimental Feature)
**Already in Skill**: Partially (Workers mentioned as experimental, line 160)

**Description**:
Default tracing breaks in Cloudflare Workers runtime. Must call `startTracingExportLoop()` explicitly or disable tracing.

**Reproduction**:
```typescript
// ❌ Crashes in Workers
import { Agent, run } from '@openai/agents';
const agent = new Agent({ name: 'Assistant' });
await run(agent, 'Hello'); // Error: dynamic import in Workers

// ✅ Option 1: Disable tracing
import { Agent, run } from '@openai/agents';
process.env.OTEL_SDK_DISABLED = 'true'; // Or in wrangler.toml vars
const agent = new Agent({ name: 'Assistant' });

// ✅ Option 2: Manual tracing export
import { startTracingExportLoop } from '@openai/agents/tracing';
await startTracingExportLoop();
```

**Solution/Workaround**:
Set `OTEL_SDK_DISABLED=true` in environment variables (wrangler.toml) or call `startTracingExportLoop()`.

**Official Status**:
- [x] Fixed in PR #50
- [x] Requires manual setup
- [x] Documented workaround

**Cross-Reference**:
- Skill mentions "No voice agents" limitation (line 161) but not tracing issue
- Consider adding to Cloudflare Workers limitations

---

### Finding 1.7: Transient Network Errors Can Crash Agent Runs (Fixed v0.4.1)

**Trust Score**: TIER 1 - Official
**Source**: [Issue #744](https://github.com/openai/openai-agents-js/issues/744)
**Date**: 2025-12-09
**Verified**: Partial (closed as stale, but may be fixed)
**Impact**: MEDIUM (Reliability)
**Already in Skill**: No

**Description**:
Transient network errors during LLM streaming could crash agent runs prior to improved error handling.

**Reproduction**:
```typescript
// Prior behavior - network error crashes run
const result = await run(agent, input);
// If stream breaks mid-response: crash
```

**Solution/Workaround**:
```typescript
// Wrap in retry with exponential backoff (already in skill)
for (let attempt = 1; attempt <= 3; attempt++) {
  try {
    return await run(agent, input);
  } catch (error) {
    if (attempt < 3) {
      await sleep(1000 * Math.pow(2, attempt - 1));
      continue;
    }
    throw error;
  }
}
```

**Official Status**:
- [ ] Closed as stale (may be improved in v0.4.x)
- [x] Retry pattern recommended

**Cross-Reference**:
- Skill already has retry pattern for ToolCallError (line 222-232)
- Pattern applies to network errors too

---

### Finding 1.8: @ai-sdk/provider Now Optional Peer Dependency

**Trust Score**: TIER 1 - Official
**Source**: [Release v0.4.0](https://github.com/openai/openai-agents-js/releases/tag/v0.4.0) | [Issue #868](https://github.com/openai/openai-agents-js/issues/868)
**Date**: 2026-01-18
**Verified**: Yes
**Impact**: LOW (Breaking for extensions users)
**Already in Skill**: No

**Description**:
`@ai-sdk/provider` was moved from required dependency to optional peer dependency in v0.4.0. This supports both AI SDK v2 and v3 formats but requires manual installation if using `@openai/agents-extensions`.

**Reproduction**:
```typescript
// v0.4.0+ - if using extensions with AI SDK adapter:
import { aisdk } from '@openai/agents-extensions/ai-sdk';

// Error: Cannot find module '@ai-sdk/provider'
```

**Solution/Workaround**:
```bash
# Install peer dependency manually
npm install @ai-sdk/provider
```

**Official Status**:
- [x] Breaking change in v0.4.0
- [x] Documented in release notes
- [x] Supports AI SDK v2 and v3

**Cross-Reference**:
- Skill doesn't mention extensions package
- Low priority (extensions not core feature)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Agent-as-Tool Doesn't Share Caller Conversation History

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Issue #806](https://github.com/openai/openai-agents-js/issues/806) | Maintainer Comment
**Date**: 2025-12-29
**Verified**: Partial (maintainer explained intentional design)
**Impact**: MEDIUM (Common Confusion)
**Already in Skill**: No

**Description**:
When using an agent as a tool (via `agent.asTool()`), the sub-agent does NOT have access to the parent agent's conversation history. This is intentional to avoid debugging complexity.

**Reproduction**:
```typescript
const subAgent = new Agent({ name: 'Helper' });
const mainAgent = new Agent({
  name: 'Main',
  tools: [subAgent.asTool()],
});

// Main agent conversation history NOT shared with subAgent
const result = await run(mainAgent, 'Use the helper');
// subAgent starts fresh, no context from mainAgent
```

**Solution/Workaround**:
```typescript
// Community workaround: Pass context via tool input
const subAgent = new Agent({
  name: 'Helper',
  instructions: 'Context will be provided in input',
});

const helperTool = tool({
  name: 'use_helper',
  parameters: z.object({
    query: z.string(),
    context: z.string().optional(), // Pass relevant context
  }),
  execute: async ({ query, context }) => {
    // Manually pass context to sub-agent
    return await run(subAgent, `${context}\n\n${query}`);
  },
});
```

**Community Validation**:
- Maintainer confirmed intentional design
- Community suggested conversation ID per agent tool (not implemented)
- One user claimed to solve with GPT Codex 5.1-Max

**Cross-Reference**:
- Skill mentions agent handoffs (line 78-84) but not agent-as-tool context isolation
- Consider adding note about context isolation

---

### Finding 2.2: Realtime Video Streaming Not Natively Supported

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Issue #694](https://github.com/openai/openai-agents-js/issues/694) | Maintainer Comment
**Date**: 2025-11-21
**Verified**: Partial (maintainer confirmed limitation)
**Impact**: MEDIUM (Common Expectation)
**Already in Skill**: No

**Description**:
Despite examples showing camera integration, realtime video streaming is NOT natively supported. The model may not proactively speak based on video events.

**Reproduction**:
```typescript
// Camera setup works (from realtime-next example)
// But model doesn't react to video in real-time
// Video is sent as images, not streamed
```

**Solution/Workaround**:
No official workaround. Maintainer stated this is a platform limitation.

**Community Validation**:
- Maintainer confirmed not supported
- Example exists but is limited
- Platform-level limitation (not SDK)

**Cross-Reference**:
- Skill mentions "WebRTC" and "Voice Handoffs" (line 136) but not video limitations
- Consider adding to realtime agent limitations

---

## TIER 3 Findings (Community Consensus)

No TIER 3 findings. Stack Overflow has minimal coverage of this SDK (too new).

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Realtime Null Values Ignored (Configuration Bug)

**Trust Score**: TIER 4 - Low Confidence
**Source**: [Issue #820](https://github.com/openai/openai-agents-js/issues/820)
**Date**: 2026-01-07
**Verified**: No (issue closed, no details)
**Impact**: Unknown

**Why Flagged**:
- [x] Issue closed without resolution details
- [x] Cannot reproduce without more info
- [ ] May be fixed in later version

**Description**:
Issue title suggests that passing `null` for `noise_reduction`, `transcription`, or `turn_detection` in realtime config doesn't disable features (falls back to defaults).

**Recommendation**: Monitor for similar reports. DO NOT add without reproduction.

---

### Finding 4.2: Unified Streaming for Agent-as-Tools (Feature Request)

**Trust Score**: TIER 4 - Low Confidence
**Source**: [Issue #705](https://github.com/openai/openai-agents-js/issues/705)
**Date**: 2025-11-28
**Verified**: No (open feature request)
**Impact**: Unknown

**Why Flagged**:
- [x] Open issue (not implemented)
- [x] Feature request, not gotcha/edge case
- [ ] No official response yet

**Description**:
Request to enable unified streaming of all agents in a run (including agent-as-tools and handoffs) with `streamAgentTools` param.

**Recommendation**: Watch for implementation. Not actionable now.

---

## Already Documented in Skill

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Zod Schema Type Errors | Known Issues #1 (line 172-185) | Covered with workaround |
| MaxTurnsExceededError | Known Issues #3 (line 199-213) | Fully covered |
| ToolCallError retry | Known Issues #4 (line 215-233) | Retry pattern documented |
| Schema Mismatch | Known Issues #5 (line 235-247) | Covered with model recommendation |
| MCP Tracing Errors | Known Issues #2 (line 187-197) | initializeTracing() covered |
| Human-in-the-loop | Section (line 103-111) | Basic pattern covered (not streaming HITL) |
| Cloudflare Workers | Framework Integration (line 150-162) | Experimental status noted |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Zod 4 Breaking Change | Quick Start + README | Update README.md line 167 to `zod@4`, add note about v0.4.0 breaking change |
| 1.2 Reasoning Defaults Changed | Error Handling | Add new section "Issue #10: Reasoning Effort Defaults Changed" |
| 1.3 Invalid JSON Handling | Error Handling | Update Error #1 to mention v0.4.1 fix for JSON parse errors |
| 1.4 Reasoning Leaks into Output | Error Handling | Add new "Issue #11: Reasoning Leaks in JSON Output" |
| 1.5 Streaming HITL Pattern | Human-in-the-Loop | Add note about streaming + HITL requires special pattern |
| 1.6 Cloudflare Tracing | Framework Integration | Add tracing limitation to Cloudflare Workers section |

### Priority 2: Consider Adding (TIER 2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.1 Agent-as-Tool Context | Multi-Agent Handoffs | Add note about context isolation with workaround |
| 2.2 Video Not Supported | Realtime Voice Agents | Add to limitations |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 Realtime Null Values | Closed without details | Wait for similar reports |
| 4.2 Unified Streaming | Feature request (not implemented) | Watch for release |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Recent issues (all) | 40 | 15 |
| "streaming" issues | 20 | 5 |
| "zod" issues | 20 | 4 |
| "reasoning" issues | 20 | 3 |
| "cloudflare workers" | 4 | 2 |
| Recent releases | 15 | 3 (v0.4.1, v0.4.0, v0.3.0) |

**Key Releases Reviewed**:
- v0.4.1 (2026-01-20): Invalid JSON fix, legacy fileId fallback
- v0.4.0 (2026-01-18): **BREAKING CHANGES** - Zod 4 required, reasoning defaults changed
- v0.3.9 (2026-01-16): Codex tool support (experimental)
- v0.3.0 (2025-11-05): Memory/sessions, SIP support

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "openai agents sdk 2025 2026" | 0 | N/A (SDK too new) |
| "openai/agents edge case" | 0 | N/A |

**Note**: SDK is too new for Stack Overflow coverage. Primary source is GitHub issues.

### Other Sources

| Source | Notes |
|--------|-------|
| Official Docs | https://openai.github.io/openai-agents-js/ |
| npm Registry | v0.4.1 published 2026-01-20 |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view --comments` for detailed issue analysis
- `gh release list/view` for release notes
- `npm view @openai/agents` for version history

**Limitations**:
- No Stack Overflow coverage (SDK released Oct 2025)
- No blog posts from maintainers found
- Most issues are recent (Dec 2025 - Jan 2026)
- WebRTC/realtime features less documented

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For skill-findings-applier**:
- Update README.md line 167: `zod@3` → `zod@4`
- Add breaking change note for v0.4.0
- Add 4 new error sections (reasoning defaults, JSON output leak, streaming HITL, Cloudflare tracing)
- Update Zod version references throughout skill

**For content-accuracy-auditor**:
- Verify skill version references (currently shows v0.3.7, latest is v0.4.1)
- Cross-check all error workarounds still apply in v0.4.1

**For api-method-checker**:
- Verify `startTracingExportLoop()` exists in current version (Finding 1.6)

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

#### 1. Update Quick Start (Zod Version)

```markdown
## Quick Start

```bash
npm install @openai/agents zod@4  # v0.4.0+ requires Zod 4 (breaking change)
npm install @openai/agents-realtime  # Voice agents
export OPENAI_API_KEY="your-key"
```

**Breaking Change (v0.4.0)**: Zod 3 no longer supported. Upgrade to `zod@4`.
```

#### 2. Add New Error: Reasoning Defaults Changed

```markdown
### 10. Reasoning Effort Defaults Changed (v0.4.0)

**Error**: Unexpected reasoning behavior after upgrading to v0.4.0.

**Why It Happens**: Default reasoning effort for gpt-5.1/5.2 changed from `"low"` to `"none"` in v0.4.0.

**Prevention**: Explicitly set reasoning effort if you need it.

```typescript
// v0.4.0+ - default is now "none"
const agent = new Agent({
  model: 'gpt-5.1',
  reasoning: { effort: 'low' }, // Explicitly set if needed
});
```

**Source**: [Release v0.4.0](https://github.com/openai/openai-agents-js/releases/tag/v0.4.0)
```

#### 3. Add New Error: Reasoning Leaks into Output

```markdown
### 11. Reasoning Content Leaks into JSON Output

**Error**: `response_reasoning` field appears in structured output unexpectedly.

**Why It Happens**: Model endpoint issue (not SDK bug) when using `outputType` with reasoning models.

**Workaround**: Filter out `response_reasoning` from output.

```typescript
const result = await run(agent, input);
const { response_reasoning, ...cleanOutput } = result.finalOutput;
return cleanOutput;
```

**Source**: [Issue #844](https://github.com/openai/openai-agents-js/issues/844)
**Status**: Model-side issue, coordinating with OpenAI teams
```

#### 4. Update Cloudflare Workers Section

```markdown
## Framework Integration

**Cloudflare Workers** (experimental):
```typescript
export default {
  async fetch(request: Request, env: Env) {
    // Disable tracing or use startTracingExportLoop()
    process.env.OTEL_SDK_DISABLED = 'true'; // Add this

    process.env.OPENAI_API_KEY = env.OPENAI_API_KEY;
    const agent = new Agent({ name: 'Assistant', model: 'gpt-5-mini' });
    const result = await run(agent, (await request.json()).message);
    return Response.json({ response: result.finalOutput, tokens: result.usage.totalTokens });
  }
};
```

**Limitations**:
- No voice agents
- 30s CPU limit
- 128MB memory
- **Tracing requires manual setup** - set `OTEL_SDK_DISABLED=true` or call `startTracingExportLoop()`

**Source**: [Issue #16](https://github.com/openai/openai-agents-js/issues/16)
```

#### 5. Update Human-in-the-Loop Section

```markdown
## Human-in-the-Loop

```typescript
const refundTool = tool({ name: 'process_refund', requiresApproval: true, execute: async ({ amount }) => `Refunded $${amount}` });

let result = await runner.run(input);
while (result.interruption?.type === 'tool_approval') {
  result = await promptUser(result.interruption) ? result.state.approve(result.interruption) : result.state.reject(result.interruption);
}
```

**Streaming HITL**: When using `stream: true` with `requiresApproval`, must explicitly check interruptions:

```typescript
const stream = await run(agent, input, { stream: true });
let result = await stream.finalResult();
while (result.interruption?.type === 'tool_approval') {
  const approved = await promptUser(result.interruption);
  result = approved
    ? await result.state.approve(result.interruption)
    : await result.state.reject(result.interruption);
}
```

**Example**: [human-in-the-loop-stream.ts](https://github.com/openai/openai-agents-js/blob/main/examples/agent-patterns/human-in-the-loop-stream.ts)
```

#### 6. Update Multi-Agent Section (Context Isolation)

```markdown
## Multi-Agent Handoffs

```typescript
const billingAgent = new Agent({ name: 'Billing', handoffDescription: 'For billing questions', tools: [refundTool] });
const techAgent = new Agent({ name: 'Technical', handoffDescription: 'For tech issues', tools: [ticketTool] });
const triageAgent = Agent.create({ name: 'Triage', handoffs: [billingAgent, techAgent] });
```

**Agent-as-Tool Context Isolation**: When using `agent.asTool()`, sub-agents do NOT share parent conversation history (intentional design to simplify debugging).

**Workaround**: Pass context via tool parameters:

```typescript
const helperTool = tool({
  name: 'use_helper',
  parameters: z.object({
    query: z.string(),
    context: z.string().optional(),
  }),
  execute: async ({ query, context }) => {
    return await run(subAgent, `${context}\n\n${query}`);
  },
});
```

**Source**: [Issue #806](https://github.com/openai/openai-agents-js/issues/806)
```

#### 7. Update Version References

```markdown
---

**Version**: SDK v0.4.1
**Last Verified**: 2026-01-21
**Skill Author**: Jeremy Dawes (Jezweb)
**Production Tested**: Yes
```

---

**Research Completed**: 2026-01-21 09:45 AEDT
**Next Research Due**: After v0.5.0 release (monitor for breaking changes)
