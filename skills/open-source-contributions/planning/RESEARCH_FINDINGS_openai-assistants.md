# Community Knowledge Research: openai-assistants

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/openai-assistants/SKILL.md
**Packages Researched**: openai@6.15.0 (latest: 6.16.0)
**Official Repo**: openai/openai-node
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 12 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 1 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 4 |
| Recommended to Add | 8 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Vector Store uploadAndPoll Incorrect Documentation

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #1337](https://github.com/openai/openai-node/issues/1337)
**Date**: 2025-02-18
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The official documentation for `vectorStores.fileBatches.uploadAndPoll` shows incorrect usage that results in "No `files` provided to process" error. The docs show passing fileStreams directly as a parameter, but the correct approach requires wrapping in a `{ files: [...] }` object.

**Reproduction**:
```typescript
// ❌ WRONG - Following official docs
await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStore.id, fileStreams)
// Error: No `files` provided to process. If you've already uploaded files you should use `.createAndPoll()` instead
```

**Solution/Workaround**:
```typescript
// ✅ CORRECT - Wrap in object
await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStore.id, { files: fileStreams })
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (docs incorrect)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects: openai v4.85.1+ (confirmed in v6.x as well)
- Issue still OPEN as of 2026-01-21

---

### Finding 1.2: Memory Leak in vectorStores.fileBatches.uploadAndPoll

**Trust Score**: TIER 1 - Official GitHub Issue (8 comments)
**Source**: [GitHub Issue #1052](https://github.com/openai/openai-node/issues/1052)
**Date**: 2024-09-09
**Verified**: Partial (maintainer acknowledged)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When uploading files from streams (e.g., S3 GetObjectCommand) to vector stores using `uploadAndPoll`, memory usage increases during upload but never returns to baseline. A 22MB file upload increased memory from 300MB to 360MB permanently. Saving the same file to disk with fs properly released memory, suggesting the leak is in the SDK's upload logic.

**Reproduction**:
```typescript
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { toFile } from "openai";

// Get file from S3
const command = new GetObjectCommand({ Bucket: "bucket", Key: fileKey });
const response = await client.send(command);

// Upload to vector store - memory leaks here
await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStoreId, {
  files: [await toFile(response.Body!, fileName)]
});

// Memory usage stays elevated (~44MB leaked per upload)
```

**Solution/Workaround**:
No complete workaround. Updating from v4.56.0 to v4.58.1 reduced leak from 60MB to 44MB per upload, but didn't eliminate it.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Maintainer (RobertCraigie) requested testing with v5 in June 2025
- Issue still OPEN as of 2026-01-21
- Affects long-running servers with multiple uploads

---

### Finding 1.3: Async Event Handlers for Streaming Helpers

**Trust Score**: TIER 1 - Official Feature Request (7 comments)
**Source**: [GitHub Issue #879](https://github.com/openai/openai-node/issues/879)
**Date**: 2024-06-05
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
The Assistant Streaming Helpers (event listeners like `imageFileDone`) don't support async/await. Users need async control for operations like moving generated files to new destinations as part of tool output submission. Current event handlers are synchronous, requiring workarounds.

**Reproduction**:
```typescript
// Current: Can't await async operations in event handlers
stream.on('imageFileDone', (image) => {
  // Can't await file operations here
  moveFileToDestination(image.file_id); // No way to handle errors properly
});
```

**Solution/Workaround**:
Use Node.js `events.once()` API for async/await:
```typescript
import { once } from 'events';

// Wait for specific event
const [image] = await once(stream, 'imageFileDone');
await moveFileToDestination(image.file_id);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required (feature request tracked)
- [ ] Won't fix

**Cross-Reference**:
- Maintainer (rattrayalex) acknowledged in July 2024
- Issue still OPEN as of 2026-01-21
- Alternative: Use `stream.finalMessages()` and `stream.finalRunSteps()` which already support async/await

---

### Finding 1.4: o3-mini Unsupported Temperature Parameter

**Trust Score**: TIER 1 - Official GitHub Issue (10 comments)
**Source**: [GitHub Issue #1318](https://github.com/openai/openai-node/issues/1318)
**Date**: 2025-02-11
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using o3-mini (or any reasoning model: o1-preview, o1-mini) in Assistants API, the SDK returns "400 Unsupported parameter: 'temperature' is not supported with this model" even when temperature is not explicitly set. This happens because assistants created with other models retain temperature settings, and updating the model to o3-mini doesn't automatically clear incompatible parameters.

**Reproduction**:
```typescript
// Create assistant with temperature
const assistant = await openai.beta.assistants.create({
  model: 'gpt-4',
  temperature: 0.7,
  instructions: '...'
});

// Update to o3-mini - ERROR!
await openai.beta.assistants.update(assistant.id, {
  model: 'o3-mini',
  reasoning_effort: 'medium'
});
// Error: Unsupported parameter: 'temperature' is not supported with this model
```

**Solution/Workaround**:
Explicitly set temperature to `null` when updating to reasoning models:
```typescript
await openai.beta.assistants.update(assistant.id, {
  model: 'o3-mini',
  reasoning_effort: 'medium',
  temperature: null,  // ✅ Explicitly clear
  top_p: null         // ✅ Also clear top_p if set
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (maintainer confirmed)
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Maintainer (RobertCraigie) reported to API team to improve behavior
- Affects: openai v4.83.0+ (confirmed in v6.x)
- Related: All reasoning models (o3-mini, o1-preview, o1-mini)

---

### Finding 1.5: uploadAndPoll Returns Wrong ID

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #1700](https://github.com/openai/openai-node/issues/1700)
**Date**: 2025-11-06
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
`vectorStores.fileBatches.uploadAndPoll` returns the vector store object instead of the file batch object. The returned ID starts with `vs_` (vector store ID) instead of `vsfb_` (vector store file batch ID), causing subsequent API calls to fail with "400 Invalid 'batch_id'".

**Reproduction**:
```typescript
const fileBatchUpload = await openai.vectorStores.fileBatches.uploadAndPoll(
  'vs_my-vector-store-id',
  { files: [fileStream] }
);

console.log(fileBatchUpload.id);  // 'vs_...' instead of 'vsfb_...'
console.log(fileBatchUpload.object);  // 'vector_store' instead of 'vector_store_file_batch'

// This fails with 400 error
const files = await openai.vectorStores.fileBatches.listFiles(
  fileBatchUpload.id,  // ❌ Wrong ID type
  { vector_store_id: 'vs_my-vector-store-id' }
);
```

**Solution/Workaround**:
The batch ID is not available from `uploadAndPoll`. Use `createAndPoll` instead or list batches to find the correct ID:
```typescript
// Option 1: Use createAndPoll after uploading files separately
const batch = await openai.vectorStores.fileBatches.createAndPoll(
  vectorStoreId,
  { file_ids: uploadedFileIds }
);

// Option 2: List batches to find the correct one
const batches = await openai.vectorStores.fileBatches.list(vectorStoreId);
const recentBatch = batches.data[0];
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects: openai v6.8.1+
- Issue still OPEN as of 2026-01-21
- Related to Finding 1.1 (uploadAndPoll API inconsistencies)

---

### Finding 1.6: Vector Store File Delete Global Effect

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #1710](https://github.com/openai/openai-node/issues/1710)
**Date**: 2025-11-29
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When a file is attached to multiple vector stores (VS_A, VS_B, VS_C), calling `vectorStores.files.delete(VS_A, file_id)` unexpectedly detaches the file from ALL vector stores, not just VS_A. The file object itself is correctly preserved in `/v1/files`, but the vector store associations are all removed.

**Reproduction**:
```typescript
// Attach file to 3 vector stores
await openai.vectorStores.files.create('VS_A', { file_id: 'file-xxx' });
await openai.vectorStores.files.create('VS_B', { file_id: 'file-xxx' });
await openai.vectorStores.files.create('VS_C', { file_id: 'file-xxx' });

// Delete from only VS_A
await openai.vectorStores.files.delete('VS_A', 'file-xxx');

// ❌ BUG: File is now detached from VS_A, VS_B, AND VS_C
// Expected: File should remain in VS_B and VS_C
```

**Solution/Workaround**:
No workaround available. This appears to be a bug in either the SDK or underlying API. Avoid sharing files across multiple vector stores if you need selective deletion.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Affects: openai v4.96.2+
- Issue still OPEN as of 2026-01-21
- Impacts: Multi-tenant applications sharing documents across contexts

---

### Finding 1.7: Streaming "Final Run Has Not Been Received" Error

**Trust Score**: TIER 1 - Official GitHub Issues (multiple reports)
**Source**: [GitHub Issue #1306](https://github.com/openai/openai-node/issues/1306), [#1439](https://github.com/openai/openai-node/issues/1439), [#945](https://github.com/openai/openai-node/issues/945)
**Date**: 2024-07-21 (first report), 2025-04-01 (latest)
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: Partially (mentioned in Known Issues but not with full context)

**Description**:
When streaming assistant runs, if the run finishes with `thread.run.incomplete` status, the SDK throws "OpenAIError: Final run has not been received" and stops the event stream. According to OpenAI docs, `incomplete` is a valid terminal state and threads should be able to continue, but the library's event processing doesn't handle this state properly. This causes long responses to get truncated or fail entirely.

**Reproduction**:
```typescript
const stream = await openai.beta.threads.runs.stream(threadId, { assistant_id });

for await (const event of stream) {
  if (event.event === 'thread.message.delta') {
    process.stdout.write(event.data.delta.content?.[0]?.text?.value || '');
  }
}
// If run ends with 'incomplete', throws OpenAIError instead of completing gracefully
```

**Solution/Workaround**:
Catch the error and handle incomplete runs:
```typescript
try {
  const stream = await openai.beta.threads.runs.stream(threadId, { assistant_id });
  for await (const event of stream) {
    // Process events
  }
} catch (error) {
  if (error.message?.includes('Final run has not been received')) {
    // Run is incomplete but thread can continue
    // Retrieve run status manually
    const run = await openai.beta.threads.runs.retrieve(threadId, runId);
    if (run.status === 'incomplete') {
      // Handle incomplete status (e.g., prompt user to continue)
    }
  }
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Multiple reports: July 2024, April 2025
- Issue CLOSED but may still occur
- Related: Long-running responses, token limits, max_completion_tokens

---

### Finding 1.8: vectorStores.files.delete Method Signature Mismatch

**Trust Score**: TIER 1 - Official GitHub Issue
**Source**: [GitHub Issue #1729](https://github.com/openai/openai-node/issues/1729)
**Date**: 2025-12-21
**Verified**: Yes
**Impact**: LOW
**Already in Skill**: No

**Description**:
The TypeScript method signature for `vectorStores.files.delete()` doesn't match the documentation in api.md. This can cause confusion when developers reference the auto-generated API docs versus the official OpenAI API reference.

**Reproduction**:
Check TypeScript definitions versus api.md documentation.

**Solution/Workaround**:
Follow the TypeScript definitions in the IDE, not the api.md file:
```typescript
// Use the actual SDK method signature
await openai.vectorStores.files.delete(vectorStoreId, fileId);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (docs inconsistency)
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Issue OPEN as of 2026-01-21
- Low impact: TypeScript types are correct, only internal docs are wrong

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Thread Already Has Active Run - Proper Handling Pattern

**Trust Score**: TIER 2 - High-Quality Community (multiple forum threads)
**Source**: [OpenAI Community Forum](https://community.openai.com/t/error-running-thread-already-has-an-active-run/782118), [GitHub dotnet issue](https://github.com/openai/openai-dotnet/issues/214)
**Date**: 2024-2025 (multiple reports)
**Verified**: Consistent across sources
**Impact**: HIGH
**Already in Skill**: Yes (Known Issue #1)

**Description**:
The "Thread already has an active run" error is well-documented but community sources reveal important nuances about run cancellation that aren't clear in official docs. Specifically, attempting to cancel a run that has already completed returns "Cannot cancel run with status 'completed'", indicating race conditions in status checking.

**Solution/Workaround**:
```typescript
async function createRunSafely(threadId: string, assistantId: string) {
  // Check for active runs first
  const runs = await openai.beta.threads.runs.list(threadId, { limit: 1 });
  const activeRun = runs.data.find(r =>
    ['queued', 'in_progress', 'requires_action'].includes(r.status)
  );

  if (activeRun) {
    try {
      // Try to cancel - may fail if run just completed
      await openai.beta.threads.runs.cancel(threadId, activeRun.id);

      // Wait for cancellation to complete
      let run = await openai.beta.threads.runs.retrieve(threadId, activeRun.id);
      while (run.status === 'cancelling') {
        await new Promise(r => setTimeout(r, 500));
        run = await openai.beta.threads.runs.retrieve(threadId, activeRun.id);
      }
    } catch (error) {
      // Ignore "already completed" errors - run finished naturally
      if (!error.message?.includes('completed')) throw error;
    }
  }

  return openai.beta.threads.runs.create(threadId, { assistant_id: assistantId });
}
```

**Community Validation**:
- Multiple forum threads with similar solutions
- Consistently reported across different SDKs (Node, .NET)
- Community consensus on proper status checking sequence

**Cross-Reference**:
- Already in Skill (Known Issue #1)
- Enhancement: Add race condition handling pattern

---

### Finding 2.2: Assistants API Deprecation Timeline Details

**Trust Score**: TIER 2 - Official Announcement + Community Discussion
**Source**: [OpenAI Community Announcement](https://community.openai.com/t/assistants-api-beta-deprecation-august-26-2026-sunset/1354666), [Migration Guide](https://platform.openai.com/docs/assistants/migration)
**Date**: 2025-08-26 (announcement)
**Verified**: Yes (official)
**Impact**: CRITICAL
**Already in Skill**: Yes (prominently featured)

**Description**:
The Assistants API v2 sunset date of August 26, 2026 is confirmed. Official migration guide to Responses API is now available. Key architectural differences:
- Assistants → Prompts (dashboard-only creation, versioned)
- Threads → Conversations (store items, not just messages)
- Better performance and new features (deep research, MCP, computer use)

**Solution/Workaround**:
N/A - Already documented in skill with migration reference.

**Community Validation**:
- Official OpenAI announcement
- Migration guide published
- Extensive community discussion about migration paths

**Cross-Reference**:
- Already in Skill (Deprecation Notice section)
- Migration guide: `references/migration-to-responses.md`
- Related skill: `openai-responses`

---

### Finding 2.3: File Search v2 Limit Increase to 10,000 Files

**Trust Score**: TIER 2 - Official Documentation + Community Validation
**Source**: [OpenAI Assistants FAQ](https://help.openai.com/en/articles/8550641-assistants-api-v2-faq), [Community Forum](https://community.openai.com/t/new-features-in-the-assistants-api/720539)
**Date**: 2024-04-17 (v2 release)
**Verified**: Yes (official)
**Impact**: MEDIUM
**Already in Skill**: Yes (documented)

**Description**:
Assistants API v2 increased the file_search limit from 20 files (v1) to 10,000 files per assistant (500x increase). This is already documented but community sources highlight the importance of this for large-scale RAG applications.

**Solution/Workaround**:
N/A - Feature, not a bug. Already documented.

**Community Validation**:
- Official documentation
- Community celebrates 500x improvement
- Confirmed in production use

**Cross-Reference**:
- Already in Skill (File Search section)
- Note: $0.10/GB/day pricing applies

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Streaming Event Examples Incorrect in README

**Trust Score**: TIER 3 - Community Observation
**Source**: [GitHub Issue #860](https://github.com/openai/openai-node/issues/860)
**Date**: 2024-05-20
**Verified**: Issue still open
**Impact**: LOW
**Already in Skill**: No

**Description**:
The streaming examples in the repository's README show incorrect or unhelpful event examples that don't reflect the actual events developers need to handle. The issue has 6 comments but remains open, suggesting the examples haven't been updated.

**Solution**:
Refer to the official API reference for correct event types:
- `thread.run.created`
- `thread.message.delta`
- `thread.run.step.delta`
- `thread.run.completed`
- `thread.run.requires_action`
- `thread.run.incomplete`

**Consensus Evidence**:
- 6 community comments
- Issue open since May 2024
- No official fix yet

**Recommendation**: Add to Community Tips section with reference to correct event list

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| Thread already has active run | Known Issues #1 | Fully covered, could add race condition handling |
| Run polling timeout | Known Issues #2 | Covered |
| Vector store indexing delay | Known Issues #3 | Covered |
| Deprecation timeline | Deprecation Notice | Prominently featured |
| 10,000 file limit | File Search (RAG) | Documented with pricing |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 uploadAndPoll Documentation Error | Known Issues | Add as Issue #13 with code examples |
| 1.4 o3-mini Temperature Parameter | Known Issues | Add as Issue #14 with workaround (set to null) |
| 1.5 uploadAndPoll Returns Wrong ID | Known Issues | Add as Issue #15 with alternative approaches |
| 1.6 Vector Store Delete Global Effect | Known Issues | Add as Issue #16 with warning |
| 1.7 Streaming Incomplete Status | Known Issues #2 | Enhance existing with incomplete handling |
| 2.1 Active Run Race Condition | Known Issues #1 | Enhance existing with race condition pattern |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.2 Memory Leak uploadAndPoll | Known Issues or Community Tips | Still unresolved, flag as known issue for long-running servers |
| 1.3 Async Streaming Helpers | Community Tips | Document `events.once()` workaround |
| 3.1 README Event Examples | Community Tips | Point to correct event list |

### Priority 3: Monitor (Low Impact)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 1.8 Method Signature Mismatch | Documentation inconsistency only | Low priority, TypeScript types are correct |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "assistants" in openai/openai-node | 30 | 12 |
| "vector store" in openai/openai-node | 15 | 6 |
| "streaming run" in openai/openai-node | 15 | 3 |
| "thread run" in openai/openai-node | 15 | 4 |
| "code_interpreter" in openai/openai-node | 10 | 2 |
| "function calling" in openai/openai-node | 10 | 2 |
| Recent releases | 10 | 2 (v6.16.0, v6.15.0) |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| "thread already has active run" | 10+ | High (official forums + GitHub) |
| "vector store uploadAndPoll memory leak" | 5+ | High (GitHub issue confirmed) |
| "final run has not been received" | 3 | High (multiple GitHub issues) |
| "o3-mini temperature parameter" | 10+ | High (widespread issue) |
| "assistants api deprecation august 2026" | 10+ | High (official announcement) |
| "assistants api v2 file search 10000 files" | 8+ | High (official docs) |

### Other Sources

| Source | Notes |
|--------|-------|
| OpenAI Community Forum | Primary source for "already has active run" discussions |
| OpenAI Official Docs | Migration guide, deprecation timeline |
| GitHub Issue Comments | Maintainer responses (RobertCraigie, rattrayalex) |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue analysis
- `gh release list` for version tracking
- `WebSearch` for community forums and Stack Overflow

**Limitations**:
- Stack Overflow site: operator not supported by WebSearch tool
- Used broader searches without site restriction
- Focus on GitHub issues as primary source (more reliable than SO for SDK-specific issues)

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that findings 1.4 (o3-mini temperature), 1.5 (uploadAndPoll ID), and 1.6 (vector store delete) are still reproducible in latest version (6.16.0).

**For api-method-checker**: Verify that the workarounds in findings 1.1, 1.4, and 1.5 use currently available APIs and method signatures.

**For code-example-validator**: Validate all code examples in findings 1.1-1.7 and 2.1 before adding to skill.

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

Insert into "Known Issues" section after existing issues:

```markdown
**13. Vector Store Upload Documentation Incorrect**
```
Error: `No 'files' provided to process`
```
**Why It Happens**: Official documentation shows incorrect usage of `uploadAndPoll`
**Prevention**: Wrap file streams in `{ files: [...] }` object
```typescript
// ✅ Correct
await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStoreId, {
  files: fileStreams
});

// ❌ Wrong (shown in docs)
await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStoreId, fileStreams);
```
**Source**: [GitHub Issue #1337](https://github.com/openai/openai-node/issues/1337)

**14. Reasoning Models Reject Temperature Parameter**
```
Error: Unsupported parameter: 'temperature' is not supported with this model
```
**Why It Happens**: When updating assistant to o3-mini/o1-preview/o1-mini, old temperature settings persist
**Prevention**: Explicitly set temperature to `null`
```typescript
await openai.beta.assistants.update(assistantId, {
  model: 'o3-mini',
  reasoning_effort: 'medium',
  temperature: null,  // ✅ Must explicitly clear
  top_p: null
});
```
**Source**: [GitHub Issue #1318](https://github.com/openai/openai-node/issues/1318)

**15. uploadAndPoll Returns Vector Store ID Instead of Batch ID**
```
Error: Invalid 'batch_id': 'vs_...'. Expected an ID that begins with 'vsfb_'.
```
**Why It Happens**: `uploadAndPoll` returns vector store object instead of batch object
**Prevention**: Use alternative methods to get batch ID
```typescript
// Option 1: Use createAndPoll after separate upload
const batch = await openai.vectorStores.fileBatches.createAndPoll(
  vectorStoreId,
  { file_ids: uploadedFileIds }
);

// Option 2: List batches to find correct ID
const batches = await openai.vectorStores.fileBatches.list(vectorStoreId);
const batchId = batches.data[0].id; // starts with 'vsfb_'
```
**Source**: [GitHub Issue #1700](https://github.com/openai/openai-node/issues/1700)

**16. Vector Store File Delete Affects All Stores**
**Warning**: Deleting a file from one vector store removes it from ALL vector stores
**Why It Happens**: SDK or API bug - delete operation has global effect
**Prevention**: Avoid sharing files across multiple vector stores if selective deletion is needed
```typescript
// ❌ This deletes file from VS_A, VS_B, AND VS_C
await openai.vectorStores.files.delete('VS_A', 'file-xxx');
```
**Source**: [GitHub Issue #1710](https://github.com/openai/openai-node/issues/1710)
```

### Enhancing Existing Issue #2 (Run Polling Timeout)

Add incomplete status handling:

```markdown
**2. Run Polling Timeout / Incomplete Status**

Long-running tasks may timeout or finish with `incomplete` status. Handle both cases:

```typescript
try {
  const stream = await openai.beta.threads.runs.stream(threadId, { assistant_id });
  for await (const event of stream) {
    // Process events
  }
} catch (error) {
  if (error.message?.includes('Final run has not been received')) {
    // Run ended with 'incomplete' status - thread can continue
    const run = await openai.beta.threads.runs.retrieve(threadId, runId);
    if (run.status === 'incomplete') {
      // Handle: prompt user to continue, reduce max_completion_tokens, etc.
    }
  }
}
```

**Source**: [GitHub Issues #945, #1306, #1439](https://github.com/openai/openai-node/issues/945)
```

### Adding Community Tips Section (New)

```markdown
## Community Tips (Community-Sourced)

> **Note**: These tips come from community discussions and open issues. Verify against your SDK version.

### Memory Leak in Large File Uploads

**Source**: [GitHub Issue #1052](https://github.com/openai/openai-node/issues/1052) | **Status**: OPEN
**Applies to**: v4.56.0+ (reduced in v4.58.1, not eliminated)

When uploading large files from streams (S3, etc.) using `vectorStores.fileBatches.uploadAndPoll`, memory may not be released after upload completes. Impact: ~44MB leaked per 22MB file upload in long-running servers.

**Workaround**: If running a long-lived server with many uploads, monitor memory usage and restart periodically or use separate worker processes.

### Async Event Handlers for Streaming

**Source**: [GitHub Issue #879](https://github.com/openai/openai-node/issues/879) | **Status**: FEATURE REQUEST
**Applies to**: All versions

Stream event handlers don't support async/await. Use Node.js `events.once()` for async operations:

```typescript
import { once } from 'events';

const [image] = await once(stream, 'imageFileDone');
await moveFileToDestination(image.file_id);
```

Alternative: Use `stream.finalMessages()` and `stream.finalRunSteps()` which already support async/await.
```

---

## Version Update Recommendation

The skill currently references `openai@6.15.0`. Latest is `openai@6.16.0` (released 2026-01-09).

**Changes in v6.16.0**:
- Added `completed_at` property to Response objects
- Breaking change detection workflow added
- No Assistants API-specific changes noted

**Recommendation**: Update skill to reference `openai@6.16.0` but note that Assistants API changes are minimal (feature frozen due to deprecation).

---

**Research Completed**: 2026-01-21 14:30
**Next Research Due**: Not recommended (API is deprecated, sunset August 2026). Focus research on `openai-responses` skill instead.
