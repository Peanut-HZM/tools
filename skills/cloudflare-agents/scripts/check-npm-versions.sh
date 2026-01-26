#!/usr/bin/env bash

# check-npm-versions.sh - Check if npm dependencies are up-to-date
# Usage: ./scripts/check-npm-versions.sh [skill-name] [--markdown REPORT_FILE]
#
# If skill-name is provided, checks that skill only
# Otherwise, checks all skills
#
# Options:
#   --markdown FILE   Append results to markdown report file
#
# Exit code: Always 0 (info only, no failures)

# Don't use set -e - we want to always exit 0
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"

# Global counters
TOTAL_PACKAGES=0
UP_TO_DATE=0
MINOR_UPDATES=0
MAJOR_UPDATES=0
ERRORS=0

# Markdown report file (optional)
MARKDOWN_REPORT=""

# Parse arguments
SKILL_NAME=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --markdown)
            MARKDOWN_REPORT="$2"
            shift 2
            ;;
        *)
            SKILL_NAME="$1"
            shift
            ;;
    esac
done

# Function to compare semantic versions
# Returns: 0=same, 1=patch, 2=minor, 3=major
compare_versions() {
    local current="$1"
    local latest="$2"

    # Extract major.minor.patch
    if [[ $current =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        local curr_major="${BASH_REMATCH[1]}"
        local curr_minor="${BASH_REMATCH[2]}"
        local curr_patch="${BASH_REMATCH[3]}"
    else
        echo "0"
        return
    fi

    if [[ $latest =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        local latest_major="${BASH_REMATCH[1]}"
        local latest_minor="${BASH_REMATCH[2]}"
        local latest_patch="${BASH_REMATCH[3]}"
    else
        echo "0"
        return
    fi

    # Compare
    if [ "$curr_major" != "$latest_major" ]; then
        echo "3"  # Major version difference
    elif [ "$curr_minor" != "$latest_minor" ]; then
        echo "2"  # Minor version difference
    elif [ "$curr_patch" != "$latest_patch" ]; then
        echo "1"  # Patch version difference
    else
        echo "0"  # Same version
    fi
}

# Function to append to markdown report
append_to_markdown() {
    local text="$1"
    if [ -n "$MARKDOWN_REPORT" ]; then
        echo "$text" >> "$MARKDOWN_REPORT"
    fi
}

# Function to check a single package.json file
check_package_json() {
    local file="$1"
    local skill_name="$2"
    local skill_warnings=0
    local skill_breaking=0

    echo -e "${BLUE}Checking: $skill_name${NC}"

    # Start markdown section for this skill
    if [ -n "$MARKDOWN_REPORT" ]; then
        append_to_markdown ""
        append_to_markdown "### $skill_name"
        append_to_markdown ""
        append_to_markdown "| Package | Current | Latest | Status |"
        append_to_markdown "|---------|---------|--------|--------|"
    fi

    # Extract dependencies
    local deps=$(cat "$file" | grep -A 999 '"dependencies"' | grep -B 999 '}' | head -n -1 | tail -n +2 || true)
    local devDeps=$(cat "$file" | grep -A 999 '"devDependencies"' | grep -B 999 '}' | head -n -1 | tail -n +2 || true)

    # Combine all deps
    local all_deps="$deps"$'\n'"$devDeps"

    # Check each dependency
    while IFS= read -r line; do
        if [[ $line =~ \"([^\"]+)\":[[:space:]]*\"([^^~]*)([0-9]+\.[0-9]+\.[0-9]+) ]]; then
            local pkg="${BASH_REMATCH[1]}"
            local current="${BASH_REMATCH[3]}"

            # Skip @types and internal packages
            if [[ $pkg == @types/* ]] || [[ $pkg == file:* ]]; then
                continue
            fi

            ((TOTAL_PACKAGES++))

            # Get latest version from npm (with timeout)
            local latest=$(timeout 5 npm view "$pkg" version 2>/dev/null || echo "error")

            if [ "$latest" == "error" ]; then
                echo -e "  ${YELLOW}⚠${NC}  $pkg@$current (couldn't fetch latest)"
                append_to_markdown "| $pkg | $current | _error_ | ⚠️ Could not fetch |"
                ((ERRORS++))
                continue
            fi

            # Compare versions
            local diff=$(compare_versions "$current" "$latest")

            case $diff in
                0)
                    echo -e "  ${GREEN}✅${NC} $pkg@$current (up-to-date)"
                    append_to_markdown "| $pkg | $current | $latest | ✅ Up-to-date |"
                    ((UP_TO_DATE++))
                    ;;
                1)
                    echo -e "  ${YELLOW}⚠${NC}  $pkg@$current → $latest available (patch)"
                    append_to_markdown "| $pkg | $current | $latest | ⚠️ Patch update |"
                    ((MINOR_UPDATES++))
                    ((skill_warnings++))
                    ;;
                2)
                    echo -e "  ${YELLOW}⚠${NC}  $pkg@$current → $latest available (minor)"
                    append_to_markdown "| $pkg | $current | $latest | ⚠️ Minor update |"
                    ((MINOR_UPDATES++))
                    ((skill_warnings++))
                    ;;
                3)
                    echo -e "  ${RED}❌${NC} $pkg@$current → $latest available (MAJOR - BREAKING)"
                    append_to_markdown "| $pkg | $current | $latest | ❌ **MAJOR** (breaking) |"
                    ((MAJOR_UPDATES++))
                    ((skill_breaking++))
                    ((skill_warnings++))
                    ;;
            esac
        fi
    done <<< "$all_deps"

    # Skill summary
    if [ $skill_warnings -eq 0 ]; then
        echo -e "${GREEN}  All dependencies up-to-date!${NC}"
    else
        if [ $skill_breaking -gt 0 ]; then
            echo -e "${RED}  $skill_breaking breaking update(s), $skill_warnings total update(s) available${NC}"
        else
            echo -e "${YELLOW}  $skill_warnings update(s) available${NC}"
        fi
    fi

    echo ""
    return 0
}

# Initialize markdown report if specified
if [ -n "$MARKDOWN_REPORT" ]; then
    # Clear existing file or create new
    echo "## NPM Packages" > "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
    echo "**Checked**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
fi

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  NPM Version Checker${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check if specific skill provided
if [ -n "$SKILL_NAME" ]; then
    SKILL_DIR="$SKILLS_DIR/$SKILL_NAME"

    if [ ! -d "$SKILL_DIR" ]; then
        echo -e "${RED}Error: Skill '$SKILL_NAME' not found${NC}"
        echo ""
        echo "Available skills:"
        ls -1 "$SKILLS_DIR" 2>/dev/null || echo "  (none found)"
        exit 0  # Still exit 0 (info only)
    fi

    # Check for package.json in templates
    if [ -f "$SKILL_DIR/templates/package.json" ]; then
        check_package_json "$SKILL_DIR/templates/package.json" "$SKILL_NAME"
    elif [ -f "$SKILL_DIR/package.json" ]; then
        check_package_json "$SKILL_DIR/package.json" "$SKILL_NAME"
    else
        echo -e "${YELLOW}No package.json found for $SKILL_NAME${NC}"
        echo ""
    fi

    exit 0
fi

# Check all skills
TOTAL_SKILLS=0
SKILLS_WITH_DEPS=0

for skill_dir in "$SKILLS_DIR"/*/ ; do
    if [ ! -d "$skill_dir" ]; then
        continue
    fi

    skill_name=$(basename "$skill_dir")
    ((TOTAL_SKILLS++))

    # Look for package.json in templates/ or root
    if [ -f "$skill_dir/templates/package.json" ]; then
        check_package_json "$skill_dir/templates/package.json" "$skill_name"
        ((SKILLS_WITH_DEPS++))
    elif [ -f "$skill_dir/package.json" ]; then
        check_package_json "$skill_dir/package.json" "$skill_name"
        ((SKILLS_WITH_DEPS++))
    fi
done

# Append summary to markdown
if [ -n "$MARKDOWN_REPORT" ]; then
    append_to_markdown ""
    append_to_markdown "---"
    append_to_markdown ""
    append_to_markdown "### NPM Summary"
    append_to_markdown ""
    append_to_markdown "- **Total Packages**: $TOTAL_PACKAGES"
    append_to_markdown "- ✅ **Up-to-date**: $UP_TO_DATE"
    append_to_markdown "- ⚠️ **Minor/Patch Updates**: $MINOR_UPDATES"
    append_to_markdown "- ❌ **Major Updates (Breaking)**: $MAJOR_UPDATES"
    append_to_markdown "- ⚠️ **Errors**: $ERRORS"
    append_to_markdown ""
fi

# Terminal summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Total skills: $TOTAL_SKILLS"
echo "Skills with dependencies: $SKILLS_WITH_DEPS"
echo "Total packages checked: $TOTAL_PACKAGES"
echo ""
echo -e "${GREEN}✅${NC} Up-to-date: $UP_TO_DATE"
echo -e "${YELLOW}⚠${NC}  Minor/Patch updates: $MINOR_UPDATES"
echo -e "${RED}❌${NC} Major updates (breaking): $MAJOR_UPDATES"
if [ $ERRORS -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  Errors fetching: $ERRORS"
fi
echo ""

if [ $MAJOR_UPDATES -gt 0 ]; then
    echo -e "${RED}⚠${NC}  WARNING: $MAJOR_UPDATES major version update(s) detected!"
    echo "  Review breaking changes before updating."
    echo ""
fi

if [ -n "$MARKDOWN_REPORT" ]; then
    echo -e "${GREEN}ℹ${NC}  Markdown report written to: $MARKDOWN_REPORT"
    echo ""
fi

echo -e "${GREEN}ℹ${NC}  This is informational only - no automatic updates performed"
echo -e "${GREEN}ℹ${NC}  Review warnings and update skills manually as needed"
echo ""

# Always exit 0 (informational only, never fail builds)
exit 0
