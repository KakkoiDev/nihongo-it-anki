#!/usr/bin/env python3
"""Add commas after への when preceded by long katakana words.

This script identifies への patterns where a long katakana/loanword
precedes the particle, and inserts a comma after への for natural TTS pauses.

Pattern needs comma when:
- Long katakana word (≥6 morae) + への + noun
- Example: ステージングデータベースへの、アクセス

Pattern does NOT need comma when:
- Short word before への
- Already has comma after への
- への inside furigana brackets
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Small katakana that don't count as separate morae
SMALL_KATAKANA = set('ァィゥェォャュョッ')
# Long vowel mark counts as 1 mora
LONG_VOWEL = 'ー'


def count_katakana_morae(text: str) -> int:
    """Count morae in a katakana string.

    - Regular katakana = 1 mora
    - Small katakana (ァィゥェォャュョッ) = 0 mora (part of previous)
    - Long vowel ー = 1 mora
    """
    count = 0
    for char in text:
        if char in SMALL_KATAKANA:
            continue  # Small kana don't add mora
        if '\u30A0' <= char <= '\u30FF' or char == LONG_VOWEL:
            count += 1
    return count


def get_preceding_katakana(text: str, pos: int) -> str:
    """Extract the katakana word immediately before position pos."""
    # Walk backwards from pos to find katakana sequence
    end = pos
    start = pos

    for i in range(pos - 1, -1, -1):
        char = text[i]
        # Check if katakana (including long vowel mark and middle dot)
        if '\u30A0' <= char <= '\u30FF' or char in 'ー・':
            start = i
        else:
            break

    return text[start:end]


def should_add_comma_after_heno(sentence: str, heno_pos: int) -> bool:
    """Determine if への at position heno_pos needs a comma after it.

    Returns True if comma should be added.
    """
    before = sentence[:heno_pos]
    after = sentence[heno_pos + 2:]  # Skip への (2 chars)

    # Skip if への is inside furigana brackets 【...】
    open_brackets = before.count('【')
    close_brackets = before.count('】')
    if open_brackets > close_brackets:
        return False

    # Skip if already has comma after への
    if after.startswith('、'):
        return False

    # Get the katakana word before への
    preceding_katakana = get_preceding_katakana(sentence, heno_pos)

    if not preceding_katakana:
        return False

    # Count morae - need ≥6 for "long" word
    morae = count_katakana_morae(preceding_katakana)

    if morae >= 6:
        return True

    return False


def add_heno_commas(text: str) -> str:
    """Add commas after への in long katakana word patterns."""
    # Find all への positions
    result = list(text)
    insertions = []

    i = 0
    while i < len(text) - 1:
        if text[i:i+2] == 'への':
            if should_add_comma_after_heno(text, i):
                insertions.append(i + 2)  # After への
            i += 2
        else:
            i += 1

    # Insert commas from end to start to preserve positions
    for pos in sorted(set(insertions), reverse=True):
        result.insert(pos, '、')

    return ''.join(result)


def process_csv(csv_path: Path, dry_run: bool = True) -> list[tuple[str, str]]:
    """Process a CSV file and add への commas to TTSPronunciation only.

    Returns list of (original, modified) tuples for changed TTSPronunciation.
    """
    changes = []
    rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if 'TTSPronunciation' not in fieldnames:
            print(f"  Warning: TTSPronunciation column not found in {csv_path.name}")
            print(f"  Run add_tts_column.py first to add the column")
            return []

        for row in reader:
            original_tts = row['TTSPronunciation']

            # Process only TTSPronunciation field
            new_tts = add_heno_commas(original_tts)

            if new_tts != original_tts:
                changes.append((original_tts, new_tts))
                row['TTSPronunciation'] = new_tts

            rows.append(row)

    if not dry_run and changes:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return changes


def main():
    dry_run = '--apply' not in sys.argv

    if dry_run:
        print("DRY RUN - use --apply to make changes\n")

    all_changes = []

    for tier in range(1, 7):
        csv_path = ROOT / f"tier{tier}-vocabulary.csv"
        if csv_path.exists():
            changes = process_csv(csv_path, dry_run=dry_run)
            if changes:
                print(f"\n=== Tier {tier}: {len(changes)} changes ===")
                for orig, new in changes:
                    print(f"  - {orig}")
                    print(f"  + {new}")
                all_changes.extend(changes)

    print(f"\n{'Would change' if dry_run else 'Changed'} {len(all_changes)} sentences total")

    if dry_run and all_changes:
        print("\nRun with --apply to make changes")


if __name__ == '__main__':
    main()
