#!/usr/bin/env python3
"""
Deep Audit Documentation Scraper

Scrapes official documentation for a skill using Firecrawl API.
Outputs markdown to archive/audit-cache/<skill>/ with content hashing for change detection.

Requirements:
    pip install firecrawl-py python-dotenv pyyaml

Environment Variables:
    FIRECRAWL_API_KEY - Your Firecrawl API key

Usage:
    python scripts/deep-audit-scrape.py <skill-name>
    python scripts/deep-audit-scrape.py fastmcp
    python scripts/deep-audit-scrape.py --list-sources fastmcp
    python scripts/deep-audit-scrape.py --force fastmcp  # Ignore cache
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CACHE_DIR = REPO_ROOT / "archive" / "audit-cache"
CACHE_DAYS = 7  # Cache validity in days


def parse_skill_frontmatter(skill_path: Path) -> dict:
    """
    Parse YAML frontmatter from SKILL.md.

    Returns dict with keys: name, description, metadata (including doc_sources)
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found at {skill_md}")

    content = skill_md.read_text(encoding="utf-8")

    # Extract YAML frontmatter
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not frontmatter_match:
        return {}

    try:
        return yaml.safe_load(frontmatter_match.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"Warning: Failed to parse YAML frontmatter: {e}")
        return {}


def extract_doc_urls_from_content(skill_path: Path) -> list[str]:
    """
    Extract documentation URLs from SKILL.md content.
    Fallback when metadata.doc_sources is not present.
    """
    skill_md = skill_path / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")

    # Find all HTTPS URLs that look like documentation
    url_pattern = r'https?://[^\s\)\]"\'<>]+'
    urls = re.findall(url_pattern, content)

    # Filter for documentation-like URLs
    doc_indicators = ['docs', 'documentation', 'guide', 'getting-started', 'reference', 'api']
    doc_urls = []

    for url in urls:
        url_lower = url.lower()
        # Skip GitHub raw/blob URLs (code, not docs)
        if 'github.com' in url_lower and ('/blob/' in url_lower or '/raw/' in url_lower):
            continue
        # Check for doc indicators
        if any(ind in url_lower for ind in doc_indicators):
            doc_urls.append(url)

    return list(set(doc_urls))[:3]  # Limit to 3 URLs


def get_doc_sources(skill_name: str) -> dict:
    """
    Get documentation sources for a skill.

    Returns dict with keys like: primary, api, changelog
    """
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_name}")

    frontmatter = parse_skill_frontmatter(skill_path)

    # Check for metadata.doc_sources
    metadata = frontmatter.get("metadata", {})
    doc_sources = metadata.get("doc_sources", {})

    if doc_sources:
        return doc_sources

    # Fallback: extract URLs from content
    urls = extract_doc_urls_from_content(skill_path)
    if urls:
        doc_sources = {"primary": urls[0]}
        if len(urls) > 1:
            doc_sources["secondary"] = urls[1]
        if len(urls) > 2:
            doc_sources["tertiary"] = urls[2]
        return doc_sources

    return {}


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for change detection."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def is_cache_valid(cache_path: Path) -> bool:
    """Check if cached content is still valid (within CACHE_DAYS)."""
    if not cache_path.exists():
        return False

    # Check modification time
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age_days = (datetime.now() - mtime).days

    return age_days < CACHE_DAYS


def scrape_url(url: str) -> dict:
    """
    Scrape a URL using Firecrawl API (v4+).

    Returns dict with: markdown, metadata
    """
    try:
        from firecrawl import Firecrawl
    except ImportError:
        print("Error: firecrawl-py not installed. Run: pip install firecrawl-py")
        sys.exit(1)

    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("Error: FIRECRAWL_API_KEY environment variable not set")
        print("Get your key at: https://www.firecrawl.dev")
        sys.exit(1)

    app = Firecrawl(api_key=api_key)

    print(f"  Scraping: {url}")

    try:
        # Firecrawl v4 API: scrape(url, formats=[], ...)
        # Returns a Pydantic Document object
        doc = app.scrape(
            url=url,
            formats=["markdown"],
            only_main_content=True,
            remove_base64_images=True,
        )
        # Convert to dict for consistent handling
        return {
            "markdown": doc.markdown or "",
            "metadata": doc.metadata_dict if hasattr(doc, "metadata_dict") else {},
        }
    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        return {"markdown": "", "error": str(e)}


def scrape_skill_docs(skill_name: str, force: bool = False) -> dict:
    """
    Scrape all documentation sources for a skill.

    Args:
        skill_name: Name of the skill
        force: If True, ignore cache and re-scrape

    Returns dict with:
        sources: dict of source_name -> {url, markdown, hash, cached}
        cache_dir: Path to cache directory
        date: Scrape date (YYYY-MM-DD)
    """
    doc_sources = get_doc_sources(skill_name)

    if not doc_sources:
        print(f"Warning: No doc_sources found for {skill_name}")
        print("Add metadata.doc_sources to SKILL.md frontmatter")
        return {"sources": {}, "cache_dir": None, "date": None}

    # Create cache directory
    cache_dir = CACHE_DIR / skill_name
    cache_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    results = {}

    for source_name, url in doc_sources.items():
        cache_file = cache_dir / f"{today}_{source_name}.md"
        hash_file = cache_dir / f"{today}_{source_name}.hash"

        # Check cache
        if not force and is_cache_valid(cache_file):
            print(f"  Using cached: {source_name}")
            markdown = cache_file.read_text(encoding="utf-8")
            content_hash = hash_file.read_text(encoding="utf-8") if hash_file.exists() else ""
            results[source_name] = {
                "url": url,
                "markdown": markdown,
                "hash": content_hash,
                "cached": True,
            }
            continue

        # Scrape fresh
        result = scrape_url(url)
        markdown = result.get("markdown", "")

        if markdown:
            # Save to cache
            cache_file.write_text(markdown, encoding="utf-8")
            content_hash = compute_content_hash(markdown)
            hash_file.write_text(content_hash, encoding="utf-8")

            results[source_name] = {
                "url": url,
                "markdown": markdown,
                "hash": content_hash,
                "cached": False,
            }
        else:
            results[source_name] = {
                "url": url,
                "markdown": "",
                "hash": "",
                "cached": False,
                "error": result.get("error", "Unknown error"),
            }

    # Update history.json
    history_file = cache_dir / "history.json"
    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []

    history.append({
        "date": today,
        "sources": {
            name: {
                "url": data["url"],
                "hash": data["hash"],
                "cached": data["cached"],
            }
            for name, data in results.items()
        }
    })

    # Keep last 10 audit records
    history = history[-10:]
    history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    return {
        "sources": results,
        "cache_dir": cache_dir,
        "date": today,
    }


def check_for_changes(skill_name: str) -> dict:
    """
    Check if documentation has changed since last audit.

    Returns dict with:
        changed: bool
        changes: list of {source, old_hash, new_hash}
    """
    cache_dir = CACHE_DIR / skill_name
    history_file = cache_dir / "history.json"

    if not history_file.exists():
        return {"changed": True, "changes": [], "reason": "No previous audit"}

    try:
        history = json.loads(history_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"changed": True, "changes": [], "reason": "Corrupted history"}

    if not history:
        return {"changed": True, "changes": [], "reason": "Empty history"}

    last_audit = history[-1]
    doc_sources = get_doc_sources(skill_name)

    changes = []
    for source_name, url in doc_sources.items():
        # Quick scrape to get current hash
        result = scrape_url(url)
        current_hash = compute_content_hash(result.get("markdown", ""))

        old_hash = last_audit.get("sources", {}).get(source_name, {}).get("hash", "")

        if current_hash != old_hash:
            changes.append({
                "source": source_name,
                "old_hash": old_hash,
                "new_hash": current_hash,
            })

    return {
        "changed": len(changes) > 0,
        "changes": changes,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape documentation for deep audit")
    parser.add_argument("skill", help="Skill name to audit")
    parser.add_argument("--list-sources", action="store_true", help="List doc sources without scraping")
    parser.add_argument("--force", action="store_true", help="Ignore cache, force re-scrape")
    parser.add_argument("--check-changes", action="store_true", help="Only check if docs changed")
    parser.add_argument("--output", help="Custom output directory")

    args = parser.parse_args()

    skill_name = args.skill

    # Check skill exists
    skill_path = SKILLS_DIR / skill_name
    if not skill_path.exists():
        print(f"Error: Skill not found: {skill_name}")
        print(f"Available skills: {', '.join(sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir()))[:200]}...")
        sys.exit(1)

    print(f"Deep Audit: {skill_name}")
    print("=" * 50)

    # List sources only
    if args.list_sources:
        doc_sources = get_doc_sources(skill_name)
        if doc_sources:
            print("\nDoc Sources:")
            for name, url in doc_sources.items():
                print(f"  {name}: {url}")
        else:
            print("\nNo doc_sources found. Add to SKILL.md frontmatter:")
            print("  metadata:")
            print("    doc_sources:")
            print('      primary: "https://docs.example.com"')
        return

    # Check changes only
    if args.check_changes:
        print("\nChecking for documentation changes...")
        result = check_for_changes(skill_name)
        if result["changed"]:
            print("Documentation HAS CHANGED:")
            for change in result.get("changes", []):
                print(f"  {change['source']}: {change['old_hash'][:8]} -> {change['new_hash'][:8]}")
            if result.get("reason"):
                print(f"  Reason: {result['reason']}")
        else:
            print("Documentation unchanged since last audit")
        return

    # Full scrape
    print("\nScraping documentation...")
    result = scrape_skill_docs(skill_name, force=args.force)

    if not result["sources"]:
        print("\nNo documentation scraped.")
        return

    print(f"\nResults cached to: {result['cache_dir']}")
    print("\nScraped sources:")
    for name, data in result["sources"].items():
        status = "cached" if data["cached"] else "fresh"
        size = len(data["markdown"])
        print(f"  {name}: {size:,} chars ({status})")
        if data.get("error"):
            print(f"    Error: {data['error']}")

    # Print summary for Claude to use
    print("\n" + "=" * 50)
    print("DOCUMENTATION CONTENT SUMMARY")
    print("=" * 50)

    for name, data in result["sources"].items():
        if data["markdown"]:
            # Print first 500 chars as preview
            preview = data["markdown"][:500].replace("\n", " ")[:200]
            print(f"\n[{name.upper()}] {data['url']}")
            print(f"Preview: {preview}...")
            print(f"Full content: {result['cache_dir']}/{result['date']}_{name}.md")


if __name__ == "__main__":
    main()
