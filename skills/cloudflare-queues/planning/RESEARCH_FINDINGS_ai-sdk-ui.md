# Community Knowledge Research: ai-sdk-ui

**Research Date**: 2026-01-20
**Researcher**: skill-researcher agent
**Skill Path**: skills/ai-sdk-ui/SKILL.md
**Packages Researched**: ai@6.0.42, @ai-sdk/react@3.0.44, @ai-sdk/openai@3.0.7
**Official Repo**: vercel/ai
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | 17 |
| TIER 1 (Official) | 12 |
| TIER 2 (High-Quality Community) | 3 |
| TIER 3 (Community Consensus) | 2 |
| TIER 4 (Low Confidence) | 0 |
| Already in Skill | 4 |
| Recommended to Add | 13 |

**Key Insight**: Skill documents v6.0.23 but latest is v6.0.42 (19 patch releases behind). Most issues discovered are TIER 1 (official GitHub issues with maintainer responses). Primary gaps: React Strict Mode behavior, concurrent request handling, tool approval edge cases, and message parts validation.

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: Stale Body/Transport Values in useChat

**Trust Score**: TIER 1 - Official (23 comments, maintainer acknowledged)
**Source**: [GitHub Issue #7819](https://github.com/vercel/ai/issues/7819)
**Date**: 2025-08-06
**Verified**: Yes (multiple reproductions)
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When passing `body` or transport configuration to `useChat`, the values are captured at first render and never update, even when dependencies change. This causes stale data to be sent with requests, breaking use cases that need dynamic context (user ID, session data, feature flags).

**Why It Happens**:
The `useChat` hook stores options in a `useRef` that only updates if the `id` prop changes. The `shouldRecreateChat` check only looks at `id` or `chat` instance equality, not deep option changes.

**Reproduction**:
```tsx
const { userId } = useUser(); // Changes after auth
const { messages, sendMessage } = useChat({
  body: { userId }, // ❌ Captured once, never updates
});

// Later when userId changes, still sends original userId
```

**Workarounds** (from maintainer & community):

1. **Pass body in sendMessage (recommended by maintainer)**:
```tsx
const { sendMessage } = useChat();
const { userId } = useUser();

sendMessage({
  content: input,
  data: { userId }, // ✅ Fresh on each send
});
```

2. **Use useRef to track values**:
```tsx
const bodyRef = useRef(body);
bodyRef.current = body; // Update on each render

useChat({
  transport: new DefaultChatTransport({
    body: () => bodyRef.current, // ✅ Always fresh
  }),
});
```

3. **Change useChat id to force recreation** (gross workaround):
```tsx
useChat({
  id: `${sessionId}-${taskId}-${userId}`, // Forces recreation
  body: { taskId, userId },
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (workaround known)
- [x] Known issue, workaround required
- [ ] Won't fix

**Maintainer Quote** (@gr2m): "We are aware that this is a problem. We just couldn't prioritize it yet, sorry. At least there is a workaround, albeit gross 😁"

**Cross-Reference**:
- Related: Issue #11686 (stale closures in onData/onFinish)
- Skill partially covers: "Stale body values" in top-ui-errors.md but workarounds incomplete

---

### Finding 1.2: React Strict Mode Double Execution (useChat/useCompletion)

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #7891](https://github.com/vercel/ai/issues/7891), [Issue #6166](https://github.com/vercel/ai/issues/6166)
**Date**: 2025-08-08 (ongoing)
**Verified**: Yes (multiple reports)
**Impact**: HIGH (causes double API calls, doubled token usage)
**Already in Skill**: No

**Description**:
When using `useChat` or `useCompletion` in React Strict Mode and calling `sendMessage()` or `complete()` in `useEffect` (e.g., auto-resume, initial message), React's double-invocation causes two concurrent streams to open. Both fight for state updates, causing race conditions and duplicate messages. Also drains token usage in development.

**Why It Happens**:
React Strict Mode intentionally double-invokes effects to catch side effects. The SDK doesn't guard against concurrent requests or provide built-in idempotency for auto-resume scenarios.

**Reproduction**:
```tsx
'use client';
import { useChat } from '@ai-sdk/react';
import { useEffect } from 'react';

export default function Chat() {
  const { messages, resumeStream } = useChat({
    api: '/api/chat',
    resume: true, // ❌ Triggers twice in strict mode
  });

  useEffect(() => {
    resumeStream(); // Called twice → two streams
  }, []);
}
```

**Solution/Workaround**:
```tsx
// ✅ Use ref to track if already sent
const hasSentRef = useRef(false);

useEffect(() => {
  if (hasSentRef.current) return;
  hasSentRef.current = true;

  sendMessage({ content: 'Hello' });
}, []);

// OR for resume specifically (from maintainer):
const hasResumedRef = useRef(false);

useEffect(() => {
  if (!autoResume || hasResumedRef.current || status === 'streaming') return;
  hasResumedRef.current = true;
  resumeStream();
}, [autoResume, resumeStream, status]);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (React Strict Mode expected)
- [x] Known issue, workaround required
- [ ] Won't fix

**Community Note**: Multiple users disabled Strict Mode to work around this, which is NOT recommended.

---

### Finding 1.3: TypeError in onFinish When Using resume: true

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #8477](https://github.com/vercel/ai/issues/8477)
**Date**: 2025-09-06
**Verified**: Yes (patch available)
**Impact**: HIGH (crashes on resume)
**Already in Skill**: No

**Description**:
When using `resume: true` with `useChat` and an `onFinish` callback, navigating away mid-stream and then resuming causes a TypeError: `Cannot read properties of undefined (reading 'state')`. This happens because `this.activeResponse` gets cleared/overwritten by concurrent `makeRequest` calls.

**Why It Happens**:
The `finally` block in `makeRequest` references `this.activeResponse`, but if an error occurs before assignment or a concurrent request overwrites it, the reference becomes undefined when `onFinish` tries to access `this.activeResponse.state`.

**Reproduction**:
```tsx
const { messages, sendMessage } = useChat({
  api: '/api/chat',
  resume: true,
  onFinish: (message) => {
    console.log('Finished:', message);
  },
});

// 1. Start streaming
// 2. Navigate to new page (doesn't stop stream)
// 3. Resume stream → TypeError
```

**Solution/Workaround** (community patch):
```typescript
// In ai package (dist/index.mjs), capture activeResponse locally:
let activeResponse;
try {
  activeResponse = {
    state: createStreamingUIMessageState({ /* ... */ })
  };
  // ... rest of makeRequest
} finally {
  if (activeResponse) { // ✅ Check before accessing
    this.onFinish?.call(this, {
      message: activeResponse.state.message,
      // ...
    });
  }
}
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, patch available (use patch-package)
- [ ] Won't fix

**Maintainer Note**: A PR (#8689) was opened but closed without explanation. Community using patch-package workaround.

---

### Finding 1.4: useChat stop() Does Not Cancel Streaming Responses

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10719](https://github.com/vercel/ai/issues/10719)
**Date**: 2025-11-29
**Verified**: Partial (Remix-only?)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Calling `stop()` from `useChat` does not reliably cancel the streaming response. The abort signal is sent but the server may continue processing. This is potentially framework-specific (reported on Remix, not reproducible on Next.js).

**Why It Happens**:
Unclear - may be related to framework-specific fetch implementations or SSE handling.

**Reproduction**:
```tsx
const { messages, stop, isLoading } = useChat();

<button onClick={stop} disabled={!isLoading}>
  Stop Generation
</button>
// ❌ Stream continues after stop() called
```

**Solution/Workaround**:
Not yet determined. Issue is still open.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, no workaround yet
- [ ] Won't fix

---

### Finding 1.5: ZodError "Message must contain at least one part" When Stopping Stream Early

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11444](https://github.com/vercel/ai/issues/11444)
**Date**: 2025-12-27
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using `createAgentUIStreamResponse` with `validateUIMessage`, calling `stop()` before the AI generates any response parts causes a ZodError: "Message must contain at least one part". This happens because `validateUIMessage` doesn't allow empty messages.

**Why It Happens**:
The validation function requires at least one part in every message, but stopping early leaves an empty assistant message.

**Reproduction**:
```tsx
const { messages, stop } = useChat({
  api: '/api/chat', // Uses createAgentUIStreamResponse + validateUIMessage
});

// User stops immediately after sending
stop(); // ❌ ZodError if no parts generated yet
```

**Solution/Workaround**:
```typescript
// Filter out empty messages before validation
const filteredMessages = messages.filter(m => m.parts && m.parts.length > 0);
const validMessages = validateUIMessages(filteredMessages);
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

**Maintainer Response**: Suggested filtering empty messages before sending to `validateUIMessages`.

---

### Finding 1.6: Concurrent sendMessage Calls Cause State Corruption

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11024](https://github.com/vercel/ai/issues/11024)
**Date**: 2025-12-10
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
Calling `sendMessage()` before the previous request finishes streaming causes a TypeError: `Cannot read properties of undefined (reading 'state')`. This happens because the second request overwrites `this.activeResponse` while the first is still streaming, causing state corruption.

**Why It Happens**:
The SDK doesn't guard against concurrent requests. Each `sendMessage()` creates a new `activeResponse`, overwriting the previous one mid-stream.

**Reproduction**:
```tsx
const { sendMessage, isLoading } = useChat();

// Rapid double-click or programmatic double-send
sendMessage({ content: 'First' });
sendMessage({ content: 'Second' }); // ❌ Overwrites activeResponse
```

**Solution/Workaround**:
```tsx
// Guard against concurrent sends
const [isSending, setIsSending] = useState(false);

const handleSend = async (content: string) => {
  if (isSending) return; // ✅ Block concurrent calls
  setIsSending(true);
  try {
    await sendMessage({ content });
  } finally {
    setIsSending(false);
  }
};
```

**Maintainer Response**: "Simply restrict sending request until in flight requests finish streaming response"

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.7: Tool Approval with onFinish Callback Breaks Workflow

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #10169](https://github.com/vercel/ai/issues/10169)
**Date**: 2025-11-11
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No (tool approval is documented but not this specific edge case)

**Description**:
When using `needsApproval` tools with an `onFinish` callback, the approval workflow breaks. Calling `sendMessage()` or `regenerate()` inside `onFinish` or `onError` triggers the TypeError from Finding 1.3.

**Why It Happens**:
The callback runs synchronously within the stream finalization, and re-entering `makeRequest` corrupts `activeResponse`.

**Reproduction**:
```tsx
const { sendMessage, regenerate } = useChat({
  onFinish: () => {
    void sendMessage({ content: 'Continue...' }); // ❌ Breaks
  },
  onError: () => {
    void regenerate(); // ❌ Breaks
  },
});
```

**Solution/Workaround**:
```tsx
// Defer the call to next tick
const { sendMessage } = useChat({
  onFinish: () => {
    queueMicrotask(() => {
      void sendMessage({ content: 'Continue...' }); // ✅ Works
    });
  },
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround required
- [ ] Won't fix

---

### Finding 1.8: useChat Crashes After Tool Calls with "Cannot read properties of undefined (reading 'text')"

**Trust Score**: TIER 1 - Official (Provider-Side Issue - FIXED)
**Source**: [GitHub Issue #11765](https://github.com/vercel/ai/issues/11765)
**Date**: 2026-01-13
**Verified**: Yes (was Anthropic provider bug)
**Impact**: HIGH (but FIXED)
**Already in Skill**: No

**Description**:
When using Anthropic provider with tools, text generation resuming after tool calls would crash with "Cannot read properties of undefined (reading 'text')". This was caused by Anthropic sending text-deltas with incorrect indices.

**Why It Happened**:
Anthropic's streaming response included text-delta chunks with index mismatches (e.g., index 1 when only index 0 exists), causing the SDK to access undefined array elements.

**Official Status**:
- [x] Fixed by Anthropic (no SDK change needed)
- [x] Temporary SDK patch available (but not needed anymore)
- [ ] Known issue
- [ ] Won't fix

**Resolution**: Anthropic fixed the bug on their end. Users should verify they're no longer experiencing this without any code changes.

---

### Finding 1.9: convertToModelMessages Fails with Tool Approval Parts

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #9968](https://github.com/vercel/ai/issues/9968)
**Date**: 2025-11-01
**Verified**: Yes
**Impact**: HIGH
**Already in Skill**: No

**Description**:
When using `convertToModelMessages` with messages containing tool approval parts (`tool-approval-request`, `tool-approval-response`), the function throws "no tool invocation found for tool call [id]". This happens even when tools are passed in the second argument.

**Why It Happens**:
The conversion function doesn't properly handle the three-part approval flow structure (tool-call → approval-request → approval-response → tool-result).

**Reproduction**:
```tsx
const tools = { myTool };
const convertedMessages = convertToModelMessages(messages, { tools });

// ❌ Error: no tool invocation found for tool call toolu_123
// Even though message structure is:
// - tool-call part
// - tool-approval-request part
// - tool-approval-response part (approved: true)
// - (expects tool-result but conversion fails before that)
```

**Solution/Workaround**:
Issue is still open. Maintainer suggested passing tools in second arg but multiple users confirm it doesn't fix the issue.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, no clear workaround
- [ ] Won't fix

**Additional Symptom**: UI shows duplicate assistant messages with same message ID when this error occurs.

---

### Finding 1.10: onData and onFinish Have Stale Closures with Memoized Options

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11686](https://github.com/vercel/ai/issues/11686)
**Date**: 2026-01-09
**Verified**: Yes (reproduction available)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When passing `onData` or `onFinish` callbacks in `useChat` options and the options object is memoized, the callbacks capture stale values from their closure. This is related to Finding 1.1 but specific to callback functions.

**Reproduction**:
```tsx
const [count, setCount] = useState(0);

const options = useMemo(() => ({
  api: '/api/chat',
  onFinish: (message) => {
    console.log(count); // ❌ Always logs 0 (stale)
  },
}), []); // Empty deps → callbacks never update

useChat(options);
```

**Solution/Workaround**:
Same workarounds as Finding 1.1 - either avoid memoization or use refs.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, related to #7819
- [ ] Won't fix

**Full Reproduction**: https://github.com/alechoey/ai-sdk-stale-ondata-repro

---

### Finding 1.11: useChat Does Not Update When Transport Changes

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #8956](https://github.com/vercel/ai/issues/8956)
**Date**: 2025-09-26
**Verified**: Yes
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Changing the `transport` option (e.g., switching API endpoints based on user action) does not cause `useChat` to update. The old transport continues to be used until the component unmounts.

**Why It Happens**:
Related to the `shouldRecreateChat` logic - transport changes aren't detected unless `id` or `chat` instance changes.

**Reproduction**:
```tsx
const [endpoint, setEndpoint] = useState('/api/chat');

const transport = useMemo(() => new DefaultChatTransport({
  api: endpoint,
}), [endpoint]);

useChat({ transport }); // ❌ Changing endpoint doesn't update transport
```

**Solution/Workaround**:
Change the `id` prop when transport should change:
```tsx
useChat({
  id: endpoint, // ✅ Forces recreation on endpoint change
  transport,
});
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [x] Known issue, workaround available
- [ ] Won't fix

---

### Finding 1.12: useCompletion Missing Access to "data-" Streaming Values

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #11619](https://github.com/vercel/ai/issues/11619)
**Date**: 2026-01-07
**Verified**: Yes (documentation issue)
**Impact**: LOW (documentation clarity)
**Already in Skill**: No

**Description**:
The official docs suggest that `useCompletion` supports streaming custom data via "data-" protocol, but there's no way to access these values in the hook's return value. Unlike `useChat` which has `data` field, `useCompletion` doesn't expose streamed metadata.

**Solution/Workaround**:
Use `useChat` instead if you need access to streamed metadata.

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [x] Documented behavior (docs need clarification)
- [ ] Known issue
- [ ] Won't fix

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: Passing undefined id to useChat Causes Infinite Rerenders

**Trust Score**: TIER 2 - Community Report
**Source**: [GitHub Issue #8087](https://github.com/vercel/ai/issues/8087)
**Date**: 2025-08-15
**Verified**: Code review (matches useRef behavior)
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
Passing `id: undefined` to `useChat` causes infinite rerenders. This can happen accidentally when using conditional logic to compute the id.

**Reproduction**:
```tsx
const chatId = someCondition ? 'chat-123' : undefined;
useChat({ id: chatId }); // ❌ Infinite loop if undefined
```

**Solution/Workaround**:
```tsx
// Always provide a stable id
const chatId = someCondition ? 'chat-123' : 'default';
useChat({ id: chatId }); // ✅
```

**Community Validation**:
- Single report, no upvotes yet (issue opened recently)
- Matches expected behavior of useRef with undefined key

---

### Finding 2.2: Flickering Issue with Multiple Tool Calls and addToolResult

**Trust Score**: TIER 2 - Community Report
**Source**: [GitHub Issue #7430](https://github.com/vercel/ai/issues/7430)
**Date**: 2025-07-21
**Verified**: Multiple users confirm
**Impact**: MEDIUM (UI issue)
**Already in Skill**: No

**Description**:
When triggering multiple tool calls rapidly and using `addToolResult`, the UI flickers as messages are added and updated. This is a race condition in state updates.

**Reproduction**:
```tsx
// Multiple rapid tool calls
onToolCall: async ({ toolCall }) => {
  const result = await executeTool(toolCall);
  addToolResult({ toolCallId: toolCall.id, result });
  // ❌ Flickering as messages update
}
```

**Solution/Workaround**:
No clear workaround yet. May need batching of tool results.

**Community Validation**:
- 5 comments confirming issue
- No accepted solution yet

---

### Finding 2.3: Resumable Streams Get Stopped Early When Abort Signal Sent

**Trust Score**: TIER 2 - Community Report
**Source**: [GitHub Issue #6502](https://github.com/vercel/ai/issues/6502)
**Date**: 2025-05-27
**Verified**: Multiple users, 10 comments
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
When using resumable streams (`resume: true`), sending an abort signal permanently stops the stream instead of allowing it to resume later. This breaks the resume functionality.

**Reproduction**:
```tsx
const { stop, resumeStream } = useChat({
  resume: true,
});

stop(); // ❌ Permanently stops, can't resume later
resumeStream(); // Doesn't work
```

**Solution/Workaround**:
Avoid using `stop()` with resumable streams. Instead, let streams finish naturally and use UI state to hide the output.

**Community Validation**:
- 10 comments
- Multiple users confirm
- No fix yet

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: Safari User Agent Errors When Sending Messages

**Trust Score**: TIER 3 - Community Discussion
**Source**: [GitHub Issue #9256](https://github.com/vercel/ai/issues/9256)
**Date**: 2025-10-07
**Verified**: Cross-referenced only (10 comments)
**Impact**: MEDIUM (Safari-specific)
**Already in Skill**: No

**Description**:
Some users report User Agent errors when sending messages from Safari. The exact cause is unclear but may be related to CORS or Safari's fetch implementation.

**Consensus Evidence**:
- 10 comments discussing workarounds
- Not reproducible in all Safari versions
- May be environment-specific (proxy/firewall)

**Recommendation**: Monitor, insufficient data to add to skill yet.

---

### Finding 3.2: Dynamic Proxy Hook for Transport (Community Pattern)

**Trust Score**: TIER 3 - Community Solution
**Source**: [GitHub Issue #7819 Comment](https://github.com/vercel/ai/issues/7819#issuecomment-3273523187)
**Date**: 2025-08-06
**Verified**: Code review only
**Impact**: MEDIUM
**Already in Skill**: No

**Description**:
A community member shared a custom hook using Proxy to make transport options dynamic without changing the `id` prop.

**Solution**:
```tsx
const useDynamicChatTransport = <UI_MESSAGE extends UIMessage = UIMessage>(
  transport: ChatTransport<UI_MESSAGE>,
): ChatTransport<UI_MESSAGE> => {
  const transportRef = useRef<ChatTransport<UI_MESSAGE>>(transport);
  useEffect(() => {
    transportRef.current = transport;
  });
  const dynamicTransport = useMemo(
    () =>
      new Proxy(transportRef.current, {
        get(_, prop) {
          const res = transportRef.current[prop as keyof ChatTransport<UI_MESSAGE>];
          return typeof res === "function" ? res.bind(transportRef.current) : res;
        },
      }),
    [],
  );
  return dynamicTransport;
};

// Usage
useChat({
  transport: useDynamicChatTransport(new HttpChatTransport({
    body: { myValue }, // ✅ Always fresh
  })),
});
```

**Consensus Evidence**:
- Single source (community member)
- Not tested by maintainers
- Clever but complex workaround

**Recommendation**: Add to "Community Tips (Advanced)" section with caveat about maintainer endorsement.

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None identified. All findings had sufficient verification or maintainer acknowledgment.

---

## Already Documented in Skill

| Finding | Skill Section | Coverage |
|---------|---------------|----------|
| Stale body values | top-ui-errors.md #7 | Partially covered - workarounds incomplete |
| useChat failed to parse stream | top-ui-errors.md #1 | Fully covered |
| React maximum update depth | top-ui-errors.md #9 | Fully covered (but not strict mode specifics) |
| Message parts structure | v6 changes section | Fully covered |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 Stale body/transport | Known Issues Prevention | Expand existing Issue #7 with all 3 workarounds |
| 1.2 React Strict Mode | New: "React Strict Mode Considerations" | Add new section with useRef pattern |
| 1.3 TypeError with resume | Known Issues Prevention | Add as new issue with patch workaround |
| 1.6 Concurrent sendMessage | Known Issues Prevention | Add as new issue with guard pattern |
| 1.7 Tool approval + onFinish | Tool Approval section | Add edge case with queueMicrotask solution |
| 1.9 convertToModelMessages | Tool Approval section | Add warning about conversion limitations |

### Priority 2: Consider Adding (TIER 1-2, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 1.4 stop() doesn't cancel | Known Issues | Framework-specific, needs more data |
| 1.5 ZodError on early stop | Known Issues | Add to agent section with filter workaround |
| 1.10 Stale closures callbacks | Known Issues | Related to 1.1, cross-reference |
| 1.11 Transport doesn't update | Known Issues | Related to 1.1, cross-reference |
| 2.1 undefined id infinite loop | Common Mistakes | Add to best practices |
| 2.2 Flickering with tools | Known Issues | Add if more users report |

### Priority 3: Monitor (TIER 2-3, Needs More Data)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 1.12 useCompletion data access | Docs issue, low impact | Wait for official doc fix |
| 2.3 Resumable + abort | Complex edge case | Wait for more reproductions |
| 3.1 Safari User Agent | Environment-specific | Need reproducible case |
| 3.2 Dynamic Proxy hook | Clever but unofficial | Wait for maintainer feedback |

---

## Package Version Updates Needed

**Current in skill**: v6.0.23
**Latest stable**: v6.0.42
**Gap**: 19 patch releases (2026-01-03 to 2026-01-20)

**Action**: Update package versions in SKILL.md and README.md to reflect latest stable.

**Breaking changes in gap**: None (patch releases only)

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "useChat" since 2025-05-01 | 50 | 15 |
| "useChat edge case OR gotcha" | 0 | 0 (too specific) |
| "useChat workaround" | 0 | 0 (too specific) |
| Label "ai/ui" since 2025-11-01 | 30 | 13 |
| Tool approval issues | 20 | 9 |
| Message parts issues | 13 | 5 |

**Key Issues Reviewed**:
- #7819 (stale body, 23 comments)
- #7891 (strict mode, 6 comments)
- #8477 (onFinish TypeError, 9 comments)
- #10719 (stop doesn't work, 1 comment)
- #11444 (ZodError on stop, 3 comments)
- #11024 (concurrent sends, 8 comments)
- #10169 (tool approval + onFinish, 1 comment)
- #11765 (Anthropic bug - fixed, 10 comments)
- #9968 (convertToModelMessages, 16 comments)
- #11686 (stale closures, 1 comment)

### Official Documentation

| Source | Relevant Findings |
|--------|-------------------|
| [AI SDK 6 Blog Post](https://vercel.com/blog/ai-sdk-6) | Tool approval UI, typed messages |
| [Migration Guide 6.0](https://ai-sdk.dev/docs/migration-guides/migration-guide-6-0) | Tool UI part helper renames |

### Stack Overflow

| Query | Results |
|-------|---------|
| "vercel ai sdk useChat" 2024-2025 | 0 relevant |
| "useChat edge case" | 0 |

**Finding**: No significant Stack Overflow activity for ai-sdk-ui. Community primarily uses GitHub issues.

### Community Blogs/Articles

- [DEV.to: Vercel AI SDK Complete Guide](https://dev.to/pockit_tools/vercel-ai-sdk-complete-guide-building-production-ready-ai-chat-apps-with-nextjs-4cp6) - General guide, no new edge cases
- [Semaphore: Developing an AI Chatbot](https://semaphore.io/blog/vercel-ai-sdk) - Tutorial, no edge cases

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `gh issue view` for detailed issue content
- `gh release list` for recent changes
- `WebSearch` for Stack Overflow and community content
- `WebFetch` for official documentation
- `npm view` for latest package versions

**Limitations**:
- Stack Overflow has very little AI SDK v6 content (too new)
- Many issues are still open with no clear resolution
- Some issues may be framework-specific (Next.js vs Remix vs others)
- Tool approval feature is v6 beta → stable, edge cases still being discovered

**Time Spent**: ~35 minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Verify that workarounds in findings 1.1, 1.2, 1.3, 1.6, 1.7 work with current v6.0.42 before adding.

**For api-method-checker**: Verify that `queueMicrotask` (Finding 1.7) and `addToolApprovalResponse` (documented in skill) are available in @ai-sdk/react@3.0.44.

**For code-example-validator**: Validate all code examples in findings before adding to skill. Especially check:
- Finding 1.1 (all 3 workarounds)
- Finding 1.2 (useRef pattern)
- Finding 1.6 (guard pattern)
- Finding 1.7 (queueMicrotask pattern)

**For web-researcher**: If needed, use Firecrawl to fetch full content of GitHub issues that were truncated.

---

## Integration Guide

### Adding to Known Issues Section

For findings 1.1, 1.2, 1.3, 1.6, 1.7, add to `references/top-ui-errors.md` using this format:

```markdown
### Issue #[N]: [Title from finding]

**Error**: `[error message if applicable]`
**Source**: [GitHub Issue #X](https://github.com/vercel/ai/issues/X)
**Affects**: useChat (v6.0+)
**Severity**: HIGH/MEDIUM/LOW

**Why It Happens**:
[explanation]

**Solution**:
```typescript
// ✅ Correct pattern
[code from finding]
```

**Alternative Workarounds**:
- [list other workarounds if multiple]
```

### Adding React Strict Mode Section

Add new section to SKILL.md after "Streaming Best Practices":

```markdown
## React Strict Mode Considerations

React Strict Mode intentionally double-invokes effects to catch bugs. When using `useChat` or `useCompletion` in effects (auto-resume, initial messages), guard against double execution:

**Problem**:
```tsx
// ❌ Triggers twice in strict mode
useEffect(() => {
  sendMessage({ content: 'Hello' });
}, []);
```

**Solution**:
```tsx
// ✅ Use ref to track execution
const hasSentRef = useRef(false);

useEffect(() => {
  if (hasSentRef.current) return;
  hasSentRef.current = true;
  sendMessage({ content: 'Hello' });
}, []);
```

**Source**: [GitHub Issue #7891](https://github.com/vercel/ai/issues/7891), [Issue #6166](https://github.com/vercel/ai/issues/6166)
```

### Updating Existing "Stale Body Values" Section

Expand the existing section in `references/top-ui-errors.md` with all workarounds from Finding 1.1.

---

**Research Completed**: 2026-01-20 14:32
**Next Research Due**: After AI SDK v7.0 release or in 3 months (2026-04-20)
**Confidence Level**: HIGH (12/17 findings are TIER 1 official sources)
