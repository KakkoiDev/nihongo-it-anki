"""GUIDs must not collide between decks that share sentences.

Anki identifies a note by its GUID. Two decks that mint the same GUID under
different model IDs do not merge and do not warn: the second import is rejected
as a notetype conflict and lands with zero cards. Verified against a real
collection in TestCrossDeckImport below.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import genanki
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import list_decks, load_deck_config

ALL_DECKS = list_decks()
ALL_CONFIGS = {slug: load_deck_config(slug) for slug in ALL_DECKS}


def sentences(slug: str) -> list[str]:
    config = ALL_CONFIGS[slug]
    out = []
    for tier in config.tier_range():
        with open(config.csv_path(tier), encoding="utf-8") as f:
            out.extend(row["Sentence"] for row in csv.DictReader(f))
    return out


def guids(slug: str) -> list[str]:
    config = ALL_CONFIGS[slug]
    return [config.note_guid(s) for s in sentences(slug)]


class TestNoteGuid:
    def test_unnamespaced_deck_keeps_bare_guid(self):
        """it-vocab is published; its GUIDs carry review history and must not move."""
        config = ALL_CONFIGS["it-vocab"]
        assert config.guid_namespace is None
        assert config.note_guid("これバグってない？") == genanki.guid_for("これバグってない？")

    def test_namespace_changes_the_guid(self):
        config = ALL_CONFIGS["agentic-lab"]
        assert config.guid_namespace == "agentic-lab"
        assert config.note_guid("これバグってない？") != genanki.guid_for("これバグってない？")


@pytest.mark.parametrize("slug", ALL_DECKS)
def test_no_duplicate_guids_within_deck(slug):
    dupes = [g for g, n in Counter(guids(slug)).items() if n > 1]
    assert not dupes, f"{slug} mints {len(dupes)} duplicate GUIDs"


def test_agentic_lab_does_not_collide_with_it_vocab():
    """agentic-lab is 179 sentences copied out of it-vocab; only the namespace
    keeps the two importable side by side."""
    shared = set(sentences("agentic-lab")) & set(sentences("it-vocab"))
    assert len(shared) == 179, f"expected all 179 to come from it-vocab, got {len(shared)}"
    assert not set(guids("agentic-lab")) & set(guids("it-vocab"))
