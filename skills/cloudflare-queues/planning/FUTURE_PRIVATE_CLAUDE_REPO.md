# Future Task: Private Repo for ~/.claude Folder

**Created**: 2026-01-03
**Status**: Proposed
**Priority**: Low (when time permits)

---

## The Idea

Create a separate **private** git repository to version control the contents of `~/.claude/` folder, specifically:

- `~/.claude/rules/*.md` - User-level correction rules
- `~/.claude/settings.json` - Global settings
- `~/.claude/CLAUDE.md` - Global instructions

## Why Private (Not Public)

Per user preference: These rules represent "special secret sauce IP" - accumulated knowledge and corrections that give a competitive advantage. Unlike the open-source `claude-skills` repo, these are personal productivity enhancements.

## Current State

- **Backup exists**: User has a backup of these files
- **Not version controlled**: Currently just local files
- **49 user-level rules**: As of Jan 2026 audit

## Implementation Approach

### Option 1: Simple Private Repo

```bash
# Create private repo
gh repo create jezweb/claude-config --private

# Clone and set up
cd ~/.claude
git init
git remote add origin git@github.com:jezweb/claude-config.git

# Create .gitignore for sensitive items
cat > .gitignore << 'EOF'
# Exclude any API keys or secrets
*.key
*.secret
auth-keys.txt

# Exclude cache/temp
.cache/
*.log

# Exclude plans (ephemeral)
plans/
EOF

# Initial commit
git add .
git commit -m "Initial commit: Claude config and rules"
git push -u origin main
```

### Option 2: Git Bare Repo with Dotfiles Pattern

Use the popular "dotfiles" pattern with a bare git repo:

```bash
# Initialize bare repo
git init --bare $HOME/.claude-repo

# Create alias
alias claude-config='git --git-dir=$HOME/.claude-repo --work-tree=$HOME/.claude'

# Set up
claude-config config --local status.showUntrackedFiles no
claude-config remote add origin git@github.com:jezweb/claude-config.git

# Use normally
claude-config add rules/
claude-config commit -m "Update rules"
claude-config push
```

### Option 3: Symlink from Private Repo

Keep repo elsewhere, symlink to ~/.claude:

```bash
# Repo lives in Documents
gh repo create jezweb/claude-config --private --clone
cd ~/Documents/claude-config

# Create structure
mkdir -p rules
cp ~/.claude/rules/*.md rules/
cp ~/.claude/CLAUDE.md .
cp ~/.claude/settings.json .

# Replace ~/.claude with symlink or symlink individual dirs
ln -sf ~/Documents/claude-config/rules ~/.claude/rules
```

## Considerations

| Aspect | Notes |
|--------|-------|
| **Sync across machines** | Git pull on each machine |
| **Sensitive data** | Ensure no API keys in rules files |
| **Conflicts with skills** | Rules are separate from skills (different concerns) |
| **Backup redundancy** | Git provides history + remote backup |

## What to Include

**Include:**
- `rules/*.md` - All correction rules
- `CLAUDE.md` - Global instructions
- `settings.json` - Preferences (if not sensitive)
- `commands/*.md` - Custom slash commands (if any outside skills)

**Exclude:**
- `skills/` - These are symlinks to public repo
- `plans/` - Ephemeral working files
- Any files with API keys or secrets
- `.cache/` or temp files

## Relationship to claude-skills Repo

```
~/.claude/
├── skills/           → Symlinks to public jezweb/claude-skills
├── rules/            → Private repo (jezweb/claude-config)
├── commands/         → Could be either (currently in public)
├── CLAUDE.md         → Private repo
└── settings.json     → Private repo
```

## Action Items (When Ready)

1. [ ] Decide on implementation approach (Option 1 recommended for simplicity)
2. [ ] Audit rules for any sensitive content before pushing
3. [ ] Create private GitHub repo
4. [ ] Set up git tracking
5. [ ] Document sync workflow for multiple machines
6. [ ] Update main CLAUDE.md to reference this setup

---

**Note**: This is a future enhancement, not urgent. Current backup is sufficient for now.
