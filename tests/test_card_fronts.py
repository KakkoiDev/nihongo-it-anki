"""No two cards may ask the same question.

Anki schedules two notes independently and the learner self-grades, so a front
that renders identically for two notes with different answers does not produce a
harmless ambiguity - it makes the grade arbitrary, and the arbitrary grade then
corrupts the scheduling of both. The Production front was the first place this
bit; the Vocabulary front does it too whenever the cloze is the whole sentence,
because blanking it leaves nothing but the English gloss.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import list_decks, load_deck_config
from create_deck import build_notes, create_model, read_tier
from import_minihongo_speak import CANDO_TIERS, resolve_production

DECKS = list_decks()
BLANK = "＿＿＿"


def rows_of(slug):
    config = load_deck_config(slug)
    model = create_model(config)
    index = {f["name"]: i for i, f in enumerate(model.fields)}
    return config, [
        {name: note.fields[i] for name, i in index.items()}
        for tier in config.tier_range()
        for note in build_notes(config, tier, model, include_audio=False)[0]
    ]


@pytest.mark.parametrize("slug", DECKS)
def test_no_two_notes_share_a_vocabulary_front(slug):
    """The Vocabulary front is the sentence with every occurrence of the cloze
    blanked, plus the translation and the category - that substitution is what
    the template's script does in the browser. Rows whose Produce is empty
    generate no Vocabulary card at all, so they ask no question to collide."""
    config, rows = rows_of(slug)
    seen: dict[tuple[str, str, str], str] = {}
    for row in rows:
        if config.production_card and not row["Produce"]:
            continue
        front = (row["Sentence"].replace(row["Cloze"], BLANK),
                 row["Translation"], row["Category"])
        assert front not in seen, (
            f"{front} is the Vocabulary front of both {seen[front]} "
            f"and {row['Sentence']}")
        seen[front] = row["Sentence"]


def test_cloze_is_a_substring_of_its_sentence():
    """A cloze the sentence does not contain blanks nothing, so the front and
    the back render the same card. Asserted for minihongo-speak, whose clozes
    are all derived; it-vocab has hand-written exceptions that predate this."""
    _, rows = rows_of("minihongo-speak")
    for row in rows:
        assert row["Cloze"] in row["Sentence"], row["Sentence"]


def test_a_demoted_row_still_shows_the_japanese_on_two_cards():
    """Losing the two English-only fronts must not cost the row its word: the
    Listening and Reading cards show the Japanese and were never ambiguous, so
    they need a sentence, its reading and its audio like any other row."""
    config = load_deck_config("minihongo-speak")
    demoted = [row for tier in config.tier_range()
               for row in read_tier(config, tier) if not row["Produce"]]
    assert demoted
    for row in demoted:
        assert row["Sentence"] and row["Pronunciation"] and row["Translation"]


def test_merging_a_real_word_does_not_split_on_sentence_punctuation():
    """RealJapanese holds whole utterances, and 、 is punctuation inside them.
    Treating it as a list delimiter would read はい out of はい、お願いします。
    and drop a demoted row's word as already present."""
    tiers = {cando: [] for cando in CANDO_TIERS}
    winner = {"Sentence": "しますか", "Translation": "shall I", "Note": "Test",
              "Cloze": "しますか", "RealJapanese": "はい、お願いします。"}
    demoted = {"Sentence": "はい", "Translation": "shall I", "Note": "Test",
               "Cloze": "はい", "RealJapanese": ""}
    tiers[CANDO_TIERS[0]] = [winner, demoted]

    resolve_production(tiers)

    assert demoted["Produce"] == ""
    assert winner["Produce"] == "y"
    assert winner["RealJapanese"] == "はい、お願いします。、はい"
