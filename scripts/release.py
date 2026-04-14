#!/usr/bin/env python3
"""Create a GitHub release for a deck with its .apkg files as assets.

Tags use a {deck}/{version} namespace so each deck has independent versioning.

Usage:
    uv run python scripts/release.py --deck it-vocab --version v4.0 --title "Card model update"
    uv run python scripts/release.py --deck it-kundoku --version v1.0 --title "Initial release"
    uv run python scripts/release.py --deck it-vocab --version v4.0 --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config, list_decks

PROJECT_ROOT = Path(__file__).parent.parent


def find_assets(slug: str, tier_count: int) -> list[Path]:
    """Find all .apkg files for a deck."""
    assets = []
    combined = PROJECT_ROOT / f"{slug}-complete.apkg"
    if combined.exists():
        assets.append(combined)
    for tier in range(1, tier_count + 1):
        tier_file = PROJECT_ROOT / f"{slug}-tier{tier}.apkg"
        if tier_file.exists():
            assets.append(tier_file)
    return assets


def main():
    parser = argparse.ArgumentParser(description="Create a GitHub release for a deck")
    parser.add_argument("--deck", type=str,
                        help="Deck slug (e.g. it-vocab, it-kundoku)")
    parser.add_argument("--version", type=str,
                        help="Version tag (e.g. v4.0)")
    parser.add_argument("--title", type=str, default="",
                        help="Release title (appended after version)")
    parser.add_argument("--notes", type=str, default="",
                        help="Release notes (markdown)")
    parser.add_argument("--notes-file", type=str, default="",
                        help="File containing release notes")
    parser.add_argument("--draft", action="store_true",
                        help="Create as draft release")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without creating the release")
    parser.add_argument("--list-decks", action="store_true",
                        help="List available decks and exit")

    args = parser.parse_args()

    if args.list_decks:
        for slug in list_decks():
            cfg = load_deck_config(slug)
            print(f"  {slug}: {cfg.name} ({cfg.tier_count} tiers)")
        sys.exit(0)

    if not args.deck or not args.version:
        parser.error("--deck and --version are required")

    config = load_deck_config(args.deck)
    assets = find_assets(config.slug, config.tier_count)

    if not assets:
        print(f"Error: no .apkg files found for {config.slug}")
        print(f"Run: uv run python scripts/create_deck.py --deck {config.slug} --combined --all")
        sys.exit(1)

    tag = f"{config.slug}/{args.version}"
    title = f"{config.name} {args.version}"
    if args.title:
        title += f" - {args.title}"

    print(f"Deck:    {config.name} ({config.slug})")
    print(f"Tag:     {tag}")
    print(f"Title:   {title}")
    print(f"Assets:  {len(assets)} files")
    for a in assets:
        size_mb = a.stat().st_size / (1024 * 1024)
        print(f"  - {a.name} ({size_mb:.1f} MB)")

    if args.dry_run:
        print("\n(dry run — no release created)")
        sys.exit(0)

    cmd = ["gh", "release", "create", tag, "--title", title]

    if args.draft:
        cmd.append("--draft")

    if args.notes_file:
        cmd.extend(["--notes-file", args.notes_file])
    elif args.notes:
        cmd.extend(["--notes", args.notes])
    else:
        cmd.extend(["--notes", ""])

    for asset in assets:
        cmd.append(str(asset))

    print(f"\nCreating release...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}")
        sys.exit(1)

    print(result.stdout.strip())
    print("Done!")


if __name__ == "__main__":
    main()
