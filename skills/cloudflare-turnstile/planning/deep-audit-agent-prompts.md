# Deep Audit Sub-Agent Prompts

These prompts are used by `/deep-audit` to launch 4 parallel comparison agents.

---

## Agent 1: API Coverage

**Purpose**: Compare documented APIs/methods against what the skill covers.

**Prompt Template**:
```
You are auditing a Claude Code skill for API coverage accuracy.

## Task
Compare the OFFICIAL DOCUMENTATION against the SKILL CONTENT to identify:
1. APIs/methods documented officially but MISSING from the skill
2. APIs/methods in the skill that are DEPRECATED or REMOVED
3. New features added since the skill was last updated

## Official Documentation (scraped)
{scraped_docs}

## Skill Content
{skill_content}

## Output Format
Return a structured assessment:

### Coverage Score: X/10

### Missing APIs (in docs, not in skill)
- `methodName()` - [brief description of what it does]

### Deprecated APIs (in skill, not in docs)
- `oldMethod()` - [what replaced it]

### New Features Not Covered
- Feature name - [brief description]

### Accurate Coverage
- List major APIs that ARE correctly documented

### Recommendation
[1-2 sentence summary of most important updates needed]
```

---

## Agent 2: Pattern Validation

**Purpose**: Check code examples for deprecated syntax or patterns that don't match current best practices.

**Prompt Template**:
```
You are auditing a Claude Code skill for code pattern accuracy.

## Task
Compare code examples in the SKILL against patterns shown in OFFICIAL DOCUMENTATION:
1. Syntax that has changed (old vs new way)
2. Import statements that have changed
3. Configuration patterns that are outdated
4. Best practices that have evolved

## Official Documentation (scraped)
{scraped_docs}

## Skill Content
{skill_content}

## Output Format

### Pattern Accuracy Score: X/10

### Deprecated Patterns Found
| Skill Shows | Docs Show | Location in Skill |
|-------------|-----------|-------------------|
| `old code` | `new code` | Section name |

### Import Changes
| Old Import | New Import | Notes |
|------------|------------|-------|

### Configuration Changes
- [List any config format changes]

### Accurate Patterns
- [List patterns that are still correct]

### Recommendation
[1-2 sentence summary of most critical pattern updates]
```

---

## Agent 3: Error/Known Issues

**Purpose**: Verify error documentation and known issues are current.

**Prompt Template**:
```
You are auditing a Claude Code skill for error documentation accuracy.

## Task
Compare error handling and known issues between OFFICIAL DOCUMENTATION and SKILL:
1. Errors that are documented in docs but missing from skill
2. Known issues that have been FIXED but skill still warns about
3. New common errors not covered in skill
4. Troubleshooting steps that have changed

## Official Documentation (scraped)
{scraped_docs}

## Skill Content
{skill_content}

## Changelog/Releases (if available)
{changelog_content}

## Output Format

### Error Documentation Score: X/10

### Missing Error Coverage
- Error: `ErrorName` - [what causes it, how to fix]

### Fixed Issues Still Documented
- Issue: [description] - Fixed in version X.X

### New Common Errors
- Error: [description] - [when it occurs]

### Accurate Error Docs
- [List errors that are correctly documented]

### Recommendation
[1-2 sentence summary of error doc updates needed]
```

---

## Agent 4: Ecosystem Validation

**Purpose**: Validate package registry, install commands, version references.

**Prompt Template**:
```
You are auditing a Claude Code skill for ecosystem/package accuracy.

## Task
Verify the skill correctly references:
1. Package registry (npm vs pypi vs github)
2. Package name (scoped vs unscoped, exact name)
3. Install commands (correct package manager, flags)
4. Version numbers and compatibility
5. Dependencies and peer dependencies

## Official Documentation (scraped)
{scraped_docs}

## Skill Content
{skill_content}

## Skill Metadata
ecosystem: {ecosystem}
package_name: {package_name}

## Output Format

### Ecosystem Accuracy Score: X/10

### Registry Issues
- [ ] Correct registry: {expected} vs skill shows: {actual}

### Package Name Issues
- [ ] Correct name: {expected} vs skill shows: {actual}

### Install Command Issues
| Skill Shows | Should Be | Notes |
|-------------|-----------|-------|

### Version Issues
- Current version: X.X.X
- Skill references: Y.Y.Y
- Breaking changes between versions: [list if any]

### Dependency Issues
- [List any missing or outdated dependencies]

### Accurate Ecosystem Info
- [List what is correct]

### Recommendation
[1-2 sentence summary - CRITICAL if wrong ecosystem like npm vs pypi]
```

---

## Orchestration Notes

### Parallel Execution
All 4 agents run in parallel using Claude Code's Task tool:
```
Task(subagent_type="general-purpose", prompt=agent1_prompt)
Task(subagent_type="general-purpose", prompt=agent2_prompt)
Task(subagent_type="general-purpose", prompt=agent3_prompt)
Task(subagent_type="general-purpose", prompt=agent4_prompt)
```

### Input Preparation
Before launching agents:
1. Run `deep-audit-scrape.py` to get cached docs
2. Read skill's SKILL.md content
3. Parse skill metadata for ecosystem info
4. Prepare prompts with actual content

### Output Aggregation
After all agents complete:
1. Collect all 4 reports
2. Calculate overall accuracy score (average of 4 scores)
3. Prioritize findings (CRITICAL > HIGH > MEDIUM > LOW)
4. Generate unified report to `planning/CONTENT_AUDIT_[skill].md`

### Scoring Guide
- 10/10: Perfect match, no updates needed
- 8-9/10: Minor updates, low priority
- 6-7/10: Several updates needed, medium priority
- 4-5/10: Significant gaps, high priority
- 1-3/10: Major rewrite needed, critical priority
