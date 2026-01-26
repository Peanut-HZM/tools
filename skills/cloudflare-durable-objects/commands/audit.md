# /audit - Multi-Agent Audit Command

Trigger parallel sub-agent swarms to audit, research, or check multiple items at once.

## Usage

```
/audit [target]
```

## Targets

| Target | What It Does |
|--------|--------------|
| `skills` | Audit all skills against official docs |
| `rules` | Audit all user-level rules |
| `versions` | Check all package versions in skills |
| `[directory]` | Audit all items in specified directory |
| `[topic]` | Research topic across multiple sources |

## Behavior

When invoked:

1. **Identify scope** - Count items to audit
2. **Group logically** - Batch related items (8-12 per agent optimal)
3. **Launch parallel** - All agents in ONE message for true parallelism
4. **Compile findings** - Create planning doc at `planning/[TARGET]_AUDIT_[DATE].md`

## Agent Prompt Template

Each agent receives:
```
Audit [ITEMS] against official documentation.

Check for:
1. NEW features not documented
2. DEPRECATED patterns still recommended
3. BREAKING CHANGES not reflected
4. VERSION updates needed

Report: Accuracy %, gaps found, priority recommendations (HIGH/MEDIUM/LOW).
```

## Examples

### Audit all skills
```
/audit skills
```
→ Launches 68 parallel agents, creates `planning/SKILL_UPDATES_[DATE].md`

### Audit rules by category
```
/audit rules
```
→ Launches 9 grouped agents (by domain), creates `planning/RULES_UPDATES_[DATE].md`

### Research a topic
```
/audit "auth libraries for cloudflare workers"
```
→ Launches agents to research better-auth, clerk, lucia, oslo, etc.

### Check versions
```
/audit versions
```
→ Parallel version checks, creates `VERSIONS_REPORT.md`

## Output

Creates a tracking document that survives context compacts:

```markdown
# [Target] Audit - [Date]

## Summary
- Total items: X
- Needing updates: Y
- Estimated effort: Z hours

## Priority Tiers
### TIER 1: URGENT
| Item | Issue | Est Hours | Status |

### TIER 2: HIGH
...

## Session Log
| Date | Work Done | Next |
```

## Reference

See `planning/multi-agent-research-protocol.md` for full patterns.

## Key Discovery

**No practical agent limit** - 68 agents ran successfully in parallel. Token usage is the constraint, not count.
