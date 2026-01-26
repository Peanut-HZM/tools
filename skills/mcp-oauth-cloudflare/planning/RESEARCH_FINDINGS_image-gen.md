# Community Knowledge Research: image-gen

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/image-gen/SKILL.md
**Packages Researched**: @google/genai@1.38.0, gemini-3-pro-image-preview, gemini-2.5-flash-image
**Official Repo**: googleapis/js-genai (NEW), google-gemini/generative-ai-js (DEPRECATED)
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 6 |
| TIER 2 (High-Quality Community) | 4 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 9 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: SDK Migration - @google/generative-ai is Deprecated

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Repository](https://github.com/google-gemini/deprecated-generative-ai-js) | [Release v0.24.1](https://github.com/google-gemini/deprecated-generative-ai-js/releases/tag/v0.24.1)
**Date**: 2025-04-29 (Support ends 2025-11-30)
**Verified**: Yes
**Impact**: CRITICAL
**Already in Skill**: No

**Description**:
The original `@google/generative-ai` package is now officially deprecated. All support ends November 30, 2025. Google created a unified SDK `@google/genai` for all GenAI models (Gemini, Veo, Imagen, etc.).

**Migration Required**:
```typescript
// OLD (deprecated)
import { GoogleGenerativeAI } from "@google/generative-ai";
const genAI = new GoogleGenerativeAI(API_KEY);

// NEW (current)
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({});
```

**Official Status**:
- [x] Deprecated - migration required by November 30, 2025
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [ ] Won't fix

**Cross-Reference**:
- Current skill uses old package name in examples
- Skill needs complete API migration

---

### Finding 1.2: Model Lifecycle Changes - Multiple Deprecations

**Trust Score**: TIER 1 - Official
**Source**: [Google AI Changelog](https://ai.google.dev/gemini-api/docs/changelog)
**Date**: 2025-11-11 (deprecation), 2025-12-04 (scheduled shutdown)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Several image generation models have been deprecated with scheduled shutdowns:

- `gemini-2.0-flash-exp-image-generation` - Shut down November 11, 2025
- `gemini-2.0-flash-preview-image-generation` - Shut down November 11, 2025
- `gemini-2.5-flash-image-preview` - Scheduled shutdown January 15, 2026

**Current Recommended Models**:
```typescript
// GA models (stable)
"gemini-2.5-flash-image"  // General availability Oct 2, 2025
"gemini-3-pro-image-preview"  // Released Nov 20, 2025
"imagen-4.0-generate-001"  // GA Aug 14, 2025

// Don't use
"gemini-2.0-flash-exp-image-generation"  // SHUT DOWN
"gemini-2.5-flash-image-preview"  // SHUTTING DOWN JAN 15
```

**Official Status**:
- [x] Documented behavior
- [x] Known issue, workaround required (migrate to new models)
- [ ] Fixed in version X.Y.Z
- [ ] Won't fix

**Cross-Reference**:
- Skill references `gemini-3-flash-image-generation` and `gemini-3-pro-image-generation` which may be outdated
- Need to verify current model naming conventions

---

### Finding 1.3: Resolution Parameter Case Sensitivity

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Google AI Image Generation Docs](https://ai.google.dev/gemini-api/docs/image-generation)
**Date**: 2025 (current)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Resolution parameters are case-sensitive and must use uppercase 'K'. Lowercase will cause request failures.

**Reproduction**:
```typescript
// ❌ WRONG - causes request failure
const response = await ai.models.generateContent({
  model: "gemini-3-pro-image-preview",
  contents: "Professional plumber",
  config: {
    imageGenerationConfig: {
      resolution: "4k",  // lowercase fails
    },
  },
});
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - uppercase required
const response = await ai.models.generateContent({
  model: "gemini-3-pro-image-preview",
  contents: "Professional plumber",
  config: {
    imageGenerationConfig: {
      resolution: "4K",  // uppercase K required
    },
  },
});
```

**Official Status**:
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [ ] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.4: Reference Image Limits

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Google AI Image Generation Docs](https://ai.google.dev/gemini-api/docs/image-generation)
**Date**: 2025 (current)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: Partially

**Description**:
Gemini 3 Pro Image supports up to 14 reference images, but only 5 can be human images for character consistency. Exceeding this causes unpredictable results.

**Reproduction**:
```typescript
// ❌ WRONG - 7 human images exceeds limit
const prompt = [
  { text: "Generate consistent characters" },
  ...sevenHumanImages.map(img => ({ inlineData: { data: img, mimeType: "image/png" }})),
];
// Result: Unpredictable character consistency
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - max 5 human images
const humanImages = images.slice(0, 5);
const objectImages = images.slice(5, 14);

const prompt = [
  { text: "Generate consistent characters" },
  ...humanImages.map(img => ({ inlineData: { data: img, mimeType: "image/png" }})),
  ...objectImages.map(img => ({ inlineData: { data: img, mimeType: "image/png" }})),
];
```

**Official Status**:
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Skill mentions "up to 14 reference images (6 objects, 5 humans)"
- Should clarify that exceeding 5 humans causes unpredictable results

---

### Finding 1.5: SynthID Watermark Cannot Be Disabled

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Google AI Image Generation Docs](https://ai.google.dev/gemini-api/docs/image-generation)
**Date**: 2025 (current)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
All generated images automatically include a SynthID watermark. This cannot be disabled by developers.

**Official Status**:
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Should be added to limitations section
- Important for commercial use cases

---

### Finding 1.6: Google Search Grounding Limitation

**Trust Score**: TIER 1 - Official Documentation
**Source**: [Google AI Image Generation Docs](https://ai.google.dev/gemini-api/docs/image-generation)
**Date**: 2025 (current)
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using Google Search tool with image generation, "image-based search results are not passed to the generation model and are excluded from the response." Only text-based search results inform the visual output.

**Reproduction**:
```typescript
// Google Search tool enabled
const response = await ai.models.generateContent({
  model: "gemini-3-pro-image-preview",
  contents: "Generate image of latest iPhone design",
  tools: [{ googleSearch: {} }],
  config: { responseModalities: ["TEXT", "IMAGE"] },
});
// Result: Only text search results used, not image results
```

**Official Status**:
- [x] Documented behavior
- [ ] Fixed in version X.Y.Z
- [ ] Known issue, workaround required
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Aspect Ratio Ignored - Model Defaults to 1:1

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Google Support Thread](https://support.google.com/gemini/thread/371311134/) | [Developer Forum](https://discuss.ai.google.dev/t/gemini-2-5-flash-nano-banana-auto-aspect-ratio-issue-output-image-has-different-aspect-ratio/108225)
**Date**: September 2025
**Verified**: Multiple users confirm
**Impact**: HIGH
**Already in Skill**: No

**Description**:
After a backend update in early September 2025, the Nano Banana model began refusing to generate images in landscape orientation, defaulting to square 1:1 outputs despite requests for 16:9 widescreen images. Even when using API code with `aspectRatio: "16:9"`, the system returns 1:1 square images.

**Reproduction**:
```typescript
// ❌ May ignore aspect ratio (Sept 2025 onwards)
const response = await ai.models.generateContent({
  model: "gemini-2.5-flash-image",
  contents: "A professional plumber in hi-vis",
  config: {
    responseModalities: ["TEXT", "IMAGE"],
    imageGenerationConfig: {
      aspectRatio: "16:9",  // May be ignored
    },
  },
});
// Result: Returns 1:1 square instead of 16:9
```

**Solution/Workaround**:
Google confirmed working on a fix. As of September 2025, workaround was to:
1. Use ImageFX instead for specific dimensions
2. Use Gemini 3 Pro Image Preview instead of 2.5 Flash
3. Generate 1:1 and crop/extend using multi-turn editing

**Community Validation**:
- Multiple users confirmed on Google Support
- Developers Forum discussions
- Google acknowledged and working on fix

**Official Response**: Google confirmed working on fix (September 2025)

---

### Finding 2.2: No usageMetadata for generateImages API

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #539](https://github.com/googleapis/js-genai/issues/539)
**Date**: 2025-05-07
**Verified**: Maintainer confirmed
**Impact**: LOW
**Already in Skill**: No

**Description**:
The `generateImages` API (Imagen models) does not return `usageMetadata` in the response, making it impossible to track token usage programmatically.

**Reproduction**:
```typescript
const response = await ai.models.generateImages({
  model: 'imagen-4.0-generate-001',
  prompt: 'Robot holding a red skateboard',
  config: { numberOfImages: 4 },
});

console.log(response.usageMetadata);  // undefined
```

**Solution/Workaround**:
Manually track costs based on pricing: $0.039 per image for Gemini 2.5 Flash Image (1290 tokens per image).

**Community Validation**:
- Contributor @sararob confirmed: "usageMetadata is not part of GenerateImagesResponse but I will share this feedback with the team."
- No fix timeline provided

---

### Finding 2.3: responseModalities Always Requires Both TEXT and IMAGE

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Cursor IDE Blog](https://www.cursor-ide.com/blog/gemini-3-pro-image-api)
**Date**: 2025
**Verified**: Documentation confirms
**Impact**: MEDIUM
**Already in Skill**: Partially (mentioned in Quick Start)

**Description**:
When using Gemini models for image generation, you cannot request image-only output. The API requires `responseModalities: ["TEXT", "IMAGE"]` - attempting to use `["IMAGE"]` alone may fail or produce unexpected results.

**Reproduction**:
```typescript
// ❌ May not work
const response = await ai.models.generateContent({
  model: "gemini-3-pro-image-preview",
  contents: "Professional plumber",
  config: {
    responseModalities: ["IMAGE"],  // Missing TEXT
  },
});
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - always include both
const response = await ai.models.generateContent({
  model: "gemini-3-pro-image-preview",
  contents: "Professional plumber",
  config: {
    responseModalities: ["TEXT", "IMAGE"],
  },
});
```

**Cross-Reference**:
- Skill shows this in Quick Start example
- Should be explicitly called out in limitations

---

### Finding 2.4: Pricing Change - Input Tokens Reduced 80%

**Trust Score**: TIER 2 - Official Blog Post
**Source**: [Google Developers Blog](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)
**Date**: November 4, 2025
**Verified**: Official announcement
**Impact**: MEDIUM (positive)
**Already in Skill**: No

**Description**:
On November 4, 2025, Google reduced input token costs for Gemini 2.5 Flash Image from 1290 to 258 tokens, lowering the cost per image from ~$0.039 to ~$0.008 per image.

**Current Pricing** (as of Nov 2025):
- Input: 258 tokens per image
- Output: 1290 tokens per image
- Rate: $30.00 per 1M output tokens
- Effective cost: ~$0.008 per image

**Cross-Reference**:
- Should update any pricing references in skill

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Text Rendering Quality Varies by Model

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Apiyi Blog](https://help.apiyi.com/gemini-3-pro-image-text-rendering-guide-en.html) | [Google DeepMind](https://deepmind.google/models/gemini-image/pro/)
**Date**: 2025
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM
**Already in Skill**: Partially (mentions Pro better for text)

**Description**:
Gemini 3 Pro Image achieves 94% legible text rendering at 4K resolution (tested with 100 generations), significantly outperforming DALL-E 3 (78%) and Midjourney (decorative pseudo-text). However, the model can still struggle with:
- Small faces in images
- Accurate spelling in complex words
- Fine details like consistent spacing

**Solution**:
For critical text legibility:
1. Use Gemini 3 Pro Image Preview (not Flash)
2. Use descriptive font descriptions ("bold sans-serif headline") instead of font names ("Arial Black")
3. 4K resolution helps
4. Keep text concise and avoid dense paragraphs

**Consensus Evidence**:
- Multiple blogs cite 94% benchmark
- Google DeepMind confirms text rendering as key feature
- Developer forum discussions confirm Flash < Pro for text

**Recommendation**: Add to skill as community-validated best practice

---

### Finding 3.2: Quality Degradation After May 2025 Update

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Google Developer Forum](https://discuss.ai.google.dev/t/gemini-2-0-flash-preview-image-generation-quality-reduction-in-recent-update/83644)
**Date**: May 2025
**Verified**: Multiple users reported
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Users reported that after a May 2025 update, the model performed "notably worse" with reduced coherence, and began automatically changing prompts by starting responses with "I will generate (its version of prompt)".

**Consensus Evidence**:
- Multiple forum posts in May 2025
- No official acknowledgment found
- May be specific to preview models

**Recommendation**: Monitor but don't add to skill (may be resolved, specific to deprecated models)

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None identified.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Reference images support (14 max) | Capabilities table | Fully covered |
| 4K resolution (Pro only) | Capabilities table | Fully covered |
| Text in images supported | Capabilities table, Model Selection | Partially covered, could expand with benchmarks |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 SDK Migration | New "Migration" section at top | Add critical notice about deprecated package |
| 1.2 Model Lifecycle | Update "Models" table | Replace deprecated models, add shutdown dates |
| 1.3 Resolution Case Sensitivity | New Known Issues section | Add as Issue #1 |
| 1.4 Reference Image Limits | Expand Capabilities section | Clarify 5-human limit and consequences |
| 1.5 SynthID Watermark | Add to Limitations section | Document cannot be disabled |
| 2.1 Aspect Ratio Bug | Known Issues section | Add as Issue #2 with workaround |
| 2.3 responseModalities | Expand Quick Start | Add explicit note about requiring both |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.6 Google Search Grounding | Limitations or Features | Useful for advanced users |
| 2.2 No usageMetadata | Community Tips | Low impact but good to know |
| 2.4 Pricing Change | New Pricing section | Add pricing info for budgeting |
| 3.1 Text Rendering Benchmarks | Model Selection | Strengthen Pro recommendation with data |

### Priority 3: Monitor (Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 3.2 Quality Degradation | May be resolved/model-specific | Check if still occurring in current models |

---

## Research Sources Consulted

### GitHub (Primary)

| Repository | Results | Relevant |
|------------|---------|----------|
| googleapis/js-genai | 30 issues | 3 |
| google-gemini/generative-ai-js (deprecated) | 30 issues | 2 |
| Release notes v1.38.0 | 1 | 1 |

### Official Documentation

| Source | Notes |
|--------|-------|
| [Image Generation Guide](https://ai.google.dev/gemini-api/docs/image-generation) | Comprehensive API documentation |
| [Changelog](https://ai.google.dev/gemini-api/docs/changelog) | Model lifecycle and deprecations |
| [Gemini 3 Guide](https://ai.google.dev/gemini-api/docs/gemini-3) | Latest model features |

### Community Sources

| Source | Quality | Findings |
|--------|---------|----------|
| Google Support Forums | High | 2 aspect ratio issues |
| Google AI Developers Forum | High | 3 discussions |
| Developer blogs (Cursor IDE, Apiyi) | Medium-High | Text rendering benchmarks |
| Google Developers Blog | Official | Pricing changes, features |

---

## Methodology Notes

**Tools Used**:
- `gh issue list` for GitHub discovery
- `gh release view` for release notes
- `WebSearch` for community sources and documentation
- `WebFetch` for official documentation parsing

**Limitations**:
- Could not access paywalled content or private forums
- Some Stack Overflow searches returned no results (may be too new)
- Aspect ratio bug may be resolved but no confirmation found

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that SDK migration guide (Finding 1.1) matches current @google/genai v1.38.0 API.

**For api-method-checker**: Verify model names in Finding 1.2 are currently available via `ai.models.list()`.

**For code-example-validator**: Validate all code examples, especially SDK migration pattern.

**For web-researcher**: Check if aspect ratio bug (Finding 2.1) has been officially resolved.

---

## Integration Guide

### Adding Critical SDK Migration Notice

Add to top of SKILL.md after frontmatter:

```markdown
## ⚠️ Critical: SDK Migration Required

**IMPORTANT**: The `@google/generative-ai` package is deprecated as of November 30, 2025.

**Migration Required**:
```typescript
// ❌ OLD (deprecated)
import { GoogleGenerativeAI } from "@google/generative-ai";

// ✅ NEW (required)
import { GoogleGenAI } from "@google/genai";
```

See [Migration Guide](#migration-guide) below.
```

### Adding Known Issues Section

Add new section after "Capabilities":

```markdown
## Known Issues & Limitations

### Issue #1: Resolution Parameter Case Sensitivity

**Error**: Request fails with invalid parameter
**Why It Happens**: Resolution must use uppercase 'K' (4K not 4k)
**Prevention**:

```typescript
// ✅ Correct
config: { imageGenerationConfig: { resolution: "4K" } }
```

### Issue #2: Aspect Ratio May Be Ignored (Sept 2025+)

**Error**: Returns 1:1 square despite requesting 16:9
**Why It Happens**: Backend update in Sept 2025 affected Gemini 2.5 Flash
**Workaround**: Use Gemini 3 Pro Image Preview or ImageFX
**Status**: Google working on fix

### Issue #3: SynthID Watermark Cannot Be Disabled

**Behavior**: All generated images include SynthID watermark
**Why**: Documented limitation for content authenticity
**Workaround**: None - watermark is required
```

---

## Sources

**Official Documentation:**
- [Gemini API Image Generation Guide](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini API Changelog](https://ai.google.dev/gemini-api/docs/changelog)
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)
- [Introducing Gemini 2.5 Flash Image](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)
- [New Gemini API Updates for Gemini 3](https://developers.googleblog.com/new-gemini-api-updates-for-gemini-3/)

**GitHub:**
- [googleapis/js-genai Repository](https://github.com/googleapis/js-genai)
- [google-gemini/deprecated-generative-ai-js](https://github.com/google-gemini/deprecated-generative-ai-js)
- [Issue #539: No usageMetadata for generateImages API](https://github.com/googleapis/js-genai/issues/539)

**Community:**
- [Gemini Aspect Ratio Issues - Google Support](https://support.google.com/gemini/thread/371311134/)
- [Nano Banana Auto Aspect Ratio Issue - Developer Forum](https://discuss.ai.google.dev/t/gemini-2-5-flash-nano-banana-auto-aspect-ratio-issue-output-image-has-different-aspect-ratio/108225)
- [Gemini 3 Pro Image API Guide - Cursor IDE](https://www.cursor-ide.com/blog/gemini-3-pro-image-api)
- [Gemini 3 Pro Image Text Rendering Guide - Apiyi](https://help.apiyi.com/gemini-3-pro-image-text-rendering-guide-en.html)
- [Google Gemini Aspect Ratio Bug Fix - Piunika Web](https://piunikaweb.com/2025/09/30/gemini-aspect-ratio-bug-fix-in-the-works/)

---

**Research Completed**: 2026-01-21 15:30
**Next Research Due**: After Gemini 3 Pro Image reaches GA (currently preview)
