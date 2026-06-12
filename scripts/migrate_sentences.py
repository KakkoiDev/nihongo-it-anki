#!/usr/bin/env python3
"""Migrate note GUIDs across sentence rewrites so review history survives.

Background:
    create_deck.py derives note GUIDs from the Sentence text
    (genanki.guid_for(Sentence)). When a sentence is rewritten in the CSVs,
    the rebuilt deck contains a NEW guid for that note. Importing it adds a
    duplicate note while the old note keeps the review history. The build
    pipeline records every rewrite in guid-migration-map.csv
    (old_guid, new_guid, old_sentence, new_sentence).

What this script does:
    Takes a user's exported collection (.colpkg/.apkg) or a bare collection
    database (.anki2/.anki21), and for every note whose guid appears as
    old_guid in the map, rewrites it to new_guid. Fields are NOT touched:
    the subsequent deck re-import matches on the new guid and updates the
    fields itself. If the user already imported a rebuilt deck (so both the
    old note and a new duplicate exist), the note with review activity wins,
    the other is deleted.

Typical workflow:
    1. In Anki: File -> Export -> Anki Collection Package (include scheduling)
    2. uv run python scripts/migrate_sentences.py input.colpkg \
           --map guid-migration-map.csv -o migrated.apkg
    3. In Anki: delete the old deck, File -> Import migrated.apkg
    4. File -> Import the rebuilt deck (e.g. it-vocab-complete.apkg);
       rewritten sentences update in place, scheduling intact.

Usage:
    uv run python scripts/migrate_sentences.py INPUT [--map MAP.csv]
        [-o OUTPUT.apkg] [--dry-run]
"""

import argparse
import csv
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from migrate_guids import (  # noqa: E402
    ANKI_DB_NAMES,
    find_db,
    is_zstd,
    pick_winner,
    repack,
    zstd_compress,
    zstd_decompress,
)

DEFAULT_MAP = Path(__file__).parent.parent / "guid-migration-map.csv"


def load_map(map_path: Path) -> dict[str, str]:
    """Read guid-migration-map.csv -> {old_guid: new_guid}."""
    mapping: dict[str, str] = {}
    with open(map_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            mapping[row["old_guid"]] = row["new_guid"]
    return mapping


def delete_notes(conn: sqlite3.Connection, nids: list[int], stats: dict) -> None:
    if not nids:
        return
    ph = ",".join("?" for _ in nids)
    cids = [c[0] for c in conn.execute(
        f"SELECT id FROM cards WHERE nid IN ({ph})", nids).fetchall()]
    if cids:
        cph = ",".join("?" for _ in cids)
        stats["revlog_deleted"] += conn.execute(
            f"SELECT COUNT(*) FROM revlog WHERE cid IN ({cph})", cids
        ).fetchone()[0]
        conn.execute(f"DELETE FROM revlog WHERE cid IN ({cph})", cids)
        conn.execute(f"DELETE FROM cards WHERE id IN ({cph})", cids)
        stats["cards_deleted"] += len(cids)
    conn.execute(f"DELETE FROM notes WHERE id IN ({ph})", nids)
    stats["notes_deleted"] += len(nids)


def migrate(db_path: Path, mapping: dict[str, str], dry_run: bool = False) -> dict:
    """Rewrite mapped guids in-place. Returns a stats dict."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.create_collation(
        "unicase", lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())
    )

    guid_to_nid = {
        guid: nid for nid, guid in conn.execute("SELECT id, guid FROM notes")
    }

    stats = {
        "mapped_guids": len(mapping),
        "guid_updated": 0,
        "not_in_collection": 0,
        "duplicates_resolved": 0,
        "notes_deleted": 0,
        "cards_deleted": 0,
        "revlog_deleted": 0,
    }

    updates: list[tuple[str, int]] = []
    deletions: list[int] = []

    for old_guid, new_guid in mapping.items():
        old_nid = guid_to_nid.get(old_guid)
        if old_nid is None:
            stats["not_in_collection"] += 1
            continue
        new_nid = guid_to_nid.get(new_guid)
        if new_nid is None:
            updates.append((new_guid, old_nid))
            continue
        # Both old note and an already-imported rewrite exist.
        stats["duplicates_resolved"] += 1
        winner = pick_winner(conn, [old_nid, new_nid])
        if winner == old_nid:
            deletions.append(new_nid)
            updates.append((new_guid, old_nid))
        else:
            deletions.append(old_nid)

    stats["guid_updated"] = len(updates)

    if dry_run:
        conn.close()
        return stats

    with conn:
        delete_notes(conn, deletions, stats)
        if updates:
            conn.executemany("UPDATE notes SET guid = ? WHERE id = ?", updates)

    conn.execute("VACUUM")
    conn.close()
    return stats


def run(input_path: Path, map_path: Path, output: Path | None, dry_run: bool) -> dict:
    """Unpack (if zipped), migrate, repack. Returns stats."""
    mapping = load_map(map_path)

    if input_path.suffix in (".anki2", ".anki21"):
        # Bare collection database: migrate in place (used by tests and
        # power users working on a copy).
        return migrate(input_path, mapping, dry_run)

    workdir = Path(tempfile.mkdtemp(prefix="migrate_sentences_"))
    try:
        unpack_dir = workdir / "unpacked"
        unpack_dir.mkdir()
        with zipfile.ZipFile(input_path) as zf:
            zf.extractall(unpack_dir)

        db_path = find_db(unpack_dir)
        compressed = is_zstd(db_path)
        if compressed:
            raw = workdir / "collection.sqlite"
            zstd_decompress(db_path, raw)
        else:
            raw = db_path

        stats = migrate(raw, mapping, dry_run)

        if not dry_run:
            if compressed:
                zstd_compress(raw, db_path)
            out = output or input_path.with_name(input_path.stem + "-migrated.apkg")
            repack(unpack_dir, out)
            stats["output"] = str(out)
        return stats
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite note GUIDs across sentence rewrites (history-preserving)"
    )
    parser.add_argument("input", type=Path,
                        help=".colpkg/.apkg export, or bare .anki2/.anki21")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP,
                        help=f"guid migration map CSV (default: {DEFAULT_MAP})")
    parser.add_argument("-o", "--output", type=Path,
                        help="output .apkg (default: INPUT-migrated.apkg)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found")
        return 1
    if not args.map.exists():
        print(f"Error: map file {args.map} not found")
        return 1

    stats = run(args.input, args.map, args.output, args.dry_run)
    print("Migration" + (" (dry run)" if args.dry_run else "") + ":")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    main()
