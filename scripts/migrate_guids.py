#!/usr/bin/env python3
"""Migrate note GUIDs in an Anki .apkg so they match the stable sentence-based
GUIDs produced by scripts/create_deck.py (genanki.guid_for(Sentence)).

Background:
    Before commit 30ddf37, create_deck.py let genanki generate random GUIDs on
    every build. Reimporting a new build into Anki created duplicate notes
    instead of updating existing ones. Commit 30ddf37 switched to stable GUIDs
    derived from the Sentence field (field 0), but users who already imported
    older builds still have notes with random GUIDs in their collection.

What this script does:
    Takes a user's exported .apkg (File -> Export -> Anki Collection Package),
    rewrites every note's guid to guid_for(field[0]), and preserves all cards,
    reviews, revlog, and media. When duplicates exist (an old random-guid note
    and a new stable-guid note for the same sentence), keeps the one with
    review activity and deletes the other.

Typical workflow:
    1. In Anki: File -> Export -> Anki Collection Package (include scheduling)
    2. uv run python scripts/migrate_guids.py input.colpkg -o migrated.apkg
    3. In Anki: delete the old deck, then File -> Import migrated.apkg
    4. Future builds will now update existing notes instead of duplicating.

Usage:
    uv run python scripts/migrate_guids.py INPUT.apkg [-o OUTPUT.apkg] [--dry-run]
"""

import argparse
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import genanki

# anki21b: zstd-compressed sqlite (Anki 2.1.50+)
# anki21/anki2: raw sqlite (older exports)
ANKI_DB_NAMES = ("collection.anki21b", "collection.anki21", "collection.anki2")


def find_db(unpack_dir: Path) -> Path:
    for name in ANKI_DB_NAMES:
        candidate = unpack_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No Anki database found in {unpack_dir} (expected one of {ANKI_DB_NAMES})"
    )


def is_zstd(path: Path) -> bool:
    """Anki 2.1.50+ stores the collection as zstd-compressed sqlite in
    collection.anki21b. Detect by the zstd magic number."""
    with open(path, "rb") as f:
        return f.read(4) == b"\x28\xb5\x2f\xfd"


def zstd_decompress(src: Path, dst: Path) -> None:
    subprocess.run(
        ["zstd", "-d", "-q", "-f", str(src), "-o", str(dst)], check=True
    )


def zstd_compress(src: Path, dst: Path) -> None:
    subprocess.run(
        ["zstd", "-q", "-f", str(src), "-o", str(dst)], check=True
    )


def card_activity(conn: sqlite3.Connection, nid: int) -> tuple[int, int]:
    """Return (total_reps, revlog_count) for cards belonging to a note."""
    reps = conn.execute(
        "SELECT COALESCE(SUM(reps), 0) FROM cards WHERE nid = ?", (nid,)
    ).fetchone()[0]
    revlog_count = conn.execute(
        "SELECT COUNT(*) FROM revlog WHERE cid IN (SELECT id FROM cards WHERE nid = ?)",
        (nid,),
    ).fetchone()[0]
    return reps, revlog_count


def pick_winner(conn: sqlite3.Connection, nids: list[int]) -> int:
    """From duplicate nids for the same stable GUID, pick the one to keep.
    Prefer the note with any review activity; tiebreak by oldest nid."""
    best_nid = nids[0]
    best_score = card_activity(conn, best_nid)
    for nid in nids[1:]:
        score = card_activity(conn, nid)
        if score > best_score or (score == best_score and nid < best_nid):
            best_nid = nid
            best_score = score
    return best_nid


def retarget_model(conn: sqlite3.Connection, target_mid: int) -> tuple[int, int]:
    """Rewrite the note type id so it matches a deck built with the given
    model_id (e.g. genanki config.model_id). Required when reimporting on
    top of a migrated deck: if model ids differ, Anki creates a new note
    type and new cards, losing scheduling on the old cards.

    Returns (old_mid, target_mid). No-op if single model already matches.
    New-format dbs have notetypes/fields/templates tables; old-format dbs
    keep the model list in col.models JSON.
    """
    has_notetypes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='notetypes'"
    ).fetchone() is not None

    if has_notetypes:
        ids = [r[0] for r in conn.execute("SELECT id FROM notetypes").fetchall()]
        if len(ids) != 1:
            raise RuntimeError(
                f"Expected a single note type, found {len(ids)}: {ids}. "
                f"Refusing to retarget to avoid ambiguity."
            )
        old = ids[0]
        if old == target_mid:
            return old, target_mid
        conn.execute("UPDATE notetypes SET id = ? WHERE id = ?", (target_mid, old))
        conn.execute("UPDATE fields SET ntid = ? WHERE ntid = ?", (target_mid, old))
        conn.execute("UPDATE templates SET ntid = ? WHERE ntid = ?", (target_mid, old))
        conn.execute("UPDATE notes SET mid = ? WHERE mid = ?", (target_mid, old))
        return old, target_mid

    raise RuntimeError(
        "Old-format (col.models JSON) retargeting not implemented. "
        "Export from a recent Anki (2.1.50+) to get notetypes tables."
    )


def migrate(db_path: Path, dry_run: bool = False, target_mid: int | None = None) -> dict:
    """Rewrite note GUIDs in-place. Returns a stats dict."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    # Anki defines a 'unicase' collation in its binary; without it, VACUUM
    # and any index touch on collated columns fails. Register a dummy that
    # falls back to case-insensitive comparison.
    conn.create_collation("unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))

    rows = conn.execute("SELECT id, guid, flds FROM notes").fetchall()
    stats = {
        "total_notes": len(rows),
        "already_stable": 0,
        "guid_updated": 0,
        "duplicate_groups": 0,
        "notes_deleted": 0,
        "cards_deleted": 0,
        "revlog_deleted": 0,
    }

    # stable_guid -> [(nid, old_guid)]
    by_stable: dict[str, list[tuple[int, str]]] = {}
    for nid, old_guid, flds in rows:
        sentence = flds.split("\x1f")[0]
        stable = genanki.guid_for(sentence)
        by_stable.setdefault(stable, []).append((nid, old_guid))

    updates: list[tuple[str, int]] = []
    deletions: list[int] = []

    for stable, notes in by_stable.items():
        if len(notes) == 1:
            nid, old_guid = notes[0]
            if old_guid == stable:
                stats["already_stable"] += 1
            else:
                updates.append((stable, nid))
            continue

        stats["duplicate_groups"] += 1
        nids = [nid for nid, _ in notes]
        winner = pick_winner(conn, nids)
        for nid, old_guid in notes:
            if nid == winner:
                if old_guid == stable:
                    stats["already_stable"] += 1
                else:
                    updates.append((stable, nid))
            else:
                deletions.append(nid)

    stats["guid_updated"] = len(updates)

    if dry_run:
        conn.close()
        return stats

    with conn:
        if updates:
            conn.executemany("UPDATE notes SET guid = ? WHERE id = ?", updates)
        if deletions:
            placeholders = ",".join("?" for _ in deletions)
            cards = conn.execute(
                f"SELECT id FROM cards WHERE nid IN ({placeholders})", deletions
            ).fetchall()
            cids = [c[0] for c in cards]
            stats["cards_deleted"] = len(cids)
            if cids:
                cid_placeholders = ",".join("?" for _ in cids)
                stats["revlog_deleted"] = conn.execute(
                    f"SELECT COUNT(*) FROM revlog WHERE cid IN ({cid_placeholders})",
                    cids,
                ).fetchone()[0]
                conn.execute(
                    f"DELETE FROM revlog WHERE cid IN ({cid_placeholders})", cids
                )
                conn.execute(
                    f"DELETE FROM cards WHERE id IN ({cid_placeholders})", cids
                )
            conn.execute(
                f"DELETE FROM notes WHERE id IN ({placeholders})", deletions
            )
            stats["notes_deleted"] = len(deletions)

    if target_mid is not None and not dry_run:
        old, new = retarget_model(conn, target_mid)
        stats["model_retarget"] = f"{old} -> {new}"
        conn.commit()

    conn.execute("VACUUM")
    conn.close()
    return stats


def repack(unpack_dir: Path, output: Path) -> None:
    """Zip unpack_dir contents into output (an .apkg)."""
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(unpack_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(unpack_dir))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate Anki note GUIDs to stable sentence-based format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", type=Path, help="Input .apkg or .colpkg file")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Output .apkg path (default: INPUT-migrated.apkg)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would change without writing output",
    )
    parser.add_argument(
        "--model-id", type=int, default=None,
        help="Rewrite the note type id to this value so a follow-up import "
             "of a deck built with the same model_id updates in place "
             "instead of creating new cards (losing scheduling).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    output = args.output or args.input.with_name(
        args.input.stem + "-migrated.apkg"
    )

    with tempfile.TemporaryDirectory() as tmp:
        unpack_dir = Path(tmp)
        with zipfile.ZipFile(args.input) as zf:
            zf.extractall(unpack_dir)

        db_path = find_db(unpack_dir)
        print(f"Input:    {args.input}")
        print(f"Database: {db_path.name}")

        compressed_path = None
        if is_zstd(db_path):
            compressed_path = db_path
            db_path = unpack_dir / (db_path.name + ".sqlite")
            zstd_decompress(compressed_path, db_path)
            print(f"Decompressed zstd -> {db_path.name}")

        stats = migrate(db_path, dry_run=args.dry_run, target_mid=args.model_id)

        print()
        print(f"Total notes:        {stats['total_notes']}")
        print(f"Already stable:     {stats['already_stable']}")
        print(f"GUIDs to rewrite:   {stats['guid_updated']}")
        print(f"Duplicate groups:   {stats['duplicate_groups']}")
        print(f"Notes to delete:    {stats['notes_deleted']}")
        print(f"Cards to delete:    {stats['cards_deleted']}")
        print(f"Revlog to delete:   {stats['revlog_deleted']}")
        if "model_retarget" in stats:
            print(f"Model retarget:     {stats['model_retarget']}")

        if args.dry_run:
            print("\n(dry run, no output written)")
            return 0

        if compressed_path is not None:
            zstd_compress(db_path, compressed_path)
            db_path.unlink()

        repack(unpack_dir, output)

    print(f"\nWrote: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
