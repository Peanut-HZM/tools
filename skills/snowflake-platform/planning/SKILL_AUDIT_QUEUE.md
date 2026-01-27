# Skill Audit Queue

**Created**: 2026-01-06
**Purpose**: Track systematic deep-dive audits of all 69 skills
**Method**: One skill at a time using full SKILL_AUDIT_PROTOCOL.md process

---

## How to Audit a Skill

```
/review-skill <skill-name>
```

Or say: "Deep audit the <skill-name> skill using the full protocol"

This triggers the 6-phase verification process from `planning/SKILL_AUDIT_PROTOCOL.md`.

---

## Priority Tiers

### Tier 1: High-Traffic Skills (Audit First)
Core skills used in most projects - errors here have wide impact.

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| cloudflare-worker-base | 2026-01-06 | ✓ | ✅ |
| tailwind-v4-shadcn | 2026-01-06 | ✓ | ✅ |
| ai-sdk-core | 2026-01-06 | ✓ | ✅ |
| drizzle-orm-d1 | 2026-01-06 | ✓ | ✅ |
| hono-routing | 2026-01-06 | ✓ | ✅ |
| clerk-auth | 2026-01-06 | ✓ | ✅ |
| better-auth | 2026-01-06 | ✓ | ✅ |

### Tier 2: AI/ML Skills (High Churn)
AI SDKs change frequently - prone to training cutoff issues.

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| openai-api | 2026-01-09 | ✓ | ✅ |
| openai-agents | 2026-01-09 | ✓ | ✅ |
| openai-assistants | 2026-01-09 | ✓ | ✅ |
| openai-responses | 2026-01-09 | ✓ | ✅ |
| claude-api | 2026-01-09 | ✓ | ✅ |
| claude-agent-sdk | 2026-01-09 | ✓ | ✅ |
| google-gemini-api | 2026-01-09 | ✓ | ✅ |
| google-gemini-embeddings | 2026-01-09 | ✓ | ✅ |
| ai-sdk-ui | 2026-01-09 | ✓ | ✅ |

### Tier 3: Cloudflare Platform (Stable but Complex)
Cloudflare products - generally stable but intricate.

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| cloudflare-d1 | 2026-01-09 | ✓ | ✅ |
| cloudflare-r2 | 2026-01-09 | ✓ | ✅ |
| cloudflare-kv | 2026-01-09 | ✓ | ✅ |
| cloudflare-workers-ai | 2026-01-09 | ✓ | ✅ |
| cloudflare-vectorize | 2026-01-09 | ✓ | ✅ |
| cloudflare-durable-objects | 2026-01-09 | ✓ | ✅ |
| cloudflare-queues | 2026-01-09 | ✓ | ✅ |
| cloudflare-workflows | 2026-01-09 | ✓ | ✅ |
| cloudflare-agents | 2026-01-09 | ✓ | ✅ |
| cloudflare-browser-rendering | 2026-01-09 | ✓ | ✅ |
| cloudflare-mcp-server | 2026-01-09 | ✓ | ✅ |
| cloudflare-turnstile | 2026-01-09 | ✓ | ✅ |
| cloudflare-hyperdrive | 2026-01-09 | ✓ | ✅ |
| cloudflare-images | 2026-01-09 | ✓ | ✅ |
| cloudflare-python-workers | 2026-01-09 | ✓ | ✅ |

### Tier 4: Frontend/UI Skills
React ecosystem - moderate churn.

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| tanstack-query | 2026-01-09 | ✓ | ✅ |
| tanstack-router | 2026-01-09 | ✓ | ✅ |
| tanstack-table | 2026-01-09 | ✓ | ✅ |
| tanstack-start | 2026-01-09 | ✓ | ✅ |
| zustand-state-management | 2026-01-09 | ✓ | ✅ |
| react-hook-form-zod | 2026-01-09 | ✓ | ✅ |
| tiptap | 2026-01-09 | ✓ | ✅ |
| motion | 2026-01-09 | ✓ | ✅ |
| auto-animate | 2026-01-09 | ✓ | ✅ |
| nextjs | 2026-01-09 | ✓ | ✅ |

### Tier 5: MCP/Tooling Skills
MCP is new - high likelihood of issues.

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| typescript-mcp | 2026-01-09 | ✓ | ✅ |
| fastmcp | 2026-01-09 | ✓ | ✅ |
| mcp-oauth-cloudflare | 2026-01-09 | ✓ | ✅ |
| ts-agent-sdk | 2026-01-09 | ⬜ | ✅ |
| mcp-cli-scripts | 2026-01-09 | ⬜ | ✅ |

### Tier 6: Vercel/Database Skills

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| vercel-blob | 2026-01-09 | ⬜ | ✅ |
| vercel-kv | 2026-01-09 | ⬜ | ✅ |
| neon-vercel-postgres | 2026-01-09 | ⬜ | ✅ |

### Tier 7: Content/CMS Skills

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| tinacms | 2026-01-09 | ⬜ | ✅ |
| sveltia-cms | 2026-01-09 | ⬜ | ✅ |

### Tier 8: Google Workspace Skills

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| google-workspace | 2026-01-09 | ✓ | ✅ |
| google-chat-api | 2026-01-09 | ⬜ | ✅ |
| google-spaces-updates | 2026-01-09 | ⬜ | ✅ |
| google-gemini-file-search | 2026-01-09 | ⬜ | ✅ |

### Tier 9: Other/Utility Skills

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| azure-auth | 2026-01-09 | ✓ | ✅ |
| elevenlabs-agents | 2026-01-09 | ⬜ | ✅ |
| wordpress-plugin-core | 2026-01-09 | ⬜ | ✅ |
| fastapi | 2026-01-09 | ⬜ | ✅ |
| flask | 2026-01-09 | ⬜ | ✅ |
| react-native-expo | 2026-01-09 | ⬜ | ✅ |
| streamlit-snowflake | 2026-01-09 | ⬜ | ✅ |
| openai-apps-mcp | 2026-01-09 | ⬜ | ✅ |
| thesys-generative-ui | 2026-01-09 | ✓ | ⏭️ |

### Tier 10: Internal/Meta Skills

| Skill | Last Audit | Has Rules | Status |
|-------|------------|-----------|--------|
| skill-review | 2026-01-09 | ⬜ | ✅ |
| skill-creator | 2026-01-09 | ⬜ | ✅ |
| project-planning | 2026-01-09 | ⬜ | ✅ |
| project-workflow | 2026-01-09 | ⬜ | ✅ |
| project-session-management | 2026-01-09 | ⬜ | ✅ |
| open-source-contributions | 2026-01-09 | ⬜ | ✅ |

---

## Audit Workflow

### Quick Start (5 min per skill)

1. Say: `/review-skill <skill-name>`
2. Review findings
3. Approve/modify fixes
4. Mark status: ⬜ → ✅

### Full Audit (15-30 min per skill)

1. **Extract**: Read SKILL.md, note all packages/versions
2. **Verify**: `npm view <package> version` for each
3. **Research**: Check GitHub releases, changelogs
4. **Compare**: Skill claims vs verified facts
5. **Fix**: Update versions, add rules if needed
6. **Commit**: One commit per skill

---

## Progress Tracking

Update this file as you complete audits:
- ⬜ = Not started
- 🔄 = In progress
- ✅ = Complete
- ⏭️ = Skipped (low priority)

**Goal**: Complete Tier 1-3 this week, rest over following weeks.

---

## Session Pattern

Each session:
1. Pick 2-3 skills from current tier
2. Run `/review-skill` for each
3. Apply fixes
4. Commit with: `audit(<skill>): <summary>`
5. Update this queue

---

**Last Updated**: 2026-01-06
