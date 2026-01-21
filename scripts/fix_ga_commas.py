#!/usr/bin/env python3
"""Add commas after が subject marker for natural TTS pauses.

This script identifies が used as a subject marker particle and inserts
a comma after it for more natural TTS output.

が needs comma when:
- Subject marker before verb: バグが発生 → バグが、発生
- Subject marker before adjective: 問題が多い → 問題が、多い
- Before ある/いる/できる: 問題がある → 問題が、ある

が does NOT need comma when:
- Part of ありがとう
- Part of 方がいい (ほうがいい)
- Part of ながら
- Already has comma after it
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def should_add_comma_after_ga(sentence: str, ga_pos: int) -> bool:
    """Determine if が at position ga_pos needs a comma after it.

    Returns True if comma should be added.
    """
    # Check what comes before が
    before = sentence[:ga_pos]
    after = sentence[ga_pos + 1:]

    # Skip if already has comma
    if after.startswith('、'):
        return False

    # Skip: ありがとう
    if before.endswith('ありがと') or 'ありがとう' in sentence[max(0, ga_pos-5):ga_pos+5]:
        return False

    # Skip: 方がいい (ほうがいい) - が is part of grammar pattern
    if before.endswith('方') or before.endswith('ほう'):
        return False

    # Skip: ながら (while doing)
    if before.endswith('な') and after.startswith('ら'):
        return False

    # Skip: が is part of verb stem (e.g., 上がる、下がる、広がる)
    # These verbs have が as part of the verb, not as particle
    # Common pattern: ends with 上/下/広 etc. + がる/がり/がって
    verb_stem_chars = ['上', '下', '広', '拡', 'あ', 'さ', 'ひろ']
    if any(before.endswith(c) for c in verb_stem_chars):
        if after and after[0] in 'りるっれろ':
            return False

    # Skip: が followed by end of sentence or punctuation immediately
    if not after or after[0] in '。、！？':
        return False

    # Add comma: が followed by verb-like patterns
    # Common verb endings that indicate subject marker usage
    verb_patterns = [
        r'^[あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっ]',
    ]

    for pattern in verb_patterns:
        if re.match(pattern, after):
            return True

    return False


def add_ga_commas(text: str) -> str:
    """Add commas after が subject markers in text."""
    result = []
    i = 0

    while i < len(text):
        if text[i] == 'が':
            result.append('が')
            if should_add_comma_after_ga(text, i):
                result.append('、')
        else:
            result.append(text[i])
        i += 1

    return ''.join(result)


def process_csv(csv_path: Path, dry_run: bool = True) -> list[tuple[str, str]]:
    """Process a CSV file and add が commas.

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
            new_sentence = add_ga_commas(original_sentence)
            new_pronunciation = add_ga_commas(original_pronunciation)

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
