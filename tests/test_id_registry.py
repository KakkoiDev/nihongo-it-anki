"""Every deck.toml must agree with jpanki's ID registry.

The registry spans every project that builds on jpanki, so it - not this repo -
is the source of truth for which integers a deck owns. `accounting` and
`jp-teaching` once shipped with the same `deck_base_id`, which silently merged
one deck's subdecks into the other in users' collections. `test_config.py` only
compares this repo's decks to each other, so it cannot see a clash with
`minihongo` or `bible`; this can.
"""

import sys
from pathlib import Path

import pytest
from jpanki import ids

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import list_decks, load_deck_config

ALL_DECKS = list_decks()
REGISTRY = ids.load()


def test_registry_is_internally_consistent():
    ids.assert_unique(REGISTRY)


@pytest.mark.parametrize("slug", ALL_DECKS)
class TestDeckMatchesRegistry:
    def test_deck_is_registered(self, slug):
        assert slug in REGISTRY, (
            f"{slug} is not in jpanki's ids.toml; register it there and bump the "
            f"pinned rev in pyproject.toml before building"
        )

    def test_model_id_matches(self, slug):
        assert load_deck_config(slug).model_id in REGISTRY[slug].model_ids

    def test_deck_base_id_matches(self, slug):
        assert load_deck_config(slug).deck_base_id == REGISTRY[slug].deck_base_id

    def test_tiers_fit_the_reserved_range(self, slug):
        """The combined female build uses base + 100 + tier, so tiers must also
        clear that offset."""
        config = load_deck_config(slug)
        reserved = REGISTRY[slug].reserved
        assert config.tier_count <= reserved
        assert 100 + config.tier_count <= reserved
