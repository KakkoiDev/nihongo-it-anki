#!/usr/bin/env python3
"""Add commas after introductory adverbs for natural TTS pauses.

Based on Kokoro TTS experiments (see experiments/kokoro-pause-test/):
Adverbs at the start of sentences or clauses benefit from a comma
to create natural pauses in speech.

Examples:
- まず → まず、
- 次に → 次に、
- その前に → その前に、
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Introductory adverbs/phrases that benefit from comma after
# These typically appear at the start of sentences or clauses
ADVERBS = [
    # Sequence
    'まず',           # first
    '次に',           # next
    '最初に',         # first (formal)
    '最後に',         # finally
    'その前に',       # before that
    'その後',         # after that
    'そして',         # and then
    'それから',       # after that
    # Addition
    'また',           # also
    'さらに',         # furthermore
    'しかも',         # moreover
    # Contrast
    'しかし',         # however
    'ただし',         # however/provided that
    'ただ',           # just/however
    # Examples/Specifics
    '例えば',         # for example
    '特に',           # especially
    '具体的には',     # specifically (には as set phrase)
    '基本的には',     # basically (には as set phrase)
    # Actuality
    '実は',           # actually
    '実際には',       # actually/in practice (には as set phrase)
    '本当は',         # really/truthfully
    # Conditions
    'もし',           # if
    '仮に',           # supposing
    # Emphasis
    '確かに',         # certainly
    '当然',           # naturally
    'もちろん',       # of course
    # Time
    '今すぐ',         # right now
    '後で',           # later
    '先に',           # first/ahead
]


def adverb_to_furigana_pattern(adverb: str) -> str:
    """Convert adverb to non-capturing regex pattern that matches with optional furigana.

    Example: 実は → 実(?:【[^】]+】)?は
    This allows matching both 実は and 実【じつ】は
    """
    parts = []
    for char in adverb:
        # Each character can optionally be followed by furigana annotation (non-capturing)
        parts.append(re.escape(char) + r'(?:【[^】]+】)?')
    return ''.join(parts)


def add_adverb_commas(text: str) -> str:
    """Add commas after introductory adverbs in text.

    Handles both plain text (実は) and furigana-annotated text (実【じつ】は).
    """
    result = text

    for adverb in ADVERBS:
        # Create pattern that matches adverb with optional furigana
        furigana_pattern = adverb_to_furigana_pattern(adverb)

        # At start of sentence: capture adverb (with possible furigana), add comma
        def add_comma_start(m):
            return m.group(1) + '、' + m.group(2)

        pattern = f'^({furigana_pattern})([^、。！？])'
        result = re.sub(pattern, add_comma_start, result)

        # After period (new sentence in same field)
        def add_comma_after_period(m):
            return '。' + m.group(1) + '、' + m.group(2)

        pattern = f'。({furigana_pattern})([^、。！？])'
        result = re.sub(pattern, add_comma_after_period, result)

    return result


def process_csv(csv_path: Path, dry_run: bool = True) -> list[tuple[str, str]]:
    """Process a CSV file and add adverb commas to TTSPronunciation only.

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
            new_tts = add_adverb_commas(original_tts)

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
