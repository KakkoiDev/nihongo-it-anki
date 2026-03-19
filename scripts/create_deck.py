#!/usr/bin/env python3
"""Create Anki deck from vocabulary CSV and audio files.

This script generates Anki decks with a 3-card design:
- Card 1 (Listening): Audio only → Japanese + Furigana + English
- Card 2 (Reading): Japanese text → Furigana + English + Conjugations
- Card 3 (Vocabulary): Blanked sentence → Full sentence + Audio + Conjugations
- Card 4 (Keigo): English situation → Conjugations (verbs only)

Prerequisites:
- Audio files must be generated first: uv run python scripts/generate_audio.py --tier N
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

# Stable IDs for Anki (generated once, keep consistent)
# These ensure deck identity persists across regenerations
MODEL_ID = 1607392322  # v2.2 - added Register field
DECK_BASE_ID = 2059400110  # Random but stable


def to_ruby_html(text: str) -> str:
    """Convert 漢字【かんじ】 to <ruby>漢字<rt>かんじ</rt></ruby>."""
    return re.sub(
        r'([\u4e00-\u9fff\u3400-\u4dbf]+)【([^】]+)】',
        r'<ruby>\1<rt>\2</rt></ruby>',
        text,
    )


def get_deck_id(tier: int) -> int:
    """Generate stable deck ID for a tier."""
    return DECK_BASE_ID + tier


def create_model() -> genanki.Model:
    """Create the 3-card Anki model.

    Card 1 (Listening): Audio only → Japanese + Furigana + English + Conjugations
    Card 2 (Reading): Japanese text → Furigana + English + Conjugations
    Card 3 (Vocabulary): Blanked sentence + English → Full sentence + Audio + Conjugations
    Card 4 (Keigo): English situation → Conjugation table (verbs only)
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
            {'name': 'Conjugations'},   # HTML conjugation table
        ],
        templates=[
            # Card 1: Listening (audio-only front)
            {
                'name': 'Listening',
                'qfmt': '''<div class="card-type">Listening</div>
<div class="audio">{{Audio}}</div>
<div class="category">{{Category}}</div>{{#Register}}<span class="register register-{{Register}}">{{Register}}</span>{{/Register}}
''',
                'afmt': '''<div class="card-type">Listening</div>
<div class="audio">{{Audio}}</div>
<div class="sentence">{{Pronunciation}}</div>
<div class="category">{{Category}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
{{Conjugations}}
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
<div class="category">{{Category}}</div>
<hr id="answer">
<div class="translation">{{Translation}}</div>
<div class="key-vocab">Key: {{#PitchAccent}}{{PitchAccent}}{{/PitchAccent}}{{^PitchAccent}}<span class="vocab">{{Cloze}}</span>{{/PitchAccent}} ({{KeyMeaning}})</div>
{{Conjugations}}
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
<div class="category">{{Category}}</div>
<hr id="answer">
<div class="pronunciation">{{Pronunciation}}</div>
{{Conjugations}}
<script>
(function() {
    var el = document.getElementById('sentence');
    var cloze = '{{Cloze}}';
    el.innerHTML = el.textContent.split(cloze).join('<span class="cloze-answer">' + cloze + '</span>');
})();
</script>
''',
            },
            # Card 4: Keigo drill (verbs only - suppressed when Conjugations is empty)
            {
                'name': 'Keigo',
                'qfmt': '''{{#Conjugations}}<div class="card-type">Keigo</div>
<div class="translation">{{Translation}}</div>
<div class="category">{{Category}}</div>
<div class="prompt">Your action - humble form?</div>
{{/Conjugations}}
''',
                'afmt': '''{{#Conjugations}}<div class="card-type">Keigo</div>
<div class="translation">{{Translation}}</div>
<hr id="answer">
<div class="sentence">{{Sentence}}</div>
{{Conjugations}}
{{/Conjugations}}
''',
            },
        ],
        css='''
.card {
    font-family: "Hiragino Kaku Gothic Pro", "Noto Sans JP", "Yu Gothic", sans-serif;
    font-size: 20px;
    text-align: center;
    color: #333;
    background-color: #fafafa;
    padding: 20px;
}

.card-type {
    font-size: 12px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
}

.sentence {
    font-size: 28px;
    font-weight: bold;
    margin: 20px 0;
    line-height: 1.5;
}

.translation {
    font-size: 22px;
    color: #444;
    margin: 15px 0;
}

.pronunciation {
    font-size: 18px;
    color: #666;
    margin: 15px 0;
    line-height: 1.8;
}

.category {
    display: inline-block;
    background: #e0e0e0;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    color: #555;
    margin-top: 10px;
}

.key-vocab {
    font-size: 16px;
    color: #555;
    margin-top: 15px;
}

.vocab {
    font-weight: bold;
    color: #2196F3;
}

.prompt {
    font-size: 16px;
    color: #888;
    font-style: italic;
    margin: 15px 0;
}

.blank {
    display: inline-block;
    min-width: 4em;
    border-bottom: 2px solid #333;
    color: transparent;
}

.cloze-answer {
    color: #2196F3;
    font-weight: bold;
}

.audio {
    margin: 10px 0;
}

ruby {
    ruby-align: center;
}

ruby rt {
    font-size: 11px;
    font-weight: normal;
    color: #888;
}

hr#answer {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}

/* Conjugation table styles */
.conjugation-section {
    margin-top: 20px;
    text-align: left;
}

.conjugation-section summary {
    cursor: pointer;
    font-size: 14px;
    color: #666;
    padding: 8px;
    background: #f0f0f0;
    border-radius: 4px;
    margin-bottom: 10px;
}

.conjugation-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    margin-top: 10px;
}

.conjugation-table th {
    background: #e8e8e8;
    padding: 8px;
    text-align: left;
    font-weight: bold;
    color: #444;
}

.conjugation-table td {
    padding: 6px 8px;
    border-bottom: 1px solid #eee;
}

.conjugation-table td:first-child {
    color: #666;
    width: 45%;
}

.conjugation-table td:last-child {
    font-weight: 500;
}

.register {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 6px;
    margin-left: 6px;
    vertical-align: middle;
}
.register-casual  { background: #e0e0e0; color: #555; }
.register-polite  { background: #e3f2fd; color: #1565c0; }
.register-formal  { background: #fff3e0; color: #e65100; }
.register-keigo   { background: #f3e5f5; color: #6a1b9a; }

.pitch-h { color: #4caf50; }  /* green = high mora */
.pitch-l { color: #f44336; }  /* red = low mora */

.te-compounds {
    margin-top: 10px;
    text-align: left;
}

.te-compounds summary {
    cursor: pointer;
    font-size: 13px;
    color: #888;
    padding: 6px;
    background: #f8f8f8;
    border-radius: 4px;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
    .card {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    .card-type { color: #888; }
    .sentence { color: #ffffff; }
    .translation { color: #cccccc; }
    .pronunciation { color: #aaaaaa; }
    .category {
        background: #333;
        color: #aaa;
    }
    .key-vocab { color: #aaa; }
    .vocab { color: #64b5f6; }
    .cloze-answer { color: #64b5f6; }
    .prompt { color: #888; }
    .register-casual  { background: #333; color: #aaa; }
    .register-polite  { background: #1a2a3a; color: #64b5f6; }
    .register-formal  { background: #2a1f0e; color: #ffb74d; }
    .register-keigo   { background: #2a1a2a; color: #ce93d8; }
    .pitch-h { color: #81c784; }
    .pitch-l { color: #e57373; }
    .blank { border-bottom-color: #aaa; }
    hr#answer { border-top-color: #444; }
    ruby rt { color: #aaa; }
    .conjugation-section summary {
        background: #2a2a2a;
        color: #aaa;
    }
    .te-compounds summary {
        background: #2a2a2a;
        color: #999;
    }
    .conjugation-table th {
        background: #333;
        color: #ddd;
    }
    .conjugation-table td {
        border-color: #444;
        color: #ccc;
    }
    .conjugation-table td:first-child {
        color: #888;
    }
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
    parser.add_argument("--no-audio", action="store_true",
                        help="Create deck without audio files")
    parser.add_argument("--output", type=str,
                        help="Output filename (default: auto-generated)")

    args = parser.parse_args()

    if not args.tier and not args.all and not args.combined:
        parser.print_help()
        sys.exit(1)

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
        print(f"Total cards: {total_notes * 3}+ (3 cards per note, 4 for verbs)")
        print(f"Media files: {len(all_media)}")

    elif args.all:
        # Create separate deck for each tier
        for tier in range(1, 9):
            deck, media_files = create_deck(tier, include_audio, args.female)
            output = f"nihongo-it-vocab-tier{tier}{suffix}.apkg"

            package = genanki.Package(deck)
            package.media_files = media_files
            package.write_to_file(output)

            print(f"Created: {output} ({len(deck.notes)} notes, {len(media_files)} audio files, 3+ cards/note)")
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
        print(f"Cards: {len(deck.notes) * 3}+ (3 cards per note, 4 for verbs)")
        print(f"Media files: {len(media_files)}")

        if not include_audio:
            print("\nNote: Audio files not included. Generate them first with:")
            print(f"  uv run python scripts/generate_audio.py --tier {tier}")


if __name__ == "__main__":
    main()
