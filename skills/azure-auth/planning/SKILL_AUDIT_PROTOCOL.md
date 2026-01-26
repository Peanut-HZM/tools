# Skill Audit Protocol

**Purpose**: Accurate, verified skill audits that avoid propagating errors from stale training data.

**Philosophy**: Quality over speed. Multiple agents, multiple verification steps. Never recommend changes based on training knowledge alone.

---

## The Problem This Solves

Audit agents have training cutoffs. They may:
- Recommend deprecated packages as "current"
- Suggest reverting to old patterns
- Cite wrong version numbers from memory
- Make confident-sounding but incorrect recommendations

**Example failure**: Agent recommended changing `@google/genai` (correct, current) to `@google/generative-ai` (deprecated). Following this would have broken a working skill.

---

## Multi-Phase Audit Process

### Phase 1: Fact Extraction (No Judgment)

**Agent Task**: Extract raw data only. Do NOT interpret or recommend.

**Prompt Template**:
```
You are a fact-extraction agent. Read the skill files and extract:

1. All package names mentioned (npm, pip, etc.)
2. All version numbers claimed
3. All API patterns shown (imports, function calls)
4. Last updated dates
5. Any version-specific notes or warnings

DO NOT:
- Recommend changes
- Judge if versions are current
- Suggest alternatives
- Use your training knowledge about "latest" versions

Output format: JSON with extracted facts only.

Skill path: {skill_path}
```

**Output**: Raw extracted data, no interpretation.

---

### Phase 2: Version Verification (Ground Truth)

**Method**: Direct npm/pip/GitHub API queries - NOT agent knowledge.

**Script Pattern**:
```bash
# For each package extracted in Phase 1:
npm view {package} version           # Current version
npm view {package} time --json       # Release dates
npm view {package} deprecated        # Deprecation status

# For GitHub releases:
gh api repos/{owner}/{repo}/releases/latest

# For Python:
pip index versions {package}
```

**Output**: Verified current versions with timestamps.

---

### Phase 3: Rules & Context Loading

**Load relevant correction rules**:
```bash
# Check if skill has domain-specific rules
ls ~/.claude/rules/ | grep -i {skill-domain}

# Load rules that might apply
cat ~/.claude/rules/{relevant-rule}.md
```

**Load related skills** that might have corrections:
- If auditing `google-gemini-embeddings`, check `google-gemini-api` for patterns
- If auditing `cloudflare-*`, check `cloudflare-worker-base` for conventions

**Output**: Context bundle with current patterns and known corrections.

---

### Phase 4: Gap Analysis (With Verified Data)

**Agent Task**: Compare extracted facts against verified data.

**Prompt Template**:
```
You are a gap analysis agent. Compare the skill's claims against VERIFIED current data.

## Skill's Extracted Facts (from Phase 1):
{phase1_output}

## Verified Current Versions (from Phase 2):
{phase2_output}

## Relevant Correction Rules (from Phase 3):
{phase3_output}

## Your Task:
1. Compare skill's package versions vs verified current versions
2. Identify version gaps (skill says X, npm says Y)
3. Check if skill's patterns match correction rules
4. Flag any API changes between skill's version and current

DO NOT use your training knowledge for versions. Only use the verified data provided.

For each finding, cite your source:
- "Skill line 42 says v2.0, npm view returned v3.1"
- "Rules file says use X, skill uses deprecated Y"

Output: List of verified discrepancies with evidence.
```

---

### Phase 5: Breaking Change Research

**Agent Task**: For significant version gaps, research actual breaking changes.

**Prompt Template**:
```
Research breaking changes between {old_version} and {new_version} of {package}.

Use WebFetch to check:
1. GitHub releases/changelog: {changelog_url}
2. Migration guides: {migration_url}
3. NPM package page: https://www.npmjs.com/package/{package}

DO NOT guess what might have changed. Only report what you find documented.

Output: Documented breaking changes with sources, or "No breaking changes found in documentation."
```

---

### Phase 6: Verification & Report

**Final verification before reporting**:

1. **Cross-check critical findings**: Run npm view again for any "critical" issues
2. **Uncertainty flagging**: Mark findings as:
   - ✅ VERIFIED - Confirmed via npm/API query
   - ⚠️ LIKELY - Found in docs but not independently verified
   - ❓ UNCERTAIN - Based on incomplete information
3. **Include reproduction commands**: User should be able to verify themselves

**Report Template**:
```markdown
## Skill Audit Report: {skill_name}

### Verification Method
- Package versions: npm view (timestamp: {date})
- Rules loaded: {rules_files}
- Sources checked: {urls}

### Verified Findings

#### Version Gaps
| Package | Skill Says | Verified Current | Gap | Severity |
|---------|------------|------------------|-----|----------|
| {pkg}   | {v1}       | {v2}             | {n} | {level}  |

Verification command: `npm view {package} version`

#### Pattern Issues
- Line {n}: {issue}
- Source: {rules_file} says {correct_pattern}

### Uncertain Findings (Need Manual Review)
- {finding} - Could not verify because {reason}

### No Issues Found
- {aspect} appears current and correct
```

---

## Agent Composition Per Skill

For thorough audits, use **4-5 specialized agents**:

| Agent | Role | Tools Allowed |
|-------|------|---------------|
| **Extractor** | Read files, extract facts | Read, Glob |
| **Verifier** | Run npm/pip/gh commands | Bash (specific commands only) |
| **Context Loader** | Load rules, related skills | Read, Glob |
| **Analyzer** | Compare facts vs verified data | None (pure analysis) |
| **Researcher** | Fetch changelogs, docs | WebFetch, WebSearch |

---

## Pre-Flight Checklist

Before launching audit agents:

- [ ] Identify all packages skill mentions
- [ ] Run `npm view` for each to get current versions
- [ ] Load relevant `~/.claude/rules/` files
- [ ] Identify related skills to cross-reference
- [ ] Prepare changelog URLs for major packages

---

## Anti-Patterns to Avoid

### ❌ DON'T: Trust agent training knowledge for versions
```
Agent: "The latest version of X is 2.0"  ← May be stale!
```

### ✅ DO: Verify with actual queries
```
Bash: npm view X version → "3.1.0"  ← Ground truth
```

### ❌ DON'T: Let agents recommend package changes
```
Agent: "Change @google/genai to @google/generative-ai"  ← WRONG!
```

### ✅ DO: Have agents report what they find, not what to change
```
Agent: "Skill uses @google/genai@1.30. npm view shows 1.34 is latest."
```

### ❌ DON'T: Run all agents in parallel without coordination
```
43 agents → 43 potentially wrong recommendations
```

### ✅ DO: Sequential phases with verification gates
```
Extract → Verify → Analyze → Review
```

---

## Example: Correct Audit Flow

**Skill**: `google-gemini-embeddings`

**Phase 1 Output** (Extraction):
```json
{
  "packages": ["@google/genai@^1.30.0"],
  "imports": ["GoogleGenAI from @google/genai"],
  "last_updated": "2025-11-28"
}
```

**Phase 2 Output** (Verification):
```bash
$ npm view @google/genai version
1.34.0

$ npm view @google/generative-ai version
0.24.1  # Old package, lower version = not actively developed
```

**Phase 4 Output** (Analysis with verified data):
```
VERIFIED GAP:
- Skill: @google/genai@1.30.0
- Current: @google/genai@1.34.0
- Gap: 4 minor versions
- Severity: LOW (same package, minor updates)

NO ISSUE:
- Package name is correct (@google/genai is current)
- Import pattern matches current SDK
```

**Final Report**:
```
✅ Package name: Correct (verified via npm)
⚠️ Version: 1.30.0 → 1.34.0 (4 minor versions behind)
   Verification: npm view @google/genai version
   Recommendation: Update version in SKILL.md line 37
```

---

## Implementation Commands

### Run Verified Audit for Single Skill

```bash
# 1. Extract packages from skill
grep -ohE "@[a-z/-]+@[0-9^~.]+" skills/{name}/SKILL.md | sort -u

# 2. Verify each package
for pkg in $(grep -ohE "@[a-z/-]+@[0-9^~.]+" skills/{name}/SKILL.md | sort -u); do
  base=$(echo $pkg | sed 's/@[0-9^~.]*$//')
  echo "=== $base ==="
  npm view $base version
done

# 3. Load relevant rules
ls ~/.claude/rules/ | grep -i {domain}

# 4. Run analysis agent with verified context
```

---

## When to Use This Protocol

- **Full audits**: New skill review, quarterly maintenance
- **Quick checks**: Version bumps, minor updates (Phase 1-2 only)
- **Critical updates**: Breaking change research (all phases)

---

## Maintenance

- Review this protocol quarterly
- Update anti-patterns when new failure modes discovered
- Add package-specific verification patterns as needed

---

**Created**: 2026-01-06
**Last Updated**: 2026-01-06
**Author**: Claude Code + Jeremy Dawes
