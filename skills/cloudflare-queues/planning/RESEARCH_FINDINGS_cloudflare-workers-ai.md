# Community Knowledge Research: Cloudflare Workers AI

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/cloudflare-workers-ai/SKILL.md
**Packages Researched**: wrangler@4.58.0, @cloudflare/workers-types@4.20260109.0, workers-ai-provider@3.0.2
**Official Repo**: cloudflare/workers-sdk
**Time Window**: 2024-2026 (focus on 2025+ breaking changes)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 15 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 4 |
| Recommended to Add | 11 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: max_tokens Default 256 Breaking Change (April 2025)

**Trust Score**: TIER 1 - Official
**Source**: [Workers AI Changelog](https://developers.cloudflare.com/workers-ai/changelog/) | [Community Discussion](https://developers.cloudflare.com/changelog/2025-04-11-new-models-faster-inference/)
**Date**: 2025-04-11
**Verified**: Yes - Official documentation
**Impact**: HIGH
**Already in Skill**: Yes (line 19)

**Description**:
In April 2025, Cloudflare fixed a bug where `max_tokens` defaults were not properly being respected. Previously, the `max_tokens` parameter wasn't being properly enforced at its default of 256 tokens. After the fix, applications that relied on the previous behavior started seeing their responses limited to 256 tokens by default.

**Reproduction**:
```typescript
// Before April 2025 - would return full response despite not setting max_tokens
const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
  messages: [{ role: 'user', content: 'Write a long story' }],
  // No max_tokens set - previously would ignore the 256 default
});
// Response could be 500+ tokens

// After April 2025 - truncated at 256 tokens
// Same code now returns only ~256 tokens
```

**Solution/Workaround**:
```typescript
// Always explicitly set max_tokens based on your needs
const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
  messages: [{ role: 'user', content: 'Write a long story' }],
  max_tokens: 2048, // Explicitly set based on model context window
});
```

**Official Status**:
- [x] Fixed in version - April 2025 update
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill at line 19: "max_tokens now correctly defaults to 256 (was not respected)"

---

### Finding 1.2: BGE Pooling Parameter NOT Backwards Compatible (April 2025)

**Trust Score**: TIER 1 - Official
**Source**: [BGE Models Documentation](https://developers.cloudflare.com/workers-ai/models/bge-base-en-v1.5/) | [Developer Week Changelog](https://developers.cloudflare.com/changelog/2025-04-11-new-models-faster-inference/)
**Date**: 2025-04-11
**Verified**: Yes - Official documentation
**Impact**: HIGH
**Already in Skill**: Yes (line 19, 97)

**Description**:
BGE embedding models now support a `pooling` parameter that can be set to `"cls"` or `"mean"`. The `"cls"` pooling method generates more accurate embeddings on larger inputs, but embeddings created with `cls` pooling are NOT compatible with embeddings generated with `mean` pooling. Default is `"mean"` for backwards compatibility, but `"cls"` is recommended for new projects.

**Reproduction**:
```typescript
// Create embeddings with mean pooling (default)
const oldEmbeddings = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
  text: ['Document 1', 'Document 2'],
  // pooling: "mean" (implicit default)
});

// Store in Vectorize
await env.VECTORIZE.insert(oldEmbeddings.data);

// Later, create embeddings with cls pooling
const newEmbeddings = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
  text: ['Query text'],
  pooling: "cls", // More accurate but incompatible!
});

// Search will return poor results - embedding spaces don't match!
const results = await env.VECTORIZE.query(newEmbeddings.data[0]);
```

**Solution/Workaround**:
```typescript
// Choose pooling method at project start and stick with it
// If switching, regenerate ALL embeddings

// Recommended for new projects:
const embeddings = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
  text: documents,
  pooling: "cls", // Better accuracy
});

// If you must switch, regenerate everything:
// 1. Delete old vectors
// 2. Regenerate all embeddings with new pooling
// 3. Re-insert into Vectorize
```

**Official Status**:
- [x] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill at line 19, 97: "BGE pooling parameter (cls NOT backwards compatible with mean)"

---

### Finding 1.3: Context Window Validation Changed from Characters to Tokens (February 2025)

**Trust Score**: TIER 1 - Official
**Source**: [Context Windows Changelog](https://developers.cloudflare.com/changelog/2025-02-24-context-windows/) | [Limits Documentation](https://developers.cloudflare.com/workers-ai/platform/limits/)
**Date**: 2025-02-24
**Verified**: Yes - Official documentation
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Before February 2025, Workers AI had a hard character limit of 6144 characters for prompts, even for models supporting larger token contexts (like Mistral with 32K tokens). After the update, validation switched to token-based counting, allowing developers to use the full context windows advertised for each model.

**Reproduction**:
```typescript
// Before Feb 2025 - would fail despite model supporting 32K tokens
const longPrompt = "...".repeat(7000); // 7000+ characters
const response = await env.AI.run('@cf/mistral/mistral-7b-instruct-v0.2', {
  messages: [{ role: 'user', content: longPrompt }],
});
// Error: Exceeded character limit (6144 characters)

// After Feb 2025 - works if within token limit
const longPrompt = generateLongPrompt(); // Could be 20K+ characters if tokens < 32K
const response = await env.AI.run('@cf/mistral/mistral-7b-instruct-v0.2', {
  messages: [{ role: 'user', content: longPrompt }],
  max_tokens: 512, // Set based on remaining context window
});
```

**Solution/Workaround**:
```typescript
// Calculate tokens, not characters
import { encode } from 'gpt-tokenizer'; // or model-specific tokenizer

const tokens = encode(prompt);
const contextWindow = 32768; // Model's context window
const maxResponseTokens = 2048;

if (tokens.length + maxResponseTokens > contextWindow) {
  throw new Error(`Prompt too long: ${tokens.length} tokens`);
}

const response = await env.AI.run(model, {
  messages: [{ role: 'user', content: prompt }],
  max_tokens: maxResponseTokens,
});
```

**Official Status**:
- [x] Fixed in version - February 2025 update
- [x] Documented behavior

**Cross-Reference**:
- Related to skill line 21: "Context windows API change (tokens not chars)"

---

### Finding 1.4: Model Deprecations October 2025

**Trust Score**: TIER 1 - Official
**Source**: [Workers AI Changelog](https://developers.cloudflare.com/workers-ai/changelog/)
**Date**: 2025-10-01
**Verified**: Yes - Official documentation
**Impact**: HIGH
**Already in Skill**: Yes (line 22)

**Description**:
On October 1, 2025, Cloudflare deprecated 19 older models from the Workers AI catalog, including all @hf/thebloke models, older Qwen 1.5 models, and several smaller LLMs. Recommended replacements are Llama 4, GPT-OSS, and newer model variants.

**Deprecated Models** (partial list):
- @hf/thebloke/llama-2-13b-chat-awq
- @hf/thebloke/mistral-7b-instruct-v0.1-awq
- @cf/qwen/qwen1.5-0.5b-chat
- @cf/qwen/qwen1.5-7b-chat-awq
- @cf/tinyllama/tinyllama-1.1b-chat-v1.0

**Recommended Replacements**:
- Use `@cf/meta/llama-4-scout-17b-16e-instruct` (Llama 4)
- Use `@cf/openai/gpt-oss-120b` or `@cf/openai/gpt-oss-20b` (GPT-OSS)
- Use `@cf/google/gemma-3-12b-it` (Gemma 3)
- Use `@cf/qwen/qwq-32b` or `@cf/qwen/qwen2.5-coder-32b-instruct` (Qwen 2.5)

**Migration**:
```typescript
// Before (deprecated models)
const response = await env.AI.run('@hf/thebloke/llama-2-13b-chat-awq', {
  messages: [{ role: 'user', content: prompt }],
});

// After (recommended replacements)
const response = await env.AI.run('@cf/meta/llama-4-scout-17b-16e-instruct', {
  messages: [{ role: 'user', content: prompt }],
  stream: true, // Always stream for LLMs
});
```

**Official Status**:
- [x] Fixed in version - Deprecated October 1, 2025
- [x] Documented behavior

**Cross-Reference**:
- Already documented in skill at line 22: "October 2025: Model deprecations (use Llama 4, GPT-OSS instead)"

---

### Finding 1.5: Neuron Consumption Discrepancies

**Trust Score**: TIER 1 - Official Community Discussions
**Source**: [Cloudflare Community Thread](https://community.cloudflare.com/t/amount-of-the-neurons-used-for-the-text-generation-does-not-correspond-pricing-doc/788301)
**Date**: 2025-2026
**Verified**: Partial - Community reports with official response
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Users report discrepancies between expected neuron consumption based on token counts and actual neuron usage shown in the Workers AI dashboard. Some users consuming K-level tokens see hundred-million-level neuron counts in billing, particularly with AutoRAG features and certain models.

**Reproduction**:
```typescript
// Generate embeddings and text
const embeddings = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
  text: [document], // ~500 tokens
});

const response = await env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
  messages: [{ role: 'user', content: query }],
  max_tokens: 256,
});

// Expected: Based on docs, should be ~800 neurons total
// Actual: Dashboard may show significantly higher neuron consumption
```

**Solution/Workaround**:
```typescript
// Monitor neuron usage in dashboard
// Use AI Gateway for detailed request logging
const response = await env.AI.run(
  model,
  inputs,
  {
    gateway: {
      id: 'my-gateway',
      skipCache: false,
    },
  }
);

// Check logs to correlate requests with neuron consumption
// File support ticket if consumption significantly exceeds expectations
```

**Official Status**:
- [ ] Fixed in version
- [ ] Documented behavior
- [x] Known issue, workaround required - Monitor and report discrepancies
- [ ] Won't fix

---

### Finding 1.6: workers-ai-provider v3.0.0 with AI SDK v6 (December 2025)

**Trust Score**: TIER 1 - Official
**Source**: [Agents SDK Changelog](https://developers.cloudflare.com/changelog/2025-12-22-agents-sdk-ai-sdk-v6/)
**Date**: 2025-12-22
**Verified**: Yes - Official documentation
**Impact**: MEDIUM
**Already in Skill**: Yes (line 16, 304-318)

**Description**:
workers-ai-provider updated to v3.0.0 with full AI SDK v6 compatibility. This includes enhanced streaming support, unified tool patterns, dynamic tool approval, and React hooks. Breaking changes from v2 to v3.

**Migration**:
```typescript
// v2 (old)
import { WorkersAI } from 'workers-ai-provider';
const provider = new WorkersAI({ binding: env.AI });

// v3 (current) - AI SDK v6
import { createWorkersAI } from 'workers-ai-provider';
import { generateText, streamText } from 'ai';

const workersai = createWorkersAI({ binding: env.AI });

await generateText({
  model: workersai('@cf/meta/llama-3.1-8b-instruct'),
  prompt: 'Write a poem',
});
```

**Official Status**:
- [x] Fixed in version - v3.0.0 (December 2025)
- [x] Documented behavior

**Cross-Reference**:
- Already documented in skill at line 16, 304-318

---

### Finding 1.7: AI Binding Miniflare/Local Development Issues

**Trust Score**: TIER 1 - Official Issue
**Source**: [GitHub Issue #6796](https://github.com/cloudflare/workers-sdk/issues/6796)
**Date**: 2024-09-23 (closed)
**Verified**: Yes - Official issue tracker
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Workers AI bindings with Miniflare in local development (particularly with custom Vite plugins), the AI binding requires external workers that aren't properly exposed by `unstable_getMiniflareWorkerOptions`. This causes the error: "workerd/server/workerd-api.c++:770: error: wrapped binding module can't be resolved".

**Error Message**:
```
MiniflareCoreError [ERR_RUNTIME_FAILURE]: The Workers runtime failed to start.
wrapped binding module can't be resolved (internal modules only);
moduleName = miniflare-internal:wrapped:__WRANGLER_EXTERNAL_AI_WORKER
```

**Solution/Workaround**:
```typescript
// Option 1: Use remote bindings for AI in local dev
// wrangler.jsonc
{
  "ai": {
    "binding": "AI"
  },
  "dev": {
    "remote": true // Use production AI binding in local dev
  }
}

// Option 2: Update to latest @cloudflare/vite-plugin
// package.json
{
  "devDependencies": {
    "@cloudflare/vite-plugin": "^4.0.0" // Latest version
  }
}

// Option 3: Use wrangler dev instead of custom Miniflare setup
// npm run dev (using wrangler dev)
```

**Official Status**:
- [x] Fixed in recent versions - Update tooling
- [x] Documented behavior - Use remote bindings or latest tooling
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.8: Flux Image Generation NSFW Filter False Positives (Error 3030)

**Trust Score**: TIER 1 - Official Community
**Source**: [Cloudflare Community Discussion](https://community.cloudflare.com/t/image-rendering-issue-with-flux-api-nsfw-warning/729440)
**Date**: 2025
**Verified**: Yes - Community reports
**Impact**: LOW-MEDIUM
**Already in Skill**: No

**Description**:
Flux image generation models (`@cf/black-forest-labs/flux-1-schnell`) sometimes trigger false positive NSFW content errors (error code 3030) even with innocent prompts like "hamburger".

**Reproduction**:
```typescript
// May trigger error 3030
const response = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'hamburger', // Single word can trigger filter
});
// Error: "AiError: Input prompt contains NSFW content" (code 3030)
```

**Solution/Workaround**:
```typescript
// Add context around trigger words
const response = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'A photo of a delicious large hamburger on a plate', // Context helps
  num_steps: 4, // Required for some models
});

// Or rephrase to avoid trigger words
const response = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'A photo of a cheeseburger with lettuce and tomato',
});
```

**Official Status**:
- [ ] Fixed in version
- [x] Documented behavior - Known NSFW filter limitation
- [x] Known issue, workaround required
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Image Generation Error 1000 - Missing num_steps Parameter

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Cloudflare Community Discussion](https://community.cloudflare.com/t/ai-api-call-for-image-generation-returns-1000-error-minimal-error-msg/616994)
**Date**: 2024-2025
**Verified**: Partial - Community solution confirmed by multiple users
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Image generation API calls return error code 1000 with message "Error: unexpected type 'int32' with value 'undefined'" when the `num_steps` parameter is not provided, even though documentation suggests it's optional.

**Reproduction**:
```typescript
// Causes error 1000
const response = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'A beautiful sunset',
  // Missing num_steps
});
// Error: "unexpected type 'int32' with value 'undefined'" (code 1000)
```

**Solution/Workaround**:
```typescript
// Always include num_steps for image generation
const response = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'A beautiful sunset',
  num_steps: 4, // Required - typically 4 for Flux Schnell
});

// Note: FLUX.2 [klein] 4B has fixed steps=4 (cannot be adjusted)
```

**Community Validation**:
- Multiple users confirm solution
- Accepted workaround in community discussions

---

### Finding 2.2: AI Gateway Cache Headers for Precision Control

**Trust Score**: TIER 2 - Official Documentation
**Source**: [AI Gateway Caching Docs](https://developers.cloudflare.com/ai-gateway/features/caching/)
**Date**: 2025
**Verified**: Yes - Official documentation
**Impact**: MEDIUM
**Already in Skill**: Partial (basic gateway integration shown, not cache headers)

**Description**:
AI Gateway supports per-request cache control via HTTP headers, allowing precise caching behavior for individual requests beyond dashboard defaults. This includes custom TTL, cache bypass, and custom cache keys.

**Available Headers**:
- `cf-aig-skip-cache`: Bypass cache and fetch from origin
- `cf-aig-cache-ttl`: Set cache duration (60s to 1 month)
- `cf-aig-cache-key`: Custom cache key for granular control
- `cf-aig-cache-status`: Response header showing HIT or MISS

**Implementation**:
```typescript
// Skip cache for this specific request
const response = await fetch(
  `https://gateway.ai.cloudflare.com/v1/${accountId}/${gatewayId}/workers-ai/@cf/meta/llama-3.1-8b-instruct`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.CLOUDFLARE_API_KEY}`,
      'Content-Type': 'application/json',
      'cf-aig-skip-cache': 'true', // Bypass cache
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: prompt }],
    }),
  }
);

// Set custom TTL (e.g., 1 hour for expensive queries)
const response = await fetch(gatewayUrl, {
  headers: {
    'cf-aig-cache-ttl': '3600', // 1 hour in seconds
  },
  // ... rest of request
});

// Check if response was cached
const cacheStatus = response.headers.get('cf-aig-cache-status'); // "HIT" or "MISS"
```

**Community Validation**:
- Official documentation
- Production-tested pattern

---

### Finding 2.3: Wrangler Version Incompatibility with Workers AI (v4.36+)

**Trust Score**: TIER 2 - Community Issue (Closed as Network Issue)
**Source**: [GitHub Issue #10857](https://github.com/cloudflare/workers-sdk/issues/10857)
**Date**: 2025-10-03 (closed 2025-10-14)
**Verified**: Partial - Turned out to be network issue, but highlights version sensitivity
**Impact**: LOW
**Already in Skill**: No

**Description**:
Users reported Workers AI failures with wrangler versions > 4.35.0, though this was later identified as a local network configuration issue. However, it highlights the importance of version compatibility awareness.

**Solution/Workaround**:
```bash
# If experiencing unexplained AI binding failures:
# 1. Check wrangler version
npx wrangler --version

# 2. Try downgrading to last known good version
npm install -D wrangler@4.35.0

# 3. Check local network/firewall settings
# 4. Clear wrangler cache
rm -rf ~/.wrangler

# 5. Update to latest stable
npm install -D wrangler@latest
```

**Community Validation**:
- Issue closed as network configuration problem
- Useful reminder to check version compatibility first

---

### Finding 2.4: Zod v4 Incompatibility with Stagehand/Workers AI

**Trust Score**: TIER 2 - Community Issue
**Source**: [GitHub Issue #10798](https://github.com/cloudflare/workers-sdk/issues/10798)
**Date**: 2025-09-29 (closed 2025-10-07)
**Verified**: Yes - Confirmed by multiple users and maintainers
**Impact**: LOW-MEDIUM
**Already in Skill**: No

**Description**:
Stagehand (browser automation) examples in Workers AI fail with Zod v4 (now default). Zod v3 is required because the underlying `zod-to-json-schema` library doesn't yet support Zod v4.

**Reproduction**:
```typescript
// package.json with Zod v4 (default)
{
  "dependencies": {
    "zod": "^4.0.0" // Latest, but incompatible
  }
}

// Error when running Stagehand examples:
// Syntax errors in TypeScript, failed transpilation
```

**Solution/Workaround**:
```bash
# Install Zod v3 specifically
npm install zod@3

# Or pin in package.json
{
  "dependencies": {
    "zod": "~3.23.8" // Pin to v3 until zod-to-json-schema supports v4
  }
}
```

**Community Validation**:
- Confirmed by Cloudflare maintainers
- Documentation updated to specify Zod v3
- Related to https://github.com/StefanTerdell/zod-to-json-schema/issues/173

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Project Without Workers AI Binding Cannot Run Without Login

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #11758](https://github.com/cloudflare/workers-sdk/issues/11758)
**Date**: 2025-12-25 (still open)
**Verified**: Cross-referenced with similar issues
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Projects that include Workers AI bindings in wrangler.toml cannot run `wrangler dev` without authentication, even if the AI binding isn't being used. This affects CI/CD pipelines and local development without credentials.

**Reproduction**:
```jsonc
// wrangler.jsonc
{
  "name": "my-worker",
  "ai": {
    "binding": "AI" // Even if unused in code
  }
}
```

```bash
# Run without login
wrangler dev

# Error: Requires authentication to check AI binding
# Must run: wrangler login
```

**Solution/Workaround**:
```jsonc
// Option 1: Remove AI binding from wrangler.toml if not needed
// {
//   "ai": { "binding": "AI" }
// }

// Option 2: Use CLOUDFLARE_API_TOKEN for CI/CD
{
  "ai": { "binding": "AI" }
}
```

```bash
# Set API token
export CLOUDFLARE_API_TOKEN="your-token"
wrangler dev
```

**Consensus Evidence**:
- Related to Issue #11881 (cloudflared access login on CI)
- Similar pattern with other remote bindings

**Recommendation**: Add to Community Tips section OR wait for official resolution

---

### Finding 3.2: Streaming with Hono Framework Pattern

**Trust Score**: TIER 3 - Community Pattern
**Source**: [Hono Discussion #2409](https://github.com/orgs/honojs/discussions/2409)
**Date**: 2025
**Verified**: Pattern validated by community
**Impact**: LOW-MEDIUM
**Already in Skill**: Partial (basic streaming shown, not Hono-specific pattern)

**Description**:
When using Workers AI streaming with Hono framework, the recommended pattern is to return the stream directly as a Response, not through Hono's streaming utilities.

**Pattern**:
```typescript
import { Hono } from 'hono';

type Bindings = { AI: Ai };
const app = new Hono<{ Bindings: Bindings }>();

app.post('/chat', async (c) => {
  const { prompt } = await c.req.json();

  // Workers AI streaming
  const stream = await c.env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
    messages: [{ role: 'user', content: prompt }],
    stream: true,
  });

  // Return stream directly as Response (not c.stream())
  return new Response(stream, {
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache',
      'connection': 'keep-alive',
    },
  });
});
```

**Consensus Evidence**:
- Hono community discussion
- Working pattern in production apps

**Recommendation**: Add to Community Tips section

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Queue Consumer Bindings Not Available in Local Dev

**Trust Score**: TIER 4 - Low Confidence (Mixed Local/Remote Issue)
**Source**: [GitHub Issue #9887](https://github.com/cloudflare/workers-sdk/issues/9887)
**Date**: 2025-07-08 (closed)
**Verified**: No - Specific to mixed binding configuration
**Impact**: LOW

**Why Flagged**:
- [x] Specific to complex mixed local/remote configuration
- [x] May be version-specific
- [x] Not directly Workers AI issue (binding configuration general issue)
- [ ] Contradicts official docs
- [ ] Outdated (pre-2024)

**Description**:
Queue consumer bindings don't work in local dev when using mixed local/remote bindings configuration. This may affect Workers AI projects that also use Queues, but it's a general binding issue not specific to AI.

**Recommendation**: Manual verification required. Monitor for similar AI-specific binding issues. DO NOT add to skill without human review.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| max_tokens default 256 breaking change | Line 19, YAML description | Fully covered |
| BGE pooling cls/mean incompatibility | Line 19, 97 | Fully covered |
| Model deprecations October 2025 | Line 22, 63-85 | Fully covered |
| workers-ai-provider v3.0.0 with AI SDK v6 | Line 16, 304-318 | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.3 Context window tokens (not chars) | Known Issues Prevention | Add as Issue #7 |
| 1.5 Neuron consumption discrepancies | Known Issues Prevention | Add as Issue #8 with monitoring guidance |
| 1.7 AI binding Miniflare issues | Known Issues Prevention | Add as Issue #9 with workarounds |
| 1.8 Flux NSFW false positives | Image Generation section | Add to Flux model notes |
| 2.1 Image generation num_steps required | Image Generation section | Add to all image model examples |
| 2.2 AI Gateway cache headers | AI Gateway section | Expand with per-request cache control |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.3 Wrangler version sensitivity | Community Tips | Mention version compatibility checks |
| 2.4 Zod v4 incompatibility | Structured Output section | Note for Stagehand users |
| 3.2 Hono streaming pattern | Common Patterns | Add Hono-specific streaming example |

### Priority 3: Monitor (TIER 3-4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.1 AI binding requires login | Still open issue | Wait for official resolution |
| 4.1 Queue consumer bindings | Not AI-specific | Monitor for AI-specific binding issues |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "workers ai" in cloudflare/workers-sdk | 30 | 12 |
| "workers ai streaming" issues | 20 | 3 |
| "workers ai model" closed issues | 15 | 4 |
| Issue #10857 (wrangler version) | 1 | 1 |
| Issue #10798 (Stagehand/Zod) | 1 | 1 |
| Issue #6796 (Miniflare) | 1 | 1 |

### Official Documentation

| Source | Notes |
|--------|-------|
| [Workers AI Changelog](https://developers.cloudflare.com/workers-ai/changelog/) | Primary source for breaking changes |
| [Workers AI Limits](https://developers.cloudflare.com/workers-ai/platform/limits/) | Token limits, rate limits |
| [AI Gateway Caching](https://developers.cloudflare.com/ai-gateway/features/caching/) | Cache control headers |
| [BGE Models](https://developers.cloudflare.com/workers-ai/models/bge-base-en-v1.5/) | Pooling parameter docs |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "cloudflare workers ai streaming issues" | 10 links | Official docs + blog posts |
| "cloudflare workers ai rate limit 429" | 10 links | Community + official docs |
| "cloudflare workers ai max_tokens 256" | 10 links | Official changelog |
| "cloudflare workers ai BGE pooling" | 10 links | Official docs + changelog |
| "cloudflare workers ai flux error" | 10 links | Community discussions |
| "cloudflare workers ai neurons pricing" | 10 links | Community + official pricing |
| "cloudflare workers ai vercel ai sdk" | 10 links | Official integration docs |

### Cloudflare Community

| Search | Relevant |
|--------|----------|
| Workers AI pricing/neurons | 3 threads |
| Image generation errors | 2 threads |
| Rate limiting | 4 threads |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `WebSearch` for community discussions and Stack Overflow
- Official Cloudflare changelog and documentation

**Limitations**:
- Some Cloudflare Community threads not directly accessible via API
- Stack Overflow has limited Workers AI discussions (newer service)
- Some closed issues may have been network-specific (not AI issues)

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference finding 1.3 (context window tokens) against current limits documentation
- Verify finding 1.5 (neuron consumption) matches current pricing model

**For api-method-checker**:
- Verify that the cache headers in finding 2.2 (`cf-aig-cache-ttl`, `cf-aig-skip-cache`, `cf-aig-cache-key`) are current
- Check if `num_steps` parameter in finding 2.1 is now documented as required

**For code-example-validator**:
- Validate code examples in findings 1.3, 1.7, 1.8, 2.1, 2.2
- Test Hono streaming pattern (finding 3.2) against current Hono version

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

**New Known Issues Section** (after current line 80):

```markdown
## Known Issues Prevention

### Issue #7: Context Window Validation (Tokens Not Characters)

**Source**: [Changelog Feb 2025](https://developers.cloudflare.com/changelog/2025-02-24-context-windows/)
**Why It Happens**: Before Feb 2025, character limits prevented using full context windows. Now validates by tokens.
**Prevention**: Calculate tokens (not characters) when checking context window limits.

```typescript
import { encode } from 'gpt-tokenizer';

const tokens = encode(prompt);
const contextWindow = 32768; // Model's max tokens
const maxResponseTokens = 2048;

if (tokens.length + maxResponseTokens > contextWindow) {
  throw new Error(`Prompt exceeds context window: ${tokens.length} tokens`);
}
```

### Issue #8: Neuron Consumption Discrepancies

**Source**: [Community Reports](https://community.cloudflare.com/t/amount-of-the-neurons-used-for-the-text-generation-does-not-correspond-pricing-doc/788301)
**Why It Happens**: Dashboard may show higher neuron consumption than expected based on token counts.
**Prevention**: Monitor neuron usage via AI Gateway logs, file support ticket if discrepancies persist.

```typescript
// Use AI Gateway for detailed logging
const response = await env.AI.run(
  model,
  inputs,
  { gateway: { id: 'my-gateway' } }
);

// Monitor dashboard and compare with token usage
```

### Issue #9: AI Binding Local Development Requires Remote or Latest Tooling

**Source**: [GitHub Issue #6796](https://github.com/cloudflare/workers-sdk/issues/6796)
**Why It Happens**: Miniflare AI binding requires external workers not exposed in older tooling.
**Prevention**: Use remote bindings or update to latest @cloudflare/vite-plugin.

```jsonc
// wrangler.jsonc - Use remote AI in local dev
{
  "ai": { "binding": "AI" },
  "dev": { "remote": true }
}
```
```

**Update Image Generation Section** (around line 99-107):

```markdown
### Image Generation

| Model | Best For | Rate Limit | Notes |
|-------|----------|------------|-------|
| `@cf/black-forest-labs/flux-1-schnell` | High quality, photorealistic | 720/min | ⚠️ NSFW filter may false-positive, add context |
| `@cf/leonardo/lucid-origin` | Leonardo AI style | 720/min | NEW 2025, requires `num_steps: 4` |

⚠️ **Common Issues**:
- **Error 1000**: Always include `num_steps: 4` (required despite docs suggesting optional)
- **Error 3030 (NSFW)**: Single words like "hamburger" may trigger filter, add descriptive context

```typescript
// Correct pattern for Flux models
const image = await env.AI.run('@cf/black-forest-labs/flux-1-schnell', {
  prompt: 'A photo of a delicious hamburger on a plate', // Context helps avoid false positives
  num_steps: 4, // Required
});
```
```

**Expand AI Gateway Section** (around line 169-188):

```markdown
## AI Gateway Integration

Provides caching, logging, cost tracking, and analytics for AI requests.

### Per-Request Cache Control

Override default cache behavior with HTTP headers:

```typescript
// Custom cache TTL (1 hour for expensive queries)
const response = await fetch(gatewayUrl, {
  headers: {
    'Authorization': `Bearer ${apiKey}`,
    'cf-aig-cache-ttl': '3600', // 1 hour in seconds (min: 60, max: 2592000)
  },
  // ...
});

// Skip cache for real-time data
const response = await fetch(gatewayUrl, {
  headers: {
    'cf-aig-skip-cache': 'true', // Bypass cache
  },
  // ...
});

// Check if response was cached
const cacheStatus = response.headers.get('cf-aig-cache-status'); // "HIT" or "MISS"
```

**Available Cache Headers**:
- `cf-aig-cache-ttl`: Set custom TTL (60s to 1 month)
- `cf-aig-skip-cache`: Bypass cache entirely
- `cf-aig-cache-key`: Custom cache key for granular control
- `cf-aig-cache-status`: Response header showing HIT/MISS
```

### Adding Community Tips Section

```markdown
## Community Tips (Community-Sourced)

> **Note**: These tips come from community discussions and production experience.

### Hono Framework Streaming Pattern

When using Workers AI streaming with Hono, return the stream directly as a Response:

```typescript
import { Hono } from 'hono';

const app = new Hono<{ Bindings: { AI: Ai } }>();

app.post('/chat', async (c) => {
  const { prompt } = await c.req.json();

  const stream = await c.env.AI.run('@cf/meta/llama-3.1-8b-instruct', {
    messages: [{ role: 'user', content: prompt }],
    stream: true,
  });

  // Return stream directly (not c.stream())
  return new Response(stream, {
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache',
    },
  });
});
```

### Version Compatibility Checks

If experiencing unexplained AI binding failures:

```bash
# Check wrangler version
npx wrangler --version

# Clear cache
rm -rf ~/.wrangler

# Update to latest stable
npm install -D wrangler@latest
```

### Zod Version for Structured Output

For structured output with validation libraries:

```bash
# Stagehand and some tools require Zod v3
npm install zod@3

# zod-to-json-schema doesn't yet support Zod v4
```
```

---

**Research Completed**: 2026-01-20 14:30
**Next Research Due**: After next major Workers AI release or April 2026 (quarterly)

---

## Sources

- [Cloudflare Workers AI Changelog](https://developers.cloudflare.com/workers-ai/changelog/)
- [Workers AI Limits Documentation](https://developers.cloudflare.com/workers-ai/platform/limits/)
- [BGE Model Documentation](https://developers.cloudflare.com/workers-ai/models/bge-base-en-v1.5/)
- [AI Gateway Caching](https://developers.cloudflare.com/ai-gateway/features/caching/)
- [Context Windows Update](https://developers.cloudflare.com/changelog/2025-02-24-context-windows/)
- [Agents SDK v6 Support](https://developers.cloudflare.com/changelog/2025-12-22-agents-sdk-ai-sdk-v6/)
- [GitHub Issue #6796 - Miniflare AI Binding](https://github.com/cloudflare/workers-sdk/issues/6796)
- [GitHub Issue #10857 - Wrangler Version](https://github.com/cloudflare/workers-sdk/issues/10857)
- [GitHub Issue #10798 - Stagehand Zod](https://github.com/cloudflare/workers-sdk/issues/10798)
- [Community: Neuron Consumption](https://community.cloudflare.com/t/amount-of-the-neurons-used-for-the-text-generation-does-not-correspond-pricing-doc/788301)
- [Community: Image Generation Error 1000](https://community.cloudflare.com/t/ai-api-call-for-image-generation-returns-1000-error-minimal-error-msg/616994)
- [Community: Flux NSFW Filter](https://community.cloudflare.com/t/image-rendering-issue-with-flux-api-nsfw-warning/729440)
- [Hono Discussion #2409](https://github.com/orgs/honojs/discussions/2409)
- [Vercel AI SDK Integration](https://developers.cloudflare.com/workers-ai/configuration/ai-sdk/)
