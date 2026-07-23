#!/usr/bin/env python3
"""Check every Pronunciation furigana reading against the UniDic dictionary.

This is the standard way to verify pronunciations in this repo. It catches
wrong furigana (and therefore wrong TTS audio) before building.

How it works
------------
For each row it builds two hiragana readings of the sentence and compares them:

  1. authored  - concatenate the furigana from the Pronunciation column
                 (漢字【よみ】 -> よみ, kana kept as-is).
  2. dictionary - tokenise the plain Sentence with fugashi/UniDic and
                 concatenate each token's reading.

Comparing at the SENTENCE level (not per kanji) is deliberate: a bracket group
like 取【と】り is correct in context even though UniDic reads the bare kanji 取
as とり, because the full reading 取り消す = とりけす matches either way. Per-kanji
comparison produces false positives on every okurigana verb; whole-sentence
comparison does not.

Legitimate divergences (rendaku, homographs UniDic guesses wrong, domain nouns
UniDic reads as verbs) are whitelisted per deck in
`decks/<slug>/pronunciation_overrides.py`:

    # surface -> the correct reading; used to override UniDic when building the
    # dictionary reading, so an accepted term stops being reported.
    ACCEPTED = {
        "月次": "げつじ",       # monthly (UniDic guesses つきなみ = commonplace)
        "消込": "けしこみ",     # accounting noun (UniDic reads verb しょうこむ)
        "計上日": "けいじょうび", # rendaku on 日 suffix
    }

Usage:
    uv run python scripts/check_pronunciation.py --deck accounting
    uv run python scripts/check_pronunciation.py --deck it-vocab --tier 3
    uv run python scripts/check_pronunciation.py --deck accounting --quiet

Exit code is non-zero if any unaccepted mismatch is found, so it can gate CI.
validate.py runs it in advisory mode (reports, never fails the build).
"""

import argparse
import csv
import importlib.util
import re
import sys
from pathlib import Path

import fugashi

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config, DECKS_DIR

tagger = fugashi.Tagger()

KANJI = r"[一-鿿㐀-䶿々]"
ANNOTATION = re.compile(rf"({KANJI}+)【([^】]+)】")
HIRA_ONLY = re.compile(r"[^ぁ-ゟ]")          # keep hiragana (incl. ー via next line)
KEEP = re.compile(r"[^ぁ-ゟー]")             # kana to keep when normalising
ASCII_NUM = re.compile(r"^[0-9A-Za-z%.,\-]+$")


def kata_to_hira(text: str) -> str:
    out = []
    for c in text:
        if "ァ" <= c <= "ヶ":
            out.append(chr(ord(c) - 0x60))
        else:
            out.append(c)
    return "".join(out)


def normalise(kana: str) -> str:
    """Lower to a comparable hiragana skeleton."""
    return KEEP.sub("", kata_to_hira(kana))


def authored_reading(pron: str) -> str:
    """Concatenate the furigana readings written in the Pronunciation field."""
    out = []
    pos = 0
    for m in ANNOTATION.finditer(pron):
        out.append(pron[pos:m.start()])   # kana between annotations
        out.append(m.group(2))            # the reading inside 【】
        pos = m.end()
    out.append(pron[pos:])
    return normalise("".join(out))


def token_reading(surface: str) -> str:
    parts = []
    for tok in tagger(surface):
        kana = getattr(tok.feature, "kana", None)
        if kana and kana != "*":
            parts.append(kana)
        else:
            pron = getattr(tok.feature, "pron", None)
            parts.append(pron if pron and pron != "*" else tok.surface)
    return "".join(parts)


def dictionary_reading(sentence: str, accepted: dict[str, str]) -> str:
    """UniDic reading of the plain sentence, with ACCEPTED surfaces overridden.

    Splits the sentence on accepted surfaces (longest first) so their business
    reading is used verbatim, and tokenises the gaps with UniDic.
    """
    keys = sorted(accepted, key=len, reverse=True)
    segments = [sentence]
    for key in keys:
        new = []
        for seg in segments:
            if seg in accepted:            # already an accepted chunk
                new.append(seg)
                continue
            parts = seg.split(key)
            for i, p in enumerate(parts):
                if p:
                    new.append(p)
                if i < len(parts) - 1:
                    new.append(key)
        segments = new

    reading = []
    for seg in segments:
        if seg in accepted:
            reading.append(accepted[seg])
            continue
        for tok in tagger(seg):
            if ASCII_NUM.match(tok.surface):
                continue
            reading.append(token_reading(tok.surface))
    return normalise("".join(reading))


def load_overrides(slug: str) -> dict[str, str]:
    path = DECKS_DIR / slug / "pronunciation_overrides.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f"{slug}_pron_overrides", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "ACCEPTED", {}))


def check_tier(csv_path: Path, tier: int, accepted: dict[str, str], quiet: bool) -> tuple[int, int]:
    if not csv_path.exists():
        print(f"  Tier {tier}: file not found, skipping")
        return 0, 0
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    mismatches = 0
    for i, row in enumerate(rows, 1):
        pron = row.get("Pronunciation", "")
        sentence = row.get("Sentence", "")
        if not pron or not sentence:
            continue
        auth = authored_reading(pron)
        dic = dictionary_reading(sentence, accepted)
        if auth == dic:
            continue
        mismatches += 1
        print(f"  Tier {tier} row {i} (cloze: {row.get('Cloze','')}):")
        print(f"      sentence:   {sentence}")
        print(f"      authored:   {auth}")
        print(f"      dictionary: {dic}")
    if not quiet:
        status = "OK" if mismatches == 0 else f"{mismatches} MISMATCH"
        print(f"  Tier {tier}: {len(rows)} rows, {status}")
    return len(rows), mismatches


def run(slug: str, tier: int | None = None, quiet: bool = False) -> tuple[int, int]:
    """Check a deck's pronunciations. Returns (total_rows, total_mismatches).

    Reusable entry point: validate.py calls this in advisory mode.
    """
    config = load_deck_config(slug)
    accepted = load_overrides(config.slug)

    print("=" * 50)
    print(f"Pronunciation check (UniDic) - {config.name}")
    if accepted:
        print(f"Accepted overrides: {len(accepted)}")
    print("=" * 50)

    tiers = [tier] if tier else list(config.tier_range())
    total_rows = 0
    total_mismatch = 0
    for t in tiers:
        rows, mismatch = check_tier(config.csv_path(t), t, accepted, quiet)
        total_rows += rows
        total_mismatch += mismatch

    print("=" * 50)
    if total_mismatch == 0:
        print(f"All {total_rows} rows match UniDic (or accepted overrides). OK")
    else:
        print(f"{total_mismatch} row(s) differ from UniDic out of {total_rows}.")
        print(f"Fix the reading, or whitelist the surface in decks/{config.slug}/pronunciation_overrides.py")
    return total_rows, total_mismatch


def main() -> None:
    ap = argparse.ArgumentParser(description="Check Pronunciation furigana against UniDic")
    ap.add_argument("--deck", default="it-vocab", help="Deck slug (default: it-vocab)")
    ap.add_argument("--tier", type=int, help="Check a single tier only")
    ap.add_argument("--quiet", action="store_true", help="Only print mismatches")
    args = ap.parse_args()

    _, mismatches = run(args.deck, args.tier, args.quiet)
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
