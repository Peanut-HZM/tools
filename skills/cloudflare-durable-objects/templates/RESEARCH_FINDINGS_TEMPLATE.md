# Community Knowledge Research: [Skill Name]

**Research Date**: YYYY-MM-DD
**Researcher**: skill-researcher agent
**Skill Path**: skills/[skill-name]/SKILL.md
**Packages Researched**: [package@version, ...]
**Official Repo**: [org/repo]
**Time Window**: May 2025 - Present (post-training-cutoff focus)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Findings | N |
| TIER 1 (Official) | X |
| TIER 2 (High-Quality Community) | Y |
| TIER 3 (Community Consensus) | Z |
| TIER 4 (Low Confidence) | W |
| Already in Skill | A |
| Recommended to Add | B |

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: [Short Descriptive Title]

**Trust Score**: TIER 1 - Official
**Source**: [GitHub Issue #123](URL) | [Maintainer Comment](URL)
**Date**: YYYY-MM-DD
**Verified**: Yes
**Impact**: HIGH / MEDIUM / LOW
**Already in Skill**: No

**Description**:
[Clear description of the edge case, gotcha, or issue]

**Reproduction**:
```typescript
// Code that triggers the issue
[code example]
```

**Solution/Workaround**:
```typescript
// Fixed code or workaround
[code example]
```

**Official Status**:
- [ ] Fixed in version X.Y.Z
- [ ] Documented behavior
- [ ] Known issue, workaround required
- [ ] Won't fix

**Cross-Reference**:
- Corroborated by: [second source if any]
- Related to: [skill section if partially covered]

---

### Finding 1.2: [Title]

[Repeat structure]

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: [Short Descriptive Title]

**Trust Score**: TIER 2 - High-Quality Community
**Source**: [Stack Overflow](URL) (X upvotes) | [GitHub Issue](URL)
**Date**: YYYY-MM-DD
**Verified**: Partial / Code Review Only
**Impact**: HIGH / MEDIUM / LOW
**Already in Skill**: No

**Description**:
[Description]

**Reproduction**:
```typescript
[code]
```

**Solution/Workaround**:
```typescript
[code]
```

**Community Validation**:
- Upvotes: X
- Accepted answer: Yes / No
- Multiple users confirm: Yes / No

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: [Title]

**Trust Score**: TIER 3 - Community Consensus
**Source**: [Blog Post](URL), [Reddit Thread](URL)
**Date**: YYYY-MM-DD
**Verified**: Cross-Referenced Only
**Impact**: MEDIUM / LOW
**Already in Skill**: No

**Description**:
[Description]

**Solution**:
```typescript
[code if applicable]
```

**Consensus Evidence**:
- Sources agreeing: [list URLs]
- Conflicting information: [if any]

**Recommendation**: Verify before adding / Add to Community Tips section

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

### Finding 4.1: [Title]

**Trust Score**: TIER 4 - Low Confidence
**Source**: [Single Source](URL)
**Date**: YYYY-MM-DD
**Verified**: No
**Impact**: Unknown

**Why Flagged**:
- [ ] Single source only
- [ ] Cannot reproduce
- [ ] Contradicts official docs
- [ ] May be version-specific (old)
- [ ] Outdated (pre-2024)

**Description**:
[Description]

**Recommendation**: Manual verification required. DO NOT add to skill without human review.

---

## Already Documented in Skill

These findings are already covered (no action needed):

| Finding | Skill Section | Notes |
|---------|---------------|-------|
| [Issue description] | Known Issues #X | Fully covered |
| [Issue description] | Error Handling | Partially covered, could expand |

---

## Recommended Actions

### Priority 1: Add to Skill (TIER 1-2, High Impact)

| Finding | Target Section | Action |
|---------|----------------|--------|
| 1.1 [Title] | Known Issues Prevention | Add as Issue #13 |
| 1.2 [Title] | Error Handling | Add to error table |
| 2.1 [Title] | Common Patterns | Add with "Community-sourced" flag |

### Priority 2: Consider Adding (TIER 2-3, Medium Impact)

| Finding | Target Section | Notes |
|---------|----------------|-------|
| 2.2 [Title] | Community Tips | Verify first |
| 3.1 [Title] | Configuration | Multiple sources agree |

### Priority 3: Monitor (TIER 4, Needs Verification)

| Finding | Why Flagged | Next Step |
|---------|-------------|-----------|
| 4.1 [Title] | Single source | Wait for corroboration |

---

## Research Sources Consulted

### GitHub (Primary)

| Search | Results | Relevant |
|--------|---------|----------|
| "edge case" in [org/repo] | 45 | 8 |
| "gotcha" in [org/repo] | 12 | 3 |
| "workaround" in [org/repo] | 67 | 5 |
| Issues with "bug" label | 234 | 10 |
| Recent releases | 15 | 4 |

### Stack Overflow

| Query | Results | Quality |
|-------|---------|---------|
| "[package] gotcha 2024" | 23 | 3 with 10+ upvotes |
| "[package] edge case" | 15 | 2 with 10+ upvotes |

### Other Sources

| Source | Notes |
|--------|-------|
| [Company blog](URL) | 2 relevant posts |
| [Maintainer blog](URL) | 1 relevant post |

---

## Methodology Notes

**Tools Used**:
- `gh search issues` for GitHub discovery
- `WebSearch` for Stack Overflow and blogs
- `WebFetch` for content retrieval

**Limitations**:
- [Any sources that couldn't be accessed]
- [Time constraints]
- [Version-specific findings flagged]

**Time Spent**: ~X minutes

---

## Suggested Follow-up

**For content-accuracy-auditor**: Cross-reference findings 1.1 and 2.1 against current official documentation before adding.

**For api-method-checker**: Verify that the workaround in finding 1.2 uses currently available APIs.

**For code-example-validator**: Validate code examples in findings 1.1, 2.1, 2.2 before adding to skill.

---

## Integration Guide

### Adding TIER 1-2 Findings to SKILL.md

```markdown
### Issue #[N]: [Title from finding]

**Error**: `[error message if applicable]`
**Source**: [GitHub Issue #X](URL)
**Why It Happens**: [explanation]
**Prevention**: [solution/workaround]

```typescript
// Correct pattern
[code from finding]
```
```

### Adding to Community Tips Section (TIER 2-3)

```markdown
## Community Tips (Community-Sourced)

> **Note**: These tips come from community discussions. Verify against your version.

### Tip: [Title]

**Source**: [Stack Overflow](URL) | **Confidence**: HIGH/MEDIUM
**Applies to**: vX.Y+

[Description and code example]
```

---

**Research Completed**: YYYY-MM-DD HH:MM
**Next Research Due**: [Suggest date, e.g., after next major release]
