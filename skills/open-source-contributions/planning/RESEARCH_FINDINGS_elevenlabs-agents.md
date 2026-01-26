# Community Knowledge Research: ElevenLabs Agents

**Research Date**: 2026-01-21
**Researcher**: skill-researcher agent
**Skill Path**: skills/elevenlabs-agents/SKILL.md
**Packages Researched**:
- @elevenlabs/elevenlabs-js@2.32.0
- @elevenlabs/react@0.12.3
- @elevenlabs/client@0.12.2
- @elevenlabs/react-native@0.5.7
- @elevenlabs/agents-cli@0.6.1

**Official Repo**: elevenlabs/elevenlabs-js
**Time Window**: January 2025 - January 2026 (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 13 |
| TIER 1 (Official) | 8 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 3 |
| Recommended to Add | 10 |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Localhost Allowlist Validation Inconsistency

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #320](https://github.com/elevenlabs/elevenlabs-js/issues/320)
**Date**: 2025-11-30
**Verified**: Yes (Open issue, detailed reproduction)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The ElevenLabs Agent Allowlist has inconsistent validation logic for localhost URLs, preventing local development. The dashboard rejects valid localhost formats but accepts invalid ones.

**Reproduction**:
When adding to Agent Allowlist in dashboard:
- `localhost:3000` → REJECTED (should be valid)
- `http://localhost:3000` → REJECTED (protocol not allowed)
- `localhost:3000/voice-chat` → REJECTED (paths not allowed)
- `www.localhost:3000` → ACCEPTED (invalid but accepted)
- `127.0.0.1:3000` → ACCEPTED (valid workaround)

**Connection Error**:
```
Host is not supported
Host is not valid or supported
Host is not in insights whitelist
WebSocket is already in CLOSING or CLOSED state
```

**Solution/Workaround**:
Use `127.0.0.1:3000` instead of `localhost:3000` in the Allowlist until validation is fixed.

**Official Status**:
- [x] Open issue (as of 2025-11-30)
- [ ] Fix announced
- [ ] Documented workaround

**Cross-Reference**:
- Related to: Skill Error #12 (Allowlist Connection Errors)
- Expands on allowlist issues with specific validation bugs

---

### Finding 1.2: Tool Parsing Fails When Tool Not Found

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #268](https://github.com/elevenlabs/elevenlabs-js/issues/268)
**Date**: 2025-09-10
**Verified**: Yes (Open issue, error message provided)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Calling `conversationalAi.conversations.get(id)` throws a parsing error when the conversation contains tool_results where the tool was not found. The SDK expects a specific type but receives `null`.

**Reproduction**:
```typescript
// When conversation has a missing/deleted tool reference
const conversation = await client.conversationalAi.conversations.get(conversationId);
// Throws: response -> transcript -> [11] -> tool_results -> [0] -> type:
// Expected string. Received null.
```

**Error Message**:
```
Error: response -> transcript -> [11] -> tool_results -> [0] -> type: [Variant 0] Expected string. Received null.;
response -> transcript -> [11] -> tool_results -> [0] -> type: [Variant 1] Expected "system". Received null.;
response -> transcript -> [11] -> tool_results -> [0] -> type: [Variant 2] Expected "workflow". Received null.
```

**Solution/Workaround**:
- SDK needs to handle null tool_results.type gracefully
- Users: Ensure all referenced tools exist before deleting them
- Users: Wrap conversation.get() in try-catch until fixed

**Official Status**:
- [x] Open issue (as of 2025-09-10)
- [ ] Fix announced
- [ ] Documented behavior

---

### Finding 1.3: Scribe Audio Format Parameter Not Transmitted (FIXED in v2.32.0)

**Trust Score**: TIER 1 - Official (GitHub PR & Release)
**Source**: [GitHub PR #319](https://github.com/elevenlabs/elevenlabs-js/pull/319), [Release v2.32.0](https://github.com/elevenlabs/elevenlabs-js/releases/tag/v2.32.0)
**Date**: Fixed 2026-01-19
**Verified**: Yes (Merged PR, released)
**Impact**: MEDIUM
**Already in Skill**: Partially (v2.28.0 fix mentioned, but not v2.32.0)

**Description**:
The Scribe WebSocket URI was not including the `audio_format` parameter even when specified, causing incorrect audio handling on the server side.

**Reproduction (Before Fix)**:
```typescript
const { connect } = useScribe({
  token: async () => fetchToken(),
  sampleRate: 24000, // This parameter was ignored
});
```

**Solution**:
Fixed in v2.32.0 (2026-01-19). Upgrade to `@elevenlabs/elevenlabs-js@2.32.0` or later.

**Official Status**:
- [x] Fixed in version 2.32.0
- [x] Documented in release notes
- [ ] Migration guide needed (minor fix, just upgrade)

**Cross-Reference**:
- Related to: Skill mentions "Scribe audio format parameter now correctly transmitted (v2.28.0)" - needs update to v2.32.0

---

### Finding 1.4: Prompt.tools Field Deprecated (Breaking Change July 2025)

**Trust Score**: TIER 1 - Official (Documentation)
**Source**: [Agent Tools Deprecation](https://elevenlabs.io/docs/agents-platform/customization/tools/agent-tools-deprecation)
**Date**: 2025-07-23 (final cutoff)
**Verified**: Yes (Official docs)
**Impact**: HIGH (Breaking change)
**Already in Skill**: No

**Description**:
The legacy `prompt.tools` array field was deprecated and removed in favor of `prompt.tool_ids` for client/server tools and `prompt.built_in_tools` for system tools. Using both fields together causes errors.

**Migration Timeline**:
| Date | Status | Impact |
|------|--------|--------|
| July 14, 2025 | Full compatibility | Legacy `prompt.tools` accepted |
| July 15, 2025 | Partial compatibility | GET endpoints stop returning `tools` field |
| July 23, 2025 | No compatibility | POST/PATCH reject requests with `prompt.tools` |

**Error Message**:
```
A request must include either prompt.tool_ids or the legacy prompt.tools array — never both
```

**Solution/Workaround**:
```typescript
// ❌ Old (deprecated):
{
  agent: {
    prompt: {
      tools: [
        { name: "get_weather", url: "https://api.weather.com", method: "GET" }
      ]
    }
  }
}

// ✅ New (required after July 23, 2025):
{
  agent: {
    prompt: {
      tool_ids: ["tool_abc123"],         // Client/server tools
      built_in_tools: ["end_call"]       // System tools (NEW field)
    }
  }
}
```

**Official Status**:
- [x] Fully deprecated (as of July 23, 2025)
- [x] Documentation updated
- [x] Tools auto-migrated to standalone records
- [x] Migration complete

**Cross-Reference**:
- Major breaking change not covered in skill
- Affects: Tool configuration, agent creation/update

---

### Finding 1.5: GPT-4o Mini Tool Calling Broken (Fixed Feb 2025)

**Trust Score**: TIER 1 - Official (Changelog)
**Source**: [Changelog Feb 17, 2025](https://elevenlabs.io/docs/changelog/2025/2/17)
**Date**: Fixed 2025-02-17
**Verified**: Yes (Official changelog)
**Impact**: HIGH (was breaking)
**Already in Skill**: No

**Description**:
Tool calling failed with agents using `gpt-4o-mini` due to an OpenAI API breaking change. This affected all tool-based workflows on that model.

**Symptoms**:
- Agents using `gpt-4o-mini` would not execute tools
- No error messages, tools silently failed
- Other models (GPT-4o, Claude, Gemini) unaffected

**Solution**:
Fixed in February 17, 2025 release. Ensure SDK version is 2.25.0+ and agents are redeployed after the fix.

**Official Status**:
- [x] Fixed (as of 2025-02-17)
- [x] Documented in changelog
- [ ] Root cause explained (OpenAI API change)

**Cross-Reference**:
- Affects: Section 5 (Tools), LLM model selection
- Historical issue worth documenting for users on older SDK versions

---

### Finding 1.6: Text-Only Conversations Require Microphone Permission (Fixed)

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #315](https://github.com/elevenlabs/elevenlabs-js/issues/315)
**Date**: Reported 2025-11-30, Fixed Dec 2025
**Verified**: Yes (Issue reported and closed)
**Impact**: MEDIUM
**Already in Skill**: Partially (December 2025 updates mention fix)

**Description**:
Starting a text-only conversation with `textOnly: true` would fail if microphone permission was denied, and would incorrectly prompt for microphone access.

**Reproduction (Before Fix)**:
```typescript
const convo = await Conversation.startSession({
  signedUrl,
  overrides: {
    conversation: {
      textOnly: true, // Should not need microphone
    },
  },
  connectionType: 'websocket',
});
// Would fail with permission error
```

**Solution**:
Fixed in Widget v0.5.5 (December 2025). Text-only mode (`chat_mode: true`) no longer requires microphone access.

**Official Status**:
- [x] Fixed in Widget v0.5.5
- [x] Documented in skill (December 2025 updates)
- [ ] SDK docs updated

**Cross-Reference**:
- Mentioned in skill under "December 2025 Updates"
- Confirms issue was real and is now resolved

---

### Finding 1.7: Speech-to-Text Webhook Response Parsing Fails

**Trust Score**: TIER 1 - Official (GitHub Issue)
**Source**: [GitHub Issue #232](https://github.com/elevenlabs/elevenlabs-js/issues/232)
**Date**: Reported 2025-08-11, Fix pending
**Verified**: Yes (Confirmed by maintainer)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
The SDK fails to parse webhook responses when using `speechToText.convert()` with `webhook: true`. The API returns only `{ request_id }` for webhook mode, but the SDK expects the full transcription schema, causing a ParseError.

**Reproduction**:
```typescript
const response = await client.speechToText.convert({
  file: audioBlob,
  modelId: 'scribe_v1',
  webhook: true,
  webhookId: 'my-webhook-id'
});
// Throws: ParseError: Missing required key "language_code"; Missing required key "text"; ...
```

**Error Message**:
```
ParseError: response: Missing required key "language_code"; response: Missing required key "language_probability"; response: Missing required key "text"; response: Missing required key "words"
```

**Workaround**:
Use direct fetch API instead of SDK for webhook mode:
```typescript
const formData = new FormData();
formData.append('file', audioFile);
formData.append('model_id', 'scribe_v1');
formData.append('webhook', 'true');
formData.append('webhook_id', webhookId);

const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
  method: 'POST',
  headers: { 'xi-api-key': apiKey },
  body: formData,
});

const result = await response.json(); // { request_id: 'xxx' }
```

**Official Status**:
- [x] Confirmed by maintainer (PaulAsjes)
- [ ] Fix in progress (as of Aug 2025)
- [ ] Documented workaround (this finding)

**Cross-Reference**:
- Affects: Scribe integration (Section 6), webhook workflows
- Blocking issue for Scribe webhook users

---

### Finding 1.8: SDK Parameter Naming - Camel Case vs Snake Case

**Trust Score**: TIER 1 - Official (GitHub Issue Comment)
**Source**: [GitHub Issue #300](https://github.com/elevenlabs/elevenlabs-js/issues/300)
**Date**: 2025-10-31
**Verified**: Yes (Maintainer clarification)
**Impact**: MEDIUM (User error but easy mistake)
**Already in Skill**: No

**Description**:
The JS SDK uses camelCase for parameters while the Python SDK and API use snake_case. This causes silent failures where parameters like `model_id` are ignored when `modelId` is expected.

**Reproduction**:
```typescript
// ❌ Wrong - parameter ignored:
const stream = await elevenlabs.textToSpeech.convert(voiceId, {
  model_id: "eleven_v3", // Snake case doesn't work
  text: "Hello"
});

// ✅ Correct - use camelCase:
const stream = await elevenlabs.textToSpeech.convert(voiceId, {
  modelId: "eleven_v3", // Camel case required
  text: "Hello"
});
```

**Common Parameters Affected**:
- `model_id` → `modelId`
- `voice_id` → `voiceId`
- `output_format` → `outputFormat`
- `voice_settings` → `voiceSettings`

**Solution**:
Always use camelCase for JS SDK parameters. Check TypeScript types for correct naming.

**Official Status**:
- [x] Documented behavior (maintainer confirmed)
- [ ] Warning in SDK for incorrect parameter names
- [ ] TypeScript types help (use them)

**Cross-Reference**:
- Affects: All API sections
- Common gotcha for Python → JS SDK migration

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: WebSocket Connection Instability - Protocol Error 1002

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #134](https://github.com/elevenlabs/elevenlabs-examples/issues/134), [WebSocket Docs](https://elevenlabs.io/docs/agents-platform/libraries/web-sockets)
**Date**: 2025-02-15
**Verified**: Multiple user reports
**Impact**: MEDIUM
**Already in Skill**: Partially (Error #10 mentions 1002)

**Description**:
Users report WebSocket connections transitioning "Disconnected → Connected → Disconnected" rapidly with protocol error 1002. This appears related to network instability or browser compatibility.

**Symptoms**:
```
Error receiving message: received 1002 (protocol error)
Error sending user audio chunk: received 1002 (protocol error)
WebSocket is already in CLOSING or CLOSED state
```

**Community Validation**:
- Multiple users reporting (GitHub issues)
- Affects React SDK primarily
- More common on certain networks/browsers

**Solution/Workaround**:
1. Use WebRTC instead of WebSocket for better stability
2. Implement reconnection logic with exponential backoff
3. Check network stability and firewall rules
4. Use `connectionType: 'webrtc'` if supported

**Cross-Reference**:
- Skill Error #10 mentions 1002 briefly
- Could expand with network troubleshooting tips

---

### Finding 2.2: elevenlabs-js Not Web-Compatible (child_process dependency)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #293](https://github.com/elevenlabs/elevenlabs-js/issues/293)
**Date**: 2025-10-21
**Verified**: Maintainer confirmed design decision
**Impact**: MEDIUM (blocking for some use cases)
**Already in Skill**: No

**Description**:
The `@elevenlabs/elevenlabs-js` package depends on Node.js `child_process` module, making it incompatible with browser/web environments (Next.js client, Electron, Tauri). The maintainer confirmed this is by design - the package is server-only.

**Use Cases Blocked**:
- Browser-based API wrapper (exposes API key risk)
- Electron apps
- Tauri desktop apps
- Serverless environments without Node.js

**Affected Frameworks**:
```
Next.js client components
Vite browser builds
Electron renderer process
Tauri webview
```

**Error Message**:
```
Module not found: Can't resolve 'child_process'
```

**Solution/Workaround**:
1. Use `@elevenlabs/client` for browser/Agents SDK use cases
2. Use `@elevenlabs/react` for React apps
3. For full API access in browser: Create proxy server endpoint
4. For Electron/Tauri: Use `@elevenlabs/elevenlabs-js` in main process only

**Official Stance** (PaulAsjes, maintainer):
> "This library is designed to operate in server environments, and there are no plans to make it work on the client long term."

**Community Validation**:
- Multiple developers requesting web support
- Some created workarounds/forks
- Official stance: use separate packages

**Cross-Reference**:
- Affects: Package selection guidance (should add to skill)
- Clarifies when to use which package

---

### Finding 2.3: Streaming Audio Playback Distortion (AudioWorklet)

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [GitHub Issue #213](https://github.com/elevenlabs/elevenlabs-js/issues/213)
**Date**: 2025-06-22
**Verified**: Detailed reproduction provided
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When streaming TTS audio directly to browser using AudioWorklet (not using ConvAI), audio arrives but plays back distorted/glitchy. This appears to be a buffering or sample rate handling issue.

**Use Case**:
- Custom TTS streaming (not using built-in Conversational AI)
- Cross-platform audio playback (iOS Safari + desktop)
- Using `outputFormat: 'pcm_24000'` with AudioWorklet

**Symptoms**:
- Audio chunks arrive correctly
- Playback sounds out-of-order or noisy
- MP3 streaming works on desktop but not iOS Safari

**Partial Details** (from issue):
```typescript
// Backend streaming works:
const stream = await elevenLabsClient.textToSpeech.stream(voiceId, {
  text: cleanTextForSpeech(text),
  modelId: 'eleven_flash_v2_5',
  outputFormat: 'pcm_24000',
});

for await (const chunk of stream) {
  socket.emit('bot-audio-chunk', chunk);
}

// Frontend AudioWorklet has playback issues (distortion)
```

**Community Validation**:
- Detailed technical reproduction
- User attempted multiple approaches
- Related to cross-browser compatibility

**Recommendation**:
Investigate further - may be user implementation issue or SDK buffering problem. Add to "Community Tips" section with caveat.

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Voice Cloning Quality Highly Input-Dependent

**Trust Score**: TIER 3 - Community Consensus
**Source**: [ElevenLabs Reviews](https://www.eesel.ai/blog/elevenlabs-reviews), [Voice Agent Trends](https://elevenlabs.io/blog/voice-agents-and-conversational-ai-new-developer-trends-2025)
**Date**: 2025
**Verified**: Multiple sources agree
**Impact**: MEDIUM (user expectation management)
**Already in Skill**: Partially (best practices mentioned)

**Description**:
Community reviews consistently report that voice cloning quality varies dramatically based on input audio quality. Poor input produces "horrifically fake" voices while clean input produces impressive results.

**Best Practices (from community)**:
- Use clean, crisp recordings with no background noise
- Avoid echo, music, or ambient sounds
- Maintain consistent microphone distance
- 10+ seconds of audio recommended (skill says 1-2 minutes)
- Use language-matched voices

**Consensus Evidence**:
- Multiple review sites mention quality variance
- ElevenLabs own blog confirms 10+ seconds requirement
- User feedback on "artificiality" linked to poor input

**Conflicting Information**:
- Skill recommends 1-2 minutes of audio
- Community suggests 10+ seconds minimum
- May depend on use case (instant clone vs professional voice)

**Recommendation**:
Add to skill with note about input quality impact. Clarify duration requirements (instant vs professional clone).

---

### Finding 3.2: Latency Trade-offs Between Models

**Trust Score**: TIER 3 - Community Consensus
**Source**: [ElevenLabs Reviews](https://www.eesel.ai/blog/elevenlabs-reviews), Blog posts
**Date**: 2025
**Verified**: Multiple sources agree
**Impact**: MEDIUM (architecture decisions)
**Already in Skill**: No

**Description**:
Community discussions highlight latency trade-offs between ElevenLabs TTS models that may impact agent responsiveness:

**Latency Numbers** (from community):
- Flash model: ~75ms (lower fidelity)
- Full model: 300ms+ (too slow for real-time)
- Turbo v2.5: (not specified but recommended for agents)

**Use Case Guidance**:
- Real-time agents: Use Flash or Turbo v2.5
- High-fidelity content: Accept 300ms+ latency
- Phone systems: Flash for responsiveness

**Consensus Evidence**:
- Multiple sources cite Flash at 75ms
- Users report 300ms+ for quality models
- ElevenLabs documentation recommends Turbo v2/v2.5 for agents

**Recommendation**:
Add latency comparison table to skill. Helps users choose models for their latency requirements.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| WebSocket error 1002 | Error #10 | Basic mention, could expand with network troubleshooting |
| Scribe audio format fix | December 2025 Updates | v2.28.0 fix mentioned, needs update to v2.32.0 |
| Text-only microphone permission | December 2025 Updates | Fix documented in Widget v0.5.5 |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Localhost Allowlist | Error #12 | Expand with validation bug details and 127.0.0.1 workaround |
| 1.2 Tool Parsing Error | Error #8 (new) | Add as new error with parsing failure details |
| 1.4 Prompt.tools Deprecated | Section 5 (Tools) | Add migration guide with timeline and code examples |
| 1.5 GPT-4o Mini Tool Calling | Section 5 (Tools) | Add historical note for users on older SDK versions |
| 1.7 Webhook Parsing | Section 6 (Scribe) | Add error + workaround for webhook users |
| 1.8 Camel Case Parameters | Common Patterns | Add parameter naming guide (camelCase vs snake_case) |
| 2.2 Web Compatibility | Package Selection | Add guidance on which package for which environment |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.3 Scribe Audio Format | December 2025 Updates | Update v2.28.0 mention to v2.32.0 |
| 2.1 WebSocket 1002 | Error #10 | Expand with network troubleshooting tips |
| 3.1 Voice Cloning Quality | Voice Features | Add input quality impact section |
| 3.2 Model Latency | TTS Configuration | Add latency comparison table |

### Priority 3: Monitor (TIER 3-4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 2.3 AudioWorklet Distortion | May be user implementation issue | Wait for maintainer response or more reports |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| Open issues list | 15 | 6 |
| Closed issues (2025+) | 30 | 8 |
| Recent releases | 10 | 3 |
| Issue #320 (Allowlist) | 1 | 1 |
| Issue #268 (Tool parsing) | 1 | 1 |
| Issue #315 (Mic permission) | 1 | 1 |
| Issue #293 (Web compat) | 1 | 1 |
| Issue #300 (Model ID) | 1 | 1 |
| Issue #232 (Webhook parsing) | 1 | 1 |

### Official Documentation

| Source | Notes |
|--------|-------|
| [Agent Tools Deprecation](https://elevenlabs.io/docs/agents-platform/customization/tools/agent-tools-deprecation) | Migration timeline |
| [Changelog Feb 17, 2025](https://elevenlabs.io/docs/changelog/2025/2/17) | GPT-4o mini fix |
| [WebSocket Docs](https://elevenlabs.io/docs/agents-platform/libraries/web-sockets) | Connection patterns |

### Web Search

| Query | Results | Quality |
|-------|---------|---------|
| WebSocket connection issues | 10 | 3 relevant (TIER 2) |
| CSP violations | 0 | No Stack Overflow results |
| Tool calling errors | 8 | 2 relevant (TIER 1) |
| Voice cloning limitations | 10 | 3 relevant (TIER 3) |
| Localhost testing | 10 | 2 relevant (TIER 1) |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release view` for changelog analysis
- `WebSearch` for community discussions
- `WebFetch` for official documentation

**Limitations**:
- Some January 2026 changelog entries were links only (no content)
- Limited Stack Overflow activity (ElevenLabs relatively new)
- Most issues in official repo vs community forums

**Time Spent**: ~25 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**:
- Verify prompt.tools deprecation timeline against current API behavior
- Check if GPT-4o mini tool calling is still an issue in latest SDK

**For api-method-checker**:
- Verify `prompt.tool_ids` and `prompt.built_in_tools` exist in current API
- Check webhook response schema for `speechToText.convert()`

**For code-example-validator**:
- Validate all code examples in findings before adding to skill
- Test camelCase parameter naming examples

---

## Integration Guide

### Adding TIER 1 Findings to SKILL.md

**Example: Finding 1.1 (Localhost Allowlist)**

```markdown
### Error 12: Allowlist Connection Errors (EXPANDED)
**Cause**: Allowlist enabled but using shared link, OR localhost validation bug
**Solution**:
1. Configure allowlist domains or disable for testing
2. **Localhost workaround**: Use `127.0.0.1:3000` instead of `localhost:3000`

**Localhost Validation Bug**:
The dashboard has inconsistent validation for localhost URLs:
- ❌ `localhost:3000` → Rejected (should be valid)
- ❌ `http://localhost:3000` → Rejected (protocol not allowed)
- ✅ `127.0.0.1:3000` → Accepted (use this for local dev)

**Source**: [GitHub Issue #320](https://github.com/elevenlabs/elevenlabs-js/issues/320)
```

**Example: Finding 1.4 (Prompt.tools Deprecated)**

```markdown
## 5. Tools (4 Types)

### ⚠️ BREAKING CHANGE: prompt.tools Deprecated (July 2025)

The legacy `prompt.tools` array was removed on **July 23, 2025**. All agent configurations must use the new format:

**Migration Timeline**:
- July 14, 2025: Legacy format still accepted
- July 15, 2025: GET responses stop including `tools` field
- **July 23, 2025**: POST/PATCH reject `prompt.tools` (active now)

**Old Format** (no longer works):
```typescript
{
  agent: {
    prompt: {
      tools: [{ name: "get_weather", url: "...", method: "GET" }]
    }
  }
}
```

**New Format** (required):
```typescript
{
  agent: {
    prompt: {
      tool_ids: ["tool_abc123"],         // Client/server tools
      built_in_tools: ["end_call"]       // System tools (new field)
    }
  }
}
```

**Error if both used**: "A request must include either prompt.tool_ids or the legacy prompt.tools array — never both"

**Source**: [Official Migration Guide](https://elevenlabs.io/docs/agents-platform/customization/tools/agent-tools-deprecation)
```

### Adding TIER 2 Findings (Community Tips Section)

```markdown
## Community Tips (Community-Sourced)

> **Note**: These tips come from community discussions and user reports. Verify against your version and use case.

### Package Selection Guide

**Which ElevenLabs package should I use?**

| Package | Environment | Use Case |
|---------|-------------|----------|
| `@elevenlabs/elevenlabs-js` | **Server only** (Node.js) | Full API access, TTS, voices, models |
| `@elevenlabs/client` | **Browser + Server** | Agents SDK, WebSocket, lightweight |
| `@elevenlabs/react` | **React apps** | Conversational AI hooks |
| `@elevenlabs/react-native` | **Mobile** | iOS/Android agents |

**Why elevenlabs-js doesn't work in browser**:
- Depends on Node.js `child_process` module
- Maintainer confirmed: server-only by design
- **Error**: `Module not found: Can't resolve 'child_process'`

**Workaround for browser API access**:
1. Create proxy server endpoint using `elevenlabs-js`
2. Call proxy from browser instead of direct API

**Source**: [GitHub Issue #293](https://github.com/elevenlabs/elevenlabs-js/issues/293) | **Confidence**: HIGH (maintainer confirmed)
```

---

**Research Completed**: 2026-01-21
**Next Research Due**: After next major release (Q2 2026) or when major breaking changes announced

---

## Sources

**GitHub Issues:**
- [ElevenLabs Agent Connection Failure on Localhost (Allowlist Issue)](https://github.com/elevenlabs/elevenlabs-js/issues/320)
- [Error when parsing conversation with tool not found](https://github.com/elevenlabs/elevenlabs-js/issues/268)
- [Cannot create a text conversation without microphone permission](https://github.com/elevenlabs/elevenlabs-js/issues/315)
- [JS SDK ignores model_id and produces poor output vs Python SDK](https://github.com/elevenlabs/elevenlabs-js/issues/300)
- [SDK fails to parse webhook responses when webhook=true](https://github.com/elevenlabs/elevenlabs-js/issues/232)
- [NextJS + web support](https://github.com/elevenlabs/elevenlabs-js/issues/293)
- [Stream audio play desktop/mobile browsers](https://github.com/elevenlabs/elevenlabs-js/issues/213)
- [Conversational AI: React example error: bundle.js:1 WebSocket is already in CLOSING or CLOSED state.](https://github.com/elevenlabs/elevenlabs-examples/issues/134)

**Official Documentation:**
- [Agent tools deprecation](https://elevenlabs.io/docs/agents-platform/customization/tools/agent-tools-deprecation)
- [February 17, 2025 Changelog](https://elevenlabs.io/docs/changelog/2025/2/17)
- [Client tools](https://elevenlabs.io/docs/agents-platform/customization/tools/client-tools)
- [Agent Testing](https://elevenlabs.io/docs/agents-platform/customization/agent-testing)
- [WebSocket Documentation](https://elevenlabs.io/docs/agents-platform/libraries/web-sockets)

**Community Resources:**
- [An honest look at ElevenLabs reviews: Is it the right AI voice for you in 2025?](https://www.eesel.ai/blog/elevenlabs-reviews)
- [Voice agents and Conversational AI: 2026 developer trends](https://elevenlabs.io/blog/voice-agents-and-conversational-ai-new-developer-trends-2025)
- [ElevenLabs API in 2025: The Ultimate Guide for Developers](https://www.webfuse.com/blog/elevenlabs-api-in-2025-the-ultimate-guide-for-developers)
