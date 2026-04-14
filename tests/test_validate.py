"""Tests for validate.py CSV validation."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import load_deck_config
from validate import REQUIRED_COLUMNS, validate_tier

CONFIG = load_deck_config("it-vocab")


class TestTierSizes:
    """Tier sizes in config match actual CSV row counts."""

    def test_all_tiers_listed(self):
        for tier in CONFIG.tier_range():
            assert tier in CONFIG.tier_sizes, f"Tier {tier} missing from tier_sizes"

    def test_csv_row_counts_match(self):
        for tier, expected in CONFIG.tier_sizes.items():
            csv_path = CONFIG.csv_path(tier)
            if csv_path.exists():
                with open(csv_path, 'r', encoding='utf-8') as f:
                    actual = len(list(csv.DictReader(f)))
                assert actual == expected, f"Tier {tier}: expected {expected} rows, got {actual}"


class TestValidateTier:
    """Integration tests for full tier validation."""

    def test_all_tiers_pass(self):
        for tier in CONFIG.tier_range():
            result = validate_tier(CONFIG, tier)
            assert not result.has_errors, f"Tier {tier} has errors: {result.errors[:3]}"

    def test_all_tiers_have_required_columns(self):
        for tier in CONFIG.tier_range():
            result = validate_tier(CONFIG, tier)
            assert result.csv_valid, f"Tier {tier} CSV invalid"

    def test_all_furigana_valid(self):
        for tier in CONFIG.tier_range():
            result = validate_tier(CONFIG, tier)
            assert result.furigana_valid == result.furigana_total, \
                f"Tier {tier}: {result.furigana_total - result.furigana_valid} invalid furigana"

    def test_all_key_meanings_translated(self):
        for tier in CONFIG.tier_range():
            result = validate_tier(CONFIG, tier)
            assert result.key_meaning_valid == result.key_meaning_total, \
                f"Tier {tier}: {result.key_meaning_total - result.key_meaning_valid} untranslated"


class TestRequiredColumns:
    """Required columns match what CSVs actually have."""

    def test_required_columns_present_in_csvs(self):
        for tier in CONFIG.tier_range():
            csv_path = CONFIG.csv_path(tier)
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            assert not missing, f"Tier {tier} missing columns: {missing}"
