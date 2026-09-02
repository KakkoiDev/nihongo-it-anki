#!/usr/bin/env python3
"""Create Anki deck from vocabulary CSV and audio files.

Generates .apkg files with a 3-card-per-note design:

  Card 1 (Listening):
    Front: Scaled 80px replay button only (audio auto-plays). No text.
    Back:  Sentence with furigana, translation, category, register badge,
           key vocab with pitch accent.

  Card 2 (Reading):
    Front: Raw Japanese sentence (no furigana), category, register badge.
    Back:  Sentence with furigana, translation, key vocab with pitch accent.

  Card 3 (Vocabulary):
    Front: Sentence with cloze word blanked (JS replacement), translation.
    Back:  Sentence with cloze highlighted in blue, audio, pronunciation.

  Card 4 (Production), only for decks with production_card = true and only on
  rows whose Produce column is set - which on those decks gates card 3 too:
    Front: English meaning and the situation cue. No Japanese, no audio.
    Back:  Sentence with furigana, audio, pitch accent, and the real Japanese
           beside the minihongo construction.

Removed in v3.0: conjugation tables, Keigo drill card, <hr> on Listening.
Removed in v3.4: Hint and Conjugations fields.

CSV columns used:
  Sentence, Translation, Cloze, Pronunciation, Note (category),
  Register, KeyMeaning, PitchAccent, Audio (generated filename).

The Pronunciation field uses 漢字【かんじ】 notation which to_ruby_html()
converts to <ruby> tags for display. This is separate from TTS processing.

Prerequisites:
  uv run python scripts/generate_pitch_accent.py  (updates PitchAccent in CSV)
  uv run python scripts/generate_audio.py --tier N (generates MP3 files)
"""

import argparse
import csv
import sys
from pathlib import Path

import genanki
import jpanki
from jpanki import furigana, theme

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import DeckConfig, list_decks, load_deck_config

# The furigana renderer, the card CSS and the force-style trick used to live
# here, in copies that had quietly drifted from minihongo's equivalents. They
# belong to jpanki now - see that project's golden-file tests, which pin this
# output against what both projects shipped before the extraction.
to_ruby_html = furigana.to_ruby


def build_css(production: bool = False) -> str:
    """The shared design system, plus this deck's own components.

    Everything in ``extra`` is specific to these card types - the pronunciation
    line, the JS cloze blank, the register badges, the pitch accent colouring -
    and stays here. The layers above it are shared with every other deck built
    on jpanki.

    ``production`` appends the fourth card type's rules. Decks without it get
    the byte-identical stylesheet they have always shipped, which matters
    because Anki only re-reads CSS behind --force-style, and that resets review
    history.
    """
    extra = COMPONENT_CSS + PRODUCTION_CSS if production else COMPONENT_CSS
    return theme.compose(
        # 28px rather than the library default: these cards put a single
        # sentence at the centre of attention, where minihongo's pair one with
        # a headword. Both are right for their layout.
        theme.base(sentence_size="28px", sentence_margin="20px 0"),
        theme.chip(".category"),
        theme.ruby(),
        theme.replay(),
        # The listening card's front is nothing but audio, so its button becomes
        # the dominant element.
        theme.replay(scope=".listening-front", size="5rem", icon_size="2.5rem",
                     radius="1.25rem"),
        theme.night(chip_selector=".category"),
        extra=extra,
    )


COMPONENT_CSS = '''
.pronunciation {
    font-size: 18px;
    color: #666666;
    margin: 15px 0;
    line-height: 1.8;
}

.key-vocab {
    font-size: 16px;
    color: #666666;
    margin-top: 15px;
}

.vocab {
    font-weight: bold;
    color: #2B70C9;
}

.blank {
    display: inline-block;
    min-width: 4em;
    border-bottom: 2px solid #2B2B2B;
    color: transparent;
}

.cloze-answer {
    color: #2B70C9;
    font-weight: bold;
}

.listening-front { margin: 40px 0; }

.register {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 0.75rem;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 6px;
    margin-left: 6px;
    vertical-align: middle;
    border: 1px solid #E5E5E5;
}
.register-casual  { background: #F7F7F7; color: #666666; }
.register-polite  { background: #e3f2fd; color: #1565c0; border-color: #bbdefb; }
.register-formal  { background: #fff3e0; color: #e65100; border-color: #ffe0b2; }
.register-keigo   { background: #f3e5f5; color: #6a1b9a; border-color: #e1bee7; }
/* Document and signage language, as opposed to anything anyone says aloud.
   Introduced by the fudosan deck, where 54 of 180 cards come off contracts and
   municipal forms. An unregistered value still renders as a neutral badge -
   see it-kundoku's `wenyan` - but this one is too common to leave bare. */
.register-written { background: #e8f5e9; color: #2e7d32; border-color: #c8e6c9; }

.pitch-h { color: #4caf50; }
.pitch-l { color: #f44336; }

.night_mode .translation { color: #E8E8E8; }
.night_mode .pronunciation { color: #999999; }
.night_mode .key-vocab { color: #999999; }
.night_mode .vocab { color: #6DB3F2; }
.night_mode .cloze-answer { color: #6DB3F2; }
.night_mode .blank { border-bottom-color: #999999; }
.night_mode .register { border-color: #333333; }
.night_mode .register-casual  { background: #252525; color: #999999; }
.night_mode .register-polite  { background: #1a2a3a; color: #64b5f6; border-color: #1a2a3a; }
.night_mode .register-formal  { background: #2a1f0e; color: #ffb74d; border-color: #2a1f0e; }
.night_mode .register-keigo   { background: #2a1a2a; color: #ce93d8; border-color: #2a1a2a; }
.night_mode .register-written { background: #16261a; color: #81c784; border-color: #16261a; }
.night_mode .pitch-h { color: #81c784; }
.night_mode .pitch-l { color: #e57373; }
'''


PRODUCTION_CSS = '''
/* Production card. The front is deliberately bare: an English meaning and a
   situation, and nothing a learner could read aloud instead of recalling. */
.production-prompt {
    font-size: 26px;
    margin: 30px 0 10px;
}

.real-japanese {
    font-size: 20px;
    margin: 12px 0;
}

.real-label {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 0.75rem;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    vertical-align: middle;
    margin-right: 6px;
    background: #F7F7F7;
    color: #666666;
    border: 1px solid #E5E5E5;
}

.night_mode .real-label {
    background: #252525;
    color: #999999;
    border-color: #333333;
}
'''


VOCABULARY_QFMT = '''<div class="card-type">Vocabulary</div>
<div id="sentence" class="sentence">{{Sentence}}</div>
<div class="translation">{{Translation}}</div>
<div class="category">{{Category}}</div>
<script>
(function() {
    var el = document.getElementById('sentence');
    var cloze = '{{Cloze}}';
    el.innerHTML = el.textContent.split(cloze).join('<span class="blank">\uff3f\uff3f\uff3f</span>');
})();
</script>
'''


def vocabulary_qfmt(production: bool) -> str:
    """The cloze front, gated on Produce for decks that carry the field.

    Blanking a cloze that is the whole sentence leaves nothing but the English
    gloss, so two rows sharing a gloss ask one question with two answers. The
    row that is not the canonical one for that front drops the card, the same
    way it drops the Production card and for the same reason. The gate can only
    be written on a deck whose notetype has the field: referencing Produce from
    a nine-field model is an Anki template error, and it would change templates
    the other six decks have already shipped.
    """
    if not production:
        return VOCABULARY_QFMT
    return "{{#Produce}}" + VOCABULARY_QFMT + "{{/Produce}}"


PRODUCTION_TEMPLATE = {
    'name': 'Production',
    # Nothing here may render Japanese, furigana or audio. The whole point of
    # the card is that the learner produces the sentence aloud from the meaning
    # alone; one readable kanji and the card tests recognition again.
    'qfmt': '''{{#Produce}}<div class="card-type">Production</div>
<div class="translation production-prompt">{{Translation}}</div>
{{#Category}}<div class="category">{{Category}}</div>{{/Category}}
{{/Produce}}''',
    'afmt': '''<div class="card-type">Production</div>
<div class="sentence">{{Pronunciation}}</div>
<div class="audio">{{Audio}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
{{#RealJapanese}}<div class="real-japanese"><span class="real-label">Real</span>{{RealJapanese}}</div>{{/RealJapanese}}
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
''',
}

# The Production template reads both, so a deck that opts in carries two more
# fields than the three-card decks do. Produce marks the canonical row for a
# front: Anki generates no card for a template whose question renders empty, so
# a row with an empty Produce grows neither a Production nor a Vocabulary card
# and keeps only Listening and Reading. Both those fronts reduce to the English
# gloss and the category once the cloze covers the whole sentence, so two rows
# sharing that pair would otherwise ask one question with two answers.
PRODUCTION_FIELDS = [{'name': 'RealJapanese'}, {'name': 'Produce'}]


def create_model(config: DeckConfig) -> genanki.Model:
    """Create the Anki model: three cards, or four when the deck opts in.

    Card 1 (Listening): Big play button -> Japanese + Furigana + English
    Card 2 (Reading): Japanese text -> Furigana + English
    Card 3 (Vocabulary): Blanked sentence + English -> Full sentence + Audio
    Card 4 (Production): English + situation -> Japanese, audio, real word

    Cards 3 and 4 exist only on rows carrying a Produce flag, and card 4 only
    under ``production_card = true``. A deck without it gets
    the same nine fields, three templates and stylesheet it has always shipped -
    see tests/test_production_card.py, which pins that.
    """
    card_count = 4 if config.production_card else 3
    model_name = f'{config.name} ({card_count}-Card)'
    return genanki.Model(
        config.model_id,
        model_name,
        fields=[
            {'name': 'Sentence'},       # Japanese sentence
            {'name': 'Translation'},    # English translation
            {'name': 'Cloze'},          # Key vocabulary word
            {'name': 'Pronunciation'},  # Japanese with furigana
            {'name': 'Category'},       # Category/context
            {'name': 'Audio'},          # Audio file reference
            {'name': 'Register'},       # Speech register: casual/polite/formal/keigo
            {'name': 'KeyMeaning'},     # English meaning of key word
            {'name': 'PitchAccent'},    # Pitch-colored ruby HTML for cloze word
            *(PRODUCTION_FIELDS if config.production_card else []),
        ],
        templates=[
            # Card 1: Listening (big play button front, everything else on back)
            {
                'name': 'Listening',
                'qfmt': '''<div class="card-type">Listening</div>
<div class="audio listening-front">{{Audio}}</div>
''',
                'afmt': '''<div class="card-type">Listening</div>
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Pronunciation}}</div>
<div class="translation">{{Translation}}</div>
<hr id="answer">
<div class="category">{{Category}}</div>{{#Register}}<span class="register register-{{Register}}">{{Register}}</span>{{/Register}}
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
''',
            },
            # Card 2: Reading (text-only front, no audio)
            {
                'name': 'Reading',
                'qfmt': '''<div class="card-type">Reading</div>
<div class="sentence">{{Sentence}}</div>
<div class="category">{{Category}}</div>{{#Register}}<span class="register register-{{Register}}">{{Register}}</span>{{/Register}}
''',
                'afmt': '''<div class="card-type">Reading</div>
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Pronunciation}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
''',
            },
            # Card 3: Vocabulary cloze (JS blanking)
            {
                'name': 'Vocabulary',
                'qfmt': vocabulary_qfmt(config.production_card),
                'afmt': '''<div class="card-type">Vocabulary</div>
<div id="sentence" class="sentence">{{Sentence}}</div>
<div class="audio">{{Audio}}</div>
<div class="translation">{{Translation}}</div>
<hr id="answer">
<div class="pronunciation">{{Pronunciation}}</div>
<script>
(function() {
    var el = document.getElementById('sentence');
    var cloze = '{{Cloze}}';
    el.innerHTML = el.textContent.split(cloze).join('<span class="cloze-answer">' + cloze + '</span>');
})();
</script>
''',
            },
            *([PRODUCTION_TEMPLATE] if config.production_card else []),
        ],
        css=build_css(config.production_card),
    )


def cards_of(config: DeckConfig, note: genanki.Note) -> int:
    """How many cards Anki generates for this note.

    A gated front that renders empty produces no card, so a note whose Produce
    is empty is worth two rather than four.
    """
    if not config.production_card:
        return 3
    return 4 if note.fields[-1] else 2


def create_deck(config: DeckConfig, tier: int, include_audio: bool = True, female: bool = False) -> tuple[genanki.Deck, list[str]]:
    """Create Anki deck for a specific tier.

    Args:
        config: Deck configuration
        tier: Tier number
        include_audio: Whether to include audio files
        female: If True, use audio from tier*-audio-female/ directory

    Returns:
        Tuple of (deck, list of media files)
    """
    deck = genanki.Deck(
        config.get_deck_id(tier),
        f'{config.name} - Tier {tier}'
    )
    notes, media_files = build_notes(config, tier, create_model(config),
                                     include_audio, female)
    for note in notes:
        deck.add_note(note)
    return deck, media_files


def read_tier(config: DeckConfig, tier: int) -> list[dict]:
    """Read a tier's CSV, preserving row order.

    Row order is load-bearing: audio filenames are positional, so inserting or
    reordering a row rebinds every later clip. Documented in docs/IMPROVEMENTS.md.
    """
    csv_path = config.csv_path(tier)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)
    with open(csv_path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def build_notes(
    config: DeckConfig,
    tier: int,
    model: genanki.Model,
    include_audio: bool = True,
    female: bool = False,
) -> tuple[list[genanki.Note], list[str]]:
    """Build one tier's notes, and the media they reference.

    The single place notes are constructed. Both the per-tier and the --combined
    build paths call this; they used to carry separate copies of the loop, and
    the --combined one called create_deck() purely to harvest media_files before
    rebuilding every note by hand.
    """
    audio_dir = config.audio_dir(tier, female)
    notes: list[genanki.Note] = []
    media_files: list[str] = []

    for idx, row in enumerate(read_tier(config, tier)):
        audio_file = f"tier{tier}_{idx + 1:03d}.mp3"
        audio_path = audio_dir / audio_file

        if include_audio and audio_path.exists():
            audio_ref = f"[sound:{audio_file}]"
            media_files.append(str(audio_path))
        else:
            # Not jpanki.sound_ref's empty string: these cards have shipped with
            # this literal placeholder, and changing a field value changes
            # nothing structurally but does alter what a learner sees.
            audio_ref = "[No audio]"

        notes.append(genanki.Note(
            model=model,
            fields=[
                row['Sentence'],
                row['Translation'],
                row['Cloze'],
                to_ruby_html(row['Pronunciation']),
                row['Note'],
                audio_ref,
                row.get('Register', ''),
                row['KeyMeaning'],
                row.get('PitchAccent', ''),
                *([row.get('RealJapanese', ''), row.get('Produce', '')]
                  if config.production_card else []),
            ],
            guid=config.note_guid(row['Sentence']),
            tags=[f'tier{tier}', row['Note'].replace(' ', '_').replace('-', '_')]
        ))

    return notes, media_files


def main():
    parser = argparse.ArgumentParser(
        description="Create Anki deck from vocabulary and audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/create_deck.py --tier 1
  uv run python scripts/create_deck.py --all
  uv run python scripts/create_deck.py --deck it-vocab --combined
  uv run python scripts/create_deck.py --list-decks
        """
    )
    parser.add_argument("--deck", type=str, default="it-vocab",
                        help="Deck slug (default: it-vocab)")
    parser.add_argument("--list-decks", action="store_true",
                        help="List available decks and exit")
    parser.add_argument("--tier", type=int,
                        help="Tier number to create")
    parser.add_argument("--all", action="store_true",
                        help="Create decks for all tiers")
    parser.add_argument("--combined", action="store_true",
                        help="Create single combined deck with all tiers")
    parser.add_argument("--female", action="store_true",
                        help="Use female voice audio from tier*-audio-female/")
    parser.add_argument("--force-style", action="store_true",
                        help="Offset MODEL_ID by CSS hash to force Anki to pick up new styles")
    parser.add_argument("--no-audio", action="store_true",
                        help="Create deck without audio files")
    parser.add_argument("--output", type=str,
                        help="Output filename (default: auto-generated)")

    args = parser.parse_args()

    if args.list_decks:
        decks = list_decks()
        if decks:
            print("Available decks:")
            for slug in decks:
                cfg = load_deck_config(slug)
                print(f"  {slug}: {cfg.name} ({cfg.tier_count} tiers)")
        else:
            print("No decks found in decks/")
        sys.exit(0)

    config = load_deck_config(args.deck)

    if args.tier and args.tier not in config.tier_range():
        print(f"Error: tier {args.tier} not in range 1-{config.tier_count}")
        sys.exit(1)

    if not args.tier and not args.all and not args.combined:
        parser.print_help()
        sys.exit(1)

    if args.force_style:
        # Presenting a new model is the only way to make Anki re-read card CSS,
        # and it resets review history for every note using it. Deliberate, and
        # deliberately not automatic.
        original = config.model_id
        config.model_id = jpanki.force_style(original, build_css(config.production_card))
        print(f"--force-style: model_id {original} -> {config.model_id} "
              f"(resets review history)")

    include_audio = not args.no_audio
    suffix = "-female" if args.female else ""

    def card_total(notes) -> int:
        return sum(cards_of(config, note) for note in notes)

    if args.combined:
        voice_label = " (Female)" if args.female else ""
        print(f"Creating combined deck with tier subdecks{voice_label}...")

        all_decks = []
        all_media = []
        total_notes = 0
        model = create_model(config)

        for tier in config.tier_range():
            subdeck_name = config.subdeck_name(tier, female=args.female)
            subdeck = genanki.Deck(
                config.deck_base_id + tier + (100 if args.female else 0),
                subdeck_name
            )

            notes, media_files = build_notes(config, tier, model, include_audio,
                                             args.female)
            for note in notes:
                subdeck.add_note(note)

            all_decks.append(subdeck)
            all_media.extend(media_files)
            total_notes += len(notes)
            print(f"  Added {config.tier_names[tier]}: {len(notes)} notes")

        output = args.output or f"{config.slug}-complete{suffix}.apkg"
        package = genanki.Package(all_decks)
        package.media_files = all_media
        package.write_to_file(output)

        print(f"\nCreated: {output}")
        print(f"Total notes: {total_notes}")
        print(f"Total cards: {card_total(n for d in all_decks for n in d.notes)}")
        print(f"Media files: {len(all_media)}")

    if args.all:
        for tier in config.tier_range():
            deck, media_files = create_deck(config, tier, include_audio, args.female)
            output = f"{config.slug}-tier{tier}{suffix}.apkg"

            package = genanki.Package(deck)
            package.media_files = media_files
            package.write_to_file(output)

            print(f"Created: {output} ({len(deck.notes)} notes, "
                  f"{len(media_files)} audio files, "
                  f"{card_total(deck.notes)} cards)")
    elif args.tier:
        tier = args.tier
        deck, media_files = create_deck(config, tier, include_audio, args.female)
        output = args.output or f"{config.slug}-tier{tier}{suffix}.apkg"

        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(output)

        print(f"\nCreated: {output}")
        print(f"Notes: {len(deck.notes)}")
        print(f"Cards: {card_total(deck.notes)}")
        print(f"Media files: {len(media_files)}")

        if not include_audio:
            print("\nNote: Audio files not included. Generate them first with:")
            print(f"  uv run python scripts/generate_audio.py --deck {config.slug} --tier {tier}")


if __name__ == "__main__":
    main()
