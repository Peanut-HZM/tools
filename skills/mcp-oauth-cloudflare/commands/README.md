# Claude Code Slash Commands

This directory contains **orphan commands** - specialized commands for managing the claude-skills repository itself. These are niche tools not needed by most users.

## Plugin System (2026-01-11)

Commands are accessed via the plugin system with namespaced format:

```
/bundle-name:command-name
```

### Bundle → Command Examples

| Bundle | Command | Access |
|--------|---------|--------|
| `project` | plan-feature | `/project:plan-feature` |
| `project` | docs-init | `/project:docs-init` |
| `cloudflare` | deploy | `/cloudflare:deploy` |
| `frontend` | setup | `/frontend:setup` |
| `auth` | setup | `/auth:setup` |
| `database` | init | `/database:init` |
| `mcp` | init | `/mcp:init` |

### Installing Bundles

```bash
# Add marketplace (one-time)
/plugin marketplace add jezweb/claude-skills

# Install bundles you need
/plugin install project      # Most-used: plan-feature, docs-init, etc.
/plugin install cloudflare   # Cloudflare Workers development
/plugin install ai           # AI/LLM integration
/plugin install frontend     # UI development
/plugin install auth         # Authentication
/plugin install database     # Database/storage
/plugin install mcp          # MCP server development
/plugin install cms          # Content management
/plugin install backend      # Python backends
/plugin install contrib      # Skill/open-source development
```

## Orphan Commands (This Directory)

These commands are specific to the claude-skills repository and not bundled with any plugin:

### `/create-skill`

**Purpose**: Scaffold a new Claude Code skill from template

**Usage**: `/create-skill my-skill-name`

**What it does**:
1. Validates skill name (lowercase-hyphen-case, max 40 chars)
2. Asks about skill type (Cloudflare/AI/Frontend/Auth/Database/Tooling/Generic)
3. Copies `templates/skill-skeleton/` to `skills/<name>/`
4. Auto-populates name and dates in SKILL.md
5. Applies type-specific customizations
6. Creates README.md with auto-trigger keywords
7. Runs metadata check
8. Installs skill

**When to use**: Creating a new skill from scratch

---

### `/review-skill`

**Purpose**: Quality review and audit of an existing skill

**Usage**: `/review-skill skill-name`

**What it does**:
1. Checks SKILL.md structure and metadata
2. Validates package versions against latest
3. Reviews error documentation
4. Checks template completeness
5. Suggests improvements

**When to use**: Before publishing a skill update

---

### `/audit`

**Purpose**: Multi-agent audit swarm for parallel skill verification

**Usage**: `/audit` or `/audit skill-name`

**What it does**:
1. Launches parallel agents to audit multiple skills
2. Checks versions, metadata, content quality
3. Generates consolidated report

**When to use**: Quarterly maintenance, bulk skill auditing

---

### `/deep-audit`

**Purpose**: Deep content validation against official documentation

**Usage**: `/deep-audit skill-name`

**What it does**:
1. Fetches official documentation for the skill's technology
2. Compares patterns and versions
3. Identifies knowledge gaps or outdated content
4. Suggests corrections and updates

**When to use**: Major version updates, accuracy verification

---

## Installation (Orphan Commands Only)

For orphan commands, copy to your `.claude/commands/` directory:

```bash
cp commands/create-skill.md ~/.claude/commands/
cp commands/review-skill.md ~/.claude/commands/
cp commands/audit.md ~/.claude/commands/
cp commands/deep-audit.md ~/.claude/commands/
```

## Related Bundles

| Bundle | Description | Commands |
|--------|-------------|----------|
| `project` | Project lifecycle management | 13 commands (plan-feature, docs-init, etc.) |
| `cloudflare` | Cloudflare platform | 3 commands (deploy, init, mcp-init) |
| `frontend` | UI development | 2 commands (setup, init) |
| `auth` | Authentication | 2 commands (setup) |
| `database` | Database/storage | 1 command (init) |
| `mcp` | MCP server development | 1 command (init) |

---

**Version**: 7.0.0
**Last Updated**: 2026-01-11
**Author**: Jeremy Dawes | Jezweb
