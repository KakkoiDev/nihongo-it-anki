#!/usr/bin/env python3
"""Add TTSPronunciation column to vocabulary CSVs.

Migration script that:
1. Creates TTSPronunciation column from Pronunciation (keeps TTS commas)
2. Removes TTS-specific commas from Sentence and Pronunciation fields

This separates display text (clean) from TTS input (with pause commas).
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Import comma-adding functions from existing scripts
from fix_ga_commas import add_ga_commas, should_add_comma_after_ga
from fix_adverb_commas import add_adverb_commas, ADVERBS


def remove_ga_commas(text: str) -> str:
    """Remove TTS-specific commas after が subject markers.

    Reverses the effect of add_ga_commas() by removing commas that were
    added after が when it functions as a subject marker particle.
    """
    result = []
    i = 0

    while i < len(text):
        if text[i] == 'が' and i + 1 < len(text) and text[i + 1] == '、':
            # Check if this が、 was likely added by our script
            # by applying the same logic used to add it
            before = text[:i]
            # Check what would come after the comma
            after = text[i + 2:] if i + 2 < len(text) else ''

            # Reconstruct what the original text would have looked like
            test_text = before + 'が' + after

            # If add_ga_commas would have added a comma here, remove it
            if should_add_comma_after_ga(test_text, i):
                result.append('が')
                i += 2  # Skip が and 、
                continue

        result.append(text[i])
        i += 1

    return ''.join(result)


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


def remove_adverb_commas(text: str) -> str:
    """Remove TTS-specific commas after introductory adverbs.

    Reverses the effect of add_adverb_commas() by removing commas that were
    added after specific introductory adverbs.

    Handles both plain text (実は、) and furigana-annotated text (実【じつ】は、).
    """
    result = text

    for adverb in ADVERBS:
        # Create pattern that matches adverb with optional furigana
        furigana_pattern = adverb_to_furigana_pattern(adverb)

        # At start of sentence: adverb、X → adverbX
        # Use a function to remove just the comma while preserving the matched adverb
        def remove_comma_start(m):
            return m.group(1) + m.group(2)

        pattern = f'^({furigana_pattern})、([^。！？])'
        result = re.sub(pattern, remove_comma_start, result)

        # After period: 。adverb、X → 。adverbX
        def remove_comma_after_period(m):
            return '。' + m.group(1) + m.group(2)

        pattern = f'。({furigana_pattern})、([^。！？])'
        result = re.sub(pattern, remove_comma_after_period, result)

    return result


def process_csv(csv_path: Path, dry_run: bool = True) -> dict:
    """Process a CSV file to add TTSPronunciation column.

    Returns dict with statistics about changes made.
    """
    stats = {
        'total_rows': 0,
        'sentence_changes': 0,
        'pronunciation_changes': 0,
    }
    rows = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        original_fieldnames = list(reader.fieldnames)

        # Add TTSPronunciation column after Pronunciation
        if 'TTSPronunciation' in original_fieldnames:
            print(f"  TTSPronunciation column already exists in {csv_path.name}")
            fieldnames = original_fieldnames
        else:
            pron_idx = original_fieldnames.index('Pronunciation')
            fieldnames = original_fieldnames[:pron_idx + 1] + ['TTSPronunciation'] + original_fieldnames[pron_idx + 1:]

        for row in reader:
            stats['total_rows'] += 1

            # Current fields (may have TTS commas)
            original_sentence = row['Sentence']
            original_pronunciation = row['Pronunciation']

            # TTSPronunciation keeps the TTS commas (copy from current Pronunciation)
            # Also ensure all TTS comma patterns are applied
            tts_pronunciation = original_pronunciation
            tts_pronunciation = add_ga_commas(tts_pronunciation)
            tts_pronunciation = add_adverb_commas(tts_pronunciation)

            # Clean versions for display (remove TTS-specific commas)
            clean_sentence = remove_adverb_commas(remove_ga_commas(original_sentence))
            clean_pronunciation = remove_adverb_commas(remove_ga_commas(original_pronunciation))

            if clean_sentence != original_sentence:
                stats['sentence_changes'] += 1
            if clean_pronunciation != original_pronunciation:
                stats['pronunciation_changes'] += 1

            # Update row
            row['Sentence'] = clean_sentence
            row['Pronunciation'] = clean_pronunciation
            row['TTSPronunciation'] = tts_pronunciation

            rows.append(row)

    if not dry_run:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return stats


def main():
    dry_run = '--apply' not in sys.argv

    if dry_run:
        print("DRY RUN - use --apply to make changes\n")

    total_stats = {
        'total_rows': 0,
        'sentence_changes': 0,
        'pronunciation_changes': 0,
    }

    for tier in range(1, 7):
        csv_path = ROOT / f"tier{tier}-vocabulary.csv"
        if csv_path.exists():
            print(f"Processing {csv_path.name}...")
            stats = process_csv(csv_path, dry_run=dry_run)

            print(f"  Rows: {stats['total_rows']}")
            print(f"  Sentence changes: {stats['sentence_changes']}")
            print(f"  Pronunciation changes: {stats['pronunciation_changes']}")

            for key in total_stats:
                total_stats[key] += stats[key]

    print(f"\n{'Would process' if dry_run else 'Processed'} {total_stats['total_rows']} total rows")
    print(f"  Sentence changes: {total_stats['sentence_changes']}")
    print(f"  Pronunciation changes: {total_stats['pronunciation_changes']}")

    if dry_run:
        print("\nRun with --apply to make changes")


if __name__ == '__main__':
    main()
