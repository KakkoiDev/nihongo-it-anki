#!/usr/bin/env python3
"""Rename Anki subdecks from "Tier N - X" to "Tier 0N - X" in place.

Background:
    Anki sorts subdecks alphabetically by full name path. "Tier 1",
    "Tier 10", "Tier 2" lexicographically sorts as 1, 10, 2 because
    ASCII ' '(0x20) < '0'(0x30) < '2'(0x32). Renaming to "Tier 01",
    "Tier 02", ..., "Tier 10" fixes the order.

    Anki does NOT auto-rename decks on .apkg import. It matches decks
    by full name path: if the apkg contains "Tier 01" and the
    collection has "Tier 1", Anki treats them as different decks and
    creates an empty "Tier 01" alongside the populated "Tier 1". This
    script renames the user's collection so future apkg imports map
    to the existing subdeck.

What this script does:
    Reads decks/<slug>/deck.toml for the NEW (zero-padded) tier names,
    derives the OLD un-padded names by regex (Tier 0N -> Tier N), and
    runs UPDATE on the decks table in collection.anki2. Updates
    decks.mtime_secs, decks.usn, and col.mod so AnkiWeb sync detects
    the change. Does not touch cards, notes, revlog, or media for the
    renamed decks. Card deck assignments (cards.did) point to deck
    IDs, which are unchanged. Review history is preserved.

    Auto-backs up the collection to a .bak-<timestamp> sibling before
    any write. Refuses to proceed if backup fails.

    Skips conflicts gracefully: if both the OLD deck (with cards) and
    the NEW deck (empty stub from a previous botched import) already
    exist, the unique index on decks.name would block the rename.
    Detected up-front and reported; user resolves manually.

    Detects orphan subdecks: decks under the same parent whose tier
    portion is neither in the current deck.toml nor in the pending
    rename map (typically leftovers from a previous deck.toml revision
    where a tier was renamed or split). Reports by default. Pass
    --delete-orphans to also remove them, with revlog tombstones in
    the graves table so AnkiWeb sync propagates the deletion. Refuses
    to delete any orphan with reviews > 0; resolve those manually.

    Handles zstd-compressed collections (Anki 2.1.50+, collection.anki21b)
    the same way migrate_guids.py does.

    Idempotent: rerunning after a successful pass is a no-op.

Implementation notes:
    Anki stores subdeck hierarchy with the ASCII Unit Separator U+001F
    between parent and child, NOT '::'. The double colon is purely a
    UI rendering convention. This script matches against \\x1f when
    reading from decks.name. The earlier version of this script used
    '::' as the separator and silently matched zero rows.

Typical workflow:
    1. Close Anki.
    2. Dry run first:
       uv run python scripts/migrate_deck_names.py \\
         ~/.local/share/Anki2/User\\ 1/collection.anki2 --deck it-vocab \\
         --dry-run
    3. Real run: drop --dry-run.
    4. Reopen Anki. Subdecks now sort 01..10.

Usage:
    uv run python scripts/migrate_deck_names.py COLLECTION --deck SLUG \\
      [--dry-run] [--no-backup]
"""

import argparse
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config

# Anki stores subdeck hierarchy with U+001F (Unit Separator) between
# parent and child names. The "::" shown in Anki's UI is a render-time
# substitution. Always match the on-disk form.
DECK_SEPARATOR = "\x1f"

# Match "Tier 0N" with a single digit after the zero. Used to derive
# the OLD un-padded name from the NEW zero-padded one in deck.toml.
ZERO_PAD_PATTERN = re.compile(r"Tier 0(\d)")

# anki21b zstd magic number
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def is_zstd(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(4) == ZSTD_MAGIC


def zstd_decompress(src: Path, dst: Path) -> None:
    subprocess.run(["zstd", "-d", "-q", "-f", str(src), "-o", str(dst)], check=True)


def zstd_compress(src: Path, dst: Path) -> None:
    subprocess.run(["zstd", "-q", "-f", str(src), "-o", str(dst)], check=True)


def display(internal_name: str) -> str:
    """Render an on-disk deck name with the user-facing :: separator."""
    return internal_name.replace(DECK_SEPARATOR, "::")


def build_rename_map(slug: str) -> dict[str, str]:
    """Return {old_internal_name -> new_internal_name} from deck.toml.

    Names use the on-disk separator (\\x1f) so they match decks.name
    rows directly. OLD names are derived by undoing the zero-pad on
    the NEW names from deck.toml; rerunning after deck.toml changes
    is the supported workflow.
    """
    config = load_deck_config(slug)
    rename: dict[str, str] = {}
    for new_tier in config.tier_names.values():
        old_tier = ZERO_PAD_PATTERN.sub(r"Tier \1", new_tier)
        if old_tier == new_tier:
            continue
        old_full = f"{config.name}{DECK_SEPARATOR}{old_tier}"
        new_full = f"{config.name}{DECK_SEPARATOR}{new_tier}"
        rename[old_full] = new_full
    return rename


def find_orphans(
    existing: list[tuple[int, str]],
    slug: str,
    rename: dict[str, str],
) -> list[tuple[int, str]]:
    """Return [(deck_id, internal_name), ...] for orphan subdecks.

    An orphan is a direct child of the parent deck (name starts with
    parent\\x1f) whose tier portion is neither in the current
    deck.toml tier_names nor in the pending rename's OLD names.
    Deeper-nested subdecks (>1 level under parent) are skipped to
    avoid touching user-created decks.
    """
    config = load_deck_config(slug)
    parent_prefix = f"{config.name}{DECK_SEPARATOR}"
    current_tiers = set(config.tier_names.values())
    old_tier_parts = {
        old[len(parent_prefix):] for old in rename
        if old.startswith(parent_prefix)
    }

    orphans: list[tuple[int, str]] = []
    for did, name in existing:
        if not name.startswith(parent_prefix):
            continue
        tier_part = name[len(parent_prefix):]
        if DECK_SEPARATOR in tier_part:
            continue  # nested >1 level, leave alone
        if tier_part in current_tiers or tier_part in old_tier_parts:
            continue
        orphans.append((did, name))
    return orphans


def orphan_metadata(
    conn: sqlite3.Connection, orphans: list[tuple[int, str]]
) -> dict[int, dict]:
    """Return per-orphan {card_ids, note_ids, reviews}."""
    meta: dict[int, dict] = {}
    for did, _ in orphans:
        card_rows = conn.execute(
            "SELECT id, nid FROM cards WHERE did = ?", (did,)
        ).fetchall()
        card_ids = [r[0] for r in card_rows]
        note_ids = {r[1] for r in card_rows}
        reviews = 0
        if card_ids:
            placeholders = ",".join("?" for _ in card_ids)
            reviews = conn.execute(
                f"SELECT COUNT(*) FROM revlog WHERE cid IN ({placeholders})",
                card_ids,
            ).fetchone()[0]
        meta[did] = {
            "card_ids": card_ids,
            "note_ids": note_ids,
            "reviews": reviews,
        }
    return meta


def delete_orphan_decks(
    conn: sqlite3.Connection,
    orphans: list[tuple[int, str]],
    meta: dict[int, dict],
) -> dict[str, int]:
    """Delete orphan decks: cards, dependent-only notes, revlog, deck row.

    Inserts graves tombstones (type 0=card, 1=note, 2=deck, usn=-1)
    so AnkiWeb sync propagates the deletion instead of restoring it.

    A note is deleted only if it has no cards in non-orphan decks.
    This keeps notes shared with other decks intact.
    """
    orphan_dids = {did for did, _ in orphans}
    deleted = {"cards": 0, "notes": 0, "revlog": 0, "decks": 0}

    for did, _ in orphans:
        m = meta[did]
        card_ids = m["card_ids"]
        note_ids = m["note_ids"]

        if card_ids:
            cph = ",".join("?" for _ in card_ids)
            rev_deleted = conn.execute(
                f"DELETE FROM revlog WHERE cid IN ({cph})", card_ids
            ).rowcount
            deleted["revlog"] += rev_deleted
            conn.executemany(
                "INSERT OR IGNORE INTO graves (oid, type, usn) "
                "VALUES (?, 0, -1)",
                [(cid,) for cid in card_ids],
            )
            conn.execute(f"DELETE FROM cards WHERE id IN ({cph})", card_ids)
            deleted["cards"] += len(card_ids)

        if note_ids:
            nph = ",".join("?" for _ in note_ids)
            still_used = {
                row[0] for row in conn.execute(
                    f"SELECT DISTINCT nid FROM cards WHERE nid IN ({nph})",
                    list(note_ids),
                )
            }
            to_delete = note_ids - still_used
            if to_delete:
                dph = ",".join("?" for _ in to_delete)
                conn.executemany(
                    "INSERT OR IGNORE INTO graves (oid, type, usn) "
                    "VALUES (?, 1, -1)",
                    [(nid,) for nid in to_delete],
                )
                conn.execute(
                    f"DELETE FROM notes WHERE id IN ({dph})",
                    list(to_delete),
                )
                deleted["notes"] += len(to_delete)

        conn.execute("DELETE FROM decks WHERE id = ?", (did,))
        conn.execute(
            "INSERT OR IGNORE INTO graves (oid, type, usn) VALUES (?, 2, -1)",
            (did,),
        )
        deleted["decks"] += 1

    return deleted


def backup_collection(path: Path) -> Path:
    """Copy `path` to a sibling `.bak-<timestamp>` and return the new path.

    Microsecond timestamp avoids collision on rapid reruns. Raises on
    failure so the caller never proceeds without a safety copy.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    if backup.exists():
        raise FileExistsError(f"Backup already exists: {backup}")
    shutil.copy2(path, backup)
    return backup


def migrate(
    db_path: Path,
    rename: dict[str, str],
    slug: str,
    *,
    dry_run: bool,
    delete_orphans: bool,
) -> dict:
    """Apply rename map to decks table; optionally delete orphan subdecks.

    Bumps decks.mtime_secs (seconds), sets decks.usn = -1 (needs sync),
    and bumps col.mod (milliseconds) so Anki and AnkiWeb sync recognize
    the change.

    Conflict handling: a UNIQUE index on decks.name blocks any UPDATE
    whose target collides with an existing row. Detected up-front by
    comparing each target against the existing name set; conflicts are
    skipped and reported (we cannot safely guess merge intent).

    Orphan handling: subdecks under the parent that are neither in
    deck.toml nor pending rename are reported. With delete_orphans=True,
    they are removed (cards, dependent-only notes, revlog, deck row)
    with graves tombstones written for sync. Refuses if any orphan has
    reviews > 0.

    Verifies each rename by SELECTing the row back after commit.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.create_collation(
        "unicase",
        lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()),
    )

    existing = conn.execute("SELECT id, name FROM decks").fetchall()
    by_name = {name: did for did, name in existing}
    new_names = set(rename.values())

    plan: list[tuple[int, str, str]] = []
    conflicts: list[tuple[int, str, str, int]] = []
    already_correct: list[str] = []
    untouched = 0

    for did, name in existing:
        if name in rename:
            target = rename[name]
            blocker = by_name.get(target)
            if blocker is not None and blocker != did:
                conflicts.append((did, name, target, blocker))
            else:
                plan.append((did, name, target))
        elif name in new_names:
            already_correct.append(name)
        else:
            untouched += 1

    orphans = find_orphans(existing, slug, rename)
    o_meta = orphan_metadata(conn, orphans)

    stats = {
        "total_decks": len(existing),
        "plan": plan,
        "conflicts": conflicts,
        "already_correct": already_correct,
        "untouched": untouched,
        "verified": 0,
        "orphans": orphans,
        "orphan_meta": o_meta,
        "orphans_deleted": None,  # set after deletion
    }

    if dry_run or (not plan and not (delete_orphans and orphans)):
        conn.close()
        return stats

    if delete_orphans:
        unsafe = [
            (did, name) for did, name in orphans
            if o_meta[did]["reviews"] > 0
        ]
        if unsafe:
            conn.close()
            raise RuntimeError(
                "Cannot --delete-orphans: the following have reviews > 0. "
                "Move cards or delete manually in Anki UI first.\n"
                + "\n".join(
                    f"  {display(name)!r}: {o_meta[did]['reviews']} reviews"
                    for did, name in unsafe
                )
            )

    now_secs = int(time.time())
    now_ms = now_secs * 1000

    try:
        with conn:
            if plan:
                conn.executemany(
                    "UPDATE decks SET name = ?, mtime_secs = ?, usn = -1 "
                    "WHERE id = ?",
                    [(new, now_secs, did) for did, _, new in plan],
                )
            if delete_orphans and orphans:
                stats["orphans_deleted"] = delete_orphan_decks(
                    conn, orphans, o_meta
                )
            conn.execute(
                "UPDATE col SET mod = ?, usn = -1", (now_ms,)
            )
    except sqlite3.IntegrityError as e:
        conn.close()
        raise RuntimeError(
            f"UPDATE failed unique-name constraint: {e}. "
            f"A target name already exists on another deck that the "
            f"pre-check missed. Re-run with --dry-run for diagnosis."
        ) from e

    for did, _, new in plan:
        actual = conn.execute(
            "SELECT name FROM decks WHERE id = ?", (did,)
        ).fetchone()
        if actual and actual[0] == new:
            stats["verified"] += 1

    conn.execute("VACUUM")
    conn.close()
    return stats


def print_stats(stats: dict, *, dry_run: bool, delete_orphans: bool) -> None:
    print(f"Total decks scanned:  {stats['total_decks']}")
    print(f"Planned renames:      {len(stats['plan'])}")
    if not dry_run:
        print(f"Verified after write: {stats['verified']}/{len(stats['plan'])}")
    print(f"Conflicts (skipped):  {len(stats['conflicts'])}")
    print(f"Already correct:      {len(stats['already_correct'])}")
    print(f"Orphans detected:     {len(stats['orphans'])}")
    print(f"Untouched (other):    {stats['untouched']}")

    if stats["plan"]:
        print("\nRenamed:" if not dry_run else "\nPlanned:")
        for _, old, new in stats["plan"]:
            print(f"  {display(old)!r}")
            print(f"    -> {display(new)!r}")

    if stats["conflicts"]:
        print("\nConflicts (NOT renamed):")
        for _, old, new, blocker_did in stats["conflicts"]:
            print(
                f"  {display(old)!r} -> {display(new)!r}  "
                f"(target name already on deck id {blocker_did})"
            )
        print(
            "\n  Resolve in Anki: right-click the empty duplicate "
            "subdeck and Delete, then re-run this script."
        )

    if stats["orphans"]:
        meta = stats["orphan_meta"]
        heading = "Orphans deleted:" if (
            stats["orphans_deleted"] is not None
        ) else "Orphans detected (not deleted):"
        print(f"\n{heading}")
        for did, name in stats["orphans"]:
            m = meta[did]
            print(
                f"  {display(name)!r}  "
                f"(deck id {did}: {len(m['card_ids'])} cards, "
                f"{len(m['note_ids'])} notes, {m['reviews']} reviews)"
            )
        if stats["orphans_deleted"] is not None:
            d = stats["orphans_deleted"]
            print(
                f"\n  Removed: {d['cards']} cards, {d['notes']} notes, "
                f"{d['revlog']} revlog rows, {d['decks']} deck rows. "
                f"Graves written for AnkiWeb sync."
            )
        elif not delete_orphans:
            print(
                "\n  Re-run with --delete-orphans to remove them "
                "(refused if any has reviews > 0).\n"
                "  Skip if their content is unique to that deck."
            )


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
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the automatic .bak-<timestamp> safety copy. Only set "
             "this if you have your own backup. Ignored under --dry-run.",
    )
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help="Also delete orphan subdecks (under the same parent but not "
             "in current deck.toml). Refused if any orphan has reviews > 0; "
             "resolve those manually first.",
    )
    args = parser.parse_args()

    if not args.collection.exists():
        print(f"Error: collection not found: {args.collection}", file=sys.stderr)
        return 1

    rename = build_rename_map(args.deck)
    if not rename and not args.delete_orphans:
        print(
            f"No renames to apply: deck.toml for '{args.deck}' is not "
            f"zero-padded (Tier 0N pattern not found). Pass --delete-orphans "
            f"to scan for orphan subdecks anyway."
        )
        return 0

    print(f"Collection: {args.collection}")
    print(f"Deck slug:  {args.deck}")
    print("Target renames (from deck.toml):")
    for old, new in rename.items():
        print(f"  {display(old)!r}")
        print(f"    -> {display(new)!r}")
    print()

    if not args.dry_run and not args.no_backup:
        try:
            backup_path = backup_collection(args.collection)
            print(f"Backup created: {backup_path}\n")
        except Exception as e:
            print(
                f"Error: backup failed: {e}\n"
                f"Refusing to proceed without a backup. Use --no-backup "
                f"to override (only if you have your own).",
                file=sys.stderr,
            )
            return 1

    db_path = args.collection
    compressed_path: Path | None = None
    tmp_path: Path | None = None

    try:
        if is_zstd(db_path):
            with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            compressed_path = db_path
            zstd_decompress(compressed_path, tmp_path)
            db_path = tmp_path
            print(f"Decompressed zstd -> {db_path}")

        try:
            stats = migrate(
                db_path, rename, args.deck,
                dry_run=args.dry_run,
                delete_orphans=args.delete_orphans,
            )
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                print(
                    "Error: database is locked. Close Anki before "
                    "running this script.",
                    file=sys.stderr,
                )
                return 1
            raise

        print_stats(stats, dry_run=args.dry_run, delete_orphans=args.delete_orphans)

        if not args.dry_run and compressed_path is not None:
            zstd_compress(db_path, compressed_path)
            print(f"\nRecompressed to: {compressed_path}")

        if args.dry_run:
            print("\n(dry run, no changes written)")

        if (
            not stats["plan"]
            and not stats["already_correct"]
            and not stats["orphans"]
        ):
            parent = load_deck_config(args.deck).name
            print(
                "\nWarning: zero decks matched. Common causes:\n"
                "  - Wrong collection path (you have multiple Anki profiles).\n"
                f"  - Parent deck name in deck.toml ({parent!r}) does "
                "not match what's in your Anki collection. Compare to\n"
                "    what appears in Anki's deck browser.",
                file=sys.stderr,
            )
            return 2

        return 0

    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
