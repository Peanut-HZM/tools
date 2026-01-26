# /review-skill - Skill Audit Command

Comprehensive skill documentation audit with automated checks and manual review phases.

## Usage

```
/review-skill <skill-name>
```

## Examples

```
/review-skill better-auth
/review-skill cloudflare-worker-base
/review-skill tiptap
```

## What It Does

### Phase 1: Automated Checks
Runs `./scripts/review-skill.sh <skill-name>` to check:
- YAML frontmatter syntax
- Package version currency (npm/PyPI)
- Broken links
- TODO/FIXME comments
- File organization
- Staleness indicators

### Phase 2: Manual Review
Systematically reviews:
1. **Accuracy** - Code examples work, patterns current
2. **Completeness** - Coverage vs official docs
3. **Error Prevention** - Known issues documented
4. **Token Efficiency** - Not bloated, well-organized

### Phase 3: Gap Analysis
Identifies:
- Missing features from latest package version
- Deprecated patterns still recommended
- Breaking changes not documented
- Rules file needed but missing

### Phase 4: Remediation
Applies fixes for:
- Version updates (after npm verification)
- Documentation inconsistencies
- Missing sections
- Stale dates

## Output

Generates an audit report with:

```markdown
## Skill Audit: [skill-name]

### Version Status
| Package | Current | Latest | Status |

### Gaps Found
1. [Issue] - [Severity] - [Evidence]

### Recommended Updates
| Priority | Task | Effort |

### Quality Score: X/10
```

## When to Use

- Before marketplace submission
- After major package updates (check changelog first)
- Skill last verified >90 days ago
- Investigating patterns that seem outdated
- User reports skill doesn't work

## Related

- **Script**: `./scripts/review-skill.sh` (automated portion)
- **Skill**: `skill-review` (full methodology)
- **Protocol**: `planning/SKILL_REVIEW_PROCESS.md` (9-phase guide)
- **Audit Protocol**: `planning/SKILL_AUDIT_PROTOCOL.md` (verification-first approach)

## Important

**Version Verification**: Per `SKILL_AUDIT_PROTOCOL.md`, always verify package versions with `npm view` before trusting audit agent recommendations. Training data has cutoffs and may suggest deprecated packages as current.
