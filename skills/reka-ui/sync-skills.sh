#!/bin/bash
# Sync skills from dev repo to ~/.claude/skills/
rsync -av --delete skills/ ~/.claude/skills/ --exclude="versions.json"
echo "✓ Skills synced to ~/.claude/skills/"
