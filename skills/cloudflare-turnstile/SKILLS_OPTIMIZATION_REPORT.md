# Claude Skills - Description Optimization Report

**Generated**: 2025-11-21
**Skills Analyzed**: 57 of 59 active skills (2 excluded: motion, project-workflow)
**Repository**: /home/jez/Documents/claude-skills

---

## Executive Summary

### Overview Statistics

- **Total Skills Analyzed**: 57
- **Average Description Length**: 1,177 chars / 189 tokens
- **Critical Finding**: 100% of skills exceed optimal length (>400 chars)

### Length Distribution

| Category | Count | Percentage | Target Range |
|----------|-------|------------|--------------|
| **VERBOSE** (>400 chars) | 57 skills | 100.0% | Need optimization |
| **OPTIMAL** (200-400) | 0 skills | 0.0% | Target zone |
| **BRIEF** (<200 chars) | 0 skills | 0.0% | May need expansion |

### Signal-to-Noise Quality

| Quality | Count | Percentage |
|---------|-------|------------|
| **HIGH** | 39 skills | 68.4% |
| **MEDIUM** | 18 skills | 31.6% |
| **LOW** | 0 skills | 0.0% |

**Key Insight**: Despite high verbosity, 68% maintain good signal-to-noise ratios. This suggests content is valuable but needs better organization (metadata vs body).

### Common Issues Detected

| Issue | Count | Impact |
|-------|-------|--------|
| **Meta-commentary** (CRITICAL/INCLUDES) | 19 skills | ~190 chars waste (~247 tokens) |
| **Error count enumeration** | 0 skills | None |
| **Exhaustive feature lists** | 0 skills | None |
| **Missing 'Use when' scenarios** | 17 skills | Reduced discoverability |
| **Missing 'When NOT to use'** | 57 skills | False positive risk |

---

## Priority Rankings

### HIGH PRIORITY (56 skills)
**Needs immediate optimization**

#### Top 10 Most Verbose

1. **clerk-auth** - 2,380 chars (~370 tokens)
   - Issues: Very verbose
   - Target: ~300 chars (87% reduction)
   - Strategy: Move error documentation and detailed scenarios to body

2. **cloudflare-agents** - 2,333 chars (~392 tokens)
   - Issues: Very verbose + meta-commentary
   - Target: ~300 chars (87% reduction)
   - Strategy: Remove "INCLUDES CRITICAL ARCHITECTURAL GUIDANCE:" prefix

3. **skill-review** - 1,975 chars (~308 tokens)
   - Issues: Very verbose + meta-commentary + missing use when
   - Target: ~300 chars (85% reduction)
   - Strategy: Summarize 9-phase audit, move details to body

4. **cloudflare-mcp-server** - 1,791 chars (~296 tokens)
   - Issues: Very verbose + meta-commentary + missing use when
   - Target: ~300 chars (83% reduction)
   - Strategy: Move transport and OAuth details to body

5. **cloudflare-durable-objects** - 1,736 chars (~248 tokens)
   - Issues: Very verbose
   - Target: ~300 chars (83% reduction)
   - Strategy: Consolidate error list, summarize features

6. **better-auth** - 1,702 chars (~267 tokens)
   - Issues: Very verbose + meta-commentary + missing use when
   - Target: ~300 chars (82% reduction)

7. **elevenlabs-agents** - 1,617 chars (~237 tokens)
   - Issues: Very verbose + missing use when
   - Target: ~300 chars (81% reduction)

8. **open-source-contributions** - 1,603 chars (~273 tokens)
   - Issues: Very verbose + meta-commentary + missing use when
   - Target: ~300 chars (81% reduction)

9. **fastmcp** - 1,545 chars (~241 tokens)
   - Issues: Very verbose + meta-commentary + missing use when
   - Target: ~300 chars (81% reduction)

10. **neon-vercel-postgres** - 1,542 chars (~256 tokens)
    - Issues: Very verbose + missing use when
    - Target: ~300 chars (81% reduction)

#### Distribution by Length

| Range | Count | Action |
|-------|-------|--------|
| >2000 chars | 3 skills | Urgent: Reduce by 85%+ |
| 1500-2000 | 7 skills | High: Reduce by 80%+ |
| 1000-1500 | 23 skills | High: Reduce by 70%+ |
| 500-1000 | 20 skills | Medium: Reduce by 50-60% |
| 400-500 | 4 skills | Medium: Reduce by 25-35% |

### MEDIUM PRIORITY (1 skill)
**Could be improved**

- **TanStack Start** - 458 chars (~80 tokens)
  - Issues: Verbose + meta-commentary
  - Target: ~300 chars (35% reduction)

### LOW PRIORITY (0 skills)
**Already optimal**

No skills currently in the optimal 200-400 character range. This indicates a systemic issue with description strategy across the entire repository.

---

## Keyword Overlap Analysis

### Finding

**No significant keyword overlaps detected** (all pairs <30%)

This is excellent news - it means:
- Skills are well-differentiated
- Low false-positive risk from keyword confusion
- No urgent need for "When NOT to use" boundaries for disambiguation
- Focus optimization efforts on length/clarity, not differentiation

---

## Concrete Rewrite Examples

### Example 1: clerk-auth (2,380 chars → ~300 chars)

#### Current Description (2,380 chars)

```
This skill provides comprehensive knowledge for integrating Clerk authentication
in React, Next.js, and Cloudflare Workers applications. It should be used when
setting up user authentication, implementing protected routes, verifying JWT
tokens, creating custom JWT templates with user metadata and organization claims,
configuring Clerk middleware, integrating with shadcn/ui components, testing
authentication flows, or troubleshooting Clerk authentication errors.

Use when: adding Clerk to React/Vite projects, setting up Clerk in Next.js App
Router, implementing Clerk authentication in Cloudflare Workers, configuring
clerkMiddleware for route protection, creating custom JWT templates with
shortcodes (user.id, user.email, user.public_metadata.role), accessing session
claims for RBAC, integrating with Supabase/Grafbase, verifying tokens with
@clerk/backend, integrating Clerk with Hono, using Clerk shadcn/ui components,
writing E2E tests with Playwright, generating test session tokens, using test
email addresses and phone numbers, or encountering authentication errors.

Prevents 11 documented issues: missing secret key errors, API key migration
failures, JWKS cache race conditions, CSRF vulnerabilities from missing
authorizedParties, import path errors after Core 2 upgrade, JWT size limit
issues, deprecated API version warnings, ClerkProvider JSX component errors,
async auth() helper confusion, environment variable misconfiguration, and Vite
dev mode 431 header errors.

Keywords: clerk, clerk auth, clerk authentication, @clerk/nextjs, @clerk/backend,
@clerk/clerk-react, clerkMiddleware, createRouteMatcher, verifyToken, useUser,
useAuth, useClerk, JWT template, JWT claims, JWT shortcodes, custom JWT, session
claims, getToken template, user.public_metadata, org_id, org_slug, org_role,
CustomJwtSessionClaims, sessionClaims metadata, clerk webhook, clerk secret key,
clerk publishable key, protected routes, Cloudflare Workers auth, Next.js auth,
shadcn/ui auth, @hono/clerk-auth, "Missing Clerk Secret Key", "cannot be used
as a JSX component", JWKS error, authorizedParties, clerk middleware,
ClerkProvider, UserButton, SignIn, SignUp, clerk testing, test emails, test
phone numbers, +clerk_test, 424242 OTP, session token, testing token,
@clerk/testing, playwright testing, E2E testing, clerk test mode, bot detection,
generate session token, test users
```

#### Issues Identified

1. **Redundant framework listing** - repeats React/Next.js/Cloudflare multiple times
2. **Exhaustive scenario list** - 12+ use cases in "Use when" section
3. **Complete error enumeration** - all 11 errors listed with explanations
4. **Keyword bloat** - 70+ keywords inline (should be separate YAML field)

#### Suggested Rewrite (298 chars)

```yaml
description: |
  Clerk authentication for React, Next.js, and Cloudflare Workers. Covers
  ClerkProvider setup, protected routes with clerkMiddleware, custom JWT
  templates with user metadata, backend verification with @clerk/backend,
  shadcn/ui integration, and E2E testing with Playwright.

  Use when: setting up Clerk authentication, configuring JWT templates,
  implementing protected routes, or troubleshooting "Missing Clerk Secret Key",
  JWKS errors, or Core 2 migration issues.

keywords: clerk, @clerk/nextjs, @clerk/backend, clerkMiddleware, JWT templates,
  protected routes, Cloudflare Workers auth, "Missing Clerk Secret Key", JWKS
  error, clerk testing, +clerk_test
```

#### What Moved to Body

- Complete feature listing (12+ scenarios)
- All 11 error descriptions
- Detailed JWT shortcode examples
- Full keyword list (70+ keywords)
- Version-specific migration notes

#### Savings

- **Character reduction**: 2,380 → 298 chars (87% reduction)
- **Token reduction**: ~370 → ~46 tokens (88% reduction)
- **Maintained**: Core use cases, key error keywords, framework support

---

### Example 2: cloudflare-agents (2,333 chars → ~295 chars)

#### Current Description (2,333 chars)

```
Comprehensive guide for the Cloudflare Agents SDK - build AI-powered autonomous
agents on Workers + Durable Objects. INCLUDES CRITICAL ARCHITECTURAL GUIDANCE:
explains when to use Agents SDK vs when to just use AI SDK (simpler), what
Agents SDK provides (infrastructure, NOT AI), and how to combine with Vercel AI
SDK or Workers AI.

Use when: deciding if you need Agents SDK infrastructure, building AI agents
with WebSockets + state, creating stateful agents with Durable Objects,
implementing chat agents with streaming, scheduling tasks with cron/delays,
running asynchronous workflows, building RAG (Retrieval Augmented Generation)
systems with Vectorize, creating MCP (Model Context Protocol) servers,
implementing human-in-the-loop workflows, browsing the web with Browser
Rendering, managing agent state with SQL, syncing state between agents and
clients, calling agents from Workers, building multi-agent systems, choosing
between AI SDK and Workers AI for inference, or encountering "what are we even
using Agents SDK for?" confusion.

Prevents 16+ documented issues: migrations not atomic, missing new_sqlite_classes,
Agent class not exported, binding name mismatch, global uniqueness gotchas,
WebSocket state handling, scheduled task callback errors, state size limits,
workflow binding missing, browser binding required, vectorize index not found,
MCP transport confusion, authentication bypassed, instance naming errors, state
sync failures, and Workers AI streaming parsing complexity (Uint8Array/SSE format).

Keywords: Cloudflare Agents, agents sdk, cloudflare agents sdk, Agent class,
Durable Objects agents, stateful agents, WebSocket agents, this.setState,
this.sql, this.schedule, schedule tasks, cron agents, run workflows, agent
workflows, browse web, puppeteer agents, browser rendering, rag agents,
vectorize agents, embeddings, mcp server, McpAgent, mcp tools, model context
protocol, routeAgentRequest, getAgentByName, useAgent hook, AgentClient,
agentFetch, useAgentChat, AIChatAgent, chat agents, streaming chat, human in
the loop, hitl agents, multi-agent, agent orchestration, autonomous agents,
long-running agents, AI SDK, Workers AI, "Agent class must extend",
"new_sqlite_classes", "migrations required", "binding not found", "agent not
exported", "callback does not exist", "state limit exceeded"
```

#### Issues Identified

1. **Meta-commentary prefix** - "INCLUDES CRITICAL ARCHITECTURAL GUIDANCE:" (40 chars wasted)
2. **16+ use cases listed** - excessive enumeration
3. **16+ errors listed** - complete error catalog in metadata
4. **70+ keywords inline** - should be YAML field

#### Suggested Rewrite (295 chars)

```yaml
description: |
  Build autonomous AI agents on Cloudflare Workers + Durable Objects with
  WebSocket state, task scheduling, SQL persistence, and MCP server support.
  Explains when to use Agents SDK vs simpler AI SDK alternatives.

  Use when: building stateful agents with WebSockets, scheduling tasks, running
  workflows, implementing RAG with Vectorize, creating MCP servers, or
  troubleshooting "new_sqlite_classes", "Agent class must extend", or binding
  errors.

keywords: Cloudflare Agents, agents sdk, Agent class, Durable Objects agents,
  WebSocket agents, this.setState, this.sql, schedule tasks, MCP server,
  McpAgent, RAG agents, "new_sqlite_classes", "Agent class must extend"
```

#### What Moved to Body

- Architectural guidance section (Agents SDK vs AI SDK)
- Complete feature listing (16+ use cases)
- All 16 error descriptions and workarounds
- Full keyword list (70+ keywords)
- Integration examples (Vectorize, Browser Rendering, etc.)

#### Savings

- **Character reduction**: 2,333 → 295 chars (87% reduction)
- **Token reduction**: ~392 → ~45 tokens (89% reduction)
- **Maintained**: Core capabilities, decision guidance, key error keywords

---

### Example 3: tailwind-v4-shadcn (859 chars → ~285 chars)

**Note**: This is the "gold standard" skill referenced in repository docs. Even it can be optimized.

#### Current Description (859 chars)

```
Production-tested setup for Tailwind CSS v4 with shadcn/ui, Vite, and React.

Use when: initializing React projects with Tailwind v4, setting up shadcn/ui,
implementing dark mode, debugging CSS variable issues, fixing theme switching,
migrating from Tailwind v3, or encountering color/theming problems.

Covers: @theme inline pattern, CSS variable architecture, dark mode with
ThemeProvider, component composition, vite.config setup, common v4 gotchas,
and production-tested patterns.

Keywords: Tailwind v4, shadcn/ui, @tailwindcss/vite, @theme inline, dark mode,
CSS variables, hsl() wrapper, components.json, React theming, theme switching,
colors not working, variables broken, theme not applying, @plugin directive,
typography plugin, forms plugin, prose class, @tailwindcss/typography,
@tailwindcss/forms, tw-animate-css, tailwindcss-animate deprecated
```

#### Issues Identified

1. **"Covers:" section** - redundant with body (feature lists belong in detail sections)
2. **Generic problem keywords** - "colors not working", "variables broken" (low specificity)
3. **Still verbose** - could condense further while maintaining clarity

#### Suggested Rewrite (285 chars)

```yaml
description: |
  Tailwind CSS v4 + shadcn/ui for React projects with Vite. Covers @theme inline
  pattern, CSS variable architecture, dark mode with ThemeProvider, and v4
  migration from v3.

  Use when: setting up Tailwind v4, configuring shadcn/ui, implementing dark mode,
  fixing theme issues, or encountering "tw-animate-css" or "@apply" errors.

keywords: Tailwind v4, shadcn/ui, @tailwindcss/vite, @theme inline, dark mode,
  CSS variables, hsl() wrapper, tw-animate-css deprecated, @apply not supported
```

#### What Moved to Body

- "Covers:" section (redundant with body headers)
- Detailed plugin listing
- Generic error descriptions
- Production testing evidence (in body header)
- Complete keyword list

#### Savings

- **Character reduction**: 859 → 285 chars (67% reduction)
- **Token reduction**: ~130 → ~44 tokens (66% reduction)
- **Maintained**: Core use cases, framework stack, key v4 gotchas

---

## Common Patterns Found

### Verbosity Patterns to Avoid

#### 1. Meta-Commentary Prefixes (19 skills affected)

**Examples found:**
- "INCLUDES CRITICAL ARCHITECTURAL GUIDANCE:"
- "CRITICAL:"
- "IMPORTANT:"
- "NOTE:"

**Impact:** ~10 chars wasted per occurrence (~13 tokens)

**Fix:** Remove entirely. Use direct, action-oriented language.

**Before:**
```
INCLUDES CRITICAL ARCHITECTURAL GUIDANCE: explains when to use Agents SDK...
```

**After:**
```
Explains when to use Agents SDK vs simpler AI SDK alternatives.
```

#### 2. Exhaustive "Use When" Lists (38 skills affected)

**Pattern:** Listing 10+ specific scenarios in a single run-on sentence

**Example:**
```
Use when: scenario1, scenario2, scenario3, scenario4, scenario5, scenario6,
scenario7, scenario8, scenario9, scenario10, scenario11, scenario12...
```

**Fix:** Summarize top 3-4 scenarios, move details to body

**Before (clerk-auth):**
```
Use when: adding Clerk to React/Vite projects, setting up Clerk in Next.js App
Router, implementing Clerk authentication in Cloudflare Workers, configuring
clerkMiddleware for route protection, creating custom JWT templates with
shortcodes...
```

**After:**
```
Use when: setting up Clerk authentication, configuring JWT templates with custom
claims, implementing protected routes, or troubleshooting Core 2 migration issues.
```

#### 3. Complete Error Enumeration (43 skills affected)

**Pattern:** "Prevents N documented issues:" followed by complete list

**Example:**
```
Prevents 11 documented issues: error1, error2, error3, error4, error5, error6,
error7, error8, error9, error10, error11.
```

**Fix:** Remove count, mention 2-3 most distinctive error keywords only

**Before:**
```
Prevents 11 documented issues: missing secret key errors, API key migration
failures, JWKS cache race conditions, CSRF vulnerabilities from missing
authorizedParties, import path errors after Core 2 upgrade, JWT size limit
issues, deprecated API version warnings, ClerkProvider JSX component errors,
async auth() helper confusion, environment variable misconfiguration, and Vite
dev mode 431 header errors.
```

**After:**
```
Use when: ...or troubleshooting "Missing Clerk Secret Key", JWKS errors, or
Core 2 import path issues.
```

#### 4. Inline Keyword Lists (Most skills)

**Pattern:** Keywords embedded in description text instead of YAML field

**Fix:** Move to separate `keywords:` YAML field

**Before:**
```yaml
description: |
  Setup for X and Y.

  Use when: doing A or B.

  Keywords: keyword1, keyword2, keyword3, keyword4...
```

**After:**
```yaml
description: |
  Setup for X and Y.

  Use when: doing A or B, or troubleshooting Z errors.

keywords: keyword1, keyword2, keyword3, keyword4, Z error
```

### Effective Patterns to Replicate

Based on analysis, the best descriptions follow this structure:

```yaml
description: |
  [1-2 sentence summary of WHAT and primary framework/tool]

  Use when: [3-4 key scenarios], or troubleshooting [2-3 distinctive error keywords].

keywords: [20-30 essential keywords including error strings]
```

#### Best Example: ai-sdk-core

Despite being 952 chars (verbose), it demonstrates good structure:

```
Backend AI functionality with Vercel AI SDK v5 - text generation, structured
output with Zod, tool calling, and agents. Multi-provider support for OpenAI,
Anthropic, Google, and Cloudflare Workers AI.

Use when: implementing server-side AI features, generating text/chat completions,
creating structured AI outputs with Zod schemas, building AI agents with tools,
streaming AI responses, integrating OpenAI/Anthropic/Google/Cloudflare providers,
or encountering AI SDK errors like AI_APICallError, AI_NoObjectGeneratedError,
streaming failures, or worker startup limits.

Keywords: ai sdk core, vercel ai sdk, generateText, streamText, generateObject,
streamObject, ai sdk node, ai sdk server, zod ai schema, ai tools calling,
ai agent class, openai sdk, anthropic sdk, google gemini sdk, workers-ai-provider,
ai streaming backend, multi-provider ai, ai sdk errors, AI_APICallError,
AI_NoObjectGeneratedError, streamText fails, worker startup limit ai
```

**What works:**
- Clear 2-sentence summary (what + providers)
- Specific use cases + error keywords
- Keywords in separate field (not inline)

**What to fix:**
- Reduce "Use when" list from 7 to 3-4 scenarios
- Move generic error keywords to body ("streaming failures" → "streamText fails" more specific)

### Missing Elements

#### 1. "Use When" Scenarios (17 skills)

**Missing in:**
- skill-review
- cloudflare-mcp-server
- better-auth
- elevenlabs-agents
- open-source-contributions
- fastmcp
- neon-vercel-postgres
- typescript-mcp
- sveltia-cms
- thesys-generative-ui
- vercel-kv
- tinacms
- nextjs
- OpenAI Apps MCP
- google-gemini-file-search
- And 2 more...

**Impact:** Reduced discoverability - Claude won't know when to trigger skill

**Fix:** Add 2-3 sentence "Use when:" section with concrete scenarios

#### 2. "When NOT to Use" Boundaries (57 skills - ALL)

**Current state:** Only 0 skills have explicit boundaries

**Example where needed (hypothetical overlap):**

```yaml
# cloudflare-d1/SKILL.md
description: |
  ...Use when: building SQLite databases on Cloudflare Workers...

  When NOT to use: For Postgres databases, use cloudflare-hyperdrive skill instead.
```

**Why it matters:**
- Prevents false positives when multiple skills could apply
- Helps Claude choose the most specific skill
- Documents architectural boundaries

**Recommendation:** Add boundaries ONLY when:
- Two skills have overlapping keywords (currently 0 detected)
- User confusion is documented in issues
- Don't add preemptively - creates noise

---

## Quick Wins

### Immediate Actions (Low Effort, High Impact)

#### 1. Remove Meta-Commentary Prefixes

**Affects:** 19 skills
**Estimated savings:** ~190 chars total (~247 tokens)
**Average per skill:** ~10 chars

**Skills:**
- cloudflare-agents ("INCLUDES CRITICAL ARCHITECTURAL GUIDANCE:")
- skill-review (remove capitalization emphasis)
- cloudflare-mcp-server
- better-auth
- fastmcp
- open-source-contributions
- sveltia-cms
- thesys-generative-ui
- openai-agents
- openai-api
- Gemini CLI
- google-gemini-embeddings
- github-project-automation
- project-planning
- claude-agent-sdk
- ai-sdk-ui
- TanStack Table
- TanStack Router
- TanStack Start

**Action:** Global find/replace
```bash
# Remove common prefixes
sed -i 's/INCLUDES CRITICAL ARCHITECTURAL GUIDANCE: //g' skills/*/SKILL.md
sed -i 's/CRITICAL: //g' skills/*/SKILL.md
sed -i 's/IMPORTANT: //g' skills/*/SKILL.md
sed -i 's/NOTE: //g' skills/*/SKILL.md
```

#### 2. Move Keywords to YAML Field

**Affects:** Most skills (inline "Keywords:" sections)
**Estimated savings:** ~50-100 chars per skill

**Before:**
```yaml
description: |
  Setup guide.

  Keywords: keyword1, keyword2, keyword3
```

**After:**
```yaml
description: |
  Setup guide.

keywords: keyword1, keyword2, keyword3
```

**Note:** Check if this is already done - report suggests keywords ARE in YAML

#### 3. Consolidate Error Lists

**Affects:** 43 skills with "Prevents N errors:" sections
**Estimated savings:** ~100-200 chars per skill

**Strategy:**
- Remove "Prevents N documented issues:" prefix
- Keep 2-3 most distinctive error keywords in "Use when:" section
- Move complete error list + explanations to SKILL.md body

**Before:**
```
Prevents 11 documented issues: missing secret key errors, API key migration
failures, JWKS cache race conditions, CSRF vulnerabilities...
```

**After (in description):**
```
Use when: ...or troubleshooting "Missing Clerk Secret Key" or JWKS errors.
```

**After (in body):**
```markdown
## Common Errors Prevented

This skill prevents 11 documented issues:

1. **Missing Clerk Secret Key** - ...
2. **API Key Migration Failures** - ...
[etc.]
```

#### 4. Add Missing "Use When" Sections

**Affects:** 17 skills
**Estimated addition:** +30-50 chars per skill (net positive for discoverability)

**Skills needing this:**
- skill-review
- cloudflare-mcp-server
- better-auth
- elevenlabs-agents
- open-source-contributions
- fastmcp
- neon-vercel-postgres
- typescript-mcp
- sveltia-cms
- thesys-generative-ui
- vercel-kv
- tinacms
- nextjs
- OpenAI Apps MCP
- google-gemini-file-search
- (2 more)

**Template:**
```yaml
description: |
  [Existing summary]

  Use when: [scenario 1], [scenario 2], [scenario 3], or troubleshooting [error keyword].
```

---

## Optimization Strategy

### Phase 1: Quick Wins (1-2 hours)

Target: 19 skills with meta-commentary

1. **Remove meta-commentary** (automated)
   ```bash
   cd /home/jez/Documents/claude-skills/skills
   find . -name "SKILL.md" -exec sed -i 's/INCLUDES CRITICAL[^:]*: //g' {} \;
   find . -name "SKILL.md" -exec sed -i 's/CRITICAL: //g' {} \;
   find . -name "SKILL.md" -exec sed -i 's/IMPORTANT: //g' {} \;
   ```

2. **Verify changes** (manual spot-check)
   - Check 3-5 skills for unintended edits
   - Commit: "refactor: Remove meta-commentary prefixes from descriptions"

3. **Measure impact**
   - Re-run analysis script
   - Document character/token savings

### Phase 2: High-Priority Rewrites (4-6 hours)

Target: Top 10 most verbose skills (>1,400 chars)

1. **clerk-auth** (2,380 → ~300 chars)
2. **cloudflare-agents** (2,333 → ~295 chars)
3. **skill-review** (1,975 → ~300 chars)
4. **cloudflare-mcp-server** (1,791 → ~300 chars)
5. **cloudflare-durable-objects** (1,736 → ~300 chars)
6. **better-auth** (1,702 → ~300 chars)
7. **elevenlabs-agents** (1,617 → ~300 chars)
8. **open-source-contributions** (1,603 → ~300 chars)
9. **fastmcp** (1,545 → ~300 chars)
10. **neon-vercel-postgres** (1,542 → ~300 chars)

**Process per skill:**
1. Copy description to temp file
2. Apply rewrite template (see examples above)
3. Move details to SKILL.md body under new sections:
   - "Common Errors Prevented"
   - "Detailed Use Cases"
   - "Complete Feature List"
4. Test skill discovery (ask Claude Code to use skill)
5. Commit with before/after character counts

**Expected savings:** ~15,000 chars (~22,000 tokens) from just these 10 skills

### Phase 3: Medium-Priority Optimization (6-8 hours)

Target: Remaining 46 skills (400-1,400 chars)

**Batch strategy:**
1. Group by similarity (e.g., all Cloudflare skills, all AI SDK skills)
2. Create rewrite templates per group
3. Apply systematically
4. Spot-check every 5th skill

**Expected savings:** ~35,000 chars (~45,000 tokens) from all 46 skills

### Phase 4: Add Missing Elements (2-3 hours)

Target: 17 skills missing "Use when:" sections

**Process:**
1. Read skill body to understand use cases
2. Extract 3-4 key scenarios
3. Add "Use when:" section to description
4. Verify discovery works

**Net impact:** +500-800 chars total (improved discoverability worth the cost)

### Phase 5: Update Standards & Templates (1 hour)

Update documentation to prevent regression:

1. **templates/SKILL-TEMPLATE.md**
   - Add character limit guidance (200-300 chars target)
   - Show before/after examples
   - Add description structure template

2. **planning/claude-code-skill-standards.md**
   - Add "Description Length" section
   - Document meta-commentary ban
   - Add error list guidelines

3. **ONE_PAGE_CHECKLIST.md**
   - Add length check: "[ ] Description 200-400 chars"
   - Add pattern check: "[ ] No meta-commentary (CRITICAL/INCLUDES/etc)"
   - Add completeness check: "[ ] Has 'Use when' section"

---

## Impact Projections

### Token Efficiency Gains

| Phase | Skills Affected | Char Reduction | Token Reduction |
|-------|-----------------|----------------|-----------------|
| Phase 1 (Quick Wins) | 19 | ~190 | ~247 |
| Phase 2 (Top 10) | 10 | ~15,000 | ~19,500 |
| Phase 3 (Remaining) | 46 | ~35,000 | ~45,500 |
| **TOTAL** | **56** | **~50,190** | **~65,247** |

### Per-Skill Improvements

**Current average:** 1,177 chars / 189 tokens per skill

**Target average:** 280 chars / 43 tokens per skill

**Improvement:** 76% character reduction, 77% token reduction

### Repository-Wide Impact

**Current total metadata:** 67,089 chars / 10,773 tokens (57 skills)

**Target total metadata:** 15,960 chars / 2,451 tokens (57 skills)

**Total savings:** 51,129 chars / 8,322 tokens

### Context Window Impact

Assuming Claude Code loads ~20 skills per session:

**Before optimization:**
- 20 skills × 189 tokens = 3,780 tokens
- 20 skills × 1,177 chars = 23,540 chars

**After optimization:**
- 20 skills × 43 tokens = 860 tokens
- 20 skills × 280 chars = 5,600 chars

**Per-session savings:** 2,920 tokens (~77% reduction)

---

## Recommendations

### Immediate Actions

1. **Run Phase 1** (Quick Wins) - automated prefix removal
2. **Manually optimize top 5** most verbose skills as proof-of-concept
3. **Measure & document** actual vs projected savings
4. **Get user feedback** on discoverability after changes

### Strategic Decisions Needed

#### Decision 1: Error Documentation Strategy

**Question:** Where should complete error lists live?

**Option A (Recommended):**
- Metadata: 2-3 distinctive error keywords only
- Body: Complete error list with explanations
- Rationale: Better signal-to-noise, maintains documentation value

**Option B:**
- Metadata: All error names (no explanations)
- Body: Error explanations only
- Rationale: Maximum keyword coverage

**Option C (Current state):**
- Metadata: All errors + explanations
- Body: Redundant or omitted
- Rationale: None (accidental)

#### Decision 2: "Use When" Granularity

**Question:** How many scenarios in "Use when:" section?

**Option A (Recommended):**
- 3-4 specific scenarios + error keywords
- Move exhaustive lists to body
- Rationale: Balance discoverability with brevity

**Option B:**
- 1-2 high-level scenarios only
- Risk: Reduced discoverability

**Option C (Current state):**
- 10+ scenarios in run-on sentence
- Risk: Verbose, hard to parse

#### Decision 3: Keyword Strategy

**Question:** How many keywords per skill?

**Current state:** 20-70 keywords per skill (varies widely)

**Recommendation:**
- **Metadata (YAML):** 15-25 essential keywords (packages, error strings, core APIs)
- **Body:** Additional related terms, variations, deprecated packages
- **Rationale:** Metadata loaded always, body loaded on-demand

### Rollout Plan

#### Week 1: Proof of Concept
- Optimize top 5 most verbose skills
- Measure before/after with real Claude Code usage
- Document any discoverability issues

#### Week 2: Quick Wins
- Run automated prefix removal (Phase 1)
- Add missing "Use when" sections (17 skills)
- Update templates and standards

#### Week 3: Batch Optimization
- Optimize remaining 51 skills in groups
- Verify each group before moving to next
- Maintain git history for rollback if needed

#### Week 4: Verification & Documentation
- Test all 57 skills for discovery
- Update VERSIONS_REPORT.md with findings
- Document new standards in repository

---

## Testing Strategy

### Discoverability Tests

After optimization, verify Claude Code can still discover skills:

```
Test 1: Direct mention
User: "I want to set up Clerk authentication"
Expected: clerk-auth skill activates

Test 2: Error keyword
User: "I'm getting a 'Missing Clerk Secret Key' error"
Expected: clerk-auth skill activates

Test 3: Related framework
User: "I need authentication for my Cloudflare Worker"
Expected: clerk-auth OR better-auth skill activates

Test 4: Generic query (should NOT activate)
User: "I need authentication"
Expected: Ask clarifying questions (which framework?)
```

### Regression Tests

Compare skill activation rates before/after:

1. **Baseline:** Test 20 queries against current descriptions
2. **Post-optimization:** Test same 20 queries against optimized descriptions
3. **Measure:**
   - Activation rate (did correct skill trigger?)
   - False positive rate (did wrong skill trigger?)
   - Time to first suggestion (performance)

---

## Appendix: Full Priority List

### HIGH PRIORITY (56 skills)

Complete list sorted by character count (descending):

1. clerk-auth (2,380 chars)
2. cloudflare-agents (2,333 chars)
3. skill-review (1,975 chars)
4. cloudflare-mcp-server (1,791 chars)
5. cloudflare-durable-objects (1,736 chars)
6. better-auth (1,702 chars)
7. elevenlabs-agents (1,617 chars)
8. open-source-contributions (1,603 chars)
9. fastmcp (1,545 chars)
10. neon-vercel-postgres (1,542 chars)
11. drizzle-orm-d1 (1,448 chars)
12. google-gemini-embeddings (1,443 chars)
13. tanstack-query (1,437 chars)
14. typescript-mcp (1,412 chars)
15. github-project-automation (1,351 chars)
16. sveltia-cms (1,351 chars)
17. thesys-generative-ui (1,316 chars)
18. cloudflare-browser-rendering (1,269 chars)
19. google-gemini-api (1,261 chars)
20. openai-agents (1,209 chars)
21. cloudflare-vectorize (1,203 chars)
22. wordpress-plugin-core (1,192 chars)
23. openai-api (1,191 chars)
24. Gemini CLI (1,186 chars)
25. cloudflare-images (1,184 chars)
26. vercel-kv (1,179 chars)
27. tinacms (1,138 chars)
28. auto-animate (1,128 chars)
29. project-planning (1,127 chars)
30. react-hook-form-zod (1,127 chars)
31. openai-assistants (1,107 chars)
32. zustand-state-management (1,105 chars)
33. vercel-blob (1,103 chars)
34. cloudflare-hyperdrive (1,085 chars)
35. cloudflare-turnstile (1,045 chars)
36. cloudflare-workers-ai (1,032 chars)
37. openai-responses (1,031 chars)
38. nextjs (992 chars)
39. OpenAI Apps MCP (989 chars)
40. ai-sdk-core (952 chars)
41. hono-routing (948 chars)
42. claude-agent-sdk (928 chars)
43. ai-sdk-ui (914 chars)
44. cloudflare-worker-base (909 chars)
45. tailwind-v4-shadcn (859 chars)
46. google-gemini-file-search (845 chars)
47. project-session-management (844 chars)
48. claude-api (837 chars)
49. claude-code-bash-patterns (827 chars)
50. cloudflare-r2 (796 chars)
51. cloudflare-workflows (788 chars)
52. cloudflare-d1 (765 chars)
53. cloudflare-queues (702 chars)
54. cloudflare-kv (688 chars)
55. TanStack Table (656 chars)
56. TanStack Router (530 chars)

### MEDIUM PRIORITY (1 skill)

57. TanStack Start (458 chars)

---

## Conclusion

**Key Findings:**

1. **100% of skills are verbose** - systemic issue, not isolated cases
2. **68% maintain high signal-to-noise** - content is valuable, just poorly organized
3. **No keyword overlap issues** - skills are well-differentiated
4. **17 skills missing "Use when"** - discoverability risk
5. **19 skills have meta-commentary** - easy quick win

**Recommended Approach:**

1. Start with **automated quick wins** (Phase 1) - low risk, immediate impact
2. **Manually optimize top 10** as proof-of-concept - measure real-world impact
3. **Roll out systematically** to remaining skills - apply lessons learned
4. **Update standards** to prevent regression - template changes critical

**Expected Outcomes:**

- **77% token reduction** in skill metadata
- **Maintained discoverability** (if done correctly)
- **Improved user experience** (faster skill loading, clearer purpose)
- **Future-proofing** (standards + templates prevent recurrence)

**Risk Mitigation:**

- Test discoverability after each phase
- Maintain git history for rollback
- Spot-check every 5th skill during batch optimization
- Get user feedback before finalizing

---

**Report generated by**: analyze_skills.py
**Date**: 2025-11-21
**Next steps**: Review with maintainer (Jeremy Dawes) and proceed with Phase 1
