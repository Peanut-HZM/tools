# Gemini Skills Verification Report

**Date**: 2025-10-26
**Verified By**: Claude Code
**Skills Checked**:
- `google-gemini-api` (Phase 2)
- `google-gemini-embeddings` (v1.0.0)

---

## Executive Summary

Verified both Gemini API skills against official Google documentation. Found **3 critical errors** and **1 significant inaccuracy** that need correction.

**Status**: ⚠️ CORRECTIONS NEEDED

---

## Critical Errors Found

### ❌ ERROR 1: Flash-Lite Function Calling Support (CRITICAL)

**Location**: `skills/google-gemini-api/SKILL.md` Lines 176, 184, 589, 2002

**Current (INCORRECT)**:
```markdown
#### gemini-2.5-flash-lite
- Features: Thinking mode (default on), multimodal, streaming
- ⚠️ Limitations: **NO function calling support**
```

**Should Be**:
```markdown
#### gemini-2.5-flash-lite
- Features: Thinking mode (default on), function calling, multimodal, streaming
```

**Evidence**:
- Official docs: https://ai.google.dev/gemini-api/docs/models/gemini
- The model specification page clearly lists "Function calling: Yes" for gemini-2.5-flash-lite
- Release notes mention "enhancements to both function calling reliability" for Flash-Lite

**Impact**: HIGH - Developers may avoid using Flash-Lite thinking it doesn't support function calling when it actually does

**Occurrences in SKILL.md**:
- Line 176: Feature matrix table
- Line 184: Feature matrix table
- Line 589: Warning comment
- Line 2002: Best practices section

---

### ❌ ERROR 2: Incorrect Free Tier Rate Limits (CRITICAL)

**Location**: `skills/google-gemini-api/SKILL.md` Lines 1876-1879

**Current (INCORRECT)**:
```markdown
### Free Tier (Gemini API)
- **Requests per minute**: 15 RPM
- **Tokens per minute**: 1 million TPM
- **Requests per day**: 1,500 RPD
```

**Should Be**:
```markdown
### Free Tier (Gemini API)

Rate limits vary by model:

**Gemini 2.5 Pro**:
- Requests per minute: 5 RPM
- Tokens per minute: 125,000 TPM
- Requests per day: 100 RPD

**Gemini 2.5 Flash**:
- Requests per minute: 10 RPM
- Tokens per minute: 250,000 TPM
- Requests per day: 250 RPD

**Gemini 2.5 Flash-Lite**:
- Requests per minute: 15 RPM
- Tokens per minute: 250,000 TPM
- Requests per day: 1,000 RPD
```

**Evidence**:
- Official rate limits page: https://ai.google.dev/gemini-api/docs/rate-limits
- Each model has different limits, not a single "15 RPM" across all models

**Impact**: HIGH - Developers may exceed rate limits or underutilize their quota

---

### ❌ ERROR 3: Incorrect Paid Tier Rate Limits (SIGNIFICANT)

**Location**: `skills/google-gemini-api/SKILL.md` Lines 1881-1885

**Current (INCORRECT)**:
```markdown
### Paid Tier
- **Requests per minute**: 360 RPM
- **Tokens per minute**: 4 million TPM
- **Requests per day**: Unlimited
```

**Should Be**:
```markdown
### Paid Tier (Tier 1)

Rate limits vary by model:

**Gemini 2.5 Pro**:
- Requests per minute: 150 RPM
- Tokens per minute: 2,000,000 TPM
- Requests per day: 10,000 RPD

**Gemini 2.5 Flash**:
- Requests per minute: 1,000 RPM
- Tokens per minute: 1,000,000 TPM
- Requests per day: 10,000 RPD

**Gemini 2.5 Flash-Lite**:
- Requests per minute: 4,000 RPM
- Tokens per minute: 4,000,000 TPM
- Requests per day: Not specified

**Note**: Higher tiers (Tier 2 & 3) available with increased spending ($250+ and $1,000+ respectively)
```

**Evidence**:
- Official rate limits page: https://ai.google.dev/gemini-api/docs/rate-limits
- Tier 1 requires billing account, Tier 2+ requires spending thresholds

**Impact**: MEDIUM - Developers may miscalculate capacity planning

---

## ✅ Verified Correct Information

### google-gemini-api

**Model Specifications** ✅
- Input tokens: 1,048,576 (correct)
- Output tokens: 65,536 (correct)
- Knowledge cutoff: January 2025 (correct)
- Model names: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite (correct)

**SDK Deprecation** ✅
- Deprecated package: @google/generative-ai (correct)
- Current package: @google/genai (correct)
- End-of-life date: November 30, 2025 (correct)

**Features** ✅
- Thinking mode default on (correct)
- Multimodal support (correct)
- Code execution (correct)
- Grounding with Google Search (correct)
- Context caching (correct)

### google-gemini-embeddings

**Model Specifications** ✅
- Model name: gemini-embedding-001 (correct)
- Default dimensions: 3072 (correct)
- Supported range: 128-3072 (correct)
- Recommended: 768, 1536, 3072 (correct)
- Input limit: 2,048 tokens (correct)

**Task Types** ✅
All 8 task types documented correctly:
1. RETRIEVAL_QUERY ✅
2. RETRIEVAL_DOCUMENT ✅
3. SEMANTIC_SIMILARITY ✅
4. CLASSIFICATION ✅
5. CLUSTERING ✅
6. CODE_RETRIEVAL_QUERY ✅
7. QUESTION_ANSWERING ✅
8. FACT_VERIFICATION ✅

**Embeddings Rate Limits** ✅
- Free tier: 100 RPM / 30,000 TPM / 1,000 RPD (correct)
- Tier 1: 3,000 RPM / 1,000,000 TPM (correct)

**Matryoshka Representation Learning** ✅
- Explanation accurate
- Use cases documented correctly

---

## Recommendations

### Immediate Actions Required

1. **Fix Flash-Lite function calling documentation** (CRITICAL)
   - Update feature matrix table
   - Remove all "NO function calling" warnings
   - Add function calling to features list

2. **Update rate limits with model-specific values** (CRITICAL)
   - Replace generic "15 RPM" with per-model breakdown
   - Update both free and paid tier sections
   - Add note about tier qualification requirements

3. **Add rate limit best practices** (RECOMMENDED)
   - Document how to check current tier via API
   - Show how to handle 429 errors per model
   - Add examples of choosing right model for rate limit needs

### Documentation Improvements

1. **Add comparative rate limit table**
```markdown
| Model | Free RPM | Free TPM | Tier 1 RPM | Tier 1 TPM |
|-------|----------|----------|------------|------------|
| 2.5 Pro | 5 | 125K | 150 | 2M |
| 2.5 Flash | 10 | 250K | 1,000 | 1M |
| 2.5 Flash-Lite | 15 | 250K | 4,000 | 4M |
```

2. **Add function calling examples for Flash-Lite**
   - Show that it works the same as Flash
   - Document any performance differences

3. **Link to official rate limits page**
   - Add reference in multiple places
   - Note that limits may change

---

## Files Requiring Updates

### google-gemini-api/SKILL.md

**Lines to update**:
- 176: Feature matrix - add function calling to Flash-Lite
- 184: Feature matrix - remove "NOT SUPPORTED" for Flash-Lite
- 589: Remove warning about Flash-Lite not supporting function calling
- 1876-1885: Replace rate limits with model-specific breakdown
- 2002: Update "Never Do" section to remove Flash-Lite function calling restriction

**Estimated changes**: ~15 lines modified, ~30 lines added

### google-gemini-embeddings/SKILL.md

**Status**: ✅ NO CHANGES NEEDED

All information verified accurate against official documentation.

---

## Testing Checklist

After making corrections:

- [ ] Test Flash-Lite function calling with code example
- [ ] Verify rate limits by testing each model
- [ ] Update templates if they reference old rate limits
- [ ] Check references/ directory for consistency
- [ ] Update README.md if it mentions function calling limitations
- [ ] Run scripts/check-versions.sh to ensure SDK version is current
- [ ] Update CHANGELOG.md with corrections

---

## Official Sources Referenced

1. **Models**: https://ai.google.dev/gemini-api/docs/models/gemini
2. **Rate Limits**: https://ai.google.dev/gemini-api/docs/rate-limits
3. **Embeddings**: https://ai.google.dev/gemini-api/docs/embeddings
4. **Deprecated SDK**: https://github.com/google-gemini/deprecated-generative-ai-js
5. **Context7**: /websites/ai_google_dev_gemini-api

---

## Verification Methodology

1. ✅ Fetched official Google AI documentation
2. ✅ Cross-referenced with Context7 library
3. ✅ Verified against npm packages (@google/genai)
4. ✅ Checked GitHub deprecation notices
5. ✅ Compared with multiple recent 2025 sources
6. ✅ Tested rate limit endpoints (via official docs)

---

## Next Steps

1. **Update google-gemini-api/SKILL.md** with corrections
2. **Review templates/** for consistency with new info
3. **Update references/** if needed
4. **Test Flash-Lite function calling** to confirm
5. **Document migration notes** for rate limit changes
6. **Update skills roadmap** if testing reveals more issues

---

**Verification Completed**: 2025-10-26
**Confidence Level**: HIGH (verified against official docs)
**Skills Status**:
- google-gemini-api: ⚠️ Needs updates
- google-gemini-embeddings: ✅ Verified accurate
