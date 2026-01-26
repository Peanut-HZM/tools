#!/usr/bin/env python3
"""
Deep Audit Bulk Operations Script

Run content audits on multiple skills using tier-based or pattern-based selection.
Reads tier definitions from planning/SKILL_AUDIT_QUEUE.md.

Requirements:
    pip install pyyaml

Usage:
    python scripts/deep-audit-bulk.py --tier 1       # Audit all Tier 1 skills
    python scripts/deep-audit-bulk.py --tier 1-3    # Audit Tiers 1, 2, and 3
    python scripts/deep-audit-bulk.py cloudflare-*  # Audit skills matching pattern
    python scripts/deep-audit-bulk.py --all         # Audit all skills (expensive!)
    python scripts/deep-audit-bulk.py --list        # List skills by tier (no audit)
    python scripts/deep-audit-bulk.py --dry-run --tier 1  # Show what would be audited
"""

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

# Constants
REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
QUEUE_FILE = REPO_ROOT / "planning" / "SKILL_AUDIT_QUEUE.md"
SCRAPE_SCRIPT = REPO_ROOT / "scripts" / "deep-audit-scrape.py"
DIFF_SCRIPT = REPO_ROOT / "scripts" / "deep-audit-diff.py"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def parse_tier_from_queue() -> dict[int, list[str]]:
    """
    Parse skill tier mappings from SKILL_AUDIT_QUEUE.md.

    Returns dict of tier_number -> list of skill names.
    """
    tiers: dict[int, list[str]] = {}

    if not QUEUE_FILE.exists():
        print(f"Warning: Queue file not found: {QUEUE_FILE}")
        return tiers

    content = QUEUE_FILE.read_text(encoding="utf-8")

    # Parse each tier section
    # Format: ### Tier N: Description
    # Followed by markdown table with | skill-name | ... |

    current_tier = None
    in_table = False

    for line in content.split("\n"):
        # Check for tier header
        tier_match = re.match(r'^### Tier (\d+):', line)
        if tier_match:
            current_tier = int(tier_match.group(1))
            tiers[current_tier] = []
            in_table = False
            continue

        # Check for table start (header row)
        if current_tier and line.startswith("| Skill"):
            in_table = True
            continue

        # Check for table separator
        if current_tier and line.startswith("|---"):
            continue

        # Parse table rows
        if current_tier and in_table and line.startswith("|"):
            # Extract skill name from first column
            # Format: | skill-name | date | rules | status |
            parts = line.split("|")
            if len(parts) >= 2:
                skill_name = parts[1].strip()
                if skill_name and skill_name != "Skill":
                    tiers[current_tier].append(skill_name)

        # End of table (empty line or new section)
        if current_tier and in_table and not line.strip():
            in_table = False

    return tiers


def get_all_skills() -> list[str]:
    """Get list of all skill directories."""
    if not SKILLS_DIR.exists():
        return []

    return sorted([
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ])


def filter_skills_by_pattern(pattern: str, skills: list[str]) -> list[str]:
    """Filter skills by glob pattern (e.g., 'cloudflare-*')."""
    return [s for s in skills if fnmatch.fnmatch(s, pattern)]


def parse_tier_range(tier_arg: str) -> list[int]:
    """
    Parse tier argument which can be:
    - Single tier: "1"
    - Range: "1-3"
    - Comma-separated: "1,2,5"
    """
    tiers = []

    for part in tier_arg.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            tiers.extend(range(int(start), int(end) + 1))
        else:
            tiers.append(int(part))

    return sorted(set(tiers))


def check_skill_needs_audit(skill_name: str) -> tuple[bool, str]:
    """
    Check if a skill needs auditing using deep-audit-diff.py.

    Returns (needs_audit: bool, reason: str).
    """
    python_cmd = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

    try:
        result = subprocess.run(
            [python_cmd, str(DIFF_SCRIPT), skill_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return False, "Up to date"
        else:
            # Parse reason from output if possible
            import json
            try:
                data = json.loads(result.stdout)
                return True, data.get("reason", "Needs audit")
            except json.JSONDecodeError:
                return True, "Needs audit (no cache)"

    except subprocess.TimeoutExpired:
        return True, "Check timed out"
    except FileNotFoundError:
        return True, "Diff script not found"


def run_scrape(skill_name: str, dry_run: bool = False) -> bool:
    """
    Run deep-audit-scrape.py for a skill.

    Returns True if successful.
    """
    python_cmd = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

    if dry_run:
        print(f"  [DRY RUN] Would scrape: {skill_name}")
        return True

    print(f"  Scraping documentation for {skill_name}...")

    try:
        result = subprocess.run(
            [python_cmd, str(SCRAPE_SCRIPT), skill_name],
            capture_output=True,
            text=True,
            timeout=120,
            env={
                **subprocess.os.environ,
                "FIRECRAWL_API_KEY": subprocess.os.environ.get(
                    "FIRECRAWL_API_KEY", ""
                )
            }
        )

        if result.returncode == 0:
            print(f"  ✅ Scraped: {skill_name}")
            return True
        else:
            print(f"  ❌ Failed: {skill_name}")
            if result.stderr:
                print(f"     Error: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ⏱️ Timeout: {skill_name}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {skill_name} - {e}")
        return False


def list_skills_by_tier(tiers: dict[int, list[str]]) -> None:
    """Print skills organized by tier."""
    print("\n📊 Skills by Tier\n")
    print("=" * 60)

    all_skills = get_all_skills()
    tiered_skills = set()

    for tier_num in sorted(tiers.keys()):
        skills = tiers[tier_num]
        tiered_skills.update(skills)
        print(f"\n### Tier {tier_num} ({len(skills)} skills)")
        for skill in skills:
            exists = "✅" if skill in all_skills else "❌"
            print(f"  {exists} {skill}")

    # Find untiered skills
    untiered = set(all_skills) - tiered_skills
    if untiered:
        print(f"\n### Untiered ({len(untiered)} skills)")
        for skill in sorted(untiered):
            print(f"  ⬜ {skill}")

    print("\n" + "=" * 60)
    print(f"Total: {len(all_skills)} skills ({len(tiered_skills)} tiered, {len(untiered)} untiered)")


def main():
    parser = argparse.ArgumentParser(
        description="Run deep audits on multiple skills",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --tier 1           # Audit all Tier 1 skills
  %(prog)s --tier 1-3         # Audit Tiers 1, 2, and 3
  %(prog)s --tier 1,3,5       # Audit specific tiers
  %(prog)s cloudflare-*       # Audit skills matching pattern
  %(prog)s ai-*               # Audit AI-related skills
  %(prog)s --all              # Audit ALL skills (expensive!)
  %(prog)s --list             # Show skills by tier
  %(prog)s --dry-run --tier 1 # Preview what would be audited
        """
    )

    parser.add_argument(
        "pattern",
        nargs="?",
        help="Glob pattern to match skill names (e.g., 'cloudflare-*')"
    )
    parser.add_argument(
        "--tier", "-t",
        help="Tier number(s) to audit (e.g., '1', '1-3', '1,2,5')"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Audit all skills (expensive!)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List skills by tier without auditing"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be audited without running"
    )
    parser.add_argument(
        "--skip-fresh",
        action="store_true",
        help="Skip skills with fresh cache (< 7 days old)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Parse tier definitions
    tiers = parse_tier_from_queue()
    all_skills = get_all_skills()

    # Handle --list
    if args.list:
        list_skills_by_tier(tiers)
        return 0

    # Determine which skills to audit
    skills_to_audit: list[str] = []

    if args.all:
        skills_to_audit = all_skills
        print(f"🎯 Auditing ALL {len(skills_to_audit)} skills")

    elif args.tier:
        tier_nums = parse_tier_range(args.tier)
        for t in tier_nums:
            if t in tiers:
                skills_to_audit.extend(tiers[t])
            else:
                print(f"Warning: Tier {t} not found in queue file")

        # Remove duplicates, preserve order
        seen = set()
        skills_to_audit = [s for s in skills_to_audit if not (s in seen or seen.add(s))]
        print(f"🎯 Auditing Tier(s) {args.tier}: {len(skills_to_audit)} skills")

    elif args.pattern:
        skills_to_audit = filter_skills_by_pattern(args.pattern, all_skills)
        print(f"🎯 Auditing pattern '{args.pattern}': {len(skills_to_audit)} skills")

    else:
        parser.print_help()
        return 1

    if not skills_to_audit:
        print("No skills matched the criteria.")
        return 1

    # Filter out skills that don't exist
    missing = [s for s in skills_to_audit if s not in all_skills]
    if missing:
        print(f"⚠️ Missing skills (not in skills/): {', '.join(missing)}")
        skills_to_audit = [s for s in skills_to_audit if s in all_skills]

    # Check which skills need auditing
    if args.skip_fresh:
        print("\n📋 Checking cache freshness...")
        needs_audit = []
        for skill in skills_to_audit:
            needs, reason = check_skill_needs_audit(skill)
            if needs:
                needs_audit.append((skill, reason))
                print(f"  🔄 {skill}: {reason}")
            else:
                print(f"  ✅ {skill}: Fresh cache")

        skills_to_audit = [s for s, _ in needs_audit]
        print(f"\n{len(skills_to_audit)} skills need auditing")

    if not skills_to_audit:
        print("All skills are up to date!")
        return 0

    # Run audits
    print(f"\n{'=' * 60}")
    print(f"Starting bulk audit of {len(skills_to_audit)} skills")
    print(f"{'=' * 60}\n")

    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }

    for i, skill in enumerate(skills_to_audit, 1):
        print(f"\n[{i}/{len(skills_to_audit)}] {skill}")

        if args.dry_run:
            results["skipped"].append(skill)
            print(f"  [DRY RUN] Would audit: {skill}")
            continue

        # Run scrape (comparison is done by Claude in the full workflow)
        success = run_scrape(skill, dry_run=args.dry_run)

        if success:
            results["success"].append(skill)
        else:
            results["failed"].append(skill)

    # Summary
    print(f"\n{'=' * 60}")
    print("BULK AUDIT SUMMARY")
    print(f"{'=' * 60}")
    print(f"✅ Successful: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    if results["skipped"]:
        print(f"⏭️ Skipped (dry run): {len(results['skipped'])}")

    if results["failed"]:
        print(f"\nFailed skills: {', '.join(results['failed'])}")

    if args.json:
        import json
        print("\n" + json.dumps(results, indent=2))

    # Exit code: 0 if all succeeded, 1 if any failed
    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
