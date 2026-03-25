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

Removed in v3.0: conjugation tables, Keigo drill card, <hr> on Listening.
Conjugations field kept in model for Anki backwards compatibility (empty).

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
import hashlib
import random
import re
import sys
from pathlib import Path

import genanki

# Project root
ROOT = Path(__file__).parent.parent

# Stable IDs for Anki (generated once, keep consistent).
# Changing MODEL_ID creates a new note type in Anki (existing cards won't update).
# Use --force-style to offset MODEL_ID by CSS hash and force Anki to pick up new styles.
MODEL_ID = 1607392323  # v3.0 - 3 cards, no conjugations, no keigo
DECK_BASE_ID = 2059400110  # Random but stable


def to_ruby_html(text: str) -> str:
    """Convert 漢字【かんじ】 to <ruby>漢字<rt>かんじ</rt></ruby>."""
    return re.sub(
        r'([\u4e00-\u9fff\u3400-\u4dbf\u3005]+)【([^】]+)】',
        r'<ruby>\1<rt>\2</rt></ruby>',
        text,
    )


def get_deck_id(tier: int) -> int:
    """Generate stable deck ID for a tier."""
    return DECK_BASE_ID + tier


def create_model() -> genanki.Model:
    """Create the 3-card Anki model.

    Card 1 (Listening): Big play button → Japanese + Furigana + English
    Card 2 (Reading): Japanese text → Furigana + English
    Card 3 (Vocabulary): Blanked sentence + English → Full sentence + Audio
    """
    return genanki.Model(
        MODEL_ID,
        'Japanese IT Vocabulary (3-Card)',
        fields=[
            {'name': 'Sentence'},       # Japanese sentence
            {'name': 'Translation'},    # English translation
            {'name': 'Cloze'},          # Key vocabulary word
            {'name': 'Pronunciation'},  # Japanese with furigana
            {'name': 'Category'},       # Category/context
            {'name': 'Audio'},          # Audio file reference
            {'name': 'Hint'},           # Kept for compatibility (unused)
            {'name': 'Register'},       # Speech register: casual/polite/formal/keigo
            {'name': 'KeyMeaning'},     # English meaning of key word
            {'name': 'PitchAccent'},    # Pitch-colored ruby HTML for cloze word
            {'name': 'Conjugations'},   # Kept for compatibility (unused)
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
<div class="sentence">{{Pronunciation}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
''',
            },
            # Card 3: Vocabulary cloze (JS blanking)
            {
                'name': 'Vocabulary',
                'qfmt': '''<div class="card-type">Vocabulary</div>
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
''',
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
        ],
        css='''
.card {
    font-family: "Noto Sans JP", "Hiragino Sans", "Yu Gothic", system-ui, sans-serif;
    font-size: 20px;
    text-align: center;
    color: #2B2B2B;
    background: #FFFFFF;
    padding: 24px;
    line-height: 1.7;
}

.card-type {
    font-size: 12px;
    color: #666666;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
}

.sentence {
    font-size: 28px;
    font-weight: bold;
    margin: 20px 0;
    line-height: 1.8;
}

.translation {
    font-size: 22px;
    margin: 15px 0;
    line-height: 1.6;
}

.pronunciation {
    font-size: 18px;
    color: #666666;
    margin: 15px 0;
    line-height: 1.8;
}

.category {
    display: inline-block;
    background: #F7F7F7;
    padding: 4px 12px;
    border-radius: 0.75rem;
    font-size: 12px;
    color: #666666;
    border: 1px solid #E5E5E5;
    margin-top: 10px;
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

.audio { margin: 10px 0; }

/* Replay button - match minihongo play-btn style */
.replay-button, .replaybutton {
    display: flex !important;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    margin: 0 auto;
    border: 2px solid #E5E5E5;
    border-radius: 0.75rem;
    background: #FFFFFF;
    cursor: pointer;
    text-decoration: none;
}
.replay-button *, .replaybutton * { display: none !important; }
.replay-button::before, .replaybutton::before {
    content: "";
    flex-shrink: 0;
    width: 1.2rem;
    height: 1.2rem;
    background: #2B70C9;
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 8.5v7a4.47 4.47 0 002.5-3.5zM14 3.23v2.06a6.51 6.51 0 010 13.42v2.06A8.51 8.51 0 0014 3.23z'/%3E%3C/svg%3E") center / contain no-repeat;
    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 8.5v7a4.47 4.47 0 002.5-3.5zM14 3.23v2.06a6.51 6.51 0 010 13.42v2.06A8.51 8.51 0 0014 3.23z'/%3E%3C/svg%3E") center / contain no-repeat;
}

/* Listening card: larger play button as dominant element */
.listening-front .replay-button,
.listening-front .replaybutton {
    width: 5rem;
    height: 5rem;
    border-radius: 1.25rem;
}
.listening-front .replay-button::before,
.listening-front .replaybutton::before {
    width: 2.5rem;
    height: 2.5rem;
}
.listening-front { margin: 40px 0; }

ruby { ruby-align: center; }
ruby rt { font-size: 12px; font-weight: normal; color: #666666; }

hr#answer { border: none; border-top: 3px solid #BC002D; margin: 20px 0; }

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

.pitch-h { color: #4caf50; }
.pitch-l { color: #f44336; }

/* Dark mode via Anki's native .night_mode class */
.night_mode .card {
    background: #1A1A1A;
    color: #E8E8E8;
}
.night_mode .card-type { color: #999999; }
.night_mode .translation { color: #E8E8E8; }
.night_mode .pronunciation { color: #999999; }
.night_mode .category {
    background: #252525;
    border-color: #333333;
    color: #999999;
}
.night_mode .key-vocab { color: #999999; }
.night_mode .vocab { color: #6DB3F2; }
.night_mode .cloze-answer { color: #6DB3F2; }
.night_mode .blank { border-bottom-color: #999999; }
.night_mode .register {
    border-color: #333333;
}
.night_mode .register-casual  { background: #252525; color: #999999; }
.night_mode .register-polite  { background: #1a2a3a; color: #64b5f6; border-color: #1a2a3a; }
.night_mode .register-formal  { background: #2a1f0e; color: #ffb74d; border-color: #2a1f0e; }
.night_mode .register-keigo   { background: #2a1a2a; color: #ce93d8; border-color: #2a1a2a; }
.night_mode .pitch-h { color: #81c784; }
.night_mode .pitch-l { color: #e57373; }
.night_mode hr#answer { border-top-color: #BC002D; }
.night_mode ruby rt { color: #999999; }
.night_mode .replay-button,
.night_mode .replaybutton {
    border-color: #333333;
    background: #1A1A1A;
}
'''
    )


def create_deck(tier: int, include_audio: bool = True, female: bool = False) -> tuple[genanki.Deck, list[str]]:
    """Create Anki deck for a specific tier.

    Args:
        tier: Tier number (1-6)
        include_audio: Whether to include audio files
        female: If True, use audio from tier*-audio-female/ directory

    Returns:
        Tuple of (deck, list of media files)
    """
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"
    audio_dir = ROOT / f"tier{tier}-audio-female" if female else ROOT / f"tier{tier}-audio"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    # Read vocabulary
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sentences = list(reader)

    # Create deck
    deck = genanki.Deck(
        get_deck_id(tier),
        f'Japanese IT Vocabulary - Tier {tier}'
    )

    model = create_model()
    media_files = []

    for idx, row in enumerate(sentences):
        num = idx + 1
        audio_file = f"tier{tier}_{num:03d}.mp3"
        audio_path = audio_dir / audio_file

        # Check if audio exists
        if include_audio and audio_path.exists():
            audio_ref = f"[sound:{audio_file}]"
            media_files.append(str(audio_path))
        else:
            audio_ref = "[No audio]"

        # Create hint (first 1-2 characters)
        sentence = row['Sentence']
        hint = sentence[:2] + "..." if len(sentence) > 2 else sentence

        note = genanki.Note(
            model=model,
            fields=[
                row['Sentence'],
                row['Translation'],
                row['Cloze'],
                to_ruby_html(row['Pronunciation']),
                row['Note'],
                audio_ref,
                hint,
                row.get('Register', ''),
                row['KeyMeaning'],
                row.get('PitchAccent', ''),
                row.get('Conjugations', ''),
            ],
            tags=[f'tier{tier}', row['Note'].replace(' ', '_').replace('-', '_')]
        )
        deck.add_note(note)

    return deck, media_files


def main():
    parser = argparse.ArgumentParser(
        description="Create Anki deck from vocabulary and audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/create_deck.py --tier 1
  uv run python scripts/create_deck.py --all
  uv run python scripts/create_deck.py --tier 1 --no-audio
        """
    )
    parser.add_argument("--tier", type=int, choices=list(range(1, 9)),
                        help="Tier number to create (1-8)")
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

    if not args.tier and not args.all and not args.combined:
        parser.print_help()
        sys.exit(1)

    if args.force_style:
        # Offset MODEL_ID by CSS hash so Anki creates a new model with updated styles
        model = create_model()
        css_hash = int(hashlib.sha256(model.css.encode()).hexdigest()[:6], 16)
        global MODEL_ID
        MODEL_ID += css_hash
        print(f"--force-style: MODEL_ID offset by {css_hash} (CSS hash)")

    include_audio = not args.no_audio
    suffix = "-female" if args.female else ""

    if args.combined:
        # Create combined deck with subdecks for each tier
        voice_label = " (Female)" if args.female else ""
        print(f"Creating combined deck with tier subdecks{voice_label}...")

        # Tier names for subdecks
        tier_names = {
            1: "Tier 1 - Foundational",
            2: "Tier 2 - Basic Development",
            3: "Tier 3 - Intermediate",
            4: "Tier 4 - Advanced",
            5: "Tier 5 - Communication",
            6: "Tier 6 - Expert",
            7: "Tier 7 - Job Interview",
            8: "Tier 8 - Problem Solving",
        }

        all_decks = []
        all_media = []
        total_notes = 0

        for tier in range(1, 9):
            # Create subdeck with :: notation
            subdeck_name = f"Japanese IT Vocabulary{voice_label}::{tier_names[tier]}"
            subdeck = genanki.Deck(
                DECK_BASE_ID + tier + (100 if args.female else 0),
                subdeck_name
            )

            _, media_files = create_deck(tier, include_audio, args.female)
            csv_path = ROOT / f"tier{tier}-vocabulary.csv"
            audio_dir = ROOT / f"tier{tier}-audio-female" if args.female else ROOT / f"tier{tier}-audio"

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                sentences = list(reader)

            model = create_model()
            for idx, row in enumerate(sentences):
                num = idx + 1
                audio_file = f"tier{tier}_{num:03d}.mp3"
                audio_path = audio_dir / audio_file

                if include_audio and audio_path.exists():
                    audio_ref = f"[sound:{audio_file}]"
                else:
                    audio_ref = "[No audio]"

                sentence = row['Sentence']
                hint = sentence[:2] + "..." if len(sentence) > 2 else sentence

                note = genanki.Note(
                    model=model,
                    fields=[
                        row['Sentence'],
                        row['Translation'],
                        row['Cloze'],
                        to_ruby_html(row['Pronunciation']),
                        row['Note'],
                        audio_ref,
                        hint,
                        row.get('Register', ''),
                        row['KeyMeaning'],
                        row.get('PitchAccent', ''),
                        row.get('Conjugations', ''),
                    ],
                    tags=[f'tier{tier}', row['Note'].replace(' ', '_').replace('-', '_')]
                )
                subdeck.add_note(note)

            all_decks.append(subdeck)
            all_media.extend(media_files)
            total_notes += len(sentences)
            print(f"  Added {tier_names[tier]}: {len(sentences)} notes")

        output = args.output or f"nihongo-it-vocab-complete{suffix}.apkg"
        package = genanki.Package(all_decks)
        package.media_files = all_media
        package.write_to_file(output)

        print(f"\nCreated: {output}")
        print(f"Total notes: {total_notes}")
        print(f"Total cards: {total_notes * 3} (3 cards per note)")
        print(f"Media files: {len(all_media)}")

    elif args.all:
        # Create separate deck for each tier
        for tier in range(1, 9):
            deck, media_files = create_deck(tier, include_audio, args.female)
            output = f"nihongo-it-vocab-tier{tier}{suffix}.apkg"

            package = genanki.Package(deck)
            package.media_files = media_files
            package.write_to_file(output)

            print(f"Created: {output} ({len(deck.notes)} notes, {len(media_files)} audio files, 3 cards/note)")
    else:
        # Single tier
        tier = args.tier
        deck, media_files = create_deck(tier, include_audio, args.female)
        output = args.output or f"nihongo-it-vocab-tier{tier}{suffix}.apkg"

        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(output)

        print(f"\nCreated: {output}")
        print(f"Notes: {len(deck.notes)}")
        print(f"Cards: {len(deck.notes) * 3} (3 cards per note)")
        print(f"Media files: {len(media_files)}")

        if not include_audio:
            print("\nNote: Audio files not included. Generate them first with:")
            print(f"  uv run python scripts/generate_audio.py --tier {tier}")


if __name__ == "__main__":
    main()
