"""Import the built decks into a real Anki collection.

The build script exiting zero says nothing about whether Anki will accept the
package. It rejected agentic-lab outright before the GUID namespace existed:
`conflicting: 179, new: 0`, deck present and empty, no error anywhere.
"""

import sys
from pathlib import Path

import genanki
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

anki = pytest.importorskip("anki", reason="anki is a dev dependency")
from anki.collection import Collection  # noqa: E402
from anki.import_export_pb2 import ImportAnkiPackageRequest  # noqa: E402

from config import load_deck_config  # noqa: E402
from create_deck import build_notes, create_model  # noqa: E402


def build_apkg(slug: str, tier: int, path: Path) -> None:
    """One tier, no audio - this is about note identity, not media."""
    config = load_deck_config(slug)
    deck = genanki.Deck(config.get_deck_id(tier), f"{config.name}::{config.tier_names[tier]}")
    notes, _ = build_notes(config, tier, create_model(config), include_audio=False)
    for note in notes:
        deck.add_note(note)
    genanki.Package(deck).write_to_file(str(path))


def import_apkg(col, path: Path):
    return col.import_anki_package(ImportAnkiPackageRequest(package_path=str(path))).log


def test_agentic_lab_imports_alongside_it_vocab(tmp_path):
    """it-vocab first, because that is what the collection already has."""
    it_vocab = tmp_path / "it-vocab.apkg"
    agentic = tmp_path / "agentic-lab.apkg"
    build_apkg("it-vocab", 12, it_vocab)   # 100 notes, 85 of them in agentic-lab
    build_apkg("agentic-lab", 1, agentic)  # 14 notes, all of them from it-vocab

    col = Collection(str(tmp_path / "collection.anki2"))
    try:
        first = import_apkg(col, it_vocab)
        assert not first.conflicting

        log = import_apkg(col, agentic)
        assert not log.conflicting, (
            f"{len(log.conflicting)} notes rejected as notetype conflicts - "
            "agentic-lab's GUIDs are colliding with it-vocab's"
        )
        assert len(log.new) == 14

        deck_id = col.decks.id_for_name("Agentic Lab Priority Path::Tier 1 - The Survival Set")
        assert deck_id is not None
        assert len(col.decks.cids(deck_id)) == 14 * 3
    finally:
        col.close()
