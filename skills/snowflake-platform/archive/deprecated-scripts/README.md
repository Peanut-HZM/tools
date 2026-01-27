# Deprecated Scripts

These scripts were archived on 2026-01-10 as we migrated from symlink-based installation to the Claude Code plugin system.

## Why Deprecated

**Old approach**: Symlinks from `skills/*` → `~/.claude/skills/`
**New approach**: Use `/plugin install` and `/plugin marketplace` commands

The plugin system:
- Distributes agents alongside skills
- Handles caching and updates
- Works the same way end users would install
- Enables better dogfooding of our own skills

## Archived Scripts

| Script | Purpose | Replacement |
|--------|---------|-------------|
| `install-skill.sh` | Symlink single skill | `/plugin install ./skills/skill-name` |
| `install-all.sh` | Symlink all skills | `/plugin install cloudflare-skills@claude-skills` etc. |
| `check-symlinks.sh` | Verify/repair symlinks | Not needed with plugin system |

## New Installation

```bash
# Add marketplace
/plugin marketplace add jezweb/claude-skills

# Install plugin bundles
/plugin install cloudflare-skills
/plugin install ai-skills
/plugin install frontend-skills
# etc.

# For local development
/plugin install ./skills/cloudflare-worker-base
```

## If You Need These Scripts

These scripts still work if you prefer symlinks:

```bash
# Restore to scripts/
git mv archive/deprecated-scripts/install-skill.sh scripts/
git mv archive/deprecated-scripts/install-all.sh scripts/
git mv archive/deprecated-scripts/check-symlinks.sh scripts/
```
