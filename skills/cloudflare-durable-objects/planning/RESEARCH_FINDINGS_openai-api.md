# Community Knowledge Research: openai-api

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/openai-api/SKILL.md
**Packages Researched**: openai@6.15.0 (latest: 6.16.0)
**Official Repo**: openai/openai-node
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 14 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 11 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: GPT-5.1/5.2 Default reasoning_effort Changed to "none"

**Trust Score**: TIER 1 - Official
**Source**: [OpenAI Cookbook](https://cookbook.openai.com/examples/gpt-5/gpt-5-2_prompting_guide), [Azure OpenAI Docs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning?view=foundry-classic)
**Date**: 2025-11-13 (GPT-5.1 release)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Yes (documented in line 211)

**Description**:
GPT-5.1 and GPT-5.2 models default to `reasoning_effort: 'none'`, a breaking change from GPT-5 which defaulted to `'medium'`. This means upgrading from GPT-5 to GPT-5.1/5.2 without explicitly setting reasoning_effort will result in no reasoning being applied, potentially degrading output quality for complex tasks.

**Reproduction**:
```typescript
// GPT-5 (defaults to medium reasoning)
const completion = await openai.chat.completions.create({
  model: 'gpt-5',
  messages: [{ role: 'user', content: 'Complex reasoning task' }],
  // reasoning_effort: 'medium' is default
});

// GPT-5.1 (defaults to none - NO reasoning unless specified)
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Complex reasoning task' }],
  // reasoning_effort: 'none' is default - NO reasoning!
});
```

**Solution/Workaround**:
```typescript
// Explicitly set reasoning_effort when upgrading to GPT-5.1/5.2
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Complex reasoning task' }],
  reasoning_effort: 'medium', // Explicitly restore previous behavior
});
```

**Official Status**:
- [x] Documented behavior (intentional breaking change)
- [x] Known issue, workaround required (explicit parameter)
- [ ] Won't fix

**Cross-Reference**:
- Already documented in skill at line 211
- See also: Finding 1.2 (xhigh reasoning level)

---

### Finding 1.2: GPT-5.2 Adds "xhigh" reasoning_effort Level

**Trust Score**: TIER 1 - Official
**Source**: [OpenAI GPT-5.2 Announcement](https://openai.com/index/introducing-gpt-5-2/), [OpenAI API Docs](https://platform.openai.com/docs/guides/latest-model)
**Date**: 2025-12-11 (GPT-5.2 release)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Yes (documented in line 196-202)

**Description**:
GPT-5.2 introduces a sixth reasoning effort level: `"xhigh"` (extreme high), beyond the existing `"high"` level. This level is designed for extremely complex problems requiring maximum reasoning time and achieves 99% on AIME 2025 math competition benchmark.

**Supported Models**:
- GPT-5.2: Yes
- GPT-5.2-pro: Yes
- GPT-5.1: No (only supports none/minimal/low/medium/high)
- GPT-5: No

**Solution/Workaround**:
```typescript
// Only works with GPT-5.2 and later
const completion = await openai.chat.completions.create({
  model: 'gpt-5.2',
  messages: [{ role: 'user', content: 'Extremely complex problem' }],
  reasoning_effort: 'xhigh', // NEW: Maximum reasoning
});
```

**Official Status**:
- [x] Documented behavior (new feature)
- [x] Model-specific (GPT-5.2+ only)

**Cross-Reference**:
- Already documented in skill at line 196-202
- Pricing: 1.4x of GPT-5.1 ($1.75/$14 per million tokens)

---

### Finding 1.3: Model Name "gpt-5.1-mini" Does Not Exist

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1706](https://github.com/openai/openai-node/issues/1706)
**Date**: 2025-11-17
**Verified**: Yes (400 error confirms)
**Impact**: MEDIUM
**Already in Skill**: No (incorrect model name not explicitly warned)

**Description**:
The model name `"gpt-5.1-mini"` does not exist and returns a 400 error: "The requested model 'gpt-5.1-mini' does not exist." The correct model name is `"gpt-5-mini"` (without the .1 suffix).

**Reproduction**:
```typescript
// ❌ WRONG - This model name doesn't exist
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1-mini', // Error: model does not exist
  messages: [{ role: 'user', content: 'Hello' }],
});

// ✅ CORRECT - Use gpt-5-mini (no .1 suffix)
const completion = await openai.chat.completions.create({
  model: 'gpt-5-mini',
  messages: [{ role: 'user', content: 'Hello' }],
});
```

**Official Status**:
- [x] Documented behavior (model name clarification needed)
- [ ] Known issue, workaround required

**Cross-Reference**:
- Skill lists correct model names at line 124-127
- Recommendation: Add to "Common Mistakes" section

---

### Finding 1.4: reasoning_effort "minimal" Value Not Available

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1690](https://github.com/openai/openai-node/issues/1690)
**Date**: 2025-10-26
**Verified**: Partial (user report, open issue)
**Impact**: LOW
**Already in Skill**: No

**Description**:
The value `reasoning_effort: "minimal"` is documented but may not be available in practice, with users reporting it's "totally unavailable." This may be a documentation-implementation mismatch or a gradual rollout issue.

**Reproduction**:
```typescript
// May not work depending on model/API version
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Hello' }],
  reasoning_effort: 'minimal', // Reported as unavailable
});
```

**Solution/Workaround**:
```typescript
// Use 'none' or 'low' instead
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Hello' }],
  reasoning_effort: 'none', // or 'low'
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Skill documents "minimal" at line 238
- Recommendation: Add caveat that "minimal" may not be available

---

### Finding 1.5: TypeScript Types Missing for text_tokens and image_tokens

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1718](https://github.com/openai/openai-node/issues/1718)
**Date**: 2025-12-11
**Verified**: Yes (open issue)
**Impact**: LOW (TypeScript only)
**Already in Skill**: No

**Description**:
The response usage object includes `text_tokens` and `image_tokens` fields for multimodal requests, but these fields are not documented in the TypeScript types or API documentation.

**Reproduction**:
```typescript
const completion = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: 'What is in this image?' },
      { type: 'image_url', image_url: { url: 'https://example.com/image.jpg' } }
    ]
  }]
});

// These fields exist but aren't typed
console.log(completion.usage.text_tokens); // TypeScript error
console.log(completion.usage.image_tokens); // TypeScript error
```

**Solution/Workaround**:
```typescript
// Use type assertion or access via any
const usage = completion.usage as any;
console.log(usage.text_tokens);
console.log(usage.image_tokens);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Recommendation: Add to TypeScript gotchas section

---

### Finding 1.6: Zod Schema Conversion Broken for Unions in Zod 4.1.13+

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1709](https://github.com/openai/openai-node/issues/1709)
**Date**: 2025-11-26
**Verified**: Yes (open issue, labeled as bug/sdk)
**Impact**: MEDIUM (affects structured outputs with Zod)
**Already in Skill**: No

**Description**:
When using `zodResponseFormat()` helper with Zod 4.1.13+, union types in schemas are not converted correctly, breaking structured outputs that use unions.

**Reproduction**:
```typescript
import { z } from 'zod';
import { zodResponseFormat } from 'openai/helpers/zod';

// Schema with union
const schema = z.object({
  status: z.union([z.literal('success'), z.literal('error')]),
  message: z.string(),
});

const format = zodResponseFormat(schema, 'response');

// Conversion fails with Zod 4.1.13+
const completion = await openai.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Generate a status response' }],
  response_format: format, // May fail with union types
});
```

**Solution/Workaround**:
1. Downgrade to Zod 4.1.12 or earlier
2. Use enum instead of union
3. Manually construct the JSON schema instead of using zodResponseFormat

```typescript
// Workaround: Use enum instead of union
const schema = z.object({
  status: z.enum(['success', 'error']),
  message: z.string(),
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Related to structured outputs section (line 393-446)
- Recommendation: Add warning in structured outputs section

---

### Finding 1.7: Response completed_at Property Added (v6.16.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Release v6.16.0](https://github.com/openai/openai-node/releases/tag/v6.16.0)
**Date**: 2026-01-09
**Verified**: Yes (official release)
**Impact**: LOW (new feature)
**Already in Skill**: No

**Description**:
Version 6.16.0 adds a new `completed_at` timestamp property to Response objects in the Responses API, complementing the existing `created_at` field. This allows tracking total response time.

**Usage**:
```typescript
const response = await openai.responses.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Hello' }],
});

console.log(response.created_at); // Start time
console.log(response.completed_at); // Completion time (NEW in v6.16.0)
```

**Official Status**:
- [x] Fixed in version 6.16.0
- [x] Documented behavior (new feature)

**Cross-Reference**:
- Related to Responses API (mentioned but not primary focus of this skill)
- Note: openai-responses skill should document this more thoroughly

---

### Finding 1.8: TypeScript Type Error - usage Field May Contain null

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1402](https://github.com/openai/openai-node/issues/1402)
**Date**: 2025-03-20
**Verified**: Yes (open issue, labeled as bug/openapi)
**Impact**: MEDIUM (TypeScript strictNullChecks)
**Already in Skill**: No

**Description**:
The `usage` field in completion responses may be `null` in some cases (e.g., when streaming), but the TypeScript type definitions don't reflect this, causing type errors with `strictNullChecks: true`.

**Reproduction**:
```typescript
// With strictNullChecks: true
const completion = await openai.chat.completions.create({
  model: 'gpt-5.1',
  messages: [{ role: 'user', content: 'Hello' }],
});

// TypeScript error: usage might be null
const tokens = completion.usage.total_tokens; // Error with strictNullChecks
```

**Solution/Workaround**:
```typescript
// Check for null before accessing
if (completion.usage) {
  const tokens = completion.usage.total_tokens;
}

// Or use optional chaining
const tokens = completion.usage?.total_tokens ?? 0;
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Recommendation: Add to TypeScript best practices section

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Realtime API Concurrent Session Limit Removed

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [OpenAI Realtime API Docs](https://platform.openai.com/docs/guides/realtime-websocket)
**Date**: 2025-02-03
**Verified**: Yes (official documentation)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
As of February 3, 2025, OpenAI removed the limit on simultaneous Realtime API sessions. Previously, there was a concurrent connection limit that could cause connection failures during high-volume usage.

**Solution/Workaround**:
No workaround needed - this is a positive change that removes a previous limitation.

**Community Validation**:
- Source: Official OpenAI documentation
- Multiple community tutorials reference this change

**Cross-Reference**:
- Skill documents Realtime API at line 738-797
- Recommendation: Update Realtime API section to note unlimited sessions

---

### Finding 2.2: GPT-4o-mini-TTS Voice Instructions and Streaming

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [OpenAI TTS Guide](https://platform.openai.com/docs/guides/text-to-speech), [OpenAI Blog](https://developers.openai.com/blog/updates-audio-models)
**Date**: 2024-11-XX (released November 2024)
**Verified**: Yes (official docs)
**Impact**: MEDIUM
**Already in Skill**: Partial (mentioned but not detailed)

**Description**:
The `gpt-4o-mini-tts` model supports two unique features not available in `tts-1` or `tts-1-hd`:
1. Voice instructions via `instructions` parameter
2. Streaming with `stream_format: "sse"`

The latest snapshot `gpt-4o-mini-tts-2025-12-15` delivers 35% lower word error rate compared to previous versions.

**Usage**:
```typescript
// Voice instructions (gpt-4o-mini-tts only)
const speech = await openai.audio.speech.create({
  model: 'gpt-4o-mini-tts',
  voice: 'nova',
  input: 'Welcome to support.',
  instructions: 'Speak in a calm, professional tone.', // Only works with gpt-4o-mini-tts
});

// Streaming (gpt-4o-mini-tts only)
const response = await fetch('https://api.openai.com/v1/audio/speech', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'gpt-4o-mini-tts',
    voice: 'nova',
    input: 'Long text...',
    stream_format: 'sse', // Only works with gpt-4o-mini-tts
  }),
});
```

**Community Validation**:
- Official documentation confirms model-specific features
- Multiple 2025 tutorials reference these capabilities

**Cross-Reference**:
- Skill documents TTS at line 640-689
- Instructions and streaming are mentioned at line 659-689
- Already well-documented but could add performance improvement note

---

### Finding 2.3: Batch API 24-Hour Window Often Completes Faster

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [OpenAI Batch API Guide](https://www.daniel-gomm.com/blog/2025/openbatch/), [Engineering Blog](https://engineering.miko.ai/save-50-on-openai-api-costs-using-batch-requests-6ad41214b4ac)
**Date**: 2025 (multiple sources)
**Verified**: Yes (multiple community reports)
**Impact**: LOW (expectation management)
**Already in Skill**: No

**Description**:
While the Batch API has a 24-hour completion window, community reports show jobs often complete much faster - in one case, a task estimated at 10+ hours completed in under 1 hour. This is important for setting realistic expectations.

**Community Validation**:
- Multiple blog posts report faster-than-24h completion
- Official docs state "24h completion window" but note it's a maximum

**Cross-Reference**:
- Skill documents Batch API at line 799-853
- Line 824 mentions "24-hour turnaround" - could clarify as maximum

**Recommendation**: Add note that 24h is maximum, actual completion often faster

---

### Finding 2.4: DALL-E 3 Always Revises Prompts for Safety/Quality

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [OpenAI Community](https://community.openai.com/t/api-image-generation-in-dall-e-3-changes-my-original-prompt-without-my-permission/476355), [DALL-E 3 Guide](https://skywork.ai/skypage/en/DALL-E-3-In-Depth-(2025):-My-Hands-On-Review,-Benchmarks,-and-Practical-Guide/1976472460575436800)
**Date**: 2025 (ongoing behavior)
**Verified**: Yes (documented in API)
**Impact**: MEDIUM (affects prompt engineering)
**Already in Skill**: Yes (documented at line 587)

**Description**:
DALL-E 3 automatically rewrites prompts to improve safety and quality, and this cannot be disabled. The API returns the revised prompt in the `revised_prompt` field, which often differs significantly from the original.

**Example**:
```typescript
const image = await openai.images.generate({
  model: 'dall-e-3',
  prompt: 'cat', // Simple prompt
});

console.log(image.data[0].revised_prompt);
// Returns: "A white siamese cat with striking blue eyes sitting on a windowsill..."
```

**Community Validation**:
- Multiple community posts about unexpected prompt changes
- Official documentation confirms this is expected behavior
- `revised_prompt` field always present in response

**Cross-Reference**:
- Already documented at line 587
- Recommendation: Emphasize that this cannot be disabled

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Embeddings Dimension Mismatch Errors

**Trust Score**: TIER 3 - Community Consensus
**Source**: [n8n Community](https://community.n8n.io/t/how-to-change-openai-embedding-dimensions-to-256/56301), [mem0ai Issue #2302](https://github.com/mem0ai/mem0/issues/2302)
**Date**: 2025 (ongoing)
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Common error when vector database dimensions don't match embedding model output: "ValueError: shapes (0,256) and (1536,) not aligned". This occurs when:
1. Database is configured for custom dimensions (e.g., 256)
2. Embeddings API is called without specifying `dimensions` parameter
3. Model returns default dimensions (1536 for text-embedding-3-small)

**Solution**:
```typescript
// ❌ WRONG - Database expects 256 dims, model returns 1536
const embedding = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: 'Sample text',
  // Missing dimensions parameter - returns 1536 default
});

// ✅ CORRECT - Specify dimensions to match database
const embedding = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: 'Sample text',
  dimensions: 256, // Match database configuration
});
```

**Consensus Evidence**:
- Multiple community forums report this error pattern
- OpenAI docs confirm `dimensions` parameter is required for custom sizes
- No conflicting information found

**Recommendation**: Add to embeddings section as common pitfall

---

### Finding 3.2: Function Calling Errors with previous_response_id

**Trust Score**: TIER 3 - Community Consensus
**Source**: [OpenAI Community Thread](https://community.openai.com/t/openai-responses-api-no-tool-output-found-for-function-call-when-using-previous-response-id-anyone-have-a-stable-workaround/1354672)
**Date**: 2025 (multiple reports)
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM (affects Responses API primarily)
**Already in Skill**: No (Responses API focus)

**Description**:
When using function calling with `previous_response_id` parameter, users report "No tool output found for function call" errors despite matching call_ids. This appears to be a state/timing issue in the Responses API.

**Note**: This primarily affects the Responses API (openai-responses skill), not traditional Chat Completions API.

**Consensus Evidence**:
- Multiple community threads report this issue
- Issue exists across different implementations
- Workarounds suggest avoiding `previous_response_id` with function calling

**Recommendation**: Note as Responses API issue, refer to openai-responses skill

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

No TIER 4 findings. All findings met minimum quality threshold (TIER 3 or higher).

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| GPT-5.1/5.2 default reasoning_effort | Line 211 | BREAKING CHANGE documented |
| GPT-5.2 xhigh reasoning level | Line 196-202 | Fully covered |
| DALL-E 3 revised_prompt | Line 587 | Documented |
| gpt-4o-mini-tts instructions/streaming | Line 659-689 | Documented |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.3 Model name gpt-5.1-mini | Known Issues | Add as common mistake |
| 1.6 Zod union bug | Structured Outputs section | Add warning with workaround |
| 1.8 usage field null | Error Handling | Add TypeScript gotcha |
| 3.1 Embeddings dimension mismatch | Embeddings section | Add common pitfall |

### Priority 2: Update Existing Content (TIER 1-2, Medium Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.4 reasoning_effort minimal | GPT-5 section line 238 | Add caveat about availability |
| 1.7 completed_at property | Update to v6.16.0 | Document new field |
| 2.1 Realtime API sessions | Realtime section line 738 | Note unlimited sessions (Feb 2025) |
| 2.3 Batch API completion | Batch section line 824 | Clarify 24h is maximum |
| 2.4 DALL-E 3 prompt revision | Images section line 587 | Emphasize cannot disable |

### Priority 3: Add TypeScript Gotchas Section (NEW)

Create new section for TypeScript-specific issues:
- Finding 1.5: text_tokens/image_tokens not typed
- Finding 1.8: usage field may be null

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Issues created >2025-05-01 | 30 | 8 |
| "typescript type" state:open | 3 | 3 |
| "streaming" state:open | 15 | 2 |
| Recent releases (v6.15-6.16) | 2 | 2 |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "reasoning_effort" openai gpt-5 2025 | 10 links | High (official sources) |
| openai "gpt-4o-mini-tts" 2025 | 10 links | High (official + tutorials) |
| openai batch api 50% savings 2025 | 10 links | High (official + guides) |
| openai realtime api websocket 2025 | 10 links | High (official) |
| openai embeddings dimension error 2025 | 10 links | Medium (community forums) |
| openai dall-e-3 revised_prompt 2025 | 10 links | Medium-High |
| "gpt-5.1" reasoning_effort none default | 7 links | High (official + docs) |
| gpt-5.2 xhigh reasoning_effort | 10 links | High (official) |

### Other Sources

| Source | Notes |
|--------|-------|
| OpenAI Platform Docs | Primary reference for all features |
| Azure OpenAI Docs | Confirms GPT-5 behavior |
| OpenAI Cookbook | GPT-5.2 prompting guide |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release list/view` for release notes
- `WebSearch` for official docs and community content

**Limitations**:
- Stack Overflow had limited recent (2025-2026) results
- Most valuable findings came from official GitHub repo and docs
- Some TypeScript issues require manual testing to reproduce

**Time Spent**: ~45 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Cross-reference Finding 1.4 (reasoning_effort minimal) against latest official docs
- Verify Finding 1.7 (completed_at) is in v6.16.0 types

**For api-method-checker**:
- Verify `reasoning_effort: 'xhigh'` exists in GPT-5.2 API
- Verify `dimensions` parameter exists for embeddings

**For code-example-validator**:
- Validate Zod workaround code in Finding 1.6
- Test embeddings dimension parameter in Finding 3.1

---

## Integration Guide

### Adding Common Mistakes Section

Add after Error Handling section:

```markdown
## Common Mistakes & Gotchas

### Mistake #1: Using Wrong Model Name "gpt-5.1-mini"

**Error**: `400 The requested model 'gpt-5.1-mini' does not exist`
**Source**: [GitHub Issue #1706](https://github.com/openai/openai-node/issues/1706)

**Wrong**:
```typescript
model: 'gpt-5.1-mini' // Does not exist
```

**Correct**:
```typescript
model: 'gpt-5-mini' // Correct (no .1 suffix)
```

Available GPT-5 series models:
- `gpt-5`, `gpt-5-mini`, `gpt-5-nano`
- `gpt-5.1`, `gpt-5.2`
- Note: No `gpt-5.1-mini` - mini variant doesn't have .1/.2 versions

### Mistake #2: Embeddings Dimension Mismatch

**Error**: `ValueError: shapes (0,256) and (1536,) not aligned`

Ensure vector database dimensions match embeddings API `dimensions` parameter:

```typescript
// ❌ Wrong - missing dimensions, returns 1536 default
const embedding = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: 'text',
});

// ✅ Correct - specify dimensions to match database
const embedding = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: 'text',
  dimensions: 256, // Match your vector database config
});
```

### Mistake #3: Forgetting reasoning_effort When Upgrading to GPT-5.1/5.2

**Issue**: GPT-5.1 and GPT-5.2 default to `reasoning_effort: 'none'` (breaking change from GPT-5)

```typescript
// GPT-5 (defaults to 'medium')
model: 'gpt-5' // Automatic reasoning

// GPT-5.1 (defaults to 'none')
model: 'gpt-5.1' // NO reasoning unless specified!
reasoning_effort: 'medium' // Must add explicitly
```
```

### TypeScript Gotchas Section

Add new section:

```markdown
## TypeScript Gotchas

### Gotcha #1: usage Field May Be Null

**Issue**: [GitHub Issue #1402](https://github.com/openai/openai-node/issues/1402)

With `strictNullChecks: true`, the `usage` field may cause type errors:

```typescript
// ❌ TypeScript error with strictNullChecks
const tokens = completion.usage.total_tokens;

// ✅ Use optional chaining or null check
const tokens = completion.usage?.total_tokens ?? 0;

// Or explicit check
if (completion.usage) {
  const tokens = completion.usage.total_tokens;
}
```

### Gotcha #2: text_tokens and image_tokens Not Typed

**Issue**: [GitHub Issue #1718](https://github.com/openai/openai-node/issues/1718)

Multimodal requests include `text_tokens` and `image_tokens` fields not in TypeScript types:

```typescript
// These fields exist but aren't typed
const usage = completion.usage as any;
console.log(usage.text_tokens);
console.log(usage.image_tokens);
```

### Gotcha #3: Zod Unions Broken in v4.1.13+

**Issue**: [GitHub Issue #1709](https://github.com/openai/openai-node/issues/1709)

Using `zodResponseFormat()` with Zod 4.1.13+ breaks union type conversion:

```typescript
// ❌ Broken with Zod 4.1.13+
const schema = z.object({
  status: z.union([z.literal('success'), z.literal('error')]),
});

// ✅ Workaround: Use enum instead
const schema = z.object({
  status: z.enum(['success', 'error']),
});
```

**Alternatives**:
1. Downgrade to Zod 4.1.12
2. Use enum instead of union
3. Manually construct JSON schema
```

---

**Research Completed**: 2026-01-20 16:30
**Next Research Due**: After GPT-5.3 or major SDK release (check quarterly)

---

## Sources

### TIER 1 (Official)
- [OpenAI API Docs - GPT-5.2](https://platform.openai.com/docs/guides/latest-model)
- [OpenAI API Docs - GPT-5.2 Pro](https://platform.openai.com/docs/models/gpt-5.2-pro)
- [OpenAI Cookbook - GPT-5.2 Prompting Guide](https://cookbook.openai.com/examples/gpt-5/gpt-5-2_prompting_guide)
- [Azure OpenAI - Reasoning Models](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning?view=foundry-classic)
- [OpenAI Blog - Introducing GPT-5](https://openai.com/index/introducing-gpt-5-for-developers/)
- [OpenAI Blog - Introducing GPT-5.1](https://openai.com/index/gpt-5-1-for-developers/)
- [OpenAI Blog - Introducing GPT-5.2](https://openai.com/index/introducing-gpt-5-2/)
- [OpenAI API Docs - Batch API](https://platform.openai.com/docs/guides/batch)
- [OpenAI API Docs - Realtime WebSocket](https://platform.openai.com/docs/guides/realtime-websocket)
- [OpenAI API Docs - Text to Speech](https://platform.openai.com/docs/guides/text-to-speech)
- [OpenAI Blog - Audio Models Update](https://developers.openai.com/blog/updates-audio-models)
- [GitHub openai/openai-node - Issue #1706](https://github.com/openai/openai-node/issues/1706)
- [GitHub openai/openai-node - Issue #1690](https://github.com/openai/openai-node/issues/1690)
- [GitHub openai/openai-node - Issue #1718](https://github.com/openai/openai-node/issues/1718)
- [GitHub openai/openai-node - Issue #1709](https://github.com/openai/openai-node/issues/1709)
- [GitHub openai/openai-node - Issue #1402](https://github.com/openai/openai-node/issues/1402)
- [GitHub openai/openai-node - Release v6.16.0](https://github.com/openai/openai-node/releases/tag/v6.16.0)

### TIER 2 (High-Quality Community)
- [Daniel Gomm - OpenAI Batch API Guide](https://www.daniel-gomm.com/blog/2025/openbatch/)
- [Miko Engineering - Batch API Cost Savings](https://engineering.miko.ai/save-50-on-openai-api-costs-using-batch-requests-6ad41214b4ac)
- [Skywork AI - DALL-E 3 2025 Review](https://skywork.ai/skypage/en/DALL-E-3-In-Depth-(2025):-My-Hands-On-Review,-Benchmarks,-and-Practical-Guide/1976472460575436800)

### TIER 3 (Community Consensus)
- [OpenAI Community - Function Calling with previous_response_id](https://community.openai.com/t/openai-responses-api-no-tool-output-found-for-function-call-when-using-previous-response-id-anyone-have-a-stable-workaround/1354672)
- [OpenAI Community - DALL-E 3 Prompt Changes](https://community.openai.com/t/api-image-generation-in-dall-e-3-changes-my-original-prompt-without-my-permission/476355)
- [n8n Community - Embeddings Dimensions](https://community.n8n.io/t/how-to-change-openai-embedding-dimensions-to-256/56301)
- [GitHub mem0ai/mem0 - Issue #2302](https://github.com/mem0ai/mem0/issues/2302)
