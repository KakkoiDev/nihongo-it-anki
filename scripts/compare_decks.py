#!/usr/bin/env python3
"""Compare two .apkg files by content, to prove a refactor changed nothing.

Written for the jpanki migration, and worth keeping: any change to the build
pipeline can be checked against a deck built before it.

Compares what a learner's collection actually keys on — note GUIDs, field
values, deck IDs, model IDs, tags, media names — and ignores what is free to
change: timestamps, note IDs, CSS formatting, rule order.

    uv run python scripts/compare_decks.py OLD.apkg NEW.apkg [--show-css-diff]

Exits non-zero if anything a collection depends on differs.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path


def load(apkg: Path) -> dict:
    """Extract the content-bearing parts of a deck package."""
    directory = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(apkg) as archive:
        archive.extractall(directory)

    collection = next(
        (directory / name for name in ("collection.anki21", "collection.anki2")
         if (directory / name).exists()),
        None,
    )
    if collection is None:
        raise SystemExit(f"{apkg}: no collection database inside")

    connection = sqlite3.connect(collection)

    notes = {}
    for guid, mid, flds, tags in connection.execute(
        "select guid, mid, flds, tags from notes"
    ):
        notes[guid] = {
            "model_id": mid,
            "fields": flds.split("\x1f"),
            "tags": sorted(tags.split()),
        }

    # Which deck each note's cards live in, keyed by GUID so a changed note id
    # does not register as a difference.
    placement: dict[str, list[int]] = {}
    for guid, did in connection.execute(
        "select n.guid, c.did from cards c join notes n on n.id = c.nid"
    ):
        placement.setdefault(guid, []).append(did)
    for guid in placement:
        placement[guid].sort()

    try:
        decks = {
            int(did): entry["name"]
            for did, entry in json.loads(
                connection.execute("select decks from col").fetchone()[0]
            ).items()
        }
    except (sqlite3.OperationalError, TypeError, KeyError):
        decks = dict(connection.execute("select id, name from decks"))

    try:
        models = {
            int(mid): {"name": entry["name"],
                       "fields": [f["name"] for f in entry["flds"]],
                       "templates": [t["name"] for t in entry["tmpls"]],
                       "css": entry.get("css", "")}
            for mid, entry in json.loads(
                connection.execute("select models from col").fetchone()[0]
            ).items()
        }
    except (sqlite3.OperationalError, TypeError, KeyError):
        models = {}
        for mid, name, config in connection.execute("select id, name, config from notetypes"):
            models[int(mid)] = {"name": name, "fields": [], "templates": [], "css": ""}

    media_names = sorted(json.loads((directory / "media").read_text()).values()) \
        if (directory / "media").exists() else []

    return {
        "notes": notes,
        "placement": placement,
        "decks": decks,
        "models": models,
        "media": media_names,
        "card_count": connection.execute("select count(*) from cards").fetchone()[0],
    }


def compare(old: dict, new: dict) -> list[str]:
    problems: list[str] = []

    old_guids, new_guids = set(old["notes"]), set(new["notes"])
    if lost := old_guids - new_guids:
        problems.append(
            f"{len(lost)} note GUID(s) disappeared — their review history would "
            f"be orphaned: {sorted(lost)[:5]}"
        )
    if gained := new_guids - old_guids:
        problems.append(
            f"{len(gained)} new note GUID(s) — these import as new cards with no "
            f"history: {sorted(gained)[:5]}"
        )

    for guid in sorted(old_guids & new_guids):
        before, after = old["notes"][guid], new["notes"][guid]
        if before["fields"] != after["fields"]:
            for index, (a, b) in enumerate(zip(before["fields"], after["fields"])):
                if a != b:
                    problems.append(f"{guid}: field {index} changed: {a!r} -> {b!r}")
            if len(before["fields"]) != len(after["fields"]):
                problems.append(
                    f"{guid}: field count changed "
                    f"{len(before['fields'])} -> {len(after['fields'])}"
                )
        if before["tags"] != after["tags"]:
            problems.append(f"{guid}: tags changed: {before['tags']} -> {after['tags']}")
        if before["model_id"] != after["model_id"]:
            problems.append(
                f"{guid}: model ID changed {before['model_id']} -> {after['model_id']} "
                f"— this resets review history"
            )
        if old["placement"].get(guid) != new["placement"].get(guid):
            problems.append(
                f"{guid}: moved deck {old['placement'].get(guid)} -> "
                f"{new['placement'].get(guid)}"
            )

    if old["decks"] != new["decks"]:
        for did in sorted(set(old["decks"]) | set(new["decks"])):
            before, after = old["decks"].get(did), new["decks"].get(did)
            if before != after:
                problems.append(f"deck {did}: {before!r} -> {after!r}")

    for mid in sorted(set(old["models"]) | set(new["models"])):
        before, after = old["models"].get(mid), new["models"].get(mid)
        if before is None or after is None:
            problems.append(f"model {mid}: {'added' if before is None else 'removed'}")
            continue
        for key in ("name", "fields", "templates"):
            if before[key] != after[key]:
                problems.append(f"model {mid} {key}: {before[key]!r} -> {after[key]!r}")

    if old["media"] != new["media"]:
        lost_media = set(old["media"]) - set(new["media"])
        gained_media = set(new["media"]) - set(old["media"])
        if lost_media:
            problems.append(f"media dropped: {sorted(lost_media)[:5]}")
        if gained_media:
            problems.append(f"media added: {sorted(gained_media)[:5]}")

    if old["card_count"] != new["card_count"]:
        problems.append(f"card count: {old['card_count']} -> {new['card_count']}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--show-css-diff", action="store_true",
                        help="report CSS changes, which are allowed but worth seeing")
    args = parser.parse_args()

    old, new = load(args.old), load(args.new)
    problems = compare(old, new)

    print(f"{args.old.name}: {len(old['notes'])} notes, {old['card_count']} cards")
    print(f"{args.new.name}: {len(new['notes'])} notes, {new['card_count']} cards")

    if args.show_css_diff:
        for mid in sorted(set(old["models"]) & set(new["models"])):
            before = old["models"][mid]["css"]
            after = new["models"][mid]["css"]
            if before != after:
                print(f"\nmodel {mid} CSS: {len(before)} -> {len(after)} chars "
                      f"(allowed; verify visually)")

    if problems:
        print(f"\n{len(problems)} difference(s) that a collection depends on:")
        for problem in problems[:40]:
            print(f"  {problem}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        return 1

    print("\nidentical in every respect a learner's collection depends on")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
