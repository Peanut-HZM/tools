# Community Knowledge Research: google-gemini-embeddings

**Research Date**: 2026-01-21
**Packages Researched**: @google/genai (v1.37.0), gemini-embedding-001 model
**Official Repo**: googleapis/js-genai (NEW - replaces google/generative-ai-js which is deprecated)
**Time Window**: May 2025 - January 2026 (post-training-cutoff focus)

---

## Executive Summary

### Critical Discovery: SDK Migration

**MAJOR BREAKING CHANGE**: Google deprecated `google/generative-ai-js` and released a new unified SDK `@google/genai` in May 2025. The old SDK reaches end-of-life on **November 30, 2025**.

**Current Skill Status**: Uses outdated package name and API patterns from deprecated SDK.

### Research Results

- **Total Findings**: 8 (5 TIER 1, 2 TIER 2, 1 TIER 3)
- **TIER 1 (Official)**: 5 findings from GitHub issues and official docs
- **TIER 2 (High-Quality Community)**: 2 findings from developer blogs and community consensus
- **TIER 3 (Community Tips)**: 1 finding requiring verification
- **TIER 4 (Low Confidence)**: 0 findings

### Top Priority Actions

1. **URGENT**: Update skill to reference new `@google/genai` SDK (migration required)
2. **HIGH**: Document normalization requirement for non-3072 dimensions
3. **HIGH**: Add batch API ordering bug warning
4. **MEDIUM**: Document batch API memory limits for large payloads

---

## TIER 1 Findings (Official Sources)

### 1.1 SDK Migration Required (CRITICAL)

**Source**: [GitHub Repository Deprecation Notice](https://github.com/google-gemini/deprecated-generative-ai-js)
**Date**: May 2025
**Status**: Breaking Change - Migration Required

**Issue**:
- Old SDK `google/generative-ai-js` is deprecated
- End-of-life: November 30, 2025
- New SDK: `@google/genai` via `googleapis/js-genai`
- Current skill uses old package name and patterns

**Breaking API Changes**:

```typescript
// OLD SDK (deprecated)
const model = genAI.getGenerativeModel({
  model: "gemini-embedding-001",
});
const result = await model.embedContent("Hello world!");

// NEW SDK (@google/genai)
const ai = new GoogleGenAI({ apiKey: "GEMINI_API_KEY" });
const result = await ai.models.embedContent({
  model: "gemini-embedding-001",
  contents: text,
  config: { outputDimensionality: 768 },
});
```

**Key Changes**:
1. Package name: `@google/generative-ai` → `@google/genai`
2. API access: `genAI.getGenerativeModel()` → `ai.models.embedContent()`
3. Method structure: Model-based → Centralized client
4. Config object: Parameters now in `config: {}` object

**Reproduction**: Install current skill package - it uses deprecated SDK.

**Solution**:
- Update all package.json templates to `@google/genai@^1.37.0`
- Update all code examples to new API pattern
- Add migration guide to skill
- Update version references from `1.27.0` to `1.37.0`

**Verification**: Official migration guide at https://ai.google.dev/gemini-api/docs/migrate

**Confidence**: 100% - Official deprecation notice

---

### 1.2 Normalization Required for Non-3072 Dimensions

**Source**: [Official Embeddings Documentation](https://ai.google.dev/gemini-api/docs/embeddings)
**Date**: Updated June 2025
**Status**: Documented Limitation (Missing from Skill)

**Issue**:
Only 3072-dimensional embeddings are pre-normalized. **All other dimensions (128-3071) require manual normalization** for accurate similarity calculations.

**Why It Matters**:
Non-normalized embeddings have varying magnitudes that distort cosine similarity:
- Correct similarity range: -1.0 to 1.0 (normalized)
- Without normalization: Unpredictable results, incorrect rankings

**Code Example (Missing from Skill)**:

```typescript
// When using 768 or 1536 dimensions
const response = await ai.models.embedContent({
  model: 'gemini-embedding-001',
  content: text,
  config: {
    taskType: 'RETRIEVAL_QUERY',
    outputDimensionality: 768  // NOT 3072
  }
});

// ❌ WRONG - Use raw values directly
const embedding = response.embedding.values;
await vectorize.insert([{ id, values: embedding }]);

// ✅ CORRECT - Normalize first
function normalize(vector: number[]): number[] {
  const magnitude = Math.sqrt(vector.reduce((sum, val) => sum + val * val, 0));
  return vector.map(val => val / magnitude);
}

const normalized = normalize(response.embedding.values);
await vectorize.insert([{ id, values: normalized }]);
```

**Reproduction**:
1. Get embeddings with `outputDimensionality: 768`
2. Compare two similar texts using raw values
3. Results will be incorrect due to magnitude differences

**Solution**:
Add normalization helper function to skill templates and document requirement in SKILL.md.

**Verification**: Official docs state "For dimensions other than 3072, you must normalize embeddings manually."

**Confidence**: 100% - Official documentation

**Related**: [Medium Article on Dimension Mismatch](https://medium.com/@henilsuhagiya0/how-to-fix-the-common-gemini-langchain-embedding-dimension-mismatch-768-vs-3072-6eb1c468729b)

---

### 1.3 Batch API Ordering Bug (CRITICAL)

**Source**: [GitHub Issue #1207](https://github.com/googleapis/js-genai/issues/1207)
**Date**: December 18, 2025
**Status**: Open - Acknowledged by maintainer

**Issue**:
Batch embedding API does not preserve ordering with large batch sizes. Example: entry 328 appears in position 628.

**Impact**:
- Results cannot be reliably matched back to input texts
- Silent data corruption - no error thrown
- Affects both embeddings and other batch APIs
- Marked as P0 (critical priority) by community

**Reproduction**:
```typescript
const texts = Array.from({ length: 1000 }, (_, i) => `Text ${i}`);
const response = await ai.models.embedContent({
  model: 'gemini-embedding-001',
  contents: texts,
  config: { taskType: 'RETRIEVAL_DOCUMENT', outputDimensionality: 768 }
});

// response.embeddings[328] might contain embedding for texts[628]
// NO ERROR - silent corruption
```

**Workaround**:
Until fixed, process smaller batches (< 100 texts) or add unique identifiers in text content to verify ordering.

```typescript
// Safer approach with verification
const taggedTexts = texts.map((text, i) => `[ID:${i}] ${text}`);
const response = await ai.models.embedContent({
  model: 'gemini-embedding-001',
  contents: taggedTexts,
  config: { taskType: 'RETRIEVAL_DOCUMENT', outputDimensionality: 768 }
});

// Verify ordering by parsing IDs from metadata if available
```

**Verification**: Maintainer comment confirms internal bug created.

**Confidence**: 100% - Official issue with maintainer acknowledgment

---

### 1.4 Batch API Memory Error with Large Payloads

**Source**: [GitHub Issue #1205](https://github.com/googleapis/js-genai/issues/1205)
**Date**: December 18, 2025
**Status**: Open - Design Limitation

**Issue**:
Batch API crashes with `ERR_STRING_TOO_LONG` when response exceeds 512MB (~11,764 categories at 768 dimensions).

**Root Cause**:
API response contains "vast amounts of whitespace around each element" causing response size to balloon. Node.js string limit is ~536MB.

**Error**:
```
Error: Cannot create a string longer than 0x1fffffe8 characters
    at TextDecoder.decode (node:internal/encoding:447:16)
```

**Reproduction Example** (from issue):
```typescript
// Shopify product taxonomy: 11,764 categories
const categories = parseCategories(categoryTxt); // 11,764 items

const batchJob = await googleGenAI.batches.createEmbeddings({
  model: 'gemini-embedding-001',
  src: {
    inlinedRequests: {
      contents: categories.map(c => ({ text: c.name })),
      config: { taskType: 'SEMANTIC_SIMILARITY', outputDimensionality: 768 }
    }
  },
  config: { displayName: 'Categories Batch' }
});

// Poll until complete
while (!completedStates.has(batchJob.state)) {
  await new Promise(resolve => setTimeout(resolve, 30000));
  batchJob = await googleGenAI.batches.get({ name: jobName });
}

// CRASH: ERR_STRING_TOO_LONG when trying to download results
```

**Limitations**:
- Inline requests: 20MB max request size
- Response size: Practically limited to ~10k embeddings due to whitespace
- No streaming option for batch results

**Workaround**:
Chunk into smaller batches (< 5,000 texts per batch) or use file-based batch API instead of inline.

**Verification**: Reproducible code example provided in issue.

**Confidence**: 100% - Verified bug with reproduction steps

---

### 1.5 Batch API Returns 429 Despite Being Under Quota

**Source**: [GitHub Issue #1264](https://github.com/googleapis/js-genai/issues/1264)
**Date**: January 19, 2026
**Status**: Open - Under Investigation

**Issue**:
Batch API returns `429 RESOURCE_EXHAUSTED` errors even when well under documented quota limits.

**Details**:
- User reports being under quota limits
- Getting 429 errors from Batch API
- Maintainer requested private project ID to investigate

**Status**: Under investigation by Google team (private Gist created for debugging)

**Workaround**: None yet - investigation ongoing

**Verification**: Maintainer actively investigating

**Confidence**: 90% - Official issue but root cause not yet confirmed

---

## TIER 2 Findings (High-Quality Community)

### 2.1 LangChain Dimension Mismatch Pattern

**Source**: [Medium Article](https://medium.com/@henilsuhagiya0/how-to-fix-the-common-gemini-langchain-embedding-dimension-mismatch-768-vs-3072-6eb1c468729b) + [GitHub Discussions](https://github.com/orgs/supabase/discussions/34547)
**Date**: 2025
**Validation**: Multiple sources confirm same issue

**Issue**:
When using LangChain's `GoogleGenerativeAIEmbeddings` class, the `output_dimensionality` parameter is **silently ignored** when passed to the constructor. Library creates default 3072-dimension vectors regardless.

**Why This Happens**:
```python
# ❌ WRONG - parameter silently ignored
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    output_dimensionality=768  # IGNORED!
)

result = embeddings.embed_documents(["text"])
# Returns 3072 dimensions, not 768

# Database expects 768 → DIMENSION MISMATCH ERROR
```

**Correct Pattern**:
```python
# ✅ CORRECT - pass to method, not constructor
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001"
)

result = embeddings.embed_documents(
    ["text"],
    output_dimensionality=768  # Pass here
)
# Returns 768 dimensions as expected
```

**JavaScript Equivalent Caution**:
While this is a Python issue, JavaScript users should verify the new `@google/genai` SDK doesn't have similar silent-fail behavior.

**Verification**: Multiple community reports + Supabase discussion thread

**Confidence**: 85% - Multiple sources, but LangChain-specific (may not apply to JS SDK)

---

### 2.2 batchEmbedContents Used Even for Single Requests

**Source**: [GitHub Issue #427 (Python SDK)](https://github.com/googleapis/python-genai/issues/427)
**Date**: March 2, 2025
**Validation**: Official issue in googleapis organization

**Issue**:
The `embed_content()` function (for single text) internally calls the `batchEmbedContents` endpoint. This causes:
1. Higher rate limit consumption (batch endpoint has different limits)
2. Easier to hit 429 errors even for small workloads
3. Unexpected rate limit behavior

**Impact**:
Users embedding single texts may hit rate limits faster than expected because the SDK routes all embedding calls through the batch endpoint.

**Workaround** (from issue comments):
```python
# Add delays between single embedding requests
import time

for text in texts:
    embedding = embed_content(text)
    time.sleep(10)  # Avoid rate limits
```

**JavaScript Relevance**:
Need to verify if `@google/genai` has the same behavior. If so, users should be warned that:
- Single `embedContent()` calls count against batch limits
- Rate limiting may be stricter than expected

**Verification**: Official issue in Google's repository

**Confidence**: 80% - Confirmed for Python SDK, needs verification for JS SDK

---

## TIER 3 Findings (Community Consensus - Verify Before Adding)

### 3.1 URL Processing Crash (Needs Verification)

**Source**: [Google AI Forum Discussion](https://discuss.ai.google.dev/t/models-gemini-embedding-001-crashes-with-urls-in-text-when-embedding-001-does-not/97540)
**Date**: August 2025
**Status**: Community Report - Unverified

**Issue**:
User reports that `gemini-embedding-001` crashes with 500 Internal Server Error when text contains URLs, while older `embedding-001` model handles URLs fine.

**Example**:
```
Text: "Check out https://example.com for more info"
Result: 500 Internal Server Error
```

**Why TIER 3**:
- Single source (forum discussion)
- No reproduction steps provided
- No maintainer confirmation
- Could be specific to LangChain integration, not direct API

**Action Required**:
1. Test with direct API (both REST and SDK)
2. Try various URL formats (http, https, with/without protocol)
3. Check if issue still present in latest SDK version (1.37.0)
4. If reproducible, escalate to GitHub issue

**DO NOT ADD TO SKILL** until verified with reproduction steps.

**Confidence**: 40% - Single unverified source

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

*No TIER 4 findings identified.*

---

## Recommended Actions (Priority Order)

### 🔴 URGENT (P0) - Breaking Changes

#### 1. Update SDK References (Entire Skill)
**Files to Update**:
- `SKILL.md` (all code examples)
- `templates/package.json` (dependencies)
- `templates/*.ts` (all import statements)
- `README.md` (version references)

**Changes**:
```json
// OLD
{
  "dependencies": {
    "@google/generative-ai": "^1.27.0"
  }
}

// NEW
{
  "dependencies": {
    "@google/genai": "^1.37.0"
  }
}
```

```typescript
// OLD
import { GoogleGenerativeAI } from "@google/generative-ai";
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-embedding-001" });
const result = await model.embedContent("text");

// NEW
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const result = await ai.models.embedContent({
  model: 'gemini-embedding-001',
  content: 'text',
  config: { taskType: 'RETRIEVAL_QUERY', outputDimensionality: 768 }
});
```

**Estimated Effort**: 2-3 hours (40+ code blocks to update)

---

#### 2. Add Migration Guide
**File**: `references/migration-guide.md` (new file)

**Content**:
- Side-by-side comparison of old vs new API
- Step-by-step migration checklist
- Breaking changes list
- Common migration errors and solutions

**Estimated Effort**: 30 minutes

---

### 🟠 HIGH (P1) - Critical Missing Content

#### 3. Document Normalization Requirement
**Files**:
- `SKILL.md` (Section 3 - Basic Embeddings)
- `templates/basic-embeddings.ts`
- `references/dimension-guide.md` (expand)

**Add Normalization Helper**:
```typescript
/**
 * Normalize embedding vector for accurate similarity calculations.
 * REQUIRED for dimensions other than 3072.
 *
 * @param vector - Embedding values from API response
 * @returns Normalized vector (unit length)
 */
function normalize(vector: number[]): number[] {
  const magnitude = Math.sqrt(
    vector.reduce((sum, val) => sum + val * val, 0)
  );
  return vector.map(val => val / magnitude);
}

// Usage
const response = await ai.models.embedContent({
  model: 'gemini-embedding-001',
  content: text,
  config: { outputDimensionality: 768 } // Not 3072
});

const normalized = normalize(response.embedding.values);
// Now safe to use for similarity calculations
```

**Update Section 8 (Best Practices)**:
Add prominent warning:
```markdown
⚠️ **CRITICAL**: When using dimensions other than 3072, you MUST normalize embeddings before computing similarity. Only 3072-dimensional embeddings are pre-normalized.
```

**Estimated Effort**: 45 minutes

---

#### 4. Add Batch API Warnings
**File**: `SKILL.md` Section 4 (Batch Embeddings)

**Add Gotchas Section**:
```markdown
### Batch API Known Issues

⚠️ **Ordering Bug (Dec 2025)**: Batch API may not preserve ordering with large batch sizes (>500 texts).
- **Symptom**: Entry 328 appears at position 628
- **Workaround**: Process smaller batches (<100 texts) or add unique IDs to verify ordering
- **Status**: Acknowledged by Google, internal bug created
- **Source**: [GitHub Issue #1207](https://github.com/googleapis/js-genai/issues/1207)

⚠️ **Memory Limit (Dec 2025)**: Large batches (>10k embeddings) can cause `ERR_STRING_TOO_LONG` crash.
- **Cause**: API response includes excessive whitespace
- **Workaround**: Limit to <5,000 texts per batch
- **Source**: [GitHub Issue #1205](https://github.com/googleapis/js-genai/issues/1205)
```

**Update Rate Limiting Section**:
```typescript
// SAFER: Smaller batches until ordering bug is fixed
async function batchEmbedWithSafety(
  texts: string[],
  batchSize: number = 50 // Reduced from 100
) {
  // Existing implementation
}
```

**Estimated Effort**: 20 minutes

---

### 🟡 MEDIUM (P2) - Documentation Improvements

#### 5. Update Error Reference
**File**: `references/top-errors.md`

**Add New Errors**:
```markdown
## Error 9: Dimension Mismatch (Normalization Required)

**Error Message**: Similarity results incorrect, no error thrown

**Cause**: Using non-normalized embeddings for dimensions other than 3072

**Solution**: Always normalize embeddings when using 768 or 1536 dimensions

## Error 10: ERR_STRING_TOO_LONG

**Error Message**: `Cannot create a string longer than 0x1fffffe8 characters`

**Cause**: Batch response exceeds Node.js string limit (~536MB)

**Solution**: Reduce batch size to <5,000 texts
```

**Estimated Effort**: 15 minutes

---

#### 6. Verify and Document Task Type Restrictions
**Investigation Needed**: Check if `text-embedding-005` limitations apply to `gemini-embedding-001`

**Reference**: [Issue #549](https://github.com/googleapis/js-genai/issues/549) - Some models don't support all task types

**Action**: Test all 8 task types with `gemini-embedding-001` and document any restrictions.

**Estimated Effort**: 30 minutes (testing) + 15 minutes (documentation)

---

### 🟢 LOW (P3) - Nice to Have

#### 7. Add SDK Comparison Table
**File**: `references/model-comparison.md`

**Add Column**:
```markdown
| Feature | Gemini (@google/genai) | OpenAI | Workers AI |
|---------|----------------------|--------|-----------|
| SDK Status | GA (May 2025) | Stable | Stable |
| Legacy SDK | Deprecated Nov 2025 | N/A | N/A |
```

**Estimated Effort**: 10 minutes

---

## Verification Testing Checklist

Before finalizing skill updates:

- [ ] Test new `@google/genai` SDK installation
- [ ] Verify all code examples run without errors
- [ ] Test normalization function with 768/1536/3072 dimensions
- [ ] Test batch processing with 10/100/1000/5000 texts
- [ ] Verify task types work as documented
- [ ] Test Vectorize integration with normalized embeddings
- [ ] Verify migration guide steps work

---

## Cross-Reference with Existing Skill Content

### Already Documented (No Action Needed)

✅ **Rate Limits**: Section 2 covers 100 RPM free tier
✅ **Task Types**: Section 5 covers all 8 task types
✅ **Dimension Options**: Section 2 mentions 768/1536/3072
✅ **Batch Processing**: Section 4 covers batch API
✅ **Error Handling**: Section 7 covers common errors

### Missing (Added by This Research)

❌ **Normalization Requirement**: NOT mentioned for non-3072 dimensions
❌ **SDK Migration**: Still references deprecated package
❌ **Batch Ordering Bug**: NOT documented
❌ **Memory Limits**: NOT documented
❌ **batchEmbedContents Behavior**: NOT explained

---

## Package Version Status

| Package | Current in Skill | Latest Available | Recommendation |
|---------|-----------------|------------------|----------------|
| @google/generative-ai | 1.27.0 | DEPRECATED | ❌ Remove |
| @google/genai | NOT USED | 1.37.0 | ✅ Add |

**Action**: Complete package migration required.

---

## Sources

### TIER 1 (Official)
- [googleapis/js-genai GitHub](https://github.com/googleapis/js-genai)
- [Migration Guide](https://ai.google.dev/gemini-api/docs/migrate)
- [Official Embeddings Docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Issue #1207 - Batch Ordering](https://github.com/googleapis/js-genai/issues/1207)
- [Issue #1205 - Memory Limit](https://github.com/googleapis/js-genai/issues/1205)
- [Issue #1264 - Rate Limit](https://github.com/googleapis/js-genai/issues/1264)
- [Deprecated SDK Notice](https://github.com/google-gemini/deprecated-generative-ai-js)

### TIER 2 (High-Quality Community)
- [Medium: Dimension Mismatch Fix](https://medium.com/@henilsuhagiya0/how-to-fix-the-common-gemini-langchain-embedding-dimension-mismatch-768-vs-3072-6eb1c468729b)
- [Supabase Discussion: Gemini Embedding](https://github.com/orgs/supabase/discussions/34547)
- [Python SDK Issue #427](https://github.com/googleapis/python-genai/issues/427)
- [Google Developers Blog: Gemini Embedding GA](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)

### TIER 3 (Verify First)
- [Forum: URL Processing Bug](https://discuss.ai.google.dev/t/models-gemini-embedding-001-crashes-with-urls-in-text-when-embedding-001-does-not/97540)

---

## Research Metadata

**Researcher**: Claude Code (skill-researcher agent)
**Research Duration**: ~15 minutes
**GitHub Issues Reviewed**: 12
**Web Sources Checked**: 8
**Official Docs Reviewed**: 3
**Stack Overflow Posts**: 0 (no relevant results found)

**Stop Conditions Met**:
- Time limit: Within 15 minutes ✅
- Finding limit: 8 findings < 15 max ✅
- Diminishing returns: Last 2 searches yielded no new findings ✅

**Next Steps**:
1. Skill owner reviews findings
2. Prioritize P0 (SDK migration) immediately
3. Create tasks for P1 items (normalization, batch warnings)
4. Test TIER 3 finding before adding

---

**Last Updated**: 2026-01-21
**Review By**: 2026-02-21 (monthly check for new issues)
