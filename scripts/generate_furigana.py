#!/usr/bin/env python3
"""Fill the Pronunciation column from the Sentence column using UniDic.

Writes 漢字【よみ】 annotations in the same convention the hand-authored rows use:
one bracket group per kanji run, so okurigana stays outside the brackets
(聞【き】き取【と】れません, not 聞き取【ききと】れません).

Readings come from the same fugashi/UniDic tagger that
scripts/check_pronunciation.py verifies against, so generated rows agree with
the checker by construction. A token whose reading cannot be aligned to its
surface is left unannotated and reported; those need a hand-written reading.

Only empty Pronunciation cells are filled unless --force is given, because the
column is the TTS input and editing it re-records audio. Even under --force a
non-empty cell survives when a token in that row could not be aligned, so a
hand-written reading is never traded for a partly unannotated one.

Usage:
    uv run python scripts/generate_furigana.py --deck agentic-lab
    uv run python scripts/generate_furigana.py --deck agentic-lab --tier 9
    uv run python scripts/generate_furigana.py --deck agentic-lab --dry-run
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import fugashi

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config

tagger = fugashi.Tagger()

KANJI = re.compile(r"[一-鿿㐀-䶿々]")
KANJI_RUN = re.compile(r"[一-鿿㐀-䶿々]+")


def kata_to_hira(text: str) -> str:
    return "".join(
        chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c
        for c in text
    )


def token_reading(token) -> str | None:
    """Hiragana reading of a token, or None if UniDic has none."""
    for attr in ("kana", "pron"):
        value = getattr(token.feature, attr, None)
        if value and value != "*":
            return kata_to_hira(value)
    return None


def annotate(surface: str, reading: str) -> str | None:
    """Annotate the kanji runs of `surface` with their share of `reading`.

    Builds a regex from the surface - kanji runs become lazy captures, kana runs
    become literals - and matches it against the reading. Returns None when the
    reading does not line up with the surface (irregular reading, UniDic
    normalising the kana away), leaving the caller to report it.
    """
    parts = [p for p in re.split(rf"({KANJI_RUN.pattern})", surface) if p]
    pattern = "".join(
        "(.+?)" if KANJI.match(p) else re.escape(kata_to_hira(p))
        for p in parts
    )
    match = re.fullmatch(pattern, reading)
    if match is None:
        return None

    out = []
    group = 1
    for part in parts:
        out.append(part)
        if KANJI.match(part):
            out.append(f"【{match.group(group)}】")
            group += 1
    return "".join(out)


def furigana(sentence: str) -> tuple[str, list[str]]:
    """Return (annotated sentence, list of tokens that could not be annotated)."""
    out = []
    failures = []
    cursor = 0
    for token in tagger(sentence):
        surface = token.surface
        # The tagger drops whitespace between tokens; copy it back so
        # `git log` does not come out as `gitlog` for the TTS.
        start = sentence.find(surface, cursor)
        if start > cursor:
            out.append(sentence[cursor:start])
        cursor = start + len(surface)
        if not KANJI.search(surface):
            out.append(surface)
            continue
        reading = token_reading(token)
        annotated = annotate(surface, reading) if reading else None
        if annotated is None:
            failures.append(surface)
            out.append(surface)
        else:
            out.append(annotated)
    out.append(sentence[cursor:])
    return "".join(out), failures


def fill_tier(config, tier: int, force: bool, dry_run: bool) -> tuple[int, int]:
    csv_path = config.csv_path(tier)
    if not csv_path.exists():
        print(f"  Tier {tier}: {csv_path} not found, skipping")
        return 0, 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filled = 0
    unresolved = 0
    for index, row in enumerate(rows, 1):
        existing = row.get("Pronunciation", "").strip()
        if existing and not force:
            continue
        annotated, failures = furigana(row["Sentence"])
        if failures:
            unresolved += 1
            kept = ", keeping the existing reading" if existing else ""
            print(f"  Tier {tier} row {index}: no reading for {', '.join(failures)}{kept}")
            if existing:
                continue
        row["Pronunciation"] = annotated
        filled += 1

    if filled and not dry_run:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            # The committed CSVs are LF; csv defaults to CRLF.
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    print(f"  Tier {tier}: {filled} filled, {unresolved} needing a hand-written reading")
    return filled, unresolved


def main() -> None:
    ap = argparse.ArgumentParser(description="Fill Pronunciation furigana from UniDic")
    ap.add_argument("--deck", default="it-vocab", help="Deck slug (default: it-vocab)")
    ap.add_argument("--tier", type=int, help="Single tier only")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite non-empty cells, except rows with a token "
                         "whose reading cannot be aligned")
    ap.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = ap.parse_args()

    config = load_deck_config(args.deck)
    tiers = [args.tier] if args.tier else list(config.tier_range())

    print(f"Furigana generation (UniDic) - {config.name}")
    total_filled = 0
    total_unresolved = 0
    for tier in tiers:
        filled, unresolved = fill_tier(config, tier, args.force, args.dry_run)
        total_filled += filled
        total_unresolved += unresolved

    print(f"{total_filled} row(s) filled, {total_unresolved} need a hand-written reading")
    sys.exit(1 if total_unresolved else 0)


if __name__ == "__main__":
    main()
