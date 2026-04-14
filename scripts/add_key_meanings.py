#!/usr/bin/env python3
"""Add KeyMeaning column to vocabulary CSVs.

Translates the Cloze (key vocabulary) field to English using
the deck's translations.py file.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config, load_translations


def get_translation(cloze: str, translations: dict[str, str]) -> str:
    """Get English translation for a Japanese key word."""
    # Direct lookup
    if cloze in translations:
        return translations[cloze]

    # Try without trailing particles
    stripped = re.sub(r'[をにがはでとも]+$', '', cloze)
    if stripped in translations:
        return translations[stripped]

    # For compound words, try to match parts
    for jp, en in translations.items():
        if jp in cloze and len(jp) > 2:
            return en

    # Return the original for unknown terms (likely English tech terms)
    return cloze


def process_csv(config, tier: int, translations: dict[str, str]):
    """Add KeyMeaning column to a tier's CSV."""
    input_path = config.csv_path(tier)
    output_path = input_path.parent / f"tier{tier}-vocabulary-new.csv"

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Add KeyMeaning to each row
    for row in rows:
        row['KeyMeaning'] = get_translation(row['Cloze'], translations)

    # Write new CSV
    fieldnames = ['Sentence', 'Translation', 'Cloze', 'Pronunciation', 'Note', 'KeyMeaning']
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Tier {tier}: {len(rows)} rows processed -> {output_path.name}")
    return rows


def main():
    """Process all tier CSVs."""
    parser = argparse.ArgumentParser(description="Add KeyMeaning column to vocabulary CSVs")
    parser.add_argument("--deck", type=str, default="it-vocab",
                        help="Deck slug (default: it-vocab)")
    args = parser.parse_args()

    config = load_deck_config(args.deck)
    translations = load_translations(args.deck)

    if not translations:
        print(f"Error: no translations.py found for deck '{args.deck}'")
        sys.exit(1)

    print(f"Adding KeyMeaning column to {config.name} CSVs\n")

    all_rows = []
    for tier in config.tier_range():
        rows = process_csv(config, tier, translations)
        all_rows.extend(rows)

    # Report untranslated terms
    untranslated = set()
    for row in all_rows:
        if row['KeyMeaning'] == row['Cloze'] and not re.match(r'^[A-Za-z0-9\s\-\.]+$', row['Cloze']):
            untranslated.add(row['Cloze'])

    if untranslated:
        print(f"\n{len(untranslated)} terms need manual translation:")
        for term in sorted(untranslated)[:20]:
            print(f"  '{term}': '',")
        if len(untranslated) > 20:
            print(f"  ... and {len(untranslated) - 20} more")


if __name__ == '__main__':
    main()
