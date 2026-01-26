# AI SDK State - January 2026

**Research Date**: 2026-01-18
**Purpose**: Inform ai-dev agent runtime verification requirements

---

## 1. Vercel AI SDK

### Current Version
- **Package**: `ai`
- **Version**: 6.0.39 (as of 2026-01-17)
- **Status**: Active development

### Recent Breaking Changes

#### v5 to v6 (Current)
**Migration**: `npx @ai-sdk/codemod v6`

**Key Changes**:
- `Experimental_Agent` → `ToolLoopAgent` class
- `system` parameter → `instructions`
- Default step limit: 1 → 20
- `CoreMessage` type removed (use `ModelMessage`)
- `convertToModelMessages()` now async
- `generateObject`/`streamObject` deprecated → use `generateText`/`streamText` with `output` parameter
- Tool definitions support per-tool `strict` mode
- `toModelOutput()` signature changed to destructured object
- Embedding methods renamed: `textEmbeddingModel` → `embeddingModel`, `textEmbedding` → `embedding`

**Provider-Specific**:
- OpenAI: `strictJsonSchema` defaults to `true`
- Azure: Defaults to Responses API (use `azure.chat()` for legacy)
- Anthropic: New `structuredOutputMode` option
- Google Vertex: Metadata key `google` → `vertex`

#### v4 to v5 (Major Breaking Change)
**Biggest Change**: Stream protocol switched from proprietary format to Server-Sent Events (SSE)

**Message Format**:
- Complete restructure of message format
- Existing v4 saved messages incompatible (no auto-migration)
- New stream protocol uses start/delta/end pattern
- Text: `text-start`, `text-delta`, `text-end`
- Reasoning: `reasoning-start`, `reasoning-delta`, `reasoning-end`
- Header required: `x-vercel-ai-ui-message-stream: v1`

**Impact**: Described as "by far the biggest breaking change" affecting everyone

### What ai-dev Agent Should Check
1. Package version (v6.x expected in 2026)
2. Migration status if using v4/v5 patterns
3. Stream protocol compatibility (SSE vs legacy)
4. Message format validation
5. Provider-specific defaults (especially OpenAI strict mode)

---

## 2. OpenAI SDK

### Current Version
- **Package**: `openai`
- **Version**: 6.16.0 (as of 2026-01-11)
- **Status**: Active development

### Model Deprecations (2025-2026)

#### February 16, 2026
**Model**: `chatgpt-4o-latest` (chat-only, text-based variant)
- **Status**: Will be retired
- **Notice**: 3-month transition period (announced Nov 2025)
- **Replacement**: GPT-5.1 series (`gpt-5.1-mini`, `gpt-5.1-base`, `gpt-5.1-ultimate`)
- **Note**: Full multimodal GPT-4o, GPT-4o Transcribe, GPT-4o mini variants remain available

#### February 27, 2026
**API**: Realtime API Beta
- **Status**: Will be deprecated and removed
- **Replacement**: TBD

#### 2026 (Date TBD)
**API**: Assistants API
- **Status**: Planned sunset in 2026
- **Replacement**: Responses API (announced March 2025)

#### Already Deprecated
- `gpt-4.5-preview` - Removed from API in 2025

### Migration Guidance
- **Immediate action**: Migrate from `chatgpt-4o-latest` to GPT-5.1 series
- **Benefits**: Larger context windows, better reasoning, lower cost per token, higher throughput

### What ai-dev Agent Should Check
1. Usage of `chatgpt-4o-latest` → flag for migration
2. Usage of Realtime API Beta → warn about February 2026 removal
3. Usage of Assistants API → suggest Responses API
4. Recommend GPT-5.1 series for new projects
5. Package version (v6.x expected)

---

## 3. Anthropic SDK

### Current Version
- **Package**: `@anthropic-ai/sdk`
- **Version**: 0.71.2 (as of 2025-12-18)
- **Status**: Active development

### Platform Changes
- **Console rebranded**: console.anthropic.com → platform.claude.com
- **Redirect active**: Until January 12, 2026
- **API unchanged**: Endpoints, headers, env vars, SDKs remain same

### SDK Changes
- **Claude Code SDK** → **Claude Agent SDK** (early 2026)
- **Migration guide available** for breaking changes
- **Package**: `@anthropic-ai/claude-agent-sdk`

### Model Deprecations (2025-2026)

#### January 5, 2026
**Model**: Claude 3 Opus
- **Status**: Will be retired
- **Deprecated**: June 30, 2025
- **Replacement**: Opus 4.1

#### Already Retired (2025)
- Claude 3 Sonnet (2024-02-29) - Retired July 21, 2025
- Claude 2.1 - Retired July 21, 2025
- Claude 3.5 Sonnet (all variants) - Retired October 28, 2025

#### Platform-Specific (Google Vertex AI)
- Claude 3.5 Sonnet: Shutdown Feb 19, 2026
- Claude 3.5 Haiku: Shutdown July 5, 2026
- Claude 3.7 Sonnet: Shutdown May 11, 2026

### Current GA Models (2026)
- Claude 4.x Sonnet
- Claude 4.x Opus 4.1
- All actively maintained

### Versioning Policy
- Follows SemVer with exceptions:
  - Static type changes (no runtime impact)
  - Library internals (not documented for external use)
  - Changes not expected to impact majority of users

### What ai-dev Agent Should Check
1. Usage of deprecated Claude 3.x models → migrate to Claude 4.x
2. Platform console references → update to platform.claude.com
3. Claude Code SDK usage → migrate to Claude Agent SDK
4. Package version (0.7x expected)
5. Ensure 60-day notice compliance for custom integrations

---

## 4. Google Generative AI SDK

### Current Version
- **Package**: `@google/genai` (NEW unified SDK)
- **Version**: 1.37.0 (as of 2026-01-16)
- **Status**: Active development for Gemini 2.0+ features

### SDK Migration
**CRITICAL**: SDK package changed in 2025-2026

**Old (Deprecated)**:
- `@google/generative-ai` - Support ends **August 31, 2025**
- `@google/generative_language` - No new features
- `@google-cloud/vertexai` - No new features

**New (Current)**:
- `@google/genai` - Unified SDK for Gemini 2.0+
- Works with Gemini Developer API and Vertex AI
- Supports Gemini 2.5 Pro and 2.0 models

### Model Deprecations (2025-2026)

#### Already Retired
- All Gemini 1.0 models - Return 404 error
- All Gemini 1.5 models - Return 404 error
- `gemini-2.0-flash-live-001` - Shutdown Dec 9, 2025
- `gemini-live-2.5-flash-preview` - Shutdown Dec 9, 2025

#### January 2026
- `text-embedding-004` - Shutdown Jan 14, 2026
- `gemini-2.5-flash-image-preview` - Shutdown Jan 15, 2026

#### February 17, 2026
- Multiple models (specific list not detailed in sources)

#### March 3, 2026
**Models**: Gemini 2.0 Flash and Gemini 2.0 Flash-Lite
- **Status**: Will be retired
- **Replacement**: `gemini-2.5-flash-lite` or newer
- **Note**: Stable Gemini Live API 2.0 models NOT impacted

### Current Models (2026)
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 2.5 Flash-Lite
- Stable Gemini Live API 2.0

### What ai-dev Agent Should Check
1. Package migration: `@google/generative-ai` → `@google/genai`
2. Usage of Gemini 1.x models → all return 404
3. Usage of Gemini 2.0 Flash → migrate by March 3, 2026
4. Embedding model: `text-embedding-004` → newer model
5. Package version (1.3x expected for `@google/genai`)
6. Warn if using deprecated package after August 31, 2025

---

## Summary: What ai-dev Agent Must Verify

### Runtime Checks (High Priority)

1. **Package Versions**
   - `ai`: v6.x (not v4/v5)
   - `openai`: v6.x
   - `@anthropic-ai/sdk`: v0.7x
   - `@google/genai`: v1.3x (NOT `@google/generative-ai`)

2. **Deprecated Models in Code**
   - OpenAI: `chatgpt-4o-latest` (dead Feb 16, 2026)
   - Anthropic: Claude 3.x (most already retired)
   - Google: Gemini 1.x (404), Gemini 2.0 Flash (dead March 3, 2026)

3. **Breaking API Patterns**
   - Vercel AI SDK v4 message format
   - Vercel AI SDK v5 → v6 class names
   - Anthropic console URLs
   - Google deprecated SDK packages

4. **Stream Protocol**
   - Vercel AI SDK: Ensure SSE (not proprietary v4 format)
   - Check for `x-vercel-ai-ui-message-stream` header

### Recommended Actions

**For Projects Using**:
- **Old AI SDK versions** → Run codemod, update deps
- **Deprecated models** → Suggest replacements with migration path
- **Google old SDK** → Flag urgently (Aug 31, 2025 cutoff)
- **Claude 3.x** → Migrate to Claude 4.x immediately

### Error Prevention Opportunities

1. Model 404 errors (Gemini 1.x, retired Claude models)
2. Breaking changes from v4 → v5 → v6 AI SDK migrations
3. Package not found (old Google SDK)
4. Stream format incompatibility
5. Deprecated API endpoints (Assistants API, Realtime API)

---

## Sources

### Vercel AI SDK
- [AI SDK 6 Migration Guide](https://ai-sdk.dev/docs/migration-guides/migration-guide-6-0)
- [AI SDK 5 Migration Guide](https://ai-sdk.dev/docs/migration-guides/migration-guide-5-0)
- [AI SDK 6 Announcement](https://vercel.com/blog/ai-sdk-6)
- [AI SDK 5 Announcement](https://vercel.com/blog/ai-sdk-5)
- [Vercel AI GitHub Releases](https://github.com/vercel/ai/releases)
- [NPM: ai package](https://www.npmjs.com/package/ai)

### OpenAI
- [OpenAI ending GPT-4o API access](https://venturebeat.com/ai/openai-is-ending-api-access-to-fan-favorite-gpt-4o-model-in-february-2026)
- [OpenAI Deprecations](https://platform.openai.com/docs/deprecations)
- [OpenAI Changelog](https://platform.openai.com/docs/changelog)
- [OpenAI Developer Changelog](https://developers.openai.com/changelog/)
- [NPM: openai package](https://www.npmjs.com/package/openai)

### Anthropic
- [Model Deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)
- [Anthropic Release Notes](https://releasebot.io/updates/anthropic)
- [Claude Developer Platform](https://platform.claude.com/docs/en/release-notes/overview)
- [NPM: @anthropic-ai/sdk](https://www.npmjs.com/package/@anthropic-ai/sdk)
- [Anthropic SDK TypeScript GitHub](https://github.com/anthropics/anthropic-sdk-typescript)

### Google Generative AI
- [Gemini Deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
- [Gemini Models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini Changelog](https://ai.google.dev/gemini-api/docs/changelog)
- [NPM: @google/genai](https://www.npmjs.com/package/@google/genai)
- [GitHub: deprecated-generative-ai-js](https://github.com/google-gemini/deprecated-generative-ai-js)

---

**Last Updated**: 2026-01-18
**Next Review**: 2026-04-18 (Quarterly)
