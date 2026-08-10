"""agentic-lab rows are copies of it-vocab rows and must stay byte-identical.

Every agentic-lab sentence exists in it-vocab. Editing one side only - fixing a
KeyMeaning or a PitchAccent in it-vocab - leaves the two decks teaching
different answers for the same sentence, with no other test noticing.
"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import load_deck_config

COLUMNS = [
    "Sentence",
    "Translation",
    "Cloze",
    "Pronunciation",
    "Note",
    "Register",
    "KeyMeaning",
    "PitchAccent",
]


def rows(slug: str) -> list[dict[str, str]]:
    config = load_deck_config(slug)
    out = []
    for tier in config.tier_range():
        with open(config.csv_path(tier), encoding="utf-8") as f:
            out.extend(csv.DictReader(f))
    return out


AGENTIC_ROWS = rows("agentic-lab")
IT_VOCAB_ROWS = {row["Sentence"]: row for row in rows("it-vocab")}


@pytest.mark.parametrize("row", AGENTIC_ROWS, ids=range(len(AGENTIC_ROWS)))
def test_row_matches_its_it_vocab_source(row):
    sentence = row["Sentence"]
    source = IT_VOCAB_ROWS.get(sentence)
    assert source is not None, f"{sentence} is not in it-vocab"
    for column in COLUMNS:
        assert row[column] == source[column], (
            f"{sentence}: column {column} drifted from it-vocab\n"
            f"  agentic-lab: {row[column]!r}\n"
            f"  it-vocab:    {source[column]!r}"
        )
