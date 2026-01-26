#!/usr/bin/env bash

# check-all-versions.sh - Comprehensive version checker for all skills
# Usage: ./scripts/check-all-versions.sh [skill-name]
#
# Runs all version checkers and generates consolidated report
# - NPM packages (with breaking change detection)
# - GitHub releases
# - YAML metadata validation
# - AI model references
# - Marketplace sync (marketplace.json vs actual skills)
#
# Exit code: Always 0 (info only, no failures)

# Don't use set -e - we want to always exit 0
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Report file
REPORT_FILE="$REPO_ROOT/VERSIONS_REPORT.md"

# Parse arguments
SKILL_NAME=""
if [ -n "$1" ]; then
    SKILL_NAME="$1"
fi

# Function to print section header
print_section() {
    local title="$1"
    echo ""
    echo -e "${CYAN}═════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $title${NC}"
    echo -e "${CYAN}═════════════════════════════════════${NC}"
    echo ""
}

# Start
echo -e "${BLUE}${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║                                           ║${NC}"
echo -e "${BLUE}${BOLD}║   Comprehensive Version Checker          ║${NC}"
echo -e "${BLUE}${BOLD}║   Claude Skills Repository                ║${NC}"
echo -e "${BLUE}${BOLD}║                                           ║${NC}"
echo -e "${BLUE}${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Started:${NC} $(date)"
echo ""

if [ -n "$SKILL_NAME" ]; then
    echo -e "${BLUE}Checking skill:${NC} $SKILL_NAME"
else
    echo -e "${BLUE}Checking:${NC} All skills"
fi

echo ""
echo -e "${YELLOW}Generating report:${NC} $REPORT_FILE"
echo ""

# Initialize markdown report
cat > "$REPORT_FILE" << EOF
# Version Check Report

**Generated**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Repository**: claude-skills
**Checked By**: check-all-versions.sh

EOF

if [ -n "$SKILL_NAME" ]; then
    echo "**Scope**: Single skill ($SKILL_NAME)" >> "$REPORT_FILE"
else
    echo "**Scope**: All skills" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Run each checker
CHECKER_ARGS=""
if [ -n "$SKILL_NAME" ]; then
    CHECKER_ARGS="$SKILL_NAME"
fi

# 1. NPM Packages
print_section "1/5: Checking NPM Packages"
"$SCRIPT_DIR/check-npm-versions.sh" $CHECKER_ARGS --markdown "$REPORT_FILE"

# 2. GitHub Releases
print_section "2/5: Checking GitHub Releases"
"$SCRIPT_DIR/check-github-releases.sh" $CHECKER_ARGS --markdown "$REPORT_FILE"

# 3. Metadata
print_section "3/5: Checking Skill Metadata"
"$SCRIPT_DIR/check-metadata.sh" $CHECKER_ARGS --markdown "$REPORT_FILE"

# 4. AI Models
print_section "4/5: Checking AI Model References"
"$SCRIPT_DIR/check-ai-models.sh" $CHECKER_ARGS --markdown "$REPORT_FILE"

# 5. Marketplace Sync
print_section "5/5: Checking Marketplace Sync"
"$SCRIPT_DIR/check-marketplace-sync.sh" --markdown "$REPORT_FILE" || true

# Generate action items section
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Action Items" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Extract warnings from report for action items
# Use tr to remove newlines and ensure single integer
npm_warnings=$(grep -c "⚠️.*update" "$REPORT_FILE" 2>/dev/null | tr -d '\n' || echo "0")
major_warnings=$(grep -c "MAJOR.*breaking" "$REPORT_FILE" 2>/dev/null | tr -d '\n' || echo "0")
stale_warnings=$(grep -c "STALE" "$REPORT_FILE" 2>/dev/null | tr -d '\n' || echo "0")
deprecated_models=$(grep -c "Deprecated" "$REPORT_FILE" 2>/dev/null | tr -d '\n' || echo "0")
marketplace_issues=$(grep -c "Phantom\|Missing" "$REPORT_FILE" 2>/dev/null | tr -d '\n' || echo "0")

echo "### High Priority" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ "$major_warnings" -gt 0 ]; then
    echo "- ❌ **$major_warnings major (breaking) package update(s)** - Review migration guides before updating" >> "$REPORT_FILE"
fi

if [ "$deprecated_models" -gt 0 ]; then
    echo "- ⚠️ **$deprecated_models deprecated AI model reference(s)** - Update to current models" >> "$REPORT_FILE"
fi

if [ "$stale_warnings" -gt 0 ]; then
    echo "- ⚠️ **$stale_warnings skill(s) with stale verification dates** - Re-test and update metadata" >> "$REPORT_FILE"
fi

if [ "$marketplace_issues" -gt 0 ]; then
    echo "- ❌ **Marketplace out of sync** - Run \`./scripts/check-marketplace-sync.sh --fix\`" >> "$REPORT_FILE"
fi

if [ "$npm_warnings" -gt 0 ]; then
    echo "" >> "$REPORT_FILE"
    echo "### Medium Priority" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "- ⚠️ **$npm_warnings minor/patch package update(s)** - Update when convenient" >> "$REPORT_FILE"
fi

if [ "$major_warnings" -eq 0 ] && [ "$deprecated_models" -eq 0 ] && [ "$stale_warnings" -eq 0 ] && [ "$npm_warnings" -eq 0 ] && [ "$marketplace_issues" -eq 0 ]; then
    echo "✅ **No action items** - All dependencies are up-to-date!" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"

# Add recommendations section
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Recommendations" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "### Maintenance Schedule" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- **Weekly**: Check for deprecated AI models" >> "$REPORT_FILE"
echo "- **Monthly**: Update minor/patch versions" >> "$REPORT_FILE"
echo "- **Quarterly**: Full audit with \`check-all-versions.sh\`" >> "$REPORT_FILE"
echo "- **Before major updates**: Test in isolation, review breaking changes" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "### Update Process" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "1. Review this report for breaking changes" >> "$REPORT_FILE"
echo "2. Update package.json files in skill templates" >> "$REPORT_FILE"
echo "3. Update version references in SKILL.md files" >> "$REPORT_FILE"
echo "4. Update metadata.last_verified dates" >> "$REPORT_FILE"
echo "5. Test updated skills in example projects" >> "$REPORT_FILE"
echo "6. Commit changes with detailed changelog" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Footer
echo "---" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "_Report generated by \`scripts/check-all-versions.sh\`_  " >> "$REPORT_FILE"
echo "_For more details, run individual checkers: \`check-npm-versions.sh\`, \`check-github-releases.sh\`, \`check-metadata.sh\`, \`check-ai-models.sh\`_" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Final summary
echo ""
echo -e "${CYAN}═════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}  Complete!${NC}"
echo -e "${CYAN}═════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ All checks completed${NC}"
echo ""
echo -e "${BOLD}Report Summary:${NC}"
echo "  • NPM packages: See report for details"
echo "  • GitHub releases: See report for details"
echo "  • Metadata: See report for details"
echo "  • AI models: See report for details"
echo "  • Marketplace sync: See report for details"
echo ""
echo -e "${YELLOW}📄 Full report:${NC} $REPORT_FILE"
echo ""

if [ "$major_warnings" -gt 0 ] || [ "$deprecated_models" -gt 0 ] || [ "$marketplace_issues" -gt 0 ]; then
    echo -e "${RED}⚠️  HIGH PRIORITY ITEMS DETECTED${NC}"
    echo ""
    if [ "$major_warnings" -gt 0 ]; then
        echo "  • $major_warnings major (breaking) package update(s)"
    fi
    if [ "$deprecated_models" -gt 0 ]; then
        echo "  • $deprecated_models deprecated AI model reference(s)"
    fi
    if [ "$marketplace_issues" -gt 0 ]; then
        echo "  • Marketplace out of sync - run ./scripts/check-marketplace-sync.sh --fix"
    fi
    echo ""
    echo "  Review $REPORT_FILE for details"
    echo ""
fi

echo -e "${GREEN}Finished:${NC} $(date)"
echo ""

# Always exit 0 (informational only, never fail builds)
exit 0
