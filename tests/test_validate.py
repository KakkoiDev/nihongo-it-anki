"""Tests for validate.py CSV validation across all decks."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import list_decks, load_deck_config
from validate import (
    ABBREV_EXPANSION_CLOZES,
    REQUIRED_COLUMNS,
    ValidationResult,
    validate_cloze_in_sentence,
    validate_tier,
)

ALL_DECKS = list_decks()
ALL_CONFIGS = {slug: load_deck_config(slug) for slug in ALL_DECKS}


@pytest.fixture(params=ALL_DECKS)
def deck_config(request):
    return ALL_CONFIGS[request.param]


class TestTierSizes:
    """Tier sizes in config match actual CSV row counts."""

    def test_all_tiers_listed(self, deck_config):
        for tier in deck_config.tier_range():
            assert tier in deck_config.tier_sizes, \
                f"{deck_config.slug} tier {tier} missing from tier_sizes"

    def test_csv_row_counts_match(self, deck_config):
        for tier, expected in deck_config.tier_sizes.items():
            csv_path = deck_config.csv_path(tier)
            if csv_path.exists():
                with open(csv_path, 'r', encoding='utf-8') as f:
                    actual = len(list(csv.DictReader(f)))
                assert actual == expected, \
                    f"{deck_config.slug} tier {tier}: expected {expected} rows, got {actual}"


class TestValidateTier:
    """Integration tests for full tier validation."""

    def test_all_tiers_pass(self, deck_config):
        for tier in deck_config.tier_range():
            result = validate_tier(deck_config, tier)
            assert not result.has_errors, \
                f"{deck_config.slug} tier {tier} has errors: {result.errors[:3]}"

    def test_all_tiers_have_required_columns(self, deck_config):
        for tier in deck_config.tier_range():
            result = validate_tier(deck_config, tier)
            assert result.csv_valid, f"{deck_config.slug} tier {tier} CSV invalid"

    def test_all_furigana_valid(self, deck_config):
        for tier in deck_config.tier_range():
            result = validate_tier(deck_config, tier)
            assert result.furigana_valid == result.furigana_total, \
                f"{deck_config.slug} tier {tier}: {result.furigana_total - result.furigana_valid} invalid furigana"

    def test_all_key_meanings_translated(self, deck_config):
        for tier in deck_config.tier_range():
            result = validate_tier(deck_config, tier)
            assert result.key_meaning_valid == result.key_meaning_total, \
                f"{deck_config.slug} tier {tier}: {result.key_meaning_total - result.key_meaning_valid} untranslated"


class TestClozeInSentence:
    """Cloze must be a substring of Sentence so Card 3 blanking works."""

    def test_cloze_present_passes(self):
        result = ValidationResult(1)
        validate_cloze_in_sentence(
            [{'Cloze': '協力', 'Sentence': '他のチームと協力してください。'}], result)
        assert not result.has_errors

    def test_cloze_absent_errors(self):
        result = ValidationResult(1)
        validate_cloze_in_sentence(
            [{'Cloze': '協力する', 'Sentence': '他のチームと協力してください。'}], result)
        assert result.has_errors

    def test_abbreviation_expansion_whitelisted(self):
        result = ValidationResult(1)
        cloze = next(iter(ABBREV_EXPANSION_CLOZES))
        validate_cloze_in_sentence(
            [{'Cloze': cloze, 'Sentence': 'AZ をまたいで配置してください。'}], result)
        assert not result.has_errors


class TestRequiredColumns:
    """Required columns match what CSVs actually have."""

    def test_required_columns_present_in_csvs(self, deck_config):
        for tier in deck_config.tier_range():
            csv_path = deck_config.csv_path(tier)
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                columns = set(reader.fieldnames or [])
            missing = REQUIRED_COLUMNS - columns
            assert not missing, f"{deck_config.slug} tier {tier} missing columns: {missing}"
