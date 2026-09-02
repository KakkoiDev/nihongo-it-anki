"""The Production card type is opt-in, and opting out changes nothing.

Every other card type in this repo tests recognition: Listening plays the audio,
Reading shows the sentence, Vocabulary blanks one word of it. Production shows
the English and the situation and nothing else, so the only way to answer is to
say the Japanese. The tests that matter are therefore (a) no Japanese reaches
its front, and (b) a deck that has not opted in ships the byte-identical model
it shipped before the card existed - Anki keys scheduling on the model, and
re-reading a changed stylesheet costs a learner their review history.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import list_decks, load_deck_config
from create_deck import build_css, build_notes, create_model

PRODUCTION_DECKS = [s for s in list_decks() if load_deck_config(s).production_card]
THREE_CARD_DECKS = [s for s in list_decks() if not load_deck_config(s).production_card]

# The nine fields and three template names every deck shipped before this card
# type existed. Frozen on purpose: a change here is a change to what is already
# in users' collections.
THREE_CARD_FIELDS = [
    "Sentence", "Translation", "Cloze", "Pronunciation", "Category",
    "Audio", "Register", "KeyMeaning", "PitchAccent",
]
THREE_CARD_TEMPLATES = ["Listening", "Reading", "Vocabulary"]

# The Vocabulary question these decks have already shipped, byte for byte. Anki
# keys scheduling on the notetype, so a deck that did not opt in must keep the
# template it is scheduled against - gating the card on Produce is only legal
# where the notetype has that field.
SHIPPED_VOCABULARY_QFMT = '<div class="card-type">Vocabulary</div>\n<div id="sentence" class="sentence">{{Sentence}}</div>\n<div class="translation">{{Translation}}</div>\n<div class="category">{{Category}}</div>\n<script>\n(function() {\n    var el = document.getElementById(\'sentence\');\n    var cloze = \'{{Cloze}}\';\n    el.innerHTML = el.textContent.split(cloze).join(\'<span class="blank">＿＿＿</span>\');\n})();\n</script>\n'

# Anything that could put Japanese, furigana or a replay button on a card front.
ANSWER_FIELDS = ["Sentence", "Pronunciation", "Audio", "RealJapanese", "Cloze"]


def field_names(model):
    return [f["name"] for f in model.fields]


def template(model, name):
    return next(t for t in model.templates if t["name"] == name)


class TestExistingDecksAreUntouched:
    """No deck without production_card sees any of this."""

    @pytest.mark.parametrize("slug", THREE_CARD_DECKS)
    def test_fields_are_the_original_nine(self, slug):
        assert field_names(create_model(load_deck_config(slug))) == THREE_CARD_FIELDS

    @pytest.mark.parametrize("slug", THREE_CARD_DECKS)
    def test_templates_are_the_original_three(self, slug):
        model = create_model(load_deck_config(slug))
        assert [t["name"] for t in model.templates] == THREE_CARD_TEMPLATES

    @pytest.mark.parametrize("slug", THREE_CARD_DECKS)
    def test_model_name_still_says_three_card(self, slug):
        config = load_deck_config(slug)
        assert create_model(config).name == f"{config.name} (3-Card)"

    @pytest.mark.parametrize("slug", THREE_CARD_DECKS)
    def test_vocabulary_question_is_unchanged(self, slug):
        model = create_model(load_deck_config(slug))
        assert template(model, "Vocabulary")["qfmt"] == SHIPPED_VOCABULARY_QFMT

    def test_stylesheet_is_unchanged(self):
        """Anki only re-reads CSS behind --force-style, which resets review
        history, so the production rules must not leak into the shared sheet."""
        assert "production-prompt" not in build_css()
        assert "real-label" not in build_css()

    @pytest.mark.parametrize("slug", THREE_CARD_DECKS)
    def test_notes_carry_nine_fields(self, slug):
        config = load_deck_config(slug)
        notes, _ = build_notes(config, 1, create_model(config), include_audio=False)
        assert notes, f"{slug} tier 1 is empty"
        assert all(len(note.fields) == 9 for note in notes)


class TestProductionDeck:
    """minihongo-speak, and any later deck that opts in."""

    def test_at_least_one_deck_opts_in(self):
        assert PRODUCTION_DECKS

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_fourth_template_is_production(self, slug):
        model = create_model(load_deck_config(slug))
        assert [t["name"] for t in model.templates] == THREE_CARD_TEMPLATES + ["Production"]

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_real_japanese_field_is_appended(self, slug):
        """Appended, not inserted: genanki writes fields positionally."""
        assert field_names(create_model(load_deck_config(slug))) == \
            THREE_CARD_FIELDS + ["RealJapanese", "Produce"]

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_model_name_says_four_card(self, slug):
        config = load_deck_config(slug)
        assert create_model(config).name == f"{config.name} (4-Card)"

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_front_shows_no_japanese_and_no_audio(self, slug):
        front = template(create_model(load_deck_config(slug)), "Production")["qfmt"]
        for field in ANSWER_FIELDS:
            assert f"{{{{{field}}}}}" not in front, f"{field} would give the answer away"
        assert not re.search(r"[぀-ヿ一-鿿]", front), "literal Japanese on the front"

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_front_asks_in_english_with_the_situation(self, slug):
        front = template(create_model(load_deck_config(slug)), "Production")["qfmt"]
        assert "{{Translation}}" in front
        assert "{{Category}}" in front

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_back_shows_furigana_audio_and_pitch_accent(self, slug):
        back = template(create_model(load_deck_config(slug)), "Production")["afmt"]
        assert "{{Pronunciation}}" in back
        assert "{{Audio}}" in back
        assert "{{PitchAccent}}" in back

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_back_shows_the_real_japanese_when_there_is_one(self, slug):
        back = template(create_model(load_deck_config(slug)), "Production")["afmt"]
        assert "{{#RealJapanese}}" in back, "an empty field must not print a bare label"
        assert "{{RealJapanese}}" in back

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_stylesheet_carries_the_production_rules(self, slug):
        css = create_model(load_deck_config(slug)).css
        assert ".production-prompt" in css
        assert ".real-label" in css

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_notes_carry_the_extra_fields(self, slug):
        config = load_deck_config(slug)
        notes, _ = build_notes(config, 1, create_model(config), include_audio=False)
        assert notes
        assert all(len(note.fields) == 11 for note in notes)

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    @pytest.mark.parametrize("card", ["Production", "Vocabulary"])
    def test_front_is_gated_on_produce(self, slug, card):
        """A row without the flag must render an empty question, which is how
        Anki is told not to generate the card at all."""
        front = template(create_model(load_deck_config(slug)), card)["qfmt"]
        assert front.startswith("{{#Produce}}")
        assert front.endswith("{{/Produce}}")

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_gated_vocabulary_question_is_otherwise_unchanged(self, slug):
        front = template(create_model(load_deck_config(slug)), "Vocabulary")["qfmt"]
        assert front == "{{#Produce}}" + SHIPPED_VOCABULARY_QFMT + "{{/Produce}}"

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_no_two_production_rows_share_a_front(self, slug):
        """The front is the English gloss and the category and nothing else, so
        two production rows sharing that pair ask one question with two right
        answers and the learner's self-grade becomes arbitrary."""
        config = load_deck_config(slug)
        model = create_model(config)
        index = {f["name"]: i for i, f in enumerate(model.fields)}
        seen: dict[tuple[str, str], str] = {}
        for tier in config.tier_range():
            for note in build_notes(config, tier, model, include_audio=False)[0]:
                if not note.fields[index["Produce"]]:
                    continue
                front = (note.fields[index["Translation"]],
                         note.fields[index["Category"]])
                assert front not in seen, (
                    f"{front} is the Production front of both "
                    f"{seen[front]} and {note.fields[index['Sentence']]}")
                seen[front] = note.fields[index["Sentence"]]

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_a_demoted_row_survives_on_the_winner_back(self, slug):
        """Dropping the fourth card must not drop the word: whatever lost the
        front is still met as a recognition-only answer on the row that kept
        it."""
        config = load_deck_config(slug)
        model = create_model(config)
        index = {f["name"]: i for i, f in enumerate(model.fields)}
        rows = [n.fields for tier in config.tier_range()
                for n in build_notes(config, tier, model, include_audio=False)[0]]
        produced = {(r[index["Translation"]], r[index["Category"]]): r
                    for r in rows if r[index["Produce"]]}
        demoted = [r for r in rows if not r[index["Produce"]]]
        assert demoted, f"{slug} has no demoted row to check"
        for row in demoted:
            winner = produced[(row[index["Translation"]], row[index["Category"]])]
            real = winner[index["RealJapanese"]]
            assert row[index["Sentence"]] in real

    @pytest.mark.parametrize("slug", PRODUCTION_DECKS)
    def test_guid_ignores_the_card_type(self, slug):
        """Scheduling is keyed on the GUID, and the GUID is keyed on the
        sentence. Adding a fourth card to a note must not orphan its history."""
        config = load_deck_config(slug)
        with_production = [n.guid for n in
                           build_notes(config, 1, create_model(config), False)[0]]
        config.production_card = False
        without = [n.guid for n in
                   build_notes(config, 1, create_model(config), False)[0]]
        assert with_production == without
