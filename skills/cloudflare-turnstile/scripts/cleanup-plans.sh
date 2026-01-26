#!/bin/bash
# Cleanup old Claude Code plan files from ~/.claude/plans/
#
# Usage:
#   ./scripts/cleanup-plans.sh              # Delete plans older than 30 days
#   ./scripts/cleanup-plans.sh --dry-run    # Show what would be deleted
#   ./scripts/cleanup-plans.sh --days 14    # Delete plans older than 14 days
#   ./scripts/cleanup-plans.sh --days 14 --dry-run  # Combine options

set -e

PLANS_DIR="$HOME/.claude/plans"
DAYS=30
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--days N]"
            echo ""
            echo "Delete Claude Code plan files older than N days (default: 30)"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be deleted without deleting"
            echo "  --days N     Delete files older than N days (default: 30)"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if plans directory exists
if [[ ! -d "$PLANS_DIR" ]]; then
    echo "Plans directory not found: $PLANS_DIR"
    exit 0
fi

# Find old plan files
OLD_FILES=$(find "$PLANS_DIR" -name "*.md" -type f -mtime +$DAYS 2>/dev/null || true)

if [[ -z "$OLD_FILES" ]]; then
    echo "No plan files older than $DAYS days found."
    exit 0
fi

# Count files
FILE_COUNT=$(echo "$OLD_FILES" | wc -l)
TOTAL_SIZE=$(echo "$OLD_FILES" | xargs du -ch 2>/dev/null | tail -1 | cut -f1)

echo "Found $FILE_COUNT plan file(s) older than $DAYS days ($TOTAL_SIZE total):"
echo ""

# List files with age
while IFS= read -r file; do
    if [[ -n "$file" ]]; then
        age_days=$(( ($(date +%s) - $(stat -c %Y "$file")) / 86400 ))
        filename=$(basename "$file")
        echo "  $filename ($age_days days old)"
    fi
done <<< "$OLD_FILES"

echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would delete $FILE_COUNT file(s). Run without --dry-run to delete."
else
    echo "Deleting $FILE_COUNT file(s)..."
    echo "$OLD_FILES" | xargs rm -f
    echo "Done."
fi
