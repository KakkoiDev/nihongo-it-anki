"""Tests for validate.py CSV validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate import REQUIRED_COLUMNS, TIER_SIZES, validate_tier


class TestTierSizes:
    """TIER_SIZES covers all tiers and matches actual CSV row counts."""

    def test_all_tiers_listed(self):
        for tier in range(1, 10):
            assert tier in TIER_SIZES, f"Tier {tier} missing from TIER_SIZES"

    def test_csv_row_counts_match(self):
        import csv
        root = Path(__file__).parent.parent
        for tier, expected in TIER_SIZES.items():
            csv_path = root / f"tier{tier}-vocabulary.csv"
            if csv_path.exists():
                with open(csv_path, 'r', encoding='utf-8') as f:
                    actual = len(list(csv.DictReader(f)))
                assert actual == expected, f"Tier {tier}: expected {expected} rows, got {actual}"


class TestValidateTier:
    """Integration tests for full tier validation."""

    def test_all_tiers_pass(self):
        for tier in range(1, 10):
            result = validate_tier(tier)
            assert not result.has_errors, f"Tier {tier} has errors: {result.errors[:3]}"

    def test_all_tiers_have_required_columns(self):
        for tier in range(1, 10):
            result = validate_tier(tier)
            assert result.csv_valid, f"Tier {tier} CSV invalid"

    def test_all_furigana_valid(self):
        for tier in range(1, 10):
            result = validate_tier(tier)
            assert result.furigana_valid == result.furigana_total, \
                f"Tier {tier}: {result.furigana_total - result.furigana_valid} invalid furigana"

    def test_all_key_meanings_translated(self):
        for tier in range(1, 10):
            result = validate_tier(tier)
            assert result.key_meaning_valid == result.key_meaning_total, \
                f"Tier {tier}: {result.key_meaning_total - result.key_meaning_valid} untranslated"


class TestRequiredColumns:
    """Required columns match what CSVs actually have."""

    def test_required_columns_present_in_csvs(self):
        import csv
        root = Path(__file__).parent.parent
        for tier in range(1, 10):
            csv_path = root / f"tier{tier}-vocabulary.csv"
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            assert not missing, f"Tier {tier} missing columns: {missing}"
