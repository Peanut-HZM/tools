# Multi-Agent Research Protocol

**Purpose**: Patterns for launching parallel sub-agent swarms to research, audit, or gather context about large sets of items efficiently.

**Last Updated**: 2026-01-03
**Proven Scale**: 68 agents in parallel (skills audit), 9 agents (rules audit)

---

## When to Use Multi-Agent Research

| Use Case | Example | Agent Count |
|----------|---------|-------------|
| **Full Repository Audit** | Audit all 68 skills against official docs | 50-70 agents |
| **Category Audit** | Audit all Cloudflare skills (20 skills) | 15-25 agents |
| **Rules Audit** | Audit all 49 user-level rules | 8-12 agents (grouped) |
| **Documentation Research** | Research 10 frameworks for comparison | 10 agents |
| **Version Check** | Check latest versions across all dependencies | 10-20 agents |
| **Codebase Exploration** | Understand large unfamiliar codebase | 5-10 agents |

---

## Key Discoveries (From Jan 2026 Audit)

### Agent Limits

| Factor | Finding |
|--------|---------|
| **Hard cap** | None discovered - 68 agents ran successfully |
| **Practical limit** | Token usage, not agent count |
| **Optimal batch** | 8-12 agents per category for manageable output |
| **Agent type** | `subagent_type: "Explore"` for research tasks |

### Timing

| Phase | Duration |
|-------|----------|
| Agent launch | ~30 seconds for 68 parallel calls |
| Agent execution | 2-5 minutes each (varies by research depth) |
| Output retrieval | ~1 minute per agent (can batch) |
| Total (68 agents) | ~10-15 minutes end-to-end |

---

## The Pattern

### Step 1: Identify Items to Research

```bash
# Skills
ls skills/ | wc -l  # Count skills

# Rules
find ~/.claude/rules -name "*.md" | wc -l  # Count user rules
find skills -path "*/rules/*.md" | wc -l   # Count skill rules

# Any directory
find /path/to/items -type f -name "*.ext" | wc -l
```

### Step 2: Organize into Logical Batches

Group by domain/category for better agent prompts:

**Skills Example**:
```
Batch 1: AI/ML (ai-sdk-core, openai-api, claude-api, etc.) - 10 skills
Batch 2: Cloudflare Core (worker-base, d1, r2, kv) - 6 skills
Batch 3: Cloudflare Advanced (agents, workflows, queues) - 6 skills
Batch 4: Frontend (tailwind, react-hook-form, motion) - 5 skills
Batch 5: Auth (clerk, better-auth) - 3 skills
...
```

**Rules Example**:
```
Batch 1: Cloudflare (workers, deploy, ai-gateway) - 9 rules
Batch 2: OAuth (github, microsoft, mcp-oauth) - 6 rules
Batch 3: Snowflake (native-app, marketplace, streamlit) - 5 rules
Batch 4: Frontend (css-tailwind, react-patterns, lucide) - 5 rules
...
```

### Step 3: Create Agent Prompt Template

**For Audits (comparing against official docs)**:
```
Audit the [CATEGORY] [items]:
- [item1]
- [item2]
- [item3]

Check against official [FRAMEWORK] documentation for:
1. NEW features not documented
2. DEPRECATED patterns still recommended
3. BREAKING CHANGES not reflected
4. VERSION updates needed
5. Missing common patterns

Report: Accuracy %, gaps found, recommended updates with priority (HIGH/MEDIUM/LOW).
```

**For Research (gathering information)**:
```
Research [TOPIC] across these sources:
- [source1]
- [source2]

Gather:
1. Current best practices
2. Common patterns
3. Known issues/gotchas
4. Version-specific guidance
5. Integration points

Create structured summary with actionable recommendations.
```

**For Exploration (understanding existing code)**:
```
Explore [AREA] of the codebase:
- [file/directory1]
- [file/directory2]

Identify:
1. Architecture patterns used
2. Key dependencies
3. Entry points
4. Data flow
5. Potential issues

Return: Architecture summary, dependency graph, key files to understand.
```

### Step 4: Launch Parallel Agents

Use the Task tool with multiple invocations in a SINGLE message:

```
Task 1: subagent_type="Explore", prompt="[Batch 1 prompt]", description="Audit Batch 1"
Task 2: subagent_type="Explore", prompt="[Batch 2 prompt]", description="Audit Batch 2"
Task 3: subagent_type="Explore", prompt="[Batch 3 prompt]", description="Audit Batch 3"
... (all in one message)
```

**Critical**: All Task calls must be in the SAME message to run in parallel.

### Step 5: Wait and Retrieve Results

Agents run in background. When complete, system shows:
```
Task [id] (type: local_agent) (status: completed) (description: Audit Batch 1)
```

Use TaskOutput to retrieve:
```
TaskOutput: task_id="[agent-id]"
```

Or wait for all to complete naturally - results stream in as agents finish.

### Step 6: Compile and Track

Create a planning document to survive context compacts:

**Naming Convention**:
- `planning/SKILL_UPDATES_[MONTH]_[YEAR].md` - Skill audit findings
- `planning/RULES_UPDATES_[MONTH]_[YEAR].md` - Rules audit findings
- `planning/[TOPIC]_RESEARCH_[DATE].md` - General research

**Document Structure**:
```markdown
# [Topic] - [Date]

## Summary
- Total items: X
- Items needing updates: Y
- Estimated effort: Z hours

## Priority Tiers
### TIER 1: URGENT
| Item | Issue | Est Hours | Status |
|------|-------|-----------|--------|

### TIER 2: HIGH
...

## Already Current (No Updates)
- item1
- item2

## Session Log
| Date | Work Done | Next Steps |
|------|-----------|------------|

## Completion Criteria
- [ ] All TIER 1 complete
- [ ] All TIER 2 complete
```

---

## Batching Strategies

### Strategy 1: One Agent Per Item (Small Sets)
- Best for: <20 items
- Each agent gets ONE item to research deeply
- Maximum detail per item

### Strategy 2: Grouped by Category (Medium Sets)
- Best for: 20-100 items
- Group 5-10 related items per agent
- Good balance of depth and efficiency

### Strategy 3: All at Once (Large Sets)
- Best for: Known patterns, quick checks
- Launch one agent per item but with focused prompts
- "Check X against Y, report accuracy %"

---

## Output Consolidation Patterns

### Pattern 1: Accuracy Matrix
```markdown
| Category | Files | Accuracy | Priority |
|----------|-------|----------|----------|
| Auth | 2 | 70% | URGENT |
| Frontend | 5 | 92% | MEDIUM |
```

### Pattern 2: Gap Analysis
```markdown
| Item | Gap Type | Description | Est Hours |
|------|----------|-------------|-----------|
| clerk-auth | Breaking Change | API v1 deprecated | 1h |
```

### Pattern 3: Version Tracking
```markdown
| Package | Current | Latest | Skill |
|---------|---------|--------|-------|
| drizzle-orm | 0.44.7 | 0.45.1 | drizzle-orm-d1 |
```

---

## Real Examples from Jan 2026

### Skills Audit (68 agents)

**Launch Command Pattern**:
```
"Audit [skill-name] skill. Read skills/[name]/SKILL.md.
Check against official docs at [url].
Report: NEW features missing, DEPRECATED patterns, BREAKING changes,
VERSION updates. Provide accuracy % and priority recommendations."
```

**Results**:
- 68 agents launched in parallel
- All completed within 10 minutes
- Findings compiled into `planning/SKILL_UPDATES_JAN_2026.md`
- 36 skills identified for updates (~100 hours work)

### Rules Audit (9 agents, grouped)

**Grouping**:
- AI Gateway (2 rules) → 1 agent
- Cloudflare Workers (6 rules) → 1 agent
- OAuth (6 rules) → 1 agent
- Snowflake (5 rules) → 1 agent
- Frontend (5 rules) → 1 agent
- Database (4 rules) → 1 agent
- Auth (2 rules) → 1 agent
- Build/Tooling (6 rules) → 1 agent
- Misc (8 rules) → 1 agent

**Results**:
- 9 agents completed in ~5 minutes
- Findings compiled into `planning/RULES_UPDATES_JAN_2026.md`
- 18 rules identified for updates (~12 hours work)
- 25 rules confirmed 100% accurate

---

## Best Practices

### DO
- ✅ Launch all agents in ONE message (parallel execution)
- ✅ Group related items for coherent agent prompts
- ✅ Create persistent planning docs for multi-session work
- ✅ Include specific deliverables in prompts (accuracy %, tables)
- ✅ Use `subagent_type: "Explore"` for research tasks

### DON'T
- ❌ Launch agents one at a time (serial execution)
- ❌ Mix unrelated items in same agent prompt
- ❌ Forget to create tracking documents
- ❌ Use vague prompts ("check if this is current")
- ❌ Ignore agent outputs (compile them!)

---

## Template: Full Audit Prompt

```
Deep audit for [ITEM_NAME]

## Files to Analyze
- [file1]
- [file2]

## Official Documentation
- Primary: [URL]
- Changelog: [URL]

## Check For
1. NEW features in official docs not in our files
2. DEPRECATED patterns we still recommend
3. BREAKING CHANGES we don't document
4. VERSION updates needed (packages, APIs)
5. MISSING common patterns developers need

## Output Format

### Accuracy Score: X%

### Gaps Found
| Gap | Type | Priority | Est Hours |
|-----|------|----------|-----------|

### Recommendations
1. URGENT: ...
2. HIGH: ...
3. MEDIUM: ...

### Sources Consulted
- [url1]
- [url2]
```

---

## Maintenance

### When to Re-Audit
- Quarterly for all items
- After major framework releases
- After user reports of outdated content
- Before major project milestones

### Tracking Audit History

Add to each planning document:
```markdown
## Audit History
| Date | Items | Agents | Findings | Actions |
|------|-------|--------|----------|---------|
| 2026-01-03 | 68 skills | 68 | 36 updates | Pending |
| 2026-01-03 | 49 rules | 9 | 18 updates | Pending |
```

---

## Related Files

- `planning/skill-audit-protocol.md` - Skills-specific audit details
- `planning/SKILL_UPDATES_JAN_2026.md` - Current skill audit findings
- `planning/RULES_UPDATES_JAN_2026.md` - Current rules audit findings
- `scripts/check-all-versions.sh` - Automated version checking

