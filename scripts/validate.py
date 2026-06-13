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

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import DeckConfig, load_deck_config

# Expected CSV columns
REQUIRED_COLUMNS = {'Sentence', 'Translation', 'Cloze', 'Pronunciation', 'Note', 'Register', 'KeyMeaning', 'PitchAccent'}

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


def validate_csv_structure(csv_path: Path, result: ValidationResult, tier_sizes: dict[int, int]) -> list[dict] | None:
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
        expected = tier_sizes.get(result.tier, 0)
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
        open_count = pronunciation.count('\u3010')
        close_count = pronunciation.count('\u3011')

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
                if not re.match(r'^[\u3040-\u309F\u30A0-\u30FF0-9A-Za-z\u30FC\u30FB]+$', reading):
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


JAPANESE_PATTERN = re.compile(r'[぀-ヿ一-鿿]')


def validate_translation(rows: list[dict], result: ValidationResult):
    """Validate the English Translation field."""
    for idx, row in enumerate(rows, 1):
        translation = row.get('Translation', '')
        if not translation.strip():
            result.add_error(f"Row {idx}: Empty Translation")
        elif JAPANESE_PATTERN.search(translation):
            result.add_error(f"Row {idx}: Translation contains Japanese: '{translation[:40]}'")
        elif not re.search(r'[A-Za-z]', translation):
            result.add_error(f"Row {idx}: Translation has no English letters: '{translation[:40]}'")


# Clozes intentionally absent from their sentence (abbreviation-expansion
# rows: sentence has AZ / P99 / Parameter Store, cloze is the spelled-out
# form). See docs/IMPROVEMENTS.md.
ABBREV_EXPANSION_CLOZES = {
    'アベイラビリティゾーン',
    'パーセンタイル',
    'パラメータストア',
}


def validate_cloze_in_sentence(rows: list[dict], result: ValidationResult):
    """Cloze must appear in Sentence, or Card 3 blanking is a silent no-op."""
    for idx, row in enumerate(rows, 1):
        cloze = row.get('Cloze', '')
        sentence = row.get('Sentence', '')
        if cloze and cloze not in sentence and cloze not in ABBREV_EXPANSION_CLOZES:
            result.add_error(f"Row {idx}: Cloze '{cloze}' not in Sentence (Card 3 blank is a no-op)")


def validate_translations_file(config: DeckConfig) -> list[str]:
    """Check the deck's translations.py for duplicate dict keys (last-wins is silent)."""
    path = config.csv_path(1).parent / "translations.py"
    if not path.exists():
        return []
    src = path.read_text(encoding='utf-8')
    keys = re.findall(r"^\s+'([^']+)':", src, re.M)
    seen, dups = set(), []
    for k in keys:
        if k in seen:
            dups.append(k)
        seen.add(k)
    return dups


def validate_audio(config: DeckConfig, tier: int, row_count: int, result: ValidationResult, verbose: bool = False, female: bool = False):
    """Validate audio files exist and are not empty."""
    audio_dir = config.audio_dir(tier, female)
    result.audio_total = row_count

    if not audio_dir.exists():
        result.add_warning(f"Audio directory not found: {audio_dir}")
        return

    for idx in range(1, row_count + 1):
        audio_file = audio_dir / f"tier{tier}_{idx:03d}.mp3"

        if not audio_file.exists():
            result.add_error(f"Missing audio: {audio_file.name}")
            continue

        # Check file size (should be > 1KB for valid audio)
        size = audio_file.stat().st_size
        if size < 1024:
            result.add_error(f"Audio too small ({size} bytes): {audio_file.name}")
            continue

        result.audio_valid += 1


def validate_tier(config: DeckConfig, tier: int, check_audio: bool = False, verbose: bool = False, female: bool = False) -> ValidationResult:
    """Validate a single tier."""
    result = ValidationResult(tier)
    csv_path = config.csv_path(tier)

    # Step 1: CSV structure
    rows = validate_csv_structure(csv_path, result, config.tier_sizes)
    if rows is None:
        return result

    # Step 2: Furigana format
    validate_furigana(rows, result, verbose)

    # Step 3: KeyMeaning
    validate_key_meaning(rows, result, verbose)

    # Step 4: English translation
    validate_translation(rows, result)
    if config.check_cloze_in_sentence:
        validate_cloze_in_sentence(rows, result)
    result.tekudasai = sum(1 for r in rows if r.get('Sentence', '').rstrip('。').endswith('てください'))

    # Step 5: Audio (optional)
    if check_audio:
        validate_audio(config, tier, len(rows), result, verbose, female)

    return result


def print_result(result: ValidationResult, verbose: bool = False):
    """Print validation results for a tier."""
    print(f"\nValidating tier {result.tier}...")

    # CSV
    if result.csv_valid:
        print(f"  CSV: {result.row_count} rows, {len(REQUIRED_COLUMNS)} columns OK")
    else:
        print(f"  CSV: FAIL")

    # Furigana
    if result.furigana_total > 0:
        status = "OK" if result.furigana_valid == result.furigana_total else "FAIL"
        print(f"  Furigana: {result.furigana_valid}/{result.furigana_total} valid {status}")

    # KeyMeaning
    if result.key_meaning_total > 0:
        status = "OK" if result.key_meaning_valid == result.key_meaning_total else "FAIL"
        print(f"  KeyMeaning: {result.key_meaning_valid}/{result.key_meaning_total} translated {status}")

    # Audio
    if result.audio_total > 0:
        status = "OK" if result.audio_valid == result.audio_total else "FAIL"
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
  uv run python scripts/validate.py --deck it-vocab --check-audio
  uv run python scripts/validate.py --verbose    # Show all errors/warnings
        """
    )
    parser.add_argument("--deck", type=str, default="it-vocab",
                        help="Deck slug (default: it-vocab)")
    parser.add_argument("--tier", type=int,
                        help="Validate specific tier only")
    parser.add_argument("--check-audio", action="store_true",
                        help="Also validate audio files")
    parser.add_argument("--female", action="store_true",
                        help="Validate female voice audio (tier*-audio-female/)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed errors and warnings")

    args = parser.parse_args()
    config = load_deck_config(args.deck)

    if args.tier and args.tier not in config.tier_range():
        print(f"Error: tier {args.tier} not in range 1-{config.tier_count}")
        sys.exit(1)

    # Determine tiers to validate
    tiers = [args.tier] if args.tier else config.tier_range()

    voice_label = " (Female)" if args.female else ""
    print("=" * 50)
    print(f"Vocabulary & Audio Validation - {config.name}{voice_label}")
    print("=" * 50)

    all_results = []
    for tier in tiers:
        result = validate_tier(config, tier, args.check_audio, args.verbose, args.female)
        all_results.append(result)
        print_result(result, args.verbose)

    # Deck counts table (paste into docs to avoid stale-count drift)
    total_rows = sum(r.row_count for r in all_results)
    total_teku = sum(getattr(r, 'tekudasai', 0) for r in all_results)
    print("\nDeck counts:")
    for r in all_results:
        teku = getattr(r, 'tekudasai', 0)
        pct = (100 * teku // r.row_count) if r.row_count else 0
        print(f"  tier {r.tier}: {r.row_count} sentences ({teku} tekudasai, {pct}%)")
    print(f"  TOTAL: {total_rows} sentences across {len(all_results)} tiers ({total_teku} tekudasai)")

    dup_keys = validate_translations_file(config)
    if dup_keys:
        print(f"\nWARNING: translations.py has {len(dup_keys)} duplicate keys (last wins): "
              f"{', '.join(dup_keys[:8])}{'...' if len(dup_keys) > 8 else ''}")

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
