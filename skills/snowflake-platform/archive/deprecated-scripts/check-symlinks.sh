#!/bin/bash

# check-symlinks.sh - Verify and maintain ~/.claude/skills/ symlinks
# Usage: ./scripts/check-symlinks.sh [--fix]

set -e

SKILLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/skills"
SYMLINK_DIR="$HOME/.claude/skills"
FIX_MODE=false

# Parse arguments
if [[ "$1" == "--fix" ]]; then
    FIX_MODE=true
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 Checking symlinks in $SYMLINK_DIR..."
echo ""

# Create symlink directory if it doesn't exist
if [[ ! -d "$SYMLINK_DIR" ]]; then
    echo -e "${YELLOW}⚠️  Symlink directory doesn't exist: $SYMLINK_DIR${NC}"
    if [[ "$FIX_MODE" == true ]]; then
        mkdir -p "$SYMLINK_DIR"
        echo -e "${GREEN}✅ Created directory${NC}"
    else
        echo "   Run with --fix to create it"
        exit 1
    fi
fi

# Arrays to track issues
declare -a broken_symlinks=()
declare -a missing_symlinks=()
declare -a valid_symlinks=()

# Check for broken symlinks (symlinks that point to non-existent targets)
echo "🔗 Checking for broken symlinks..."
for link in "$SYMLINK_DIR"/*; do
    if [[ -L "$link" ]]; then
        if [[ ! -e "$link" ]]; then
            skill_name=$(basename "$link")
            broken_symlinks+=("$skill_name")
            echo -e "${RED}❌ Broken: $skill_name → $(readlink "$link")${NC}"
        else
            valid_symlinks+=("$(basename "$link")")
        fi
    fi
done

# Check for missing symlinks (skills that exist but aren't symlinked)
echo ""
echo "📁 Checking for missing symlinks..."
for skill_dir in "$SKILLS_DIR"/*; do
    if [[ -d "$skill_dir" && -f "$skill_dir/SKILL.md" ]]; then
        skill_name=$(basename "$skill_dir")
        symlink_path="$SYMLINK_DIR/$skill_name"

        if [[ ! -L "$symlink_path" ]]; then
            missing_symlinks+=("$skill_name")
            echo -e "${YELLOW}⚠️  Missing: $skill_name${NC}"
        elif [[ "$(readlink "$symlink_path")" != "$skill_dir" ]]; then
            echo -e "${YELLOW}⚠️  Wrong target: $skill_name${NC}"
            echo "   Current: $(readlink "$symlink_path")"
            echo "   Expected: $skill_dir"
            missing_symlinks+=("$skill_name (wrong target)")
        fi
    fi
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary:"
echo ""
echo -e "${GREEN}✅ Valid symlinks: ${#valid_symlinks[@]}${NC}"

if [[ ${#broken_symlinks[@]} -gt 0 ]]; then
    echo -e "${RED}❌ Broken symlinks: ${#broken_symlinks[@]}${NC}"
    for skill in "${broken_symlinks[@]}"; do
        echo "   - $skill"
    done
fi

if [[ ${#missing_symlinks[@]} -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Missing symlinks: ${#missing_symlinks[@]}${NC}"
    for skill in "${missing_symlinks[@]}"; do
        echo "   - $skill"
    done
fi

# Fix mode
if [[ "$FIX_MODE" == true ]]; then
    echo ""
    echo "🔧 Fixing issues..."

    # Remove broken symlinks
    if [[ ${#broken_symlinks[@]} -gt 0 ]]; then
        echo ""
        echo "Removing broken symlinks..."
        for skill in "${broken_symlinks[@]}"; do
            rm "$SYMLINK_DIR/$skill"
            echo -e "${GREEN}✅ Removed: $skill${NC}"
        done
    fi

    # Create missing symlinks
    if [[ ${#missing_symlinks[@]} -gt 0 ]]; then
        echo ""
        echo "Creating missing symlinks..."
        for skill_dir in "$SKILLS_DIR"/*; do
            if [[ -d "$skill_dir" && -f "$skill_dir/SKILL.md" ]]; then
                skill_name=$(basename "$skill_dir")
                symlink_path="$SYMLINK_DIR/$skill_name"

                # Remove wrong target symlink if exists
                if [[ -L "$symlink_path" && "$(readlink "$symlink_path")" != "$skill_dir" ]]; then
                    rm "$symlink_path"
                fi

                # Create symlink if missing
                if [[ ! -L "$symlink_path" ]]; then
                    ln -s "$skill_dir" "$symlink_path"
                    echo -e "${GREEN}✅ Created: $skill_name → $skill_dir${NC}"
                fi
            fi
        done
    fi

    echo ""
    echo -e "${GREEN}✅ All symlinks fixed!${NC}"
else
    # Report mode
    if [[ ${#broken_symlinks[@]} -gt 0 || ${#missing_symlinks[@]} -gt 0 ]]; then
        echo ""
        echo -e "${BLUE}💡 Run with --fix to repair automatically:${NC}"
        echo "   ./scripts/check-symlinks.sh --fix"
        exit 1
    else
        echo ""
        echo -e "${GREEN}✅ All symlinks are healthy!${NC}"
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
