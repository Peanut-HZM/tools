#!/usr/bin/env bash

# check-metadata.sh - Check YAML frontmatter metadata in skills
# Usage: ./scripts/check-metadata.sh [skill-name] [--markdown REPORT_FILE]
#
# Parses YAML frontmatter from SKILL.md files
# Validates package versions, checks last_verified dates
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
TOTAL_SKILLS_WITH_METADATA=0
STALE_VERIFICATIONS=0
PACKAGE_ISSUES=0

# Markdown report file (optional)
MARKDOWN_REPORT=""

# Stale threshold (days)
STALE_DAYS=90

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

# Function to append to markdown report
append_to_markdown() {
    local text="$1"
    if [ -n "$MARKDOWN_REPORT" ]; then
        echo "$text" >> "$MARKDOWN_REPORT"
    fi
}

# Function to calculate days since date
# Compatible with both GNU date and BSD date (macOS)
days_since() {
    local date_str="$1"
    local date_epoch
    local now_epoch=$(date +%s)

    # Try GNU date first (Linux)
    date_epoch=$(date -d "$date_str" +%s 2>/dev/null) || \
    # Try BSD date (macOS)
    date_epoch=$(date -j -f "%Y-%m-%d" "$date_str" +%s 2>/dev/null) || \
    date_epoch="0"

    if [ "$date_epoch" == "0" ]; then
        echo "-1"
        return
    fi

    local diff=$(( (now_epoch - date_epoch) / 86400 ))
    echo "$diff"
}

# Function to check a single skill's metadata
check_skill_metadata() {
    local skill_dir="$1"
    local skill_name="$2"
    local skill_file="$skill_dir/SKILL.md"

    if [ ! -f "$skill_file" ]; then
        return
    fi

    # Extract YAML frontmatter (between --- lines)
    local yaml_content=$(awk '/^---$/{flag=!flag;next}flag' "$skill_file")

    if [ -z "$yaml_content" ]; then
        return  # No frontmatter
    fi

    # Check if metadata section exists
    if ! echo "$yaml_content" | grep -q "metadata:"; then
        return  # No metadata
    fi

    ((TOTAL_SKILLS_WITH_METADATA++))

    echo -e "${BLUE}Checking: $skill_name${NC}"

    # Start markdown section for this skill
    if [ -n "$MARKDOWN_REPORT" ]; then
        append_to_markdown ""
        append_to_markdown "### $skill_name"
        append_to_markdown ""
    fi

    # Extract last_verified date (handle both quoted and unquoted)
    local last_verified=$(echo "$yaml_content" | grep -oP 'last_verified:\s*"\K[^"]+' || \
                          echo "$yaml_content" | grep -oP 'last_verified:\s*\K[0-9-]+' || echo "")

    if [ -n "$last_verified" ]; then
        local days=$(days_since "$last_verified")

        if [ "$days" -lt 0 ]; then
            echo -e "  ${YELLOW}⚠${NC}  last_verified: $last_verified (invalid date format)"
            append_to_markdown "- ⚠️ **last_verified**: $last_verified (invalid format)"
        elif [ "$days" -gt "$STALE_DAYS" ]; then
            echo -e "  ${YELLOW}⚠${NC}  last_verified: $last_verified ($days days ago - STALE)"
            append_to_markdown "- ⚠️ **last_verified**: $last_verified ($days days ago - **STALE**)"
            ((STALE_VERIFICATIONS++))
        else
            echo -e "  ${GREEN}✅${NC} last_verified: $last_verified ($days days ago)"
            append_to_markdown "- ✅ **last_verified**: $last_verified ($days days ago)"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC}  last_verified: not set"
        append_to_markdown "- ⚠️ **last_verified**: not set"
        ((STALE_VERIFICATIONS++))
    fi

    # Extract packages list
    local in_packages=false
    local packages=""

    while IFS= read -r line; do
        if [[ $line =~ packages: ]]; then
            in_packages=true
            continue
        fi

        if $in_packages; then
            if [[ $line =~ ^[[:space:]]*- ]]; then
                # Extract package line
                local pkg=$(echo "$line" | sed 's/^[[:space:]]*-[[:space:]]*//' | tr -d '"')
                packages="$packages$pkg"$'\n'
            else
                # End of packages section
                break
            fi
        fi
    done <<< "$yaml_content"

    if [ -n "$packages" ]; then
        echo -e "  ${BLUE}Packages listed in metadata:${NC}"
        append_to_markdown ""
        append_to_markdown "**Packages**:"
        append_to_markdown ""

        while IFS= read -r pkg; do
            if [ -z "$pkg" ]; then
                continue
            fi

            # Parse package@version format
            if [[ $pkg =~ ^(@?[a-zA-Z0-9@/_-]+)@([0-9.^~]+)$ ]]; then
                local pkg_name="${BASH_REMATCH[1]}"
                local pkg_version="${BASH_REMATCH[2]}"

                # Check if package exists on npm
                local latest=$(timeout 5 npm view "$pkg_name" version 2>/dev/null || echo "error")

                if [ "$latest" == "error" ]; then
                    echo -e "    ${YELLOW}⚠${NC}  $pkg (could not verify)"
                    append_to_markdown "- ⚠️ $pkg (could not verify)"
                else
                    echo -e "    ${GREEN}✅${NC} $pkg (verified)"
                    append_to_markdown "- ✅ $pkg"
                fi
            else
                echo -e "    ${YELLOW}⚠${NC}  $pkg (invalid format - use package@version)"
                append_to_markdown "- ⚠️ $pkg (invalid format)"
                ((PACKAGE_ISSUES++))
            fi
        done <<< "$packages"
    else
        echo -e "  ${YELLOW}⚠${NC}  No packages listed in metadata"
        append_to_markdown ""
        append_to_markdown "- ⚠️ No packages listed"
    fi

    # Check for breaking_changes field (handle both quoted and unquoted)
    local breaking_changes=$(echo "$yaml_content" | grep -oP 'breaking_changes:\s*"\K[^"]+' || \
                              echo "$yaml_content" | grep -oP 'breaking_changes:\s*\K.+$' || echo "")

    if [ -n "$breaking_changes" ]; then
        echo -e "  ${BLUE}ℹ${NC}  breaking_changes: $breaking_changes"
        append_to_markdown ""
        append_to_markdown "**Breaking Changes**: $breaking_changes"
    fi

    # Check for production_tested field
    local production_tested=$(echo "$yaml_content" | grep -oP 'production_tested:\s*\K(true|false)' || echo "")

    if [ "$production_tested" == "true" ]; then
        echo -e "  ${GREEN}✅${NC} production_tested: true"
        append_to_markdown ""
        append_to_markdown "**Production Tested**: ✅ Yes"
    elif [ "$production_tested" == "false" ]; then
        echo -e "  ${YELLOW}⚠${NC}  production_tested: false"
        append_to_markdown ""
        append_to_markdown "**Production Tested**: ⚠️ No"
    fi

    echo ""
}

# Initialize markdown report if specified
if [ -n "$MARKDOWN_REPORT" ]; then
    # Append to existing file or create new section
    if [ -f "$MARKDOWN_REPORT" ]; then
        echo "" >> "$MARKDOWN_REPORT"
        echo "---" >> "$MARKDOWN_REPORT"
        echo "" >> "$MARKDOWN_REPORT"
    fi
    echo "## Skill Metadata" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
    echo "**Checked**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
    echo "**Stale Threshold**: $STALE_DAYS days" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
fi

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Metadata Checker${NC}"
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

    check_skill_metadata "$SKILL_DIR" "$SKILL_NAME"
    exit 0
fi

# Check all skills
TOTAL_SKILLS=0

for skill_dir in "$SKILLS_DIR"/*/ ; do
    if [ ! -d "$skill_dir" ]; then
        continue
    fi

    skill_name=$(basename "$skill_dir")
    ((TOTAL_SKILLS++))

    check_skill_metadata "$skill_dir" "$skill_name"
done

# Append summary to markdown
if [ -n "$MARKDOWN_REPORT" ]; then
    append_to_markdown ""
    append_to_markdown "---"
    append_to_markdown ""
    append_to_markdown "### Metadata Summary"
    append_to_markdown ""
    append_to_markdown "- **Total Skills**: $TOTAL_SKILLS"
    append_to_markdown "- **Skills with Metadata**: $TOTAL_SKILLS_WITH_METADATA"
    append_to_markdown "- ⚠️ **Stale Verifications**: $STALE_VERIFICATIONS (>$STALE_DAYS days)"
    append_to_markdown "- ⚠️ **Package Issues**: $PACKAGE_ISSUES"
    append_to_markdown ""
fi

# Terminal summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Total skills: $TOTAL_SKILLS"
echo "Skills with metadata: $TOTAL_SKILLS_WITH_METADATA"
echo ""
echo -e "${YELLOW}⚠${NC}  Stale verifications (>$STALE_DAYS days): $STALE_VERIFICATIONS"
echo -e "${YELLOW}⚠${NC}  Package format issues: $PACKAGE_ISSUES"
echo ""

if [ $STALE_VERIFICATIONS -gt 0 ]; then
    echo -e "${YELLOW}ℹ${NC}  Consider updating last_verified dates for stale skills"
    echo ""
fi

if [ -n "$MARKDOWN_REPORT" ]; then
    echo -e "${GREEN}ℹ${NC}  Markdown report updated: $MARKDOWN_REPORT"
    echo ""
fi

echo -e "${GREEN}ℹ${NC}  This is informational only - no automatic updates performed"
echo -e "${GREEN}ℹ${NC}  Review warnings and update skill metadata manually as needed"
echo ""

# Always exit 0 (informational only, never fail builds)
exit 0
