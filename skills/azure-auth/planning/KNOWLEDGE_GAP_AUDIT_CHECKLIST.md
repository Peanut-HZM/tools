# Knowledge-Gap Audit Checklist for Skills

**Purpose**: Systematically audit existing skills to remove "obvious knowledge" (pre-Jan 2025) and keep only knowledge gaps and error prevention.

**Last Updated**: 2025-11-22

---

## Background: Why This Matters

**LLM Knowledge Cutoff**: January 2025

Skills should only contain:
1. **Knowledge Gaps** - Information from December 2024 onward (not in LLM training data)
2. **Error Prevention** - Exact error messages with solutions (prevents trial-and-error)

Everything else is "obvious knowledge" that wastes tokens.

**Example**: The nextjs skill went from 2,414 lines → 1,383 lines (43% reduction) by removing Server Components basics, Server Actions basics, etc. (all pre-2023 content).

---

## Step 1: Pre-Audit Assessment

**Before starting, gather baseline metrics:**

```bash
# Count current lines
wc -l skills/SKILL_NAME/SKILL.md

# Estimate tokens (rough: lines ÷ 0.3 = tokens)
# Example: 2,414 lines ≈ 8,000 tokens
```

**Record**:
- Current line count: _______
- Estimated tokens: _______
- Last verified date: _______
- Skill focus: _______

**⚠️ IMPORTANT**: Even "recently updated" skills may be missing recent knowledge gaps!
- Example: cloudflare-vectorize (updated Oct 2025) was missing Vectorize V2 GA (Sept 2024)
- **Always research** regardless of last update date

---

## Step 2: Research Phase (CRITICAL!)

**Default Knowledge Boundary**: January 2025

**Why Research First**:
- Find knowledge gaps you might have missed
- Discover breaking changes not in skill
- Check for deprecations/removals
- Verify current versions

### Research Sources (Use These Tools)

**1. Web Search** (WebSearch tool):
```
Query patterns:
- "[technology] updates 2024 2025"
- "[technology] breaking changes 2024"
- "[technology] changelog December 2024"
- "[technology] deprecated 2024"
- "[technology] migration guide 2024"
```

**2. MCP Documentation Tools** (if available):
```
- Cloudflare: mcp__cloudflare-docs__search_cloudflare_documentation
- Query: "[technology] latest features updates 2024 2025"
```

**3. Official Sources** (WebFetch):
```
- Official blog: "[technology] blog"
- Changelog page: "[technology] changelog"
- Migration guides: "[technology] migration"
- GitHub releases: "github.com/[org]/[repo]/releases"
```

**4. Package Versions** (if npm package):
```bash
npm view [package-name] version
npm view [package-name] time
npm view [package-name] versions --json | tail -20
```

**5. Context7 MCP** (if available):
```
Query library documentation for latest API references
```

### Questions to Answer

1. **What major release happened Dec 2024+?**
2. **What breaking changes occurred?**
3. **What new APIs/features were added?**
4. **What deprecated/removed features?**
5. **What's the current version?**
6. **Are there migration guides?**

### Document Findings

**Technology**: _______
**Current Version**: _______
**Latest Release Date**: _______
**Breaking Changes Found**: _______
**New Features Found**: _______
**Deprecations Found**: _______
**Migration Guides**: _______

**Example (Cloudflare Vectorize)**:
- Technology: Cloudflare Vectorize
- Current Version: V2 (GA September 2024)
- Breaking Changes: Async mutations, returnMetadata enum, V1 deprecation Dec 2024
- New Features: 5M vectors/index, 31ms latency, topK 100, range queries
- Sources: WebSearch + Cloudflare MCP + Official changelog

---

## Step 3: Content Categorization

**Read through SKILL.md and categorize each section:**

### ✅ KEEP: Knowledge Gaps (Dec 2024+)

**Criteria**:
- Released/announced December 2024 or later
- Breaking changes from recent versions
- New APIs, features, directives
- Changed defaults or behaviors

**Examples**:
- Next.js 16 breaking changes (async params, proxy.ts)
- Cache Components with `"use cache"` directive
- React 19.2 features (View Transitions, useEffectEvent)
- Turbopack stable (Next.js 16)
- Updated caching APIs (revalidateTag with cacheLife)

**Document**:
```
Section: [name]
Lines: [start-end]
Reason: [why it's a knowledge gap]
Keep: YES
```

---

### ✅ KEEP: Error Prevention

**Criteria**:
- Exact error messages with solutions
- Common mistakes with root causes
- Breaking change errors
- Migration errors

**Examples**:
- "Error: params is a Promise" (Next.js 16)
- "Error: Parallel route @modal/login was matched but no default.js was found"
- "Error: revalidateTag() requires 2 arguments"

**Document**:
```
Section: [name]
Lines: [start-end]
Errors: [count]
Keep: YES
```

---

### ❌ REMOVE: Obvious Pre-2025 Content

**Criteria**:
- Well-established patterns (pre-2023)
- Basic concepts (framework fundamentals)
- No breaking changes in recent versions
- Widely documented in official docs

**Examples**:
- Server Components basics (React 18, 2022)
- Server Actions basics (Next.js 13.4, 2023)
- Metadata API (Next.js 13, 2023 - no changes in 16)
- TypeScript configuration (no Next.js 16 changes)
- Image & Font optimization basics (no breaking changes)

**Document**:
```
Section: [name]
Lines: [start-end]
Reason: [why it's obvious]
Remove: YES
Estimated savings: [lines]
```

---

## Step 4: Calculate Token Impact

**For each section to remove**:

```
Lines to remove: _______
Estimated tokens (lines ÷ 0.3): _______
```

**Total Impact**:
```
Total lines to remove: _______
Total tokens saved: _______
Percentage reduction: _______
```

**Target**: 40-50% reduction minimum

---

## Step 5: Create Audit Report

**Document in SESSION.md** (or create `SKILL_NAME_AUDIT.md`):

```markdown
## [SKILL_NAME] Audit - [DATE]

### Current State
- Lines: [current]
- Estimated tokens: [current]

### Content Analysis

#### ✅ Keep (Knowledge Gaps - Dec 2024+)
1. **[Section Name]** ([lines] lines)
   - Reason: [knowledge gap description]
   - Content: [brief summary]

2. **[Section Name]** ([lines] lines)
   - Reason: [knowledge gap description]
   - Content: [brief summary]

#### ✅ Keep (Error Prevention)
**[Section Name]** ([lines] lines, [X] errors documented)
- Error 1: [exact message]
- Error 2: [exact message]
- ...

#### ❌ Remove (Obvious Pre-2025 Content)
1. **[Section Name]** ([lines] lines)
   - Reason: [why obvious]
   - Release date: [when established]
   - Alternative: [where to find this info]

2. **[Section Name]** ([lines] lines)
   - Reason: [why obvious]
   - Release date: [when established]
   - Alternative: [where to find this info]

### Projected Impact
- Lines after trim: ~[projected]
- Tokens after trim: ~[projected]
- Savings: ~[X]% ([tokens] tokens)

### Next Actions
1. Trim content
2. Verify completeness
3. Update Table of Contents
4. Update "When to Use This Skill" section
5. Test skill discovery
```

---

## Step 6: Trim Content

**Execute the trim** (use Edit tool):

**Process**:
1. Start with largest sections first
2. Remove one section at a time
3. Verify file structure after each removal
4. Keep all Next.js 16+ content intact

**Removal Order** (largest first):
```
1. [Section name] - [lines] lines
2. [Section name] - [lines] lines
3. [Section name] - [lines] lines
...
```

**After each removal**:
```bash
# Verify file is valid
cat skills/SKILL_NAME/SKILL.md | head -20

# Check line count
wc -l skills/SKILL_NAME/SKILL.md
```

---

## Step 7: Verify Completeness

**Checklist** (after trimming):

```bash
# Count major sections
grep -n "^## " skills/SKILL_NAME/SKILL.md

# Count breaking changes subsections
sed -n '/^## [Technology] [Version] Breaking Changes/,/^## /p' skills/SKILL_NAME/SKILL.md | grep -c "^### "

# Count errors in Common Errors section
sed -n '/^## Common Errors & Solutions/,/^## /p' skills/SKILL_NAME/SKILL.md | grep -c "^### "

# Verify all knowledge gaps present
grep -i "new in" skills/SKILL_NAME/SKILL.md
grep -i "breaking" skills/SKILL_NAME/SKILL.md
grep -i "deprecated" skills/SKILL_NAME/SKILL.md
```

**Manual Verification**:
- [ ] All breaking changes documented
- [ ] All new APIs/features documented
- [ ] All error messages intact
- [ ] All knowledge gaps (Dec 2024+) present
- [ ] No obvious pre-2025 content remains
- [ ] Table of Contents updated
- [ ] "When to Use This Skill" updated

---

## Step 8: Update Table of Contents

**Pattern**: Remove sections that were trimmed, keep only knowledge-gap sections.

**Before** (example):
```markdown
1. [When to Use This Skill](#when-to-use-this-skill)
2. [Breaking Changes](#breaking-changes)
3. [Server Components](#server-components)  ← REMOVE
4. [Server Actions](#server-actions)        ← REMOVE
5. [Common Errors](#common-errors)
```

**After**:
```markdown
1. [When to Use This Skill](#when-to-use-this-skill)
2. [Breaking Changes](#breaking-changes)
3. [Common Errors](#common-errors)
```

---

## Step 9: Update "When to Use This Skill" Section

**Add knowledge-gap focus statement**:

```markdown
## When to Use This Skill

**Focus**: [Technology] [Version] breaking changes and knowledge gaps (December 2024+).

Use this skill when you need:

- **[Technology] [Version] breaking changes** (specific changes listed)
- **New APIs/features** (NEW in [Version])
- **Updated APIs** (Updated in [Version])
- **Migration from [Old Version] to [New Version]**
- **Error prevention** ([X]+ documented errors with solutions)
```

**Remove**:
- Generic patterns (e.g., "best practices", "data fetching patterns")
- Pre-2025 features (e.g., "Server Components basics")
- Basics that haven't changed (e.g., "TypeScript configuration")

---

## Step 10: Final Metrics

**Record final metrics**:

```bash
# Final line count
wc -l skills/SKILL_NAME/SKILL.md

# Calculate reduction
# Before: [lines]
# After: [lines]
# Removed: [lines]
# Savings: [X]%
```

**Document in SESSION.md**:
```markdown
### [SKILL_NAME] Audit Results

**Date**: [DATE]

**Before**:
- Lines: [count]
- Estimated tokens: [count]

**After**:
- Lines: [count]
- Estimated tokens: [count]

**Removed**:
- Lines: [count]
- Estimated tokens: [count]
- Savings: [X]%

**Content Removed**:
- [Section 1]: [lines] lines
- [Section 2]: [lines] lines
- ...

**Content Retained**:
- [X] breaking changes
- [X] new APIs/features
- [X] error solutions
- All Dec 2024+ knowledge gaps ✅
```

---

## Step 11: Test Skill Discovery

**Verify skill still works**:

```bash
# Install skill
./scripts/install-skill.sh SKILL_NAME

# Verify symlink
ls -la ~/.claude/skills/SKILL_NAME

# Test discovery (ask Claude Code to use the skill)
# Example prompt:
"I need help with [Technology] [Version]. Can you help me set up [feature]?"
```

**Expected**: Claude should discover and propose using the skill automatically.

---

## Step 12: Commit Changes

**Commit message template**:

```
refactor(SKILL_NAME): Remove obvious pre-2025 content, focus on knowledge gaps

Before: [X] lines (~[X] tokens)
After: [X] lines (~[X] tokens)
Savings: ~[X]% (~[X] tokens)

Removed (Obvious Pre-2025 Content):
- [Section 1] ([lines] lines) - [reason]
- [Section 2] ([lines] lines) - [reason]
- ...

Retained (Knowledge Gaps + Error Prevention):
- [X] breaking changes (Dec 2024+)
- [X] new APIs/features
- [X] error solutions
- All [Technology] [Version] knowledge gaps ✅

Part of Phase 2: Knowledge-Gap-Focused Skills & Content Audit
```

---

## Common Patterns by Skill Type

### Framework Skills (Next.js, React, etc.)

**KEEP**:
- Breaking changes from latest version
- New directives/APIs
- Changed defaults
- Migration guides
- Version-specific errors

**REMOVE**:
- Basic component patterns (pre-2023)
- Established routing patterns
- General TypeScript config (no changes)
- Standard optimization patterns (no changes)

---

### Platform Skills (Cloudflare Workers, Vercel, etc.)

**KEEP**:
- New platform features (Dec 2024+)
- API changes/updates
- Deployment breaking changes
- New bindings/integrations
- Platform-specific errors

**REMOVE**:
- Basic request/response patterns
- Standard environment variable usage
- Generic deployment steps (no changes)

---

### Database Skills (D1, Postgres, etc.)

**KEEP**:
- New query syntax
- Schema migration changes
- Breaking changes in ORM versions
- New database features
- Connection errors specific to new versions

**REMOVE**:
- Basic SQL patterns
- Standard CRUD operations
- Generic connection setup (no changes)

---

### UI Library Skills (shadcn, Tailwind, etc.)

**KEEP**:
- New component patterns (Dec 2024+)
- Breaking changes in latest versions
- New styling features
- Migration guides for major versions

**REMOVE**:
- Basic component usage (established)
- Standard styling patterns
- Generic theming setup (no changes)

---

## Red Flags (Don't Remove These!)

**Even if content seems obvious, KEEP if it includes**:

- ⚠️ **Exact error messages** - Always valuable for error prevention
- ⚠️ **Breaking changes** - Even if documented elsewhere, keep in skill
- ⚠️ **Changed defaults** - Users won't expect these
- ⚠️ **Deprecated features** - Critical for migrations
- ⚠️ **Version-specific quirks** - Not always in official docs
- ⚠️ **Known issues** - GitHub issue links with workarounds

---

## Success Criteria

**A successful audit achieves**:

- ✅ **40-50% token reduction minimum**
- ✅ **All knowledge gaps (Dec 2024+) retained**
- ✅ **All error prevention content retained**
- ✅ **No breaking changes documentation lost**
- ✅ **Skill discovery still works**
- ✅ **Table of Contents updated**
- ✅ **"When to Use This Skill" reflects knowledge-gap focus**

---

## Audit Priority List

**Prioritize skills by**:

1. **Size** (largest first - most savings potential)
2. **Age** (oldest first - likely has most obvious content)
3. **Recent version changes** (likely has knowledge gaps + obvious content)

**Check skill size**:
```bash
for skill in skills/*/SKILL.md; do
  lines=$(wc -l < "$skill")
  echo "$lines lines - $(basename $(dirname "$skill"))"
done | sort -rn | head -20
```

**Check skill age** (last verified):
```bash
for skill in skills/*/SKILL.md; do
  date=$(grep "last_verified:" "$skill" | head -1 | awk '{print $2}')
  echo "$date - $(basename $(dirname "$skill"))"
done | sort
```

---

## Examples

### Example 1: Next.js Skill Audit (2025-11-22)

**Before**: 2,414 lines (~8,000 tokens)
**After**: 1,383 lines (~4,600 tokens)
**Savings**: 43% (~3,400 tokens)

**Removed**:
- Server Components basics (200 lines) - React 18 feature (2022)
- Server Actions basics (235 lines) - Next.js 13.4 (2023)
- Route Handlers basics (80 lines) - Next.js 13 (2023)
- Metadata API (100 lines) - Next.js 13 (2023), no changes in 16
- Image & Font Optimization (95 lines) - No breaking changes
- Performance Patterns basics (76 lines) - Kept only Turbopack
- TypeScript Configuration (65 lines) - No Next.js 16 changes
- Parallel Routes/Route Groups basics (70 lines) - Kept only default.js breaking change
- Templates/Resources verbose listings (83 lines) - Condensed to Next.js 16-specific

**Retained**:
- 6 breaking changes subsections (Next.js 16)
- 6 Cache Components & Caching APIs subsections (NEW in 16)
- 18 error solutions
- React 19.2 features
- Turbopack (stable in 16)

---

## Troubleshooting

### "I'm not sure if this is obvious knowledge or a knowledge gap"

**Ask**:
1. When was this feature released? (before Dec 2024 = likely obvious)
2. Did it change in Dec 2024+? (yes = knowledge gap)
3. Is there an exact error message? (yes = keep for error prevention)
4. Is this in every tutorial/doc? (yes = likely obvious)

**When in doubt, keep it** - better to have slightly more content than miss a knowledge gap.

---

### "The skill seems too short after trimming"

**Check**:
1. Did you keep all breaking changes? ✅
2. Did you keep all error solutions? ✅
3. Did you keep all new APIs/features? ✅

**If yes to all**: The skill is focused correctly. Short skills are efficient skills.

**Example**: A 1,000-line skill with 100% knowledge gaps is better than a 3,000-line skill with 30% knowledge gaps.

---

### "I removed too much - how do I know?"

**Verify**:
```bash
# Check for breaking changes
grep -i "breaking" skills/SKILL_NAME/SKILL.md

# Check for new features
grep -i "new in" skills/SKILL_NAME/SKILL.md

# Check for errors
sed -n '/^## Common Errors/,/^## /p' skills/SKILL_NAME/SKILL.md | grep "^### "
```

**If any of these are missing**: You removed too much. Restore from git.

---

## Maintenance

**Quarterly Review** (every 3 months):

1. Check for new releases (Dec 2024+)
2. Add new knowledge gaps
3. Re-audit for obvious content that aged out
4. Update knowledge cutoff boundary if needed

**Example**: In April 2025, anything from Jan 2025 is now "obvious knowledge" (3 months old, in new LLM training data).

---

## Lessons Learned from Audits

### Cloudflare Vectorize Proof-of-Concept (2025-11-22)

**Skill**: cloudflare-vectorize (613 → 387 lines, 37% reduction)

**Key Insight**: **Even "recently updated" skills can be missing major knowledge gaps!**

**What We Found**:
- Skill last updated: October 2025
- Missing: Vectorize V2 GA (September 2024) - ENTIRE major version!
- Research discovered: 100+ lines of critical V2 knowledge gaps
- Still achieved 37% reduction after ADDING V2 content

**Critical Learnings**:

1. **Research Phase is NON-NEGOTIABLE**:
   - Don't assume skill is current just because it was recently updated
   - Check official changelogs, not just main docs
   - Use MCP tools (Cloudflare docs search found V2 details)
   - WebSearch for "[tech] updates 2024 2025" is invaluable

2. **Adding Content Can Still Yield Savings**:
   - Added ~100 lines of V2 knowledge gaps
   - Removed ~388 lines of obvious content
   - Net result: 37% reduction
   - Proof: Knowledge-gap focus works even when adding new content

3. **Small Skills Can Have Big Gaps**:
   - 613-line skill seemed "complete"
   - Was missing entire V2 GA announcement (Sept 2024)
   - Smaller skills aren't necessarily more current

4. **Research Sources That Worked**:
   - WebSearch: "Cloudflare Vectorize updates 2024 2025"
   - Cloudflare MCP: `search_cloudflare_documentation("Vectorize latest features")`
   - Found: Official changelog, migration guide, V2 breaking changes
   - Time spent: ~5 minutes research, saved hours of missing knowledge

5. **What to Look For**:
   - "GA" announcements (General Availability)
   - "V2" or major version changes
   - Deprecation timelines
   - Breaking changes with migration guides
   - Performance improvements (often indicate architectural changes)

**Template for Research**:
```
1. WebSearch: "[technology] updates 2024 2025"
2. Check changelog page
3. Look for "breaking changes", "migration", "deprecated"
4. Verify current version vs skill version
5. Document all findings BEFORE auditing
```

---

### Next.js Skill Audit (2025-11-22)

**Skill**: nextjs (2,414 → 1,383 lines, 43% reduction)

**Key Insight**: **Established frameworks accumulate "obvious knowledge" over time**

**What We Removed**:
- Server Components basics (2022) - 200 lines
- Server Actions basics (2023) - 235 lines
- Metadata API (2023) - 100 lines
- All pre-2025 content that LLMs already know

**What We Kept**:
- Next.js 16 breaking changes (Oct 2025) - 266 lines
- Cache Components (Oct 2025) - 268 lines
- React 19.2 features (Dec 2024) - 117 lines
- All error prevention (18 errors) - 391 lines

**Learnings**:
- Frameworks with multi-year history accumulate cruft
- "Basics" sections are almost always removable
- Error prevention is always high-value (keep 100%)
- Breaking changes from latest version = pure knowledge gap

---

## References

- **Session Log**: SESSION.md (Phase 2 section)
- **Vectorize Audit**: SESSION.md (Cloudflare Vectorize Skill Audit section)
- **Next.js Audit**: SESSION.md (Next.js Skill Audit section)
- **Skills Standards**: planning/claude-code-skill-standards.md
- **Common Mistakes**: planning/COMMON_MISTAKES.md

---

**Last Updated**: 2025-11-22 (added research phase + lessons learned)
**Next Review**: 2026-02-22 (Quarterly)
**Maintainer**: Jezweb | jeremy@jezweb.net
