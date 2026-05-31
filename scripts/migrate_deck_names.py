#!/usr/bin/env python3
"""Rename Anki subdecks from "Tier N - X" to "Tier 0N - X" in place.

Background:
    Anki sorts subdecks alphabetically by full name path. "Tier 1",
    "Tier 10", "Tier 2" lexicographically sorts as 1, 10, 2 because
    ASCII ' '(0x20) < '0'(0x30) < '2'(0x32). Renaming to "Tier 01",
    "Tier 02", ..., "Tier 10" fixes the order.

    Anki does NOT auto-rename decks on .apkg import. It matches decks by
    full name path: if the apkg contains "Tier 01" and the collection has
    "Tier 1", Anki treats them as different decks and creates an empty
    "Tier 01" alongside the populated "Tier 1". This script renames the
    user's collection so future apkg imports map to the right subdeck.

What this script does:
    Reads decks/<slug>/deck.toml for the NEW (zero-padded) tier names,
    derives the OLD un-padded names by regex (Tier 0N -> Tier N), and
    runs UPDATE on the decks table in collection.anki2. Does not touch
    cards, notes, revlog, or media. Card deck assignments (cards.did)
    point to deck IDs, which are unchanged. Review history is preserved.

    Handles zstd-compressed collections (Anki 2.1.50+, collection.anki21b)
    the same way migrate_guids.py does.

    Idempotent: rerunning after a successful pass is a no-op.

Typical workflow:
    1. Close Anki.
    2. Dry run first:
       uv run python scripts/migrate_deck_names.py \\
         ~/.local/share/Anki2/User\\ 1/collection.anki2 --deck it-vocab \\
         --dry-run
    3. Real run: drop --dry-run.
    4. Reopen Anki. Subdecks now sort 01..10.

Usage:
    uv run python scripts/migrate_deck_names.py COLLECTION --deck SLUG [--dry-run]
"""

import argparse
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config

ZERO_PAD_PATTERN = re.compile(r"Tier 0(\d)")


def is_zstd(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == b"\x28\xb5\x2f\xfd"


def zstd_decompress(src: Path, dst: Path) -> None:
    subprocess.run(["zstd", "-d", "-q", "-f", str(src), "-o", str(dst)], check=True)


def zstd_compress(src: Path, dst: Path) -> None:
    subprocess.run(["zstd", "-q", "-f", str(src), "-o", str(dst)], check=True)


def build_rename_map(slug: str) -> dict[str, str]:
    """Return {old_full_name -> new_full_name} from deck.toml.

    Derives OLD names from NEW names by undoing the zero-pad: 'Tier 0N'
    becomes 'Tier N'. Only entries that actually change are included; if
    deck.toml is not zero-padded, returns {}.
    """
    config = load_deck_config(slug)
    rename: dict[str, str] = {}
    for new_tier in config.tier_names.values():
        old_tier = ZERO_PAD_PATTERN.sub(r"Tier \1", new_tier)
        if old_tier == new_tier:
            continue
        old_full = f"{config.name}::{old_tier}"
        new_full = f"{config.name}::{new_tier}"
        rename[old_full] = new_full
    return rename


def migrate(db_path: Path, rename: dict[str, str], dry_run: bool) -> dict:
    """Apply the rename map to the decks table. Returns stats."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.create_collation(
        "unicase",
        lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()),
    )

    existing = conn.execute("SELECT id, name FROM decks").fetchall()
    stats = {
        "total_decks": len(existing),
        "renamed": [],
        "already_correct": 0,
        "no_match": 0,
    }
    new_names = set(rename.values())

    updates: list[tuple[str, int]] = []
    for did, name in existing:
        if name in rename:
            updates.append((rename[name], did))
            stats["renamed"].append((name, rename[name]))
        elif name in new_names:
            stats["already_correct"] += 1
        else:
            stats["no_match"] += 1

    if dry_run:
        conn.close()
        return stats

    if updates:
        with conn:
            conn.executemany(
                "UPDATE decks SET name = ? WHERE id = ?", updates
            )
        conn.execute("VACUUM")

    conn.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rename Anki subdecks to zero-padded tier numbers in place.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "collection",
        type=Path,
        help="Path to collection.anki2 or collection.anki21b",
    )
    parser.add_argument(
        "--deck",
        type=str,
        required=True,
        help="Deck slug whose tier names to migrate (e.g. it-vocab)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing",
    )
    args = parser.parse_args()

    if not args.collection.exists():
        print(f"Error: collection not found: {args.collection}", file=sys.stderr)
        return 1

    rename = build_rename_map(args.deck)
    if not rename:
        print(
            f"No renames to apply: deck.toml for '{args.deck}' is not "
            f"zero-padded (Tier 0N pattern not found)."
        )
        return 0

    print(f"Collection: {args.collection}")
    print(f"Deck slug:  {args.deck}")
    print("Planned renames:")
    for old, new in rename.items():
        print(f"  {old!r}")
        print(f"    -> {new!r}")
    print()

    db_path = args.collection
    compressed_path: Path | None = None
    if is_zstd(db_path):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        compressed_path = db_path
        zstd_decompress(compressed_path, tmp_path)
        db_path = tmp_path
        print(f"Decompressed zstd -> {db_path}")

    try:
        stats = migrate(db_path, rename, dry_run=args.dry_run)
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            print(
                "Error: database is locked. Close Anki before running this "
                "script.",
                file=sys.stderr,
            )
            if compressed_path is not None:
                db_path.unlink()
            return 1
        raise

    print(f"Total decks scanned:  {stats['total_decks']}")
    print(f"Decks renamed:        {len(stats['renamed'])}")
    print(f"Already correct:      {stats['already_correct']}")
    print(f"Other (unchanged):    {stats['no_match']}")
    if stats["renamed"]:
        print("\nRenamed:")
        for old, new in stats["renamed"]:
            print(f"  {old!r}")
            print(f"    -> {new!r}")

    if args.dry_run:
        print("\n(dry run, no changes written)")
        if compressed_path is not None:
            db_path.unlink()
        return 0

    if compressed_path is not None:
        zstd_compress(db_path, compressed_path)
        db_path.unlink()
        print(f"\nRecompressed to: {compressed_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
