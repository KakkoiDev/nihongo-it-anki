#!/usr/bin/env python3
"""Validate vocabulary CSVs and audio files before deck generation.

Catches common issues:
- Missing or incorrectly named CSV columns
- Empty required fields
- Invalid furigana format (unclosed brackets, invalid readings)
- Untranslated KeyMeaning values
- Missing or empty audio files
"""

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Expected CSV columns
REQUIRED_COLUMNS = {'Sentence', 'Translation', 'Cloze', 'Pronunciation', 'Note', 'KeyMeaning'}

# Expected row counts per tier
TIER_SIZES = {1: 150, 2: 200, 3: 250, 4: 200, 5: 100, 6: 100}

# Hiragana range for validating furigana readings
HIRAGANA_PATTERN = re.compile(r'^[\u3040-\u309F\u30A0-\u30FFー・]+$')

# Furigana bracket pattern
FURIGANA_PATTERN = re.compile(r'【([^】]*)】')


class ValidationResult:
    """Tracks validation results for a tier."""

    def __init__(self, tier: int):
        self.tier = tier
        self.errors = []
        self.warnings = []
        self.row_count = 0
        self.csv_valid = False
        self.furigana_valid = 0
        self.furigana_total = 0
        self.key_meaning_valid = 0
        self.key_meaning_total = 0
        self.audio_valid = 0
        self.audio_total = 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def validate_csv_structure(csv_path: Path, result: ValidationResult) -> list[dict] | None:
    """Validate CSV exists and has required columns."""
    if not csv_path.exists():
        result.add_error(f"CSV file not found: {csv_path}")
        return None

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Check columns
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            result.add_error(f"Missing columns: {', '.join(missing)}")
            return None

        rows = list(reader)
        result.row_count = len(rows)

        # Check row count
        expected = TIER_SIZES.get(result.tier, 0)
        if result.row_count != expected:
            result.add_warning(f"Row count {result.row_count} differs from expected {expected}")

        result.csv_valid = True
        return rows


def validate_furigana(rows: list[dict], result: ValidationResult, verbose: bool = False):
    """Validate furigana format in Pronunciation field."""
    result.furigana_total = len(rows)

    for idx, row in enumerate(rows, 1):
        pronunciation = row.get('Pronunciation', '')

        # Check bracket matching
        open_count = pronunciation.count('【')
        close_count = pronunciation.count('】')

        if open_count != close_count:
            result.add_error(f"Row {idx}: Unmatched brackets in '{pronunciation[:50]}...'")
            continue

        # Check each furigana reading
        readings = FURIGANA_PATTERN.findall(pronunciation)
        valid = True

        for reading in readings:
            # Allow hiragana, katakana, and common punctuation
            if reading and not HIRAGANA_PATTERN.match(reading):
                # Allow mixed readings with numbers/letters for edge cases
                if not re.match(r'^[\u3040-\u309F\u30A0-\u30FF0-9A-Za-zー・]+$', reading):
                    result.add_error(f"Row {idx}: Invalid reading '{reading}' (not hiragana/katakana)")
                    valid = False
                    break

        if valid:
            result.furigana_valid += 1


def validate_key_meaning(rows: list[dict], result: ValidationResult, verbose: bool = False):
    """Validate KeyMeaning translations."""
    result.key_meaning_total = len(rows)

    for idx, row in enumerate(rows, 1):
        cloze = row.get('Cloze', '')
        key_meaning = row.get('KeyMeaning', '')

        # Check empty
        if not key_meaning.strip():
            result.add_error(f"Row {idx}: Empty KeyMeaning for '{cloze}'")
            continue

        # Check untranslated (same as Cloze)
        if key_meaning == cloze:
            # Allow if it's English (like API, JSON)
            if not re.match(r'^[A-Za-z0-9\s\-\./]+$', cloze):
                result.add_warning(f"Row {idx}: KeyMeaning '{key_meaning}' same as Cloze (possibly untranslated)")
                continue

        # Check reasonable length
        if len(key_meaning) > 50:
            result.add_warning(f"Row {idx}: KeyMeaning too long ({len(key_meaning)} chars)")

        result.key_meaning_valid += 1


def validate_audio(tier: int, row_count: int, result: ValidationResult, verbose: bool = False, female: bool = False):
    """Validate audio files exist and are not empty."""
    audio_dir = ROOT / f"tier{tier}-audio-female" if female else ROOT / f"tier{tier}-audio"
    result.audio_total = row_count

    if not audio_dir.exists():
        result.add_warning(f"Audio directory not found: {audio_dir}")
        return

    for idx in range(1, row_count + 1):
        audio_file = audio_dir / f"tier{tier}_{idx:03d}.wav"

        if not audio_file.exists():
            result.add_error(f"Missing audio: {audio_file.name}")
            continue

        # Check file size (should be > 1KB for valid audio)
        size = audio_file.stat().st_size
        if size < 1024:
            result.add_error(f"Audio too small ({size} bytes): {audio_file.name}")
            continue

        result.audio_valid += 1


def validate_tier(tier: int, check_audio: bool = False, verbose: bool = False, female: bool = False) -> ValidationResult:
    """Validate a single tier."""
    result = ValidationResult(tier)
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"

    # Step 1: CSV structure
    rows = validate_csv_structure(csv_path, result)
    if rows is None:
        return result

    # Step 2: Furigana format
    validate_furigana(rows, result, verbose)

    # Step 3: KeyMeaning
    validate_key_meaning(rows, result, verbose)

    # Step 4: Audio (optional)
    if check_audio:
        validate_audio(tier, len(rows), result, verbose, female)

    return result


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation results for a tier."""
    print(f"\nValidating tier {result.tier}...")

    # CSV
    if result.csv_valid:
        print(f"  CSV: {result.row_count} rows, {len(REQUIRED_COLUMNS)} columns ✓")
    else:
        print(f"  CSV: ✗")

    # Furigana
    if result.furigana_total > 0:
        status = "✓" if result.furigana_valid == result.furigana_total else "✗"
        print(f"  Furigana: {result.furigana_valid}/{result.furigana_total} valid {status}")

    # KeyMeaning
    if result.key_meaning_total > 0:
        status = "✓" if result.key_meaning_valid == result.key_meaning_total else "✗"
        print(f"  KeyMeaning: {result.key_meaning_valid}/{result.key_meaning_total} translated {status}")

    # Audio
    if result.audio_total > 0:
        status = "✓" if result.audio_valid == result.audio_total else "✗"
        print(f"  Audio: {result.audio_valid}/{result.audio_total} files exist {status}")

    # Errors
    if result.errors and verbose:
        print("\n  Errors:")
        for error in result.errors[:10]:  # Limit output
            print(f"    {error}")
        if len(result.errors) > 10:
            print(f"    ... and {len(result.errors) - 10} more errors")

    # Warnings
    if result.warnings and verbose:
        print("\n  Warnings:")
        for warning in result.warnings[:5]:
            print(f"    {warning}")
        if len(result.warnings) > 5:
            print(f"    ... and {len(result.warnings) - 5} more warnings")


def main():
    parser = argparse.ArgumentParser(
        description="Validate vocabulary CSVs and audio files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/validate.py              # Validate all tiers
  uv run python scripts/validate.py --tier 1     # Validate tier 1 only
  uv run python scripts/validate.py --check-audio # Include audio validation
  uv run python scripts/validate.py --verbose    # Show all errors/warnings
        """
    )
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Validate specific tier only")
    parser.add_argument("--check-audio", action="store_true",
                        help="Also validate audio files")
    parser.add_argument("--female", action="store_true",
                        help="Validate female voice audio (tier*-audio-female/)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed errors and warnings")

    args = parser.parse_args()

    # Determine tiers to validate
    tiers = [args.tier] if args.tier else range(1, 7)

    voice_label = " (Female)" if args.female else ""
    print("=" * 50)
    print(f"Vocabulary & Audio Validation{voice_label}")
    print("=" * 50)

    all_results = []
    for tier in tiers:
        result = validate_tier(tier, args.check_audio, args.verbose, args.female)
        all_results.append(result)
        print_result(result, args.verbose)

    # Summary
    total_errors = sum(len(r.errors) for r in all_results)
    total_warnings = sum(len(r.warnings) for r in all_results)

    print("\n" + "=" * 50)
    if total_errors == 0:
        print(f"All validations passed! ({total_warnings} warnings)")
        sys.exit(0)
    else:
        print(f"Validation failed: {total_errors} errors, {total_warnings} warnings")
        if not args.verbose:
            print("Run with --verbose to see details")
        sys.exit(1)


if __name__ == "__main__":
    main()
