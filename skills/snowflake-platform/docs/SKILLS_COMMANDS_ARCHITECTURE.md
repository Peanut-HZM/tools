# Skills & Commands Architecture

**Last Updated**: 2026-01-10
**Claude Code Version**: v2.1.3+

This document describes the unified skills and commands architecture introduced in Claude Code v2.1.3.

---

## Overview

Claude Code v2.1.3 (January 10, 2026) unified the concepts of **commands** and **skills**:

- **Skills** can now be manually invoked like commands via `/skill-name`
- **Commands** can have auto-discovery keywords like skills
- Both share the same underlying infrastructure

This creates a spectrum from pure knowledge (auto-triggered) to explicit entry points (manually invoked).

---

## The Spectrum

| Type | Discovery | Invocation | Use Case |
|------|-----------|------------|----------|
| **Knowledge-only skill** | Auto (keywords) | Passive | Reference material, corrections |
| **Invocable skill** | Auto + Manual | `/skill-name` | Rich workflows with context |
| **Skill with commands** | Auto + Manual | `/skill-name/command` | Multiple entry points |
| **Standalone command** | Manual only | `/command` | Workflow automation |

---

## Making Skills Invocable

Add `user-invocable: true` to the YAML frontmatter:

```yaml
---
name: cloudflare-worker-base
description: |
  Set up Cloudflare Workers with Hono routing, Vite plugin, and Static Assets.
user-invocable: true
---
```

**Effect**: The skill appears in the `/` slash command menu and can be invoked with `/cloudflare-worker-base`.

**When to use**:
- Skills that scaffold projects or components
- Skills with clear "entry point" workflows
- Skills users might want to invoke directly

**When NOT to use**:
- Pure reference/knowledge skills (auto-discovery sufficient)
- Skills that only provide corrections or patterns

---

## Commands Inside Skills

Skills can contain a `commands/` directory for multiple entry points:

```
skills/cloudflare-worker-base/
├── SKILL.md              ← Knowledge (auto-triggered)
├── README.md             ← Discovery keywords
├── templates/            ← Resources
├── rules/                ← Correction rules
└── commands/             ← Entry points
    └── init.md           ← /cloudflare-worker-base/init
```

**Command format** (same as standalone commands):

```markdown
# Command Title

Brief description of what this command does.

---

## Your Task

Step-by-step instructions for Claude to follow when this command is invoked.

### 1. First Step
- Instructions...

### 2. Second Step
- Instructions...
```

---

## Best Practices

### When to Use Each Approach

| Scenario | Approach |
|----------|----------|
| Reference material, API docs | Knowledge-only skill |
| Project scaffolding | Invocable skill + init command |
| Multiple related workflows | Skill with commands directory |
| Standalone automation | Standalone command |
| Corrections for outdated patterns | Rules in skill (auto-triggered) |

### Naming Conventions

- **Skill names**: `technology-domain` (e.g., `cloudflare-worker-base`)
- **Command names**: Action verbs (e.g., `init`, `scaffold`, `migrate`)
- **Full invocation**: `/skill-name/command` (e.g., `/cloudflare-worker-base/init`)

### Directory Structure for Skill with Commands

```
skills/my-skill/
├── SKILL.md                 # Required: Core knowledge
├── README.md                # Required: Discovery keywords
├── templates/               # Optional: Starter files
├── references/              # Optional: Deep-dive docs
├── scripts/                 # Optional: Helper scripts
├── rules/                   # Optional: Correction rules
└── commands/                # Optional: Entry points
    ├── init.md              # /my-skill/init
    ├── migrate.md           # /my-skill/migrate
    └── setup.md             # /my-skill/setup
```

---

## Skills with Commands (Examples)

### project-workflow (Existing Pattern)

```
skills/project-workflow/
├── SKILL.md
├── README.md
└── commands/
    ├── wrap-session.md      # /project-workflow/wrap-session
    ├── continue-session.md  # /project-workflow/continue-session
    ├── plan-project.md      # /project-workflow/plan-project
    ├── plan-feature.md      # /project-workflow/plan-feature
    ├── explore-idea.md      # /project-workflow/explore-idea
    ├── release.md           # /project-workflow/release
    └── workflow.md          # /project-workflow/workflow
```

### cloudflare-worker-base (Prototype)

```
skills/cloudflare-worker-base/
├── SKILL.md                 # Core knowledge + user-invocable: true
├── README.md
├── templates/               # Project starter files
├── agents/                  # Companion agents
├── rules/                   # Correction rules
└── commands/
    └── init.md              # /cloudflare-worker-base/init
```

---

## Invocable Skills (Top 10)

These skills have `user-invocable: true` and can be invoked directly:

| Skill | Invocation | Purpose |
|-------|------------|---------|
| `cloudflare-worker-base` | `/cloudflare-worker-base` | Set up Workers + Hono + Vite |
| `tailwind-v4-shadcn` | `/tailwind-v4-shadcn` | Configure Tailwind v4 + shadcn |
| `drizzle-orm-d1` | `/drizzle-orm-d1` | Set up Drizzle with D1 |
| `cloudflare-d1` | `/cloudflare-d1` | D1 database operations |
| `clerk-auth` | `/clerk-auth` | Clerk authentication setup |
| `hono-routing` | `/hono-routing` | Hono API routing patterns |
| `ai-sdk-core` | `/ai-sdk-core` | Vercel AI SDK integration |
| `react-hook-form-zod` | `/react-hook-form-zod` | Form validation patterns |
| `typescript-mcp` | `/typescript-mcp` | MCP server development |
| `playwright-local` | `/playwright-local` | Browser automation |

---

## Migration Path

### Existing Standalone Commands

Commands in `~/.claude/commands/` or project `.claude/commands/` continue to work. They can optionally be moved into related skills for better organization.

### Adding Commands to Existing Skills

1. Create `commands/` directory inside the skill
2. Add markdown files following the command format
3. Optionally add `user-invocable: true` to SKILL.md frontmatter

### Deciding Whether to Add Commands

**Add commands when the skill**:
- Has distinct "entry point" workflows (init, migrate, scaffold)
- Could benefit from guided step-by-step execution
- Has multiple related but separate use cases

**Keep knowledge-only when the skill**:
- Primarily provides reference information
- Is auto-triggered contextually (corrections, patterns)
- Doesn't have distinct "start here" workflows

---

## Future Considerations

- **Command discovery**: Commands inside skills could have their own keywords
- **Command chaining**: `/skill/cmd1 | /skill/cmd2` workflows
- **Argument passing**: `/skill/init --name my-project`
- **Interactive commands**: Multi-step wizards with prompts

---

## References

- Claude Code v2.1.3 Changelog (January 10, 2026)
- Official Claude Code Skills Documentation: https://docs.claude.com/en/docs/claude-code/skills
- Agent Skills Spec: https://github.com/anthropics/skills/blob/main/agent_skills_spec.md
