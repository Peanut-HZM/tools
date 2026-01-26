# /audit-skill-deep - Comprehensive Skill QA

Orchestrates multiple specialized agents to perform comprehensive quality assurance on a skill. Catches issues that version-only audits miss.

## Usage

```bash
/audit-skill-deep <skill-name>           # Full audit of single skill
/audit-skill-deep <skill-name> --quick   # Skip content-accuracy (faster)
/audit-skill-deep <skill-name> --fix     # Audit and auto-fix issues
```

## What This Does

Unlike basic audits that check version numbers and structure, this command validates:

1. **Package Versions** - Are version references current?
2. **Content Coverage** - Does skill cover features from official docs?
3. **Code Syntax** - Are code examples syntactically correct?
4. **API Methods** - Do documented methods actually exist?

**Problems it catches**:
- Firecrawl skill missing 40% of API features
- ai-sdk-core using `topK` instead of `topN`
- Outdated experimental_ prefixes
- Deprecated methods still documented

## Workflow

### Step 1: Version Check

First, run the version-checker agent:

```
Launch version-checker agent:
"Check package versions for skill [skill-name].
Report outdated versions and breaking changes."
```

This establishes the baseline - are we even checking against current versions?

### Step 2: Content Accuracy (Parallel with Step 3 & 4)

Launch content-accuracy-auditor agent:

```
Launch content-accuracy-auditor agent:
"Compare skill [skill-name] against official documentation.
Identify missing features and deprecated patterns.
Generate coverage report."
```

Catches: Missing features, deprecated patterns, new APIs not covered.

### Step 3: Code Example Validation (Parallel)

Launch code-example-validator agent:

```
Launch code-example-validator agent:
"Validate all code examples in skill [skill-name].
Check syntax, imports, and method names.
Report issues with line numbers."
```

Catches: Syntax errors, wrong method names, outdated imports.

### Step 4: API Method Verification (Parallel)

Launch api-method-checker agent:

```
Launch api-method-checker agent:
"Verify all documented API methods in skill [skill-name] exist.
Check current package version exports.
Report renamed, removed, or deprecated methods."
```

Catches: Non-existent methods, renamed APIs, deprecated functions.

### Step 5: Aggregate Results

After all agents complete, combine their reports:

1. **Deduplicate Issues**: Same issue may be found by multiple agents
2. **Prioritize**: CRITICAL > HIGH > MEDIUM > LOW
3. **Generate Summary**: Overall health score

### Step 6: Generate Report

Write comprehensive report to `planning/QA_AUDIT_[skill].md`.

## Execution Instructions

When `/audit-skill-deep <skill-name>` is invoked:

### 1. Validate Skill Exists

```bash
ls skills/<skill-name>/SKILL.md || echo "Skill not found"
```

### 2. Run Version Checker First

```
Launch Task with version-checker agent:
"Check package versions for [skill-name]. Report any outdated versions."
```

Wait for completion before proceeding (establishes version baseline).

### 3. Launch 3 Agents in Parallel

Use a SINGLE message with multiple Task tool calls:

```
# Agent 1: Content Accuracy
Task(content-accuracy-auditor):
"Audit skill [skill-name] for content coverage against official documentation.
Find missing features and deprecated patterns."

# Agent 2: Code Validation
Task(code-example-validator):
"Validate code examples in skill [skill-name].
Check syntax, imports, method names. Report with line numbers."

# Agent 3: API Verification
Task(api-method-checker):
"Verify API methods documented in skill [skill-name] exist.
Check against current package exports."
```

All three run simultaneously for efficiency.

### 4. Collect Results

After all agents complete, collect their reports.

### 5. Generate Unified Report

Create `planning/QA_AUDIT_[skill].md`:

```markdown
# QA Audit: [skill-name]

**Date**: YYYY-MM-DD
**Overall Score**: X/10
**Status**: [PASS | NEEDS_FIXES | CRITICAL]

## Summary

| Check | Score | Issues |
|-------|-------|--------|
| Version Currency | X/10 | N |
| Content Coverage | X/10 | N |
| Code Syntax | X/10 | N |
| API Validity | X/10 | N |

## Critical Issues

[Issues that must be fixed immediately]

## High Priority

[Issues that should be fixed soon]

## Medium Priority

[Issues to address opportunistically]

## Low Priority

[Minor improvements]

---

## Detailed Reports

### Version Check Report
[version-checker output]

### Content Accuracy Report
[content-accuracy-auditor output]

### Code Validation Report
[code-example-validator output]

### API Verification Report
[api-method-checker output]
```

### 6. Report to User

Display summary and offer next steps:
- View full report
- Start fixing issues
- Run with --fix to auto-fix

## Quick Mode (--quick)

Skip the content-accuracy-auditor (slowest due to web fetching):

```bash
/audit-skill-deep ai-sdk-core --quick
```

Only runs:
- version-checker
- code-example-validator
- api-method-checker

Useful for quick syntax/API validation after edits.

## Auto-Fix Mode (--fix)

After audit, attempt to auto-fix issues:

```bash
/audit-skill-deep ai-sdk-core --fix
```

Auto-fixable issues:
- Version number updates
- Simple method renames (topK → topN)
- Import path updates
- Deprecated prefix removal
- Missing feature documentation (content-accuracy-auditor adds from official docs)
- Syntax corrections

Non-auto-fixable (require manual):
- Complex code restructuring
- Ambiguous replacements (multiple options)
- Major architectural changes

### Fix Workflow

When `--fix` is used:

1. **version-checker**: Updates version references
2. **content-accuracy-auditor**: Adds missing features from official docs (uses Firecrawl fallback if needed)
3. **code-example-validator**: Fixes syntax errors and wrong method names
4. **api-method-checker**: Updates renamed/deprecated methods

Each agent reports what it fixed. Human reviews changes before commit.

## Scoring

### Overall Score Calculation

```
Overall = (Version + Coverage + Syntax + API) / 4
```

Each component scored 1-10:

| Score | Meaning |
|-------|---------|
| 9-10 | Excellent - Production ready |
| 7-8 | Good - Minor issues |
| 5-6 | Needs Work - Several issues |
| <5 | Critical - Major problems |

### Status Assignment

| Score | Status |
|-------|--------|
| ≥ 8.0 | PASS |
| 5.0-7.9 | NEEDS_FIXES |
| < 5.0 | CRITICAL |

## Relationship to Other Commands

| Command | Focus | When to Use |
|---------|-------|-------------|
| `/audit` | Structure (YAML, files) | Quick structural check |
| `/deep-audit` | Content via Firecrawl | When need full doc scraping |
| **`/audit-skill-deep`** | **Code + API + Coverage** | **Comprehensive QA** |
| `review-skill.sh` | Links, TODOs | Pre-commit check |

## Example Session

```bash
# User
/audit-skill-deep ai-sdk-core

# Claude
Running comprehensive QA audit for ai-sdk-core...

## Phase 1: Version Check
Checking package versions...
✅ ai@4.0.26 - current
⚠️ Documented as 4.0.9 in skill

## Phase 2: Parallel Audits (3 agents)
Launching content-accuracy-auditor...
Launching code-example-validator...
Launching api-method-checker...

[Agents run in parallel]

## Results

### Overall Score: 6.5/10 (NEEDS_FIXES)

| Check | Score | Issues |
|-------|-------|--------|
| Versions | 7/10 | 1 outdated |
| Coverage | 8/10 | 2 missing features |
| Syntax | 5/10 | 3 errors |
| API | 6/10 | 2 wrong methods |

### Critical Issues

1. **topK should be topN** (Line 234)
   - Found by: api-method-checker + code-example-validator
   - Fix: `topK: 5` → `topN: 5`

2. **experimental_streamText deprecated** (Line 156)
   - Found by: api-method-checker
   - Fix: Remove `experimental_` prefix

Full report: planning/QA_AUDIT_ai-sdk-core.md

Would you like me to auto-fix these issues?
```

## Cost Estimate

| Component | Token Cost | Time |
|-----------|-----------|------|
| version-checker | ~5k | 10s |
| content-accuracy-auditor | ~15k | 30s |
| code-example-validator | ~10k | 20s |
| api-method-checker | ~10k | 20s |
| **Total** | **~40k** | **~45s** |

With --quick (no content audit): ~25k tokens, ~25s

## When to Use

- **Before releasing skill updates**: Full audit
- **After editing code examples**: Quick mode
- **Quarterly maintenance**: Full audit on all high-priority skills
- **After package major version bump**: Full audit to catch breaking changes
