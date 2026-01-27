# /deep-audit - Content Accuracy Audit

Validate skill CONTENT against official documentation using Firecrawl for web scraping and sub-agents for semantic comparison. Complements version-number audits by catching content errors.

## Usage

```bash
/deep-audit <skill-name>           # Audit single skill
/deep-audit cloudflare-*           # Audit skills matching pattern
/deep-audit --tier 1               # Audit all Tier 1 skills
/deep-audit --all                  # Audit all skills (expensive)
/deep-audit --diff <skill-name>    # Only if docs changed since last audit
```

## What This Does

Unlike `/audit` which checks structural aspects (YAML frontmatter, file organization), `/deep-audit` validates that skill **content** matches current official documentation.

**Problem it solves**: Version audits can pass while content is wrong. Example: fastmcp skill referenced npm version 3.26.8 when the Python package (PyPI) is at 2.14.2 - completely different ecosystem!

## Prerequisites

1. **Firecrawl API Key**: Set in environment or `.env`:
   ```bash
   export FIRECRAWL_API_KEY=fc-xxxxxxxx
   ```

2. **Skill Metadata**: Skills should have `doc_sources` in YAML frontmatter:
   ```yaml
   metadata:
     doc_sources:
       primary: "https://docs.example.com/getting-started"
       api: "https://docs.example.com/api-reference"
       changelog: "https://github.com/org/repo/releases"
     ecosystem: pypi  # npm | pypi | github
     package_name: example-package
   ```

## Workflow

### Step 1: Discovery

Extract documentation URLs from skill's `metadata.doc_sources`. If not present, attempt to infer from:
- Links in SKILL.md
- Package registry (npm/PyPI) URLs
- GitHub repository

### Step 2: Scrape Documentation

Use Firecrawl to fetch official docs as markdown:

```bash
python scripts/deep-audit-scrape.py <skill-name>
```

Output cached to `archive/audit-cache/<skill>/`:
- `YYYY-MM-DD_primary.md` - Scraped content
- `YYYY-MM-DD_hash` - Content hash for change detection

### Step 3: Sub-Agent Comparison

Launch 4 parallel sub-agents to compare skill against scraped docs:

| Agent | Focus | Checks |
|-------|-------|--------|
| **API Coverage** | Methods & features | Are documented APIs covered in skill? Missing new features? |
| **Pattern Validation** | Code examples | Deprecated syntax? New patterns not reflected? |
| **Error Check** | Known issues | Fixed bugs still documented? New common errors? |
| **Ecosystem** | Package info | Correct registry? Right install commands? Version accuracy? |

### Step 4: Generate Report

Output to `planning/CONTENT_AUDIT_<skill>.md`:

```markdown
# Content Audit: <skill-name>
**Date**: YYYY-MM-DD
**Accuracy Score**: 85-92%

## Summary
- [x] API coverage current
- [ ] 2 deprecated patterns found
- [x] Error documentation accurate
- [ ] Install command uses wrong package manager

## Findings

### Critical
- Pattern `oldMethod()` deprecated in v2.0, skill still recommends

### Warnings
- New feature `newFeature()` not documented in skill
- Changelog shows breaking change not mentioned

### OK
- Core concepts accurate
- Error handling patterns correct
```

## Cost Estimates

| Scope | Firecrawl Cost | Tokens |
|-------|---------------|--------|
| Single skill | ~$0.003 | ~35k |
| Pattern (10 skills) | ~$0.03 | ~350k |
| Tier 1 (10 skills) | ~$0.03 | ~350k |
| All skills (68) | ~$0.20 | ~2.4M |

**Optimization**:
- Cache lasts 7 days
- Use `--diff` flag to only audit if docs changed
- Prioritize Tier 1/2 skills

## Integration with Existing Tools

| Tool | What It Checks | Relationship |
|------|---------------|--------------|
| `/audit` | Structure (YAML, files) | Run first for quick checks |
| `review-skill.sh` | Links, versions, TODOs | Complements deep-audit |
| `check-all-versions.sh` | Package version numbers | Deep-audit validates content |
| **`/deep-audit`** | **Content accuracy** | **Catches semantic errors** |

## Recommended Workflow

```bash
# 1. Quick structural audit
/audit <skill-name>

# 2. If passes, deep content audit
/deep-audit <skill-name>

# 3. Review findings
cat planning/CONTENT_AUDIT_<skill>.md

# 4. Fix issues and commit
git add skills/<skill-name>/
git commit -m "audit(<skill>): Fix content accuracy issues"
```

## Cache Management

```bash
# View cached audits
ls archive/audit-cache/

# Clear cache for skill (force re-scrape)
rm -rf archive/audit-cache/<skill-name>/

# Clear all cache
rm -rf archive/audit-cache/*/
```

## Adding doc_sources to Skills

For skills without `doc_sources`, add to YAML frontmatter:

```yaml
---
name: my-skill
description: |
  [description]
metadata:
  doc_sources:
    primary: "https://official-docs.com/getting-started"
    api: "https://official-docs.com/api"
    changelog: "https://github.com/org/repo/releases"
  ecosystem: npm  # or pypi, github
  package_name: package-name
---
```

## Example: fastmcp Audit

```bash
/deep-audit fastmcp
```

**Found Issue** (actual example that motivated this tool):
- Skill referenced `fastmcp>=3.26.8` (npm package)
- PyPI shows `fastmcp>=2.14.2` (Python package)
- **Completely different ecosystems!**

This error passed all version checks because the npm version exists - but the skill is for Python!

---

## Execution Instructions

When `/deep-audit <skill-name>` is invoked, execute the following steps:

### Step 0: Check for --diff Flag (Incremental Audit)

If `--diff` flag is present, first check if documentation has changed:

```bash
# Check if docs changed since last audit
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-diff.py <skill-name>
```

**If exit code is 0** (docs unchanged): Report "Documentation unchanged since last audit" and skip full audit.

**If exit code is 1** (needs re-audit): Continue with full audit below.

**Output interpretation:**
- `STATUS: UP TO DATE` → Skip audit, inform user
- `STATUS: NEEDS RE-AUDIT` → Continue with full audit
- `Reason: Last audit is X days old` → Cache expired, re-audit needed

### Step 1: Validate and Scrape

```bash
# Check skill exists
ls skills/<skill-name>/SKILL.md

# Run scraper (uses cached content if fresh)
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  python scripts/deep-audit-scrape.py <skill-name>
```

If scrape fails due to missing `doc_sources`, inform user they need to add metadata.

### Step 2: Read Content

Read these files into context:
1. `skills/<skill-name>/SKILL.md` - The skill being audited
2. `archive/audit-cache/<skill-name>/*.md` - All scraped doc files

### Step 3: Launch 4 Parallel Comparison Agents

Use the Task tool to launch 4 agents **in parallel** (single message, multiple Task calls):

**Reference**: See `planning/deep-audit-agent-prompts.md` for full prompt templates.

```
Agent 1: API Coverage
- Compare documented APIs in scraped docs vs skill coverage
- Find missing features, deprecated methods

Agent 2: Pattern Validation
- Check code examples for outdated syntax
- Find import changes, config changes

Agent 3: Error/Issues
- Verify error documentation is current
- Check if fixed issues are still documented

Agent 4: Ecosystem Validation
- Verify correct package registry (npm/pypi/github)
- Check install commands, version references
```

Each agent receives:
- Scraped documentation content
- Skill SKILL.md content
- Skill metadata (ecosystem, package_name)

### Step 4: Aggregate and Report

After all 4 agents complete:

1. **Calculate Overall Score**: Average of 4 agent scores (X/10)

2. **Prioritize Findings**:
   - CRITICAL: Wrong ecosystem, major API gaps
   - HIGH: Deprecated patterns, missing features
   - MEDIUM: Minor updates, new features not covered
   - LOW: Style improvements, optional enhancements

3. **Generate Report**: Write to `planning/CONTENT_AUDIT_<skill>.md`:

```markdown
# Content Audit: <skill-name>

**Date**: YYYY-MM-DD
**Overall Score**: X.X/10
**Status**: [PASS | NEEDS_UPDATE | CRITICAL]

## Summary

| Category | Score | Status |
|----------|-------|--------|
| API Coverage | X/10 | ✅/⚠️/❌ |
| Pattern Validation | X/10 | ✅/⚠️/❌ |
| Error Documentation | X/10 | ✅/⚠️/❌ |
| Ecosystem Accuracy | X/10 | ✅/⚠️/❌ |

## Critical Issues
[List any critical findings that need immediate attention]

## Recommended Updates
[Prioritized list of updates to make]

## Agent Reports

### API Coverage Agent
[Full report from Agent 1]

### Pattern Validation Agent
[Full report from Agent 2]

### Error/Issues Agent
[Full report from Agent 3]

### Ecosystem Agent
[Full report from Agent 4]

## Sources Audited
- primary: [URL] ([X] chars)
- api: [URL] ([X] chars)
- changelog: [URL] ([X] chars)
```

4. **Inform User**: Display summary and path to full report.

### Step 5: Update History with Audit Result

After generating the report, update `archive/audit-cache/<skill>/history.json` with the audit score:

```python
# Append audit result to history
history[-1]["audit_result"] = {
    "score": 8.5,  # Overall score
    "status": "PASS",  # PASS | NEEDS_UPDATE | CRITICAL
    "report_path": "planning/CONTENT_AUDIT_<skill>.md"
}
```

This enables tracking audit quality over time.

### Step 6: Offer Next Steps

After report is generated, offer:
1. Open report for review: `cat planning/CONTENT_AUDIT_<skill>.md`
2. Start fixing issues (if any critical/high findings)
3. Mark audit complete if score >= 8/10

---

## Bulk Operations

Use the bulk operations script for auditing multiple skills at once.

### List Skills by Tier

```bash
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --list
```

Shows all skills organized by tier with existence status.

### Check All Cached Skills

```bash
# See which skills need re-auditing
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-diff.py --all
```

Output shows:
- Skills that need re-audit (cache expired or docs changed)
- Skills that are up to date

### Tier-Based Auditing

```bash
# Single tier
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --tier 1

# Multiple tiers (range)
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --tier 1-3

# Multiple tiers (specific)
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --tier 1,3,5

# Dry run (preview only)
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --dry-run --tier 1
```

Tier definitions are read from `planning/SKILL_AUDIT_QUEUE.md`.

### Pattern Matching

```bash
# Cloudflare skills
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py 'cloudflare-*'

# AI-related skills
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py 'ai-*'

# OpenAI skills
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py 'openai-*'
```

### Skip Fresh Cache

Only audit skills that need re-auditing (cache > 7 days old):

```bash
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --tier 1 --skip-fresh
```

### Audit All Skills

```bash
# WARNING: Expensive! (~$0.20 Firecrawl, ~2.4M tokens)
/home/jez/Documents/claude-skills/.venv/bin/python \
  scripts/deep-audit-bulk.py --all
```
