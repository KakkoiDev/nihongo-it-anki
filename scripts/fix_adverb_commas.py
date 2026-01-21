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


def add_adverb_commas(text: str) -> str:
    """Add commas after introductory adverbs in text."""
    result = text

    for adverb in ADVERBS:
        # Pattern: adverb at start of string or after certain punctuation,
        # followed by non-punctuation (to avoid adding comma if already there)
        # Also match after 。or space (new clause)

        # At start of sentence
        pattern = f'^{re.escape(adverb)}([^、。！？])'
        result = re.sub(pattern, f'{adverb}、\\1', result)

        # After period (new sentence in same field)
        pattern = f'。{re.escape(adverb)}([^、。！？])'
        result = re.sub(pattern, f'。{adverb}、\\1', result)

    return result


def process_csv(csv_path: Path, dry_run: bool = True) -> list[tuple[str, str]]:
    """Process a CSV file and add adverb commas.

    Returns list of (original, modified) tuples for changed sentences.
    """
    changes = []
    rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        for row in reader:
            original_sentence = row['Sentence']
            original_pronunciation = row['Pronunciation']

            # Process both Sentence and Pronunciation fields
            new_sentence = add_adverb_commas(original_sentence)
            new_pronunciation = add_adverb_commas(original_pronunciation)

            if new_sentence != original_sentence:
                changes.append((original_sentence, new_sentence))
                row['Sentence'] = new_sentence
                row['Pronunciation'] = new_pronunciation

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
