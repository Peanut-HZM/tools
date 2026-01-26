#!/bin/bash
# fix-frontmatter.sh - Remove non-standard YAML frontmatter fields from skills
# Valid fields: name, description, allowed-tools (only)

set -e

SKILLS_DIR="${1:-skills}"
DRY_RUN="${2:-false}"

echo "=== Frontmatter Fixer ==="
echo "Skills directory: $SKILLS_DIR"
echo "Dry run: $DRY_RUN"
echo ""

fixed_count=0
error_count=0

for skill_file in "$SKILLS_DIR"/*/SKILL.md; do
    if [[ ! -f "$skill_file" ]]; then
        continue
    fi

    skill_name=$(basename "$(dirname "$skill_file")")

    # Check if file has non-standard fields
    if grep -q "^license:\|^metadata:" "$skill_file" 2>/dev/null; then
        echo "Processing: $skill_name"

        if [[ "$DRY_RUN" == "true" ]]; then
            echo "  Would remove non-standard fields"
            ((fixed_count++))
            continue
        fi

        # Create temp file
        temp_file=$(mktemp)

        # Extract content, removing license: and metadata: blocks
        awk '
        BEGIN { in_frontmatter = 0; in_metadata = 0; frontmatter_end = 0 }

        /^---$/ && !in_frontmatter {
            in_frontmatter = 1
            print
            next
        }

        /^---$/ && in_frontmatter {
            in_frontmatter = 0
            frontmatter_end = 1
            in_metadata = 0
            print
            next
        }

        in_frontmatter {
            # Skip license: line
            if (/^license:/) { next }

            # Start of metadata block
            if (/^metadata:/) {
                in_metadata = 1
                next
            }

            # Inside metadata block (indented lines)
            if (in_metadata && /^[[:space:]]/) { next }

            # End of metadata block (non-indented line that is not ---)
            if (in_metadata && /^[^[:space:]]/) {
                in_metadata = 0
            }

            # Print valid frontmatter lines
            if (!in_metadata) { print }
        }

        !in_frontmatter { print }
        ' "$skill_file" > "$temp_file"

        # Verify the temp file has valid frontmatter
        if head -1 "$temp_file" | grep -q "^---$"; then
            mv "$temp_file" "$skill_file"
            echo "  ✓ Fixed"
            ((fixed_count++))
        else
            echo "  ✗ Error: Invalid output, skipping"
            rm "$temp_file"
            ((error_count++))
        fi
    fi
done

echo ""
echo "=== Summary ==="
echo "Fixed: $fixed_count skills"
echo "Errors: $error_count skills"

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "This was a dry run. Run with 'false' as second argument to apply changes."
fi
