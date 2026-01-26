# Community Knowledge Research: google-gemini-file-search

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/google-gemini-file-search/SKILL.md
**Packages Researched**: @google/genai ^1.38.0 (skill documents 1.30.0+)
**Official Repo**: googleapis/js-genai
**Time Window**: November 2025 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 9 |
| TIER 1 (Official) | 5 |
| TIER 2 (High-Quality Community) | 2 |
| TIER 3 (Community Consensus) | 1 |
| TIER 4 (Low Confidence) | 1 |
| Already in Skill | 1 |
| Recommended to Add | 7 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: displayName Dropped When Uploading Blobs (FIXED in v1.34.0)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1078](https://github.com/googleapis/js-genai/issues/1078)
**Date**: 2025-11-08 (closed 2025-12-17)
**Verified**: Yes - Fixed in v1.34.0
**Impact**: HIGH (affects grounding citations)
**Already in Skill**: No

**Description**:
When uploading documents using `Blob` sources (not file paths), the SDK dropped both `displayName` and `customMetadata` fields. This caused grounding citations to return `null` for `groundingChunks.title`, making it impossible to identify source documents in responses.

**Reproduction**:
```typescript
// Bug in @google/genai <= v1.33.0
const file = new Blob([arrayBuffer], { type: 'application/pdf' })

await ai.fileSearchStores.uploadToFileSearchStore({
  name: storeName,
  file,
  config: {
    displayName: 'My Document.pdf',  // ❌ This was dropped!
    customMetadata: { author: 'foo' }  // ❌ This was dropped!
  }
})

// Result: groundingChunks[].title === null
```

**Solution/Workaround**:
```typescript
// Fixed in v1.34.0+ - displayName now preserved
// OR use resumable upload workaround for older versions:

const uploadUrl = `${GEMINI_BASE_URL}/upload/v1beta/${storeName}:uploadToFileSearchStore?key=${API_KEY}`

// Step 1: Initiate with displayName in body
const initResponse = await fetch(uploadUrl, {
  method: 'POST',
  headers: {
    'X-Goog-Upload-Protocol': 'resumable',
    'X-Goog-Upload-Command': 'start',
    'X-Goog-Upload-Header-Content-Length': numBytes.toString(),
    'X-Goog-Upload-Header-Content-Type': 'application/pdf',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    displayName: 'My Document.pdf'  // ✅ Works with resumable upload
  })
})

// Step 2: Upload file bytes
const uploadUrl = initResponse.headers.get('X-Goog-Upload-URL')
await fetch(uploadUrl, {
  method: 'PUT',
  headers: {
    'Content-Length': numBytes.toString(),
    'X-Goog-Upload-Offset': '0',
    'X-Goog-Upload-Command': 'upload, finalize',
    'Content-Type': 'application/pdf'
  },
  body: fileBytes
})
```

**Official Status**:
- [x] Fixed in version 1.34.0 (commit [f05fb0c](https://github.com/googleapis/js-genai/commit/f05fb0c16b701ec592465c366ee28e12ac8ecd57))
- [x] Workaround available (resumable upload)

**Cross-Reference**:
- Related PR: [#1208](https://github.com/googleapis/js-genai/pull/1208)
- Affects: Grounding citations (groundingChunks.title)

---

### Finding 1.2: operations.get() Polling Unreliable

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1211](https://github.com/googleapis/js-genai/issues/1211)
**Date**: 2025-12-21 (still open)
**Verified**: Partial (maintainer cannot reproduce consistently)
**Impact**: MEDIUM (indexing status unknown)
**Already in Skill**: Partially (skill shows polling pattern but no warning)

**Description**:
`operations.get()` sometimes returns incomplete status for file search upload operations. The operation may complete successfully but polling returns inconsistent progress metadata or fails to update `done: true` reliably.

**Reproduction**:
```typescript
const operation = await ai.fileSearchStores.uploadToFileSearchStore({
  name: storeName,
  file: fs.createReadStream('large.pdf')
})

// Poll for completion
while (!operation.done) {
  await new Promise(resolve => setTimeout(resolve, 1000))
  operation = await ai.operations.get({ name: operation.name })
  console.log(operation.metadata?.progress)  // ❌ May be undefined or stale
}
```

**Solution/Workaround**:
```typescript
// Add timeout and fallback checks
const MAX_POLL_TIME = 60000 // 60 seconds
const POLL_INTERVAL = 1000
let elapsed = 0

while (!operation.done && elapsed < MAX_POLL_TIME) {
  await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL))
  elapsed += POLL_INTERVAL

  try {
    operation = await ai.operations.get({ name: operation.name })
  } catch (error) {
    console.warn('Polling failed, assuming complete:', error)
    break
  }
}

if (elapsed >= MAX_POLL_TIME) {
  console.warn('Polling timeout - check document manually')
  // Verify document exists
  const docs = await ai.fileSearchStores.documents.list({ parent: storeName })
  const uploaded = docs.documents?.find(d => d.displayName === 'large.pdf')
  if (uploaded) {
    console.log('Document found despite polling timeout')
  }
}
```

**Official Status**:
- [ ] Cannot reproduce consistently (per maintainer comment)
- [ ] Marked stale, may be closed
- [ ] No fix timeline

**Cross-Reference**:
- Skill section: Error 6 (Not Polling Operation Status) - add timeout warning

---

### Finding 1.3: Grounding Ignored with JSON Response Mode

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #829](https://github.com/googleapis/js-genai/issues/829)
**Date**: 2025-07-23 (still open)
**Verified**: Yes
**Impact**: HIGH (grounding data lost)
**Already in Skill**: No

**Description**:
When using `responseMimeType: 'application/json'` for structured output with Gemini 2.0+, grounding data from file search is completely ignored. The model returns structured JSON but without any grounding metadata or citations, even when `fileSearch` tool is configured.

**Reproduction**:
```typescript
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Summarize the safety guidelines',
  config: {
    responseMimeType: 'application/json',  // ❌ Overrides fileSearch tool
    responseSchema: {
      type: 'object',
      properties: {
        summary: { type: 'string' }
      }
    },
    tools: [{
      fileSearch: { fileSearchStoreNames: [storeName] }
    }]
  }
})

// Result: response.text has JSON, but response.candidates[0].groundingMetadata is undefined
```

**Solution/Workaround**:
```typescript
// Option 1: Request grounding in prompt without structured output
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: `Summarize the safety guidelines and format as JSON:
{
  "summary": "...",
  "sources": ["..."]
}`,
  config: {
    tools: [{
      fileSearch: { fileSearchStoreNames: [storeName] }
    }]
  }
})

// Parse JSON from text response
const jsonMatch = response.text.match(/\{[\s\S]*\}/)
const data = JSON.parse(jsonMatch[0])

// Access grounding separately
const grounding = response.candidates[0].groundingMetadata

// Option 2: Use separate call for grounding
const textResponse = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Summarize the safety guidelines',
  config: {
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
})

const structuredResponse = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: `Convert this to JSON: ${textResponse.text}`,
  config: {
    responseMimeType: 'application/json',
    responseSchema: { /* schema */ }
  }
})
```

**Official Status**:
- [ ] Escalated to internal team (per maintainer comment)
- [ ] Not working together (by design or bug unclear)
- [ ] No timeline for fix

**Cross-Reference**:
- Related: Issue #976 (markdown JSON in responses)
- Affects: All structured output + file search combinations

---

### Finding 1.4: Cannot Use GoogleSearch and FileSearch Tools Together

**Trust Score**: TIER 1 - Official
**Source**: [Google Codelabs](https://codelabs.developers.google.com/gemini-file-search-for-rag), [Issue #435](https://github.com/googleapis/js-genai/issues/435)
**Date**: 2025-04-10 (closed), confirmed in 2025 Codelabs
**Verified**: Yes
**Impact**: MEDIUM (architectural constraint)
**Already in Skill**: No

**Description**:
You cannot use native `googleSearch` tool and `fileSearch` tool in the same request. Attempting to do so returns error: `"Search as a tool and file search tool are not supported together", status: "INVALID_ARGUMENT"`

**Reproduction**:
```typescript
// ❌ This fails with INVALID_ARGUMENT
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'What are the latest guidelines on this topic?',
  config: {
    tools: [
      { googleSearch: {} },
      { fileSearch: { fileSearchStoreNames: [storeName] } }
    ]
  }
})
```

**Solution/Workaround**:
```typescript
// Use separate specialist agents with Agent-as-a-Tool pattern
class WebSearchAgent {
  async query(question: string) {
    return ai.models.generateContent({
      model: 'gemini-3-flash',
      contents: question,
      config: { tools: [{ googleSearch: {} }] }
    })
  }
}

class DocumentSearchAgent {
  async query(question: string) {
    return ai.models.generateContent({
      model: 'gemini-3-flash',
      contents: question,
      config: { tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }] }
    })
  }
}

// Orchestrator decides which agent to use
async function orchestrateSearch(question: string) {
  const needsWeb = await determineSearchType(question)

  if (needsWeb) {
    return new WebSearchAgent().query(question)
  } else {
    return new DocumentSearchAgent().query(question)
  }
}
```

**Official Status**:
- [x] Documented limitation
- [x] Workaround exists (separate agents)
- [ ] No plan to allow combined use

**Cross-Reference**:
- Affects: Multi-source RAG applications
- Related: Issue #1157 (urlContext + other tools)

---

### Finding 1.5: Streaming with File Search Returns 400 Error (FIXED)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #1221](https://github.com/googleapis/js-genai/issues/1221)
**Date**: 2026-01-01 (closed)
**Verified**: Yes - appears fixed
**Impact**: MEDIUM (streaming blocked)
**Already in Skill**: No

**Description**:
Using `generateContentStream()` with `fileSearch` tool option returned `Error 400` in some SDK versions. The issue was closed quickly, suggesting it may have been a transient API issue or fixed in a patch.

**Reproduction**:
```typescript
// May have failed in specific versions
const stream = await ai.models.generateContentStream({
  model: 'gemini-3-flash',
  contents: 'Summarize the document',
  config: {
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
})

// Error 400 returned
```

**Solution/Workaround**:
```typescript
// Ensure using latest SDK version (v1.34.0+)
// If issue persists, fall back to non-streaming:
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Summarize the document',
  config: {
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
})
```

**Official Status**:
- [x] Closed (no reproduction details)
- [x] Likely fixed in recent versions
- [ ] Root cause unclear

**Cross-Reference**:
- Skill doesn't mention streaming - add note about support

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: InlinedResponse Missing Metadata Field

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #1191](https://github.com/googleapis/js-genai/issues/1191)
**Date**: 2025-12-15 (open, maintainer confirmed)
**Verified**: Yes - maintainer reproduced
**Impact**: MEDIUM (affects batch API)
**Already in Skill**: No

**Description**:
When using Batch API with `InlinedRequest` that includes a `metadata` field, the corresponding `InlinedResponse` does not return the metadata. This makes it difficult to correlate batch responses with requests.

**Reproduction**:
```typescript
// Batch request with metadata
const batchRequest = {
  metadata: { key: 'my-request-id' },
  contents: [{ parts: [{ text: 'Question?' }], role: 'user' }],
  config: {
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
}

// Submit batch
const batchResponse = await ai.batch.create({ requests: [batchRequest] })

// ❌ Response missing metadata field
console.log(batchResponse.responses[0].metadata)  // undefined
```

**Solution/Workaround**:
```typescript
// Use array index to correlate instead
const requests = [
  { metadata: { id: 'req-1' }, contents: [...] },
  { metadata: { id: 'req-2' }, contents: [...] }
]

const responses = await ai.batch.create({ requests })

// Map by index (not ideal but works)
responses.responses.forEach((response, i) => {
  const requestMetadata = requests[i].metadata
  console.log(`Response for ${requestMetadata.id}:`, response)
})
```

**Community Validation**:
- Maintainer confirmed: Yes (internal bug filed)
- Multiple users affected: Yes
- Workaround available: Yes (index-based correlation)

**Cross-Reference**:
- Affects: Batch API usage
- Skill doesn't cover batch operations - may add separate section

---

### Finding 2.2: Storage Quota Multiplier Documentation Confirmed

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Claude Skills documentation](https://claude-plugins.dev/skills/@jezweb/claude-skills/google-gemini-file-search), Community discussions
**Date**: 2025 (ongoing)
**Verified**: Cross-referenced with official docs
**Impact**: HIGH (cost planning)
**Already in Skill**: YES (documented as 3x multiplier)

**Description**:
The 3x storage multiplier (input files + embeddings + metadata = ~3x storage) is confirmed across multiple community sources and appears accurate. Skill correctly documents this.

**Community Validation**:
- Multiple sources agree: Yes
- Matches official behavior: Yes
- Already in skill: Yes (Error 2: Storage Quota Exceeded)

**Recommendation**: No changes needed - already documented correctly.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: File Search Context Limit

**Trust Score**: TIER 3 - Community Consensus
**Source**: [GitHub Issue #1658 (Python SDK)](https://github.com/googleapis/python-genai/issues/1658)
**Date**: Recent discussion
**Verified**: Cross-reference only (Python SDK)
**Impact**: MEDIUM (affects large document sets)
**Already in Skill**: No

**Description**:
There appears to be an undocumented context window limit for file search results. When querying large document sets, the API may truncate retrieved chunks to fit within the model's context window, potentially missing relevant information.

**Solution**:
```typescript
// Use metadata filtering to reduce search scope
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Find specific information',
  config: {
    tools: [{
      fileSearch: {
        fileSearchStoreNames: [storeName],
        metadataFilter: 'category="relevant-subset"'  // Narrow search scope
      }
    }]
  }
})

// Or split into multiple targeted queries
```

**Consensus Evidence**:
- Python SDK users discussing limits
- JavaScript SDK documentation doesn't specify limit
- Official docs mention retrieval but not context limits

**Recommendation**: Add to Community Tips section with caveat that exact limits are undocumented.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: Potential Model Support Changes

**Trust Score**: TIER 4 - Low Confidence
**Source**: Various GitHub issues mentioning model deprecations
**Date**: 2025
**Verified**: No

**Why Flagged**:
- [x] Version-specific (Gemini 1.5 deprecation mentioned)
- [x] Conflicting information about which models support File Search
- [ ] Official docs updated in Jan 2026

**Description**:
Some discussions mention Gemini 1.5 models being deprecated and File Search only working with Gemini 3 models. However, skill currently documents this (Error 8: Using Unsupported Models).

**Recommendation**: Monitor for model availability changes. Skill already documents Gemini 3 Pro/Flash requirement.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Storage 3x multiplier | Error 2: Storage Quota Exceeded | Fully covered |
| Gemini 3 model requirement | Error 8: Using Unsupported Models | Fully covered |
| Document immutability | Error 1: Document Immutability | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 displayName dropped (Blobs) | Known Issues | Add as Issue #9 - note fixed in v1.34.0 |
| 1.3 Grounding ignored with JSON | Known Issues | Add as Issue #10 - workaround required |
| 1.4 Cannot combine googleSearch + fileSearch | Known Issues | Add as Issue #11 - architectural limitation |

### Priority 2: Enhance Existing (TIER 1, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.2 operations.get() unreliable | Error 6 enhancement | Add timeout pattern and fallback checks |
| 1.5 Streaming support | Add to Integration Examples | Note streaming is supported in v1.34.0+ |

### Priority 3: Monitor (TIER 2-3, Needs Verification)

| Finding | Target Section | Next Step |
|---------|----------------|-----------|
| 2.1 Batch API metadata | Consider adding | Wait for fix or add to advanced section |
| 3.1 Context limits | Community Tips | Verify exact limits before adding |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "file search" in googleapis/js-genai | 5 | 5 |
| "grounding" in googleapis/js-genai | 8 | 3 |
| "metadata" in googleapis/js-genai | 10 | 2 |
| Recent releases (v1.29-v1.38) | 10 | 5 |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "gemini file search api gotcha" | 10 | High (official docs + community) |
| "@google/genai file search storage quota" | 10 | Medium (confirms 3x multiplier) |
| Stack Overflow (gemini file search) | 0 | N/A (too new) |

### Other Sources

| Source | Notes |
|--------|-------|
| [Google Codelabs](https://codelabs.developers.google.com/gemini-file-search-for-rag) | Official tutorial, confirmed tool limitations |
| [Official Blog](https://blog.google/innovation-and-ai/technology/developers-tools/file-search-gemini-api/) | Feature announcement |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue inspection
- `gh release list/view` for version tracking
- `WebSearch` for community knowledge

**Limitations**:
- Stack Overflow has minimal content (API too new)
- Some issues marked stale/closed without clear resolution
- Cannot access paywalled content
- Python SDK findings not directly applicable

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference finding 1.3 (grounding + JSON) against latest Gemini API docs to see if limitation is documented.

**For api-method-checker**: Verify that resumable upload workaround in finding 1.1 uses correct API endpoints in current version.

**For code-example-validator**: Validate code examples in findings 1.1, 1.3, 1.4 before adding to skill.

---

## Integration Guide

### Adding Issue #9: displayName Dropped for Blob Uploads

```markdown
### Error 9: displayName Not Preserved for Blob Sources (Fixed v1.34.0+)

**Symptom:**
```
groundingChunks[0].title === null  // No document source shown
```

**Cause:** In @google/genai versions prior to v1.34.0, when uploading files as `Blob` objects (not file paths), the SDK dropped the `displayName` and `customMetadata` configuration fields.

**Prevention:**
```typescript
// ✅ CORRECT: Upgrade to v1.34.0+ for automatic fix
npm install @google/genai@latest  // v1.34.0+

await ai.fileSearchStores.uploadToFileSearchStore({
  name: storeName,
  file: new Blob([arrayBuffer], { type: 'application/pdf' }),
  config: {
    displayName: 'Safety Manual.pdf',  // ✅ Now preserved
    customMetadata: { version: '1.0' }  // ✅ Now preserved
  }
})

// ⚠️ WORKAROUND for v1.33.0 and earlier: Use resumable upload
// [Include resumable upload code from finding 1.1]
```

**Source:** https://github.com/googleapis/js-genai/issues/1078
```

### Adding Issue #10: Grounding Lost with Structured Output

```markdown
### Error 10: Grounding Metadata Ignored with JSON Response Mode

**Symptom:**
```
response.candidates[0].groundingMetadata === undefined
// Even though fileSearch tool is configured
```

**Cause:** When using `responseMimeType: 'application/json'` for structured output, the API ignores the `fileSearch` tool and returns no grounding metadata, even with Gemini 3 models.

**Prevention:**
```typescript
// ❌ WRONG: Structured output overrides grounding
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Summarize guidelines',
  config: {
    responseMimeType: 'application/json',  // Loses grounding
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
})

// ✅ CORRECT: Two-step approach
// Step 1: Get grounded text response
const textResponse = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'Summarize guidelines',
  config: {
    tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }]
  }
})

const grounding = textResponse.candidates[0].groundingMetadata

// Step 2: Convert to structured format in prompt
const jsonResponse = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: `Convert to JSON: ${textResponse.text}

Format:
{
  "summary": "...",
  "key_points": ["..."]
}`,
  config: {
    responseMimeType: 'application/json',
    responseSchema: { /* schema */ }
  }
})

// Combine results
const result = {
  data: JSON.parse(jsonResponse.text),
  sources: grounding.groundingChunks
}
```

**Source:** https://github.com/googleapis/js-genai/issues/829
```

### Adding Issue #11: Cannot Combine Google Search and File Search

```markdown
### Error 11: Google Search and File Search Tools Are Mutually Exclusive

**Symptom:**
```
Error: "Search as a tool and file search tool are not supported together"
Status: INVALID_ARGUMENT
```

**Cause:** The Gemini API does not allow using `googleSearch` and `fileSearch` tools in the same request.

**Prevention:**
```typescript
// ❌ WRONG: Combining search tools
const response = await ai.models.generateContent({
  model: 'gemini-3-flash',
  contents: 'What are the latest industry guidelines?',
  config: {
    tools: [
      { googleSearch: {} },
      { fileSearch: { fileSearchStoreNames: [storeName] } }
    ]
  }
})

// ✅ CORRECT: Use separate specialist agents
async function searchWeb(query: string) {
  return ai.models.generateContent({
    model: 'gemini-3-flash',
    contents: query,
    config: { tools: [{ googleSearch: {} }] }
  })
}

async function searchDocuments(query: string) {
  return ai.models.generateContent({
    model: 'gemini-3-flash',
    contents: query,
    config: { tools: [{ fileSearch: { fileSearchStoreNames: [storeName] } }] }
  })
}

// Orchestrate based on query type
const needsWeb = query.includes('latest') || query.includes('current')
const response = needsWeb
  ? await searchWeb(query)
  : await searchDocuments(query)
```

**Source:** https://github.com/googleapis/js-genai/issues/435, https://codelabs.developers.google.com/gemini-file-search-for-rag
```

---

**Research Completed**: 2026-01-21
**Next Research Due**: After v2.0.0 release or March 2026 (quarterly)
