#!/usr/bin/env bash

# check-github-releases.sh - Check GitHub releases for tools/SDKs in skills
# Usage: ./scripts/check-github-releases.sh [skill-name] [--markdown REPORT_FILE]
#
# Parses GitHub URLs from SKILL.md files and checks latest releases
# Compares against documented versions
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
TOTAL_REPOS=0
UP_TO_DATE=0
OUTDATED=0
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

# Function to append to markdown report
append_to_markdown() {
    local text="$1"
    if [ -n "$MARKDOWN_REPORT" ]; then
        echo "$text" >> "$MARKDOWN_REPORT"
    fi
}

# Function to get latest GitHub release
# Tries gh CLI first, falls back to curl
get_latest_release() {
    local repo="$1"
    local release=""

    # Try gh CLI first (authenticated, higher rate limit)
    if command -v gh &> /dev/null; then
        release=$(gh api "repos/$repo/releases/latest" --jq '.tag_name' 2>/dev/null || echo "error")
        if [ "$release" != "error" ] && [ -n "$release" ]; then
            echo "$release"
            return
        fi
    fi

    # Fallback to curl (unauthenticated, 60 req/hr limit)
    local github_token="${GITHUB_TOKEN:-}"
    if [ -n "$github_token" ]; then
        release=$(curl -s -H "Authorization: token $github_token" \
            "https://api.github.com/repos/$repo/releases/latest" | \
            grep -o '"tag_name": "[^"]*"' | sed 's/"tag_name": "//; s/"$//' || echo "error")
    else
        release=$(curl -s "https://api.github.com/repos/$repo/releases/latest" | \
            grep -o '"tag_name": "[^"]*"' | sed 's/"tag_name": "//; s/"$//' || echo "error")
    fi

    if [ -z "$release" ] || [ "$release" == "error" ]; then
        echo "error"
    else
        echo "$release"
    fi
}

# Function to normalize version tags (remove v prefix)
normalize_version() {
    local version="$1"
    # Remove leading 'v' if present
    echo "${version#v}"
}

# Function to check a single skill
check_skill_github_releases() {
    local skill_dir="$1"
    local skill_name="$2"
    local skill_file="$skill_dir/SKILL.md"

    if [ ! -f "$skill_file" ]; then
        return
    fi

    echo -e "${BLUE}Checking: $skill_name${NC}"

    # Extract GitHub URLs from SKILL.md
    local github_urls=$(grep -oE 'https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+' "$skill_file" | sort -u)

    if [ -z "$github_urls" ]; then
        echo -e "${YELLOW}  No GitHub URLs found${NC}"
        echo ""
        return
    fi

    # Start markdown section for this skill
    if [ -n "$MARKDOWN_REPORT" ]; then
        append_to_markdown ""
        append_to_markdown "### $skill_name"
        append_to_markdown ""
        append_to_markdown "| Repository | Latest Release | Status |"
        append_to_markdown "|------------|----------------|--------|"
    fi

    local found_repos=0

    # Check each unique GitHub repo
    while IFS= read -r url; do
        # Extract owner/repo from URL
        if [[ $url =~ github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+) ]]; then
            local repo="${BASH_REMATCH[1]}"
            # Remove .git suffix if present
            repo="${repo%.git}"

            ((found_repos++))
            ((TOTAL_REPOS++))

            # Get latest release
            local latest=$(get_latest_release "$repo")

            if [ "$latest" == "error" ]; then
                echo -e "  ${YELLOW}⚠${NC}  $repo - Could not fetch latest release"
                append_to_markdown "| $repo | _error_ | ⚠️ Could not fetch |"
                ((ERRORS++))
            else
                # Normalize version for comparison
                local normalized=$(normalize_version "$latest")

                # Check if this version is mentioned in SKILL.md
                if grep -q "$normalized" "$skill_file" || grep -q "$latest" "$skill_file"; then
                    echo -e "  ${GREEN}✅${NC} $repo - $latest (documented)"
                    append_to_markdown "| $repo | $latest | ✅ Documented |"
                    ((UP_TO_DATE++))
                else
                    # Check if skill mentions a different version
                    echo -e "  ${YELLOW}⚠${NC}  $repo - Latest: $latest (check if documented)"
                    append_to_markdown "| $repo | $latest | ⚠️ Check docs |"
                    ((OUTDATED++))
                fi
            fi
        fi
    done <<< "$github_urls"

    if [ $found_repos -eq 0 ]; then
        echo -e "${YELLOW}  No valid GitHub repos found${NC}"
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
    echo "## GitHub Releases" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
    echo "**Checked**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> "$MARKDOWN_REPORT"
    echo "" >> "$MARKDOWN_REPORT"
fi

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  GitHub Release Checker${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Check authentication method
if command -v gh &> /dev/null; then
    echo -e "${GREEN}ℹ${NC}  Using gh CLI (authenticated)"
elif [ -n "${GITHUB_TOKEN:-}" ]; then
    echo -e "${GREEN}ℹ${NC}  Using GITHUB_TOKEN for authentication"
else
    echo -e "${YELLOW}⚠${NC}  No authentication - rate limited to 60 requests/hour"
    echo "  Set GITHUB_TOKEN or install gh CLI for higher limits"
fi
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

    check_skill_github_releases "$SKILL_DIR" "$SKILL_NAME"
    exit 0
fi

# Check all skills
TOTAL_SKILLS=0
SKILLS_WITH_REPOS=0

for skill_dir in "$SKILLS_DIR"/*/ ; do
    if [ ! -d "$skill_dir" ]; then
        continue
    fi

    skill_name=$(basename "$skill_dir")
    ((TOTAL_SKILLS++))

    # Check if skill has GitHub URLs
    if [ -f "$skill_dir/SKILL.md" ]; then
        has_github=$(grep -c 'https://github\.com/' "$skill_dir/SKILL.md" || true)
        if [ "$has_github" -gt 0 ]; then
            check_skill_github_releases "$skill_dir" "$skill_name"
            ((SKILLS_WITH_REPOS++))
        fi
    fi
done

# Append summary to markdown
if [ -n "$MARKDOWN_REPORT" ]; then
    append_to_markdown ""
    append_to_markdown "---"
    append_to_markdown ""
    append_to_markdown "### GitHub Releases Summary"
    append_to_markdown ""
    append_to_markdown "- **Total Repositories**: $TOTAL_REPOS"
    append_to_markdown "- ✅ **Documented**: $UP_TO_DATE"
    append_to_markdown "- ⚠️ **Needs Review**: $OUTDATED"
    append_to_markdown "- ⚠️ **Errors**: $ERRORS"
    append_to_markdown ""
fi

# Terminal summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo "Total skills: $TOTAL_SKILLS"
echo "Skills with GitHub repos: $SKILLS_WITH_REPOS"
echo "Total repositories checked: $TOTAL_REPOS"
echo ""
echo -e "${GREEN}✅${NC} Documented: $UP_TO_DATE"
echo -e "${YELLOW}⚠${NC}  Needs review: $OUTDATED"
if [ $ERRORS -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC}  Errors fetching: $ERRORS"
fi
echo ""

if [ -n "$MARKDOWN_REPORT" ]; then
    echo -e "${GREEN}ℹ${NC}  Markdown report updated: $MARKDOWN_REPORT"
    echo ""
fi

echo -e "${GREEN}ℹ${NC}  This is informational only - no automatic updates performed"
echo -e "${GREEN}ℹ${NC}  Review 'needs review' items and update skills manually as needed"
echo ""

# Always exit 0 (informational only, never fail builds)
exit 0
