# Skill Audit Protocol

**Purpose**: Systematic deep-dive into official documentation to identify gaps, outdated patterns, and missing features in skills.

**Last Updated**: 2026-01-03
**Recommended Frequency**: Quarterly, or after major version releases
**Related**: See `multi-agent-research-protocol.md` for general parallel agent patterns

---

## When to Run Audits

| Trigger | Scope |
|---------|-------|
| **Quarterly Review** | All skills (batch by priority) |
| **Major Version Release** | Affected skill only (e.g., AI SDK v6, TanStack Query v5) |
| **User Report** | Specific skill flagged as outdated |
| **New Framework Feature** | Skills that integrate with it |

---

## Audit Process

### Step 1: Prioritize Skills

Run version checker first to identify outdated packages:

```bash
./scripts/check-all-versions.sh
```

Review `VERSIONS_REPORT.md` and prioritize:
1. **Critical**: Major version behind, breaking changes likely
2. **High**: Minor version behind, new features available
3. **Medium**: Patch version behind, mostly fixes
4. **Low**: Up to date, periodic review only

### Step 2: Launch Parallel Sub-Agents

Use Task tool with `subagent_type: "Explore"` to research multiple skills simultaneously:

```
Task: Deep dive documentation audit for [skill-name]

Research the official [framework] documentation thoroughly:
1. Read our current skill: skills/[skill-name]/SKILL.md
2. Fetch and analyze official docs (main features, guides, API reference)
3. Check changelog/release notes for recent changes
4. Identify:
   - NEW features not in our skill
   - DEPRECATED patterns we still recommend
   - BREAKING CHANGES we don't document
   - MISSING patterns (common use cases)
   - VERSION updates needed

Create a structured report with:
- Feature gaps table (feature | description | priority)
- Breaking changes table
- Recommended additions (HIGH/MEDIUM/LOW priority)
- Package version updates needed

Focus on: What would a developer need that we don't provide?
```

**Parallel Execution**: Launch ALL agents simultaneously in a single message. No practical limit - 68 agents ran successfully in Jan 2026 audit. Each agent takes 2-5 minutes. See `planning/multi-agent-research-protocol.md` for full patterns.

### Step 3: Compile Findings

After all agents complete, consolidate into priority matrix:

| Skill | Critical | High | Medium | Low |
|-------|----------|------|--------|-----|
| skill-a | X | X | X | X |
| skill-b | X | X | X | X |

### Step 4: Update Skills

Work through skills in priority order:
1. **Critical** items first (breaking changes, deprecated patterns)
2. **High** items next (new major features)
3. **Medium** items if time permits
4. **Low** items can wait for next audit

### Step 5: Document Changes

For each skill updated:
1. Update version in SKILL.md metadata
2. Add new sections/patterns
3. Update README.md keywords if needed
4. Regenerate marketplace manifest: `./scripts/generate-plugin-manifests.sh`
5. Commit with descriptive message

---

## Sub-Agent Prompt Template

```
Deep dive documentation audit for [SKILL_NAME]

## Instructions

1. Read our current skill file: skills/[SKILL_NAME]/SKILL.md
2. Fetch official documentation:
   - Main docs: [PRIMARY_DOCS_URL]
   - API reference: [API_DOCS_URL]
   - Changelog: [CHANGELOG_URL]
3. Compare what we document vs what's available
4. Identify gaps, outdated patterns, missing features

## Output Format

### NEW FEATURES Not in Our Skill
| Feature | Description | Priority |
|---------|-------------|----------|
| ... | ... | HIGH/MEDIUM/LOW |

### DEPRECATED Patterns We Still Document
| Pattern | Replacement | Notes |
|---------|-------------|-------|
| ... | ... | ... |

### BREAKING CHANGES We Don't Cover
| Change | Impact | Notes |
|--------|--------|-------|
| ... | ... | ... |

### MISSING Patterns
| Pattern | Use Case | Priority |
|---------|----------|----------|
| ... | ... | HIGH/MEDIUM/LOW |

### VERSION Updates Needed
| Package | Current | Latest |
|---------|---------|--------|
| ... | ... | ... |

### RECOMMENDATIONS
1. HIGH: [what to add immediately]
2. MEDIUM: [what to add soon]
3. LOW: [nice to have]
```

---

## Documentation URLs by Skill

Keep this list updated for quick reference:

| Skill | Primary Docs | Changelog |
|-------|--------------|-----------|
| ai-sdk-core | https://ai-sdk.dev/docs | https://ai-sdk.dev/changelog |
| ai-sdk-ui | https://ai-sdk.dev/docs/ai-sdk-ui | https://ai-sdk.dev/changelog |
| better-auth | https://www.better-auth.com/docs | https://github.com/better-auth/better-auth/releases |
| clerk-auth | https://clerk.com/docs | https://clerk.com/changelog |
| cloudflare-worker-base | https://developers.cloudflare.com/workers | https://github.com/cloudflare/workers-sdk/releases |
| cloudflare-d1 | https://developers.cloudflare.com/d1 | https://developers.cloudflare.com/d1/changelog |
| drizzle-orm-d1 | https://orm.drizzle.team/docs | https://github.com/drizzle-team/drizzle-orm/releases |
| hono-routing | https://hono.dev/docs | https://github.com/honojs/hono/releases |
| openai-api | https://platform.openai.com/docs | https://platform.openai.com/docs/changelog |
| tanstack-query | https://tanstack.com/query/latest/docs | https://github.com/TanStack/query/releases |
| tailwind-v4-shadcn | https://tailwindcss.com/docs | https://github.com/tailwindlabs/tailwindcss/releases |

---

## Audit History

Track completed audits here:

| Date | Skills Audited | Findings | Updates Made |
|------|----------------|----------|--------------|
| 2026-01-03 | ai-sdk, clerk, tanstack-query, drizzle, hono, openai | AI SDK v6 breaking changes, Clerk API Keys beta, TanStack v5 hooks | Pending |
| 2026-01-03 | better-auth | 8 plugins, rate limiting, session caching, Expo | v5.0.0 released |

---

## Automation Ideas

### Future: Scheduled Audit Script

```bash
#!/bin/bash
# scripts/audit-skills.sh - Run quarterly

# 1. Check versions
./scripts/check-all-versions.sh

# 2. Parse VERSIONS_REPORT.md for outdated skills
# 3. Generate audit prompts
# 4. (Manual) Run sub-agents in Claude Code
# 5. (Manual) Update skills based on findings
```

### Future: Changelog Monitoring

Consider setting up GitHub Actions or RSS monitoring for:
- Major releases of tracked packages
- Breaking change announcements
- Deprecation notices

---

## Quality Checklist

After updating a skill from audit findings:

- [ ] All HIGH priority gaps addressed
- [ ] Breaking changes documented with migration path
- [ ] Deprecated patterns removed or marked deprecated
- [ ] Version numbers updated in SKILL.md
- [ ] README.md keywords updated
- [ ] Marketplace manifest regenerated
- [ ] Commit message references audit findings
