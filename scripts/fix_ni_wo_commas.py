#!/usr/bin/env python3
"""Add commas in に...を patterns for natural TTS pauses.

This script identifies the pattern [X]に[Y]を[verb] and inserts commas
after BOTH particles for more natural TTS output.

Pattern needs commas when:
- Location + object pattern: フローに問題を見つけました → フローに、問題を、見つけました
- に marks location/target, を marks object, followed by verb

Pattern does NOT need commas when:
- ために / のために (purpose clause)
- に...される (passive agent marker)
- Already has commas
- No を follows the に
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def should_add_commas_in_ni_wo_pattern(sentence: str, ni_pos: int) -> tuple[bool, int | None]:
    """Determine if に at position ni_pos is part of a に...を pattern needing commas.

    Returns (should_add, wo_pos) where wo_pos is the position of を if found.
    """
    before = sentence[:ni_pos]
    after = sentence[ni_pos + 1:]

    # Skip if に is inside furigana brackets 【...】
    # Count open/close brackets before this position
    open_brackets = before.count('【')
    close_brackets = before.count('】')
    if open_brackets > close_brackets:
        return False, None

    # Skip if already has comma after に
    if after.startswith('、'):
        return False, None

    # Skip: ために / のために (purpose clause)
    if before.endswith('ため') or before.endswith('の'):
        # Check if this is part of ために pattern
        if ni_pos >= 2 and sentence[ni_pos - 2:ni_pos] == 'ため':
            return False, None

    # Look for を in the rest of the sentence (before next clause boundary)
    # Clause boundaries: 。！？ and also か (question/embedded clause), が (but), けど
    boundary_match = re.search(r'[。！？かが]', after)
    search_area = after[:boundary_match.start()] if boundary_match else after

    # Find を position - must be BEFORE に (object comes before destination in this pattern)
    # Pattern is [Object]を[Destination]に or [Destination]に[Object]を
    # We want: [X]に[Y]を where に marks destination and を marks object
    wo_pos_relative = search_area.find('を')
    if wo_pos_relative == -1:
        return False, None

    wo_pos = ni_pos + 1 + wo_pos_relative
    after_wo = sentence[wo_pos + 1:]

    # Skip if を is inside furigana brackets
    before_wo = sentence[:wo_pos]
    open_brackets_wo = before_wo.count('【')
    close_brackets_wo = before_wo.count('】')
    if open_brackets_wo > close_brackets_wo:
        return False, None

    # Skip if already has comma after を
    if after_wo.startswith('、'):
        return False, None

    # Skip: passive pattern に...される
    # Check if after を we have される/されて/された etc.
    if re.match(r'[、]?され', after_wo):
        return False, None

    # Verify を is followed by verb (hiragana start indicates verb)
    # Skip if を is at end or followed by punctuation
    if not after_wo or after_wo[0] in '。、！？':
        return False, None

    # Check if followed by hiragana (verb indicator)
    if re.match(r'^[あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっ]', after_wo):
        return True, wo_pos

    return False, None


def add_ni_wo_commas(text: str) -> str:
    """Add commas in に...を patterns in text."""
    result = list(text)
    insertions = []  # Track positions to insert commas

    i = 0
    while i < len(text):
        if text[i] == 'に':
            should_add, wo_pos = should_add_commas_in_ni_wo_pattern(text, i)
            if should_add and wo_pos is not None:
                # Mark both positions for comma insertion (after に and after を)
                insertions.append(i + 1)  # After に
                insertions.append(wo_pos + 1)  # After を
        i += 1

    # Insert commas from end to start to preserve positions
    for pos in sorted(set(insertions), reverse=True):
        result.insert(pos, '、')

    return ''.join(result)


def process_csv(csv_path: Path, dry_run: bool = True) -> list[tuple[str, str]]:
    """Process a CSV file and add に...を commas to TTSPronunciation only.

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

            # Process only TTSPronunciation field (keep Sentence/Pronunciation clean)
            new_tts = add_ni_wo_commas(original_tts)

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
