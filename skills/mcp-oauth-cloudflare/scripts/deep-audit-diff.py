#!/usr/bin/env python3
"""
Deep Audit Change Detection Script

Analyzes documentation changes between audits to determine if a full re-audit is needed.
Provides detailed diff analysis including section-level changes.

Requirements:
    pip install pyyaml

Usage:
    python scripts/deep-audit-diff.py <skill-name>
    python scripts/deep-audit-diff.py fastmcp --verbose
    python scripts/deep-audit-diff.py fastmcp --since 2026-01-01
    python scripts/deep-audit-diff.py --all  # Check all skills with cached audits
"""

import argparse
import json
import re
import sys
from datetime import datetime
from difflib import unified_diff
from pathlib import Path

# Constants
REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CACHE_DIR = REPO_ROOT / "archive" / "audit-cache"


def load_history(skill_name: str) -> list:
    """Load audit history for a skill."""
    history_file = CACHE_DIR / skill_name / "history.json"
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def get_cached_content(skill_name: str, date: str, source: str) -> str:
    """Get cached markdown content for a specific date and source."""
    cache_file = CACHE_DIR / skill_name / f"{date}_{source}.md"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    return ""


def extract_sections(markdown: str) -> dict:
    """
    Extract sections from markdown content.

    Returns dict of section_title -> content
    """
    sections = {}
    current_section = "intro"
    current_content = []

    for line in markdown.split("\n"):
        # Check for heading (# or ##)
        heading_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if heading_match:
            # Save previous section
            if current_content:
                sections[current_section] = "\n".join(current_content)

            current_section = heading_match.group(2).strip()
            current_content = [line]
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections[current_section] = "\n".join(current_content)

    return sections


def analyze_changes(old_content: str, new_content: str) -> dict:
    """
    Analyze changes between two versions of content.

    Returns dict with:
        changed: bool
        summary: str
        additions: int (lines added)
        deletions: int (lines removed)
        sections_changed: list of section names
        diff_preview: str (first 20 lines of diff)
    """
    if old_content == new_content:
        return {
            "changed": False,
            "summary": "No changes",
            "additions": 0,
            "deletions": 0,
            "sections_changed": [],
            "diff_preview": "",
        }

    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(unified_diff(old_lines, new_lines, lineterm=""))

    additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

    # Analyze section-level changes
    old_sections = extract_sections(old_content)
    new_sections = extract_sections(new_content)

    sections_changed = []

    # Check for added/removed sections
    for section in set(old_sections.keys()) | set(new_sections.keys()):
        old_sec = old_sections.get(section, "")
        new_sec = new_sections.get(section, "")
        if old_sec != new_sec:
            sections_changed.append(section)

    # Generate summary
    if additions > 100 or deletions > 100:
        summary = "Major changes detected"
    elif additions > 20 or deletions > 20:
        summary = "Moderate changes detected"
    else:
        summary = "Minor changes detected"

    # Preview (first 20 diff lines)
    diff_preview = "\n".join(diff_lines[:20])

    return {
        "changed": True,
        "summary": summary,
        "additions": additions,
        "deletions": deletions,
        "sections_changed": sections_changed[:10],  # Limit to 10
        "diff_preview": diff_preview,
    }


def compare_audits(skill_name: str, old_date: str, new_date: str, verbose: bool = False) -> dict:
    """
    Compare two audit dates for a skill.

    Returns detailed change analysis.
    """
    results = {
        "skill": skill_name,
        "old_date": old_date,
        "new_date": new_date,
        "overall_changed": False,
        "sources": {},
    }

    history = load_history(skill_name)

    # Find the audit entries
    old_audit = next((h for h in history if h["date"] == old_date), None)
    new_audit = next((h for h in history if h["date"] == new_date), None)

    if not old_audit:
        return {"error": f"No audit found for date {old_date}"}
    if not new_audit:
        return {"error": f"No audit found for date {new_date}"}

    # Compare each source
    all_sources = set(old_audit.get("sources", {}).keys()) | set(new_audit.get("sources", {}).keys())

    for source in all_sources:
        old_hash = old_audit.get("sources", {}).get(source, {}).get("hash", "")
        new_hash = new_audit.get("sources", {}).get(source, {}).get("hash", "")

        if old_hash == new_hash and old_hash:
            results["sources"][source] = {
                "changed": False,
                "hash": old_hash,
            }
            continue

        # Hashes differ - do detailed analysis
        old_content = get_cached_content(skill_name, old_date, source)
        new_content = get_cached_content(skill_name, new_date, source)

        if not old_content and not new_content:
            results["sources"][source] = {
                "changed": False,
                "note": "No cached content available",
            }
            continue

        analysis = analyze_changes(old_content, new_content)
        results["sources"][source] = analysis

        if analysis["changed"]:
            results["overall_changed"] = True

    return results


def check_skill_changes(skill_name: str, since_date: str = None, verbose: bool = False) -> dict:
    """
    Check if a skill's documentation has changed since last audit or a specific date.

    Returns recommendation on whether to re-audit.
    """
    history = load_history(skill_name)

    if not history:
        return {
            "skill": skill_name,
            "needs_audit": True,
            "reason": "No previous audit found",
        }

    # Get the most recent audit with valid hashes
    valid_audits = [h for h in history if any(
        s.get("hash") for s in h.get("sources", {}).values()
    )]

    if not valid_audits:
        return {
            "skill": skill_name,
            "needs_audit": True,
            "reason": "No audits with valid hashes found",
        }

    latest = valid_audits[-1]
    latest_date = latest["date"]

    # Check if since_date is provided
    if since_date:
        # Find audit on or after since_date
        matching = [h for h in valid_audits if h["date"] >= since_date]
        if not matching:
            return {
                "skill": skill_name,
                "needs_audit": True,
                "reason": f"No audit found since {since_date}",
                "last_audit": latest_date,
            }

    # Calculate age
    try:
        audit_date = datetime.strptime(latest_date, "%Y-%m-%d")
        age_days = (datetime.now() - audit_date).days
    except ValueError:
        age_days = 999

    # Recommend re-audit if older than 7 days
    if age_days > 7:
        return {
            "skill": skill_name,
            "needs_audit": True,
            "reason": f"Last audit is {age_days} days old (threshold: 7 days)",
            "last_audit": latest_date,
        }

    return {
        "skill": skill_name,
        "needs_audit": False,
        "reason": f"Recent audit available ({age_days} days old)",
        "last_audit": latest_date,
        "sources_checked": list(latest.get("sources", {}).keys()),
    }


def list_all_cached_skills() -> list:
    """List all skills that have cached audit data."""
    if not CACHE_DIR.exists():
        return []
    return [d.name for d in CACHE_DIR.iterdir() if d.is_dir() and (d / "history.json").exists()]


def main():
    parser = argparse.ArgumentParser(description="Analyze documentation changes between audits")
    parser.add_argument("skill", nargs="?", help="Skill name to analyze")
    parser.add_argument("--all", action="store_true", help="Check all cached skills")
    parser.add_argument("--since", help="Check for changes since date (YYYY-MM-DD)")
    parser.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"), help="Compare two specific dates")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed diff output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Check all skills
    if args.all:
        skills = list_all_cached_skills()
        if not skills:
            print("No cached audits found")
            sys.exit(0)

        print(f"Checking {len(skills)} skills with cached audits...\n")

        needs_audit = []
        up_to_date = []

        for skill in sorted(skills):
            result = check_skill_changes(skill, since_date=args.since)
            if result.get("needs_audit"):
                needs_audit.append(result)
            else:
                up_to_date.append(result)

        if args.json:
            print(json.dumps({"needs_audit": needs_audit, "up_to_date": up_to_date}, indent=2))
        else:
            print("NEEDS RE-AUDIT:")
            for r in needs_audit:
                print(f"  {r['skill']}: {r['reason']}")

            print(f"\nUP TO DATE ({len(up_to_date)} skills):")
            for r in up_to_date:
                print(f"  {r['skill']}: {r['reason']}")

        sys.exit(0)

    # Single skill analysis
    if not args.skill:
        parser.print_help()
        sys.exit(1)

    skill_name = args.skill

    # Check skill exists in cache
    cache_path = CACHE_DIR / skill_name
    if not cache_path.exists():
        print(f"Error: No cached audit found for {skill_name}")
        print("Run: python scripts/deep-audit-scrape.py {skill_name}")
        sys.exit(1)

    # Compare specific dates
    if args.compare:
        old_date, new_date = args.compare
        result = compare_audits(skill_name, old_date, new_date, verbose=args.verbose)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Comparing {skill_name}: {old_date} vs {new_date}")
            print("=" * 50)

            if result.get("error"):
                print(f"Error: {result['error']}")
                sys.exit(1)

            if result["overall_changed"]:
                print("CHANGES DETECTED")
            else:
                print("NO CHANGES")

            print("\nSources:")
            for source, analysis in result["sources"].items():
                if analysis.get("changed"):
                    print(f"  {source}: CHANGED")
                    print(f"    +{analysis['additions']} -{analysis['deletions']} lines")
                    if analysis.get("sections_changed"):
                        print(f"    Sections: {', '.join(analysis['sections_changed'][:5])}")
                    if args.verbose and analysis.get("diff_preview"):
                        print(f"    Preview:\n{analysis['diff_preview'][:500]}")
                else:
                    print(f"  {source}: unchanged")

        sys.exit(0)

    # Default: check if skill needs re-audit
    result = check_skill_changes(skill_name, since_date=args.since, verbose=args.verbose)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Skill: {skill_name}")
        print("=" * 50)

        if result.get("needs_audit"):
            print(f"STATUS: NEEDS RE-AUDIT")
            print(f"Reason: {result['reason']}")
        else:
            print(f"STATUS: UP TO DATE")
            print(f"Last audit: {result.get('last_audit', 'Unknown')}")
            print(f"Sources: {', '.join(result.get('sources_checked', []))}")

    # Exit code: 0 if up to date, 1 if needs audit
    sys.exit(0 if not result.get("needs_audit") else 1)


if __name__ == "__main__":
    main()
