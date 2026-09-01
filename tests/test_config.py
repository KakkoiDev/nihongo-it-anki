"""Tests for deck configuration loading and validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import DeckConfig, list_decks, load_deck_config


class TestListDecks:
    """list_decks() finds all configured decks."""

    def test_it_vocab_exists(self):
        decks = list_decks()
        assert "it-vocab" in decks

    def test_returns_list(self):
        decks = list_decks()
        assert isinstance(decks, list)


class TestLoadDeckConfig:
    """load_deck_config() loads and parses deck.toml correctly."""

    def test_loads_it_vocab(self):
        config = load_deck_config("it-vocab")
        assert isinstance(config, DeckConfig)
        assert config.slug == "it-vocab"
        assert config.name == "Japanese IT Vocabulary"

    def test_model_id_is_int(self):
        config = load_deck_config("it-vocab")
        assert isinstance(config.model_id, int)
        assert config.model_id > 0

    def test_deck_base_id_is_int(self):
        config = load_deck_config("it-vocab")
        assert isinstance(config.deck_base_id, int)
        assert config.deck_base_id > 0

    def test_tier_count_matches_names(self):
        config = load_deck_config("it-vocab")
        assert config.tier_count == len(config.tier_names)

    def test_tier_count_matches_sizes(self):
        config = load_deck_config("it-vocab")
        assert config.tier_count == len(config.tier_sizes)

    def test_tier_range(self):
        config = load_deck_config("it-vocab")
        assert list(config.tier_range()) == list(range(1, config.tier_count + 1))

    def test_csv_paths_exist(self):
        config = load_deck_config("it-vocab")
        for tier in config.tier_range():
            assert config.csv_path(tier).exists(), f"Missing CSV for tier {tier}"

    def test_nonexistent_deck_raises(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            load_deck_config("nonexistent-deck")

    def test_cloze_in_sentence_defaults_true(self):
        assert load_deck_config("it-vocab").check_cloze_in_sentence is True

    def test_kundoku_cloze_check_disabled(self):
        assert load_deck_config("it-kundoku").check_cloze_in_sentence is False

    def test_subdeck_names_are_padded_from_collection_size(self):
        config = load_deck_config("it-vocab")
        assert config.subdeck_name(2).endswith("::02 Basic Development")
        assert config.subdeck_name(10).endswith(
            "::10 Documentation & Engineering Culture"
        )

    def test_female_subdeck_uses_same_padding(self):
        config = load_deck_config("it-vocab")
        assert config.subdeck_name(2, female=True).startswith(
            "Japanese IT Vocabulary (Female)::02 "
        )


class TestNoDuplicateIds:
    """No two decks share model_id or deck_base_id."""

    def test_unique_model_ids(self):
        decks = list_decks()
        model_ids = []
        for slug in decks:
            config = load_deck_config(slug)
            model_ids.append(config.model_id)
        assert len(model_ids) == len(set(model_ids)), "Duplicate model_id found across decks"

    def test_unique_deck_base_ids(self):
        decks = list_decks()
        base_ids = []
        for slug in decks:
            config = load_deck_config(slug)
            base_ids.append(config.deck_base_id)
        assert len(base_ids) == len(set(base_ids)), "Duplicate deck_base_id found across decks"
