#!/usr/bin/env python3
"""
Fix non-standard YAML frontmatter in skills.
Valid fields: name, description, allowed-tools (only)
"""

import os
import re
import sys
from pathlib import Path

def fix_skill_frontmatter(skill_path: Path, dry_run: bool = False) -> bool:
    """Fix a single skill's frontmatter. Returns True if changes were made."""
    content = skill_path.read_text()

    # Check if file has YAML frontmatter
    if not content.startswith('---'):
        return False

    # Find the end of frontmatter
    second_delimiter = content.find('---', 3)
    if second_delimiter == -1:
        print(f"  ⚠ No closing --- found in {skill_path}")
        return False

    frontmatter = content[3:second_delimiter].strip()
    body = content[second_delimiter + 3:]

    # Check if there are non-standard fields
    has_license = re.search(r'^license:', frontmatter, re.MULTILINE)
    has_metadata = re.search(r'^metadata:', frontmatter, re.MULTILINE)

    if not has_license and not has_metadata:
        return False

    # Parse and rebuild frontmatter keeping only valid fields
    lines = frontmatter.split('\n')
    new_lines = []
    skip_until_unindent = False

    for line in lines:
        # Check if this is a top-level field (no leading whitespace)
        is_top_level = line and not line[0].isspace()

        if skip_until_unindent:
            if is_top_level:
                skip_until_unindent = False
            else:
                continue  # Skip indented lines under metadata

        if line.startswith('license:'):
            continue  # Skip license line

        if line.startswith('metadata:'):
            skip_until_unindent = True
            continue  # Skip metadata and its children

        new_lines.append(line)

    new_frontmatter = '\n'.join(new_lines)
    new_content = f"---\n{new_frontmatter}\n---{body}"

    if dry_run:
        print(f"  Would fix: {skill_path.parent.name}")
        return True

    skill_path.write_text(new_content)
    print(f"  ✓ Fixed: {skill_path.parent.name}")
    return True


def main():
    skills_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('skills')
    dry_run = sys.argv[2].lower() == 'true' if len(sys.argv) > 2 else False

    print("=== Frontmatter Fixer ===")
    print(f"Skills directory: {skills_dir}")
    print(f"Dry run: {dry_run}")
    print()

    fixed_count = 0

    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / 'SKILL.md'
        if skill_file.exists():
            if fix_skill_frontmatter(skill_file, dry_run):
                fixed_count += 1

    print()
    print(f"=== Summary ===")
    print(f"Fixed: {fixed_count} skills")

    if dry_run:
        print()
        print("This was a dry run. Run without 'true' to apply changes.")


if __name__ == '__main__':
    main()
