# QA Agents Guide

This guide explains how to use the skill quality assurance agents in claude-skills.

## Quick Reference

| I want to... | Use Agent | How to Invoke |
|--------------|-----------|---------------|
| **Full skill audit** | All 4 agents | `/audit-skill-deep skill-name` |
| **Find missing features** | content-accuracy-auditor | "Check what features are missing from cloudflare-d1 skill" |
| **Validate code examples** | code-example-validator | "Validate code examples in ai-sdk-core" |
| **Verify APIs exist** | api-method-checker | "Check if documented methods in clerk-auth exist" |
| **Check package versions** | version-checker | "Check versions in hono-routing skill" |

## The QA Agent Squad

### 1. content-accuracy-auditor

**Purpose**: Find features documented in official docs but missing from skill.

**Catches**:
- Missing API features (the "Firecrawl 40% gap" problem)
- Deprecated patterns still recommended
- New features not documented

**Invocation**:
```
"Audit cloudflare-d1 skill for content accuracy"
"Compare hono-routing skill against official Hono documentation"
```

**Output**: Coverage report with missing features, confidence ratings, and recommendations.

---

### 2. code-example-validator

**Purpose**: Validate code examples are syntactically correct and use valid APIs.

**Catches**:
- Wrong method names (`topK` vs `topN`)
- Outdated imports (`experimental_` prefixes)
- Syntax errors in code blocks

**Invocation**:
```
"Validate code examples in ai-sdk-core skill"
"Check if code blocks in clerk-auth are syntactically correct"
```

**Output**: Issues with line numbers, confidence ratings, and suggested fixes.

---

### 3. api-method-checker

**Purpose**: Verify documented methods actually exist in current package versions.

**Catches**:
- Renamed APIs
- Removed methods
- Changed function signatures

**Invocation**:
```
"Verify APIs documented in better-auth skill exist"
"Check if ai-sdk-core methods are in ai@6.0.26"
```

**Output**: Verification results with TypeScript definition evidence.

---

### 4. version-checker

**Purpose**: Keep package version references current.

**Catches**:
- Outdated version numbers
- Version mismatches within skill
- Breaking changes needing migration

**Invocation**:
```
"Check package versions in cloudflare-worker-base"
"Update version references in tailwind-v4-shadcn"
```

**Output**: Version report with current vs documented versions.

---

## Confidence Ratings

All agents rate their findings:

| Rating | Meaning | Evidence |
|--------|---------|----------|
| **HIGH** | Certain | Verified programmatically (npm exports, TypeScript defs) |
| **MEDIUM** | Likely correct | Found in changelog/search but can't fully verify |
| **LOW** | Uncertain | Couldn't access sources, multiple interpretations possible |

**What to do**:
- HIGH: Fix immediately
- MEDIUM: Verify then fix
- LOW: Manual review needed

---

## Common Workflows

### Quarterly Skill Audit

Full audit of high-priority skills:

```bash
# Run comprehensive audit
/audit-skill-deep ai-sdk-core
/audit-skill-deep cloudflare-d1
/audit-skill-deep hono-routing

# Review findings, fix CRITICAL/HIGH first
# Then run with --fix to auto-apply safe fixes
/audit-skill-deep ai-sdk-core --fix
```

### After Package Update

When a package releases a new version:

```
1. "Check if ai-sdk-core skill matches ai@6.1.0"
2. Agent runs, finds issues
3. Agent suggests which other agents should verify
4. Apply fixes, commit
```

### Quick Syntax Check

Before committing skill changes:

```
"Validate code examples in my-skill"
```

Fix any HIGH confidence issues before committing.

### Finding Missing Features

When you suspect a skill is incomplete:

```
"Compare cloudflare-kv skill against official Cloudflare KV documentation"
```

Agent will list what's missing with priority levels.

---

## Orchestrated vs On-Demand

### Orchestrated: `/audit-skill-deep`

Runs all agents in coordinated workflow:

```
/audit-skill-deep skill-name [--quick] [--fix]
```

- `--quick`: Skip content-accuracy (faster, syntax/API only)
- `--fix`: Auto-apply safe fixes

**Flow**:
1. version-checker (establishes baseline)
2. Three agents in parallel (content, code, API)
3. Aggregated report with overall score

### On-Demand: Ask Directly

Ask Claude to use a specific agent:

```
"Use code-example-validator to check ai-sdk-core"
"Ask content-accuracy-auditor about missing features in hono-routing"
```

Good for quick targeted checks.

---

## Cross-Agent Coordination

Agents suggest follow-ups when they find related issues:

| Agent Finds | Suggests |
|-------------|----------|
| Missing feature | content-accuracy-auditor → "add to skill" |
| Wrong method name | code-example-validator → api-method-checker to verify |
| Renamed API | api-method-checker → code-example-validator to update examples |
| Version mismatch | version-checker → all agents to re-verify |

Example output:
```markdown
### Suggested Follow-up

**For api-method-checker**: Verify if `experimental_generateSpeech`
has graduated to stable `generateSpeech` in ai@6.0.26.
```

---

## Output Locations

| Agent | Output Location |
|-------|-----------------|
| `/audit-skill-deep` | `planning/QA_AUDIT_[skill].md` |
| version-checker | `VERSIONS_REPORT.md` (repo root) |
| Individual agents | Inline report in conversation |

---

## Troubleshooting

### Agent can't access documentation

The content-accuracy-auditor has a 3-tier fallback:
1. WebFetch (fast)
2. WebSearch (alternative sources)
3. Firecrawl via web-researcher (anti-bot)

If all fail, agent reports LOW confidence and suggests manual verification.

### Too many findings

If an audit returns 20+ issues:
1. Focus on CRITICAL and HIGH confidence first
2. Use `--quick` mode for faster checks
3. Batch fixes by category (versions, then code, then content)

### Agent keeps investigating

Agents have stop conditions:
- Max 5 pages fetched per audit
- Max 3 verification attempts per issue
- Escalates to human when uncertain

If an agent seems stuck, it will report what it tried and suggest manual steps.

---

## Related Resources

- **Command**: `commands/audit-skill-deep.md`
- **Protocol**: `planning/skill-audit-protocol.md`
- **Scripts**: `scripts/check-all-versions.sh`
