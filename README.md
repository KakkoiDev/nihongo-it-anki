# nihongo-it-anki

<img src="demo.png" alt="Anki deck demo" width="600">

Japanese IT vocabulary for Anki. 1075 sentences with AI-generated audio, pitch accent coloring, and 3 card types designed for real workplace skill building. Open source.

## Download

**[AnkiWeb](https://ankiweb.net/shared/info/698107537)** - install directly from Anki app

**[GitHub Release](https://github.com/KakkoiDev/nihongo-it-anki/releases/latest/download/nihongo-it-vocab-complete.apkg)** - manual download

## What Changed in v3.3

v3.3 is a complete overhaul from the original Kokoro TTS release.

- **Audio engine** - Switched from Kokoro TTS to Microsoft Edge TTS (KeitaNeural). Significantly more natural prosody and pronunciation.
- **Teaching method** - Cards now train listening comprehension first. The Listening card plays audio with no text on the front, forcing you to parse spoken Japanese before seeing the answer. This mirrors real workplace conditions where you hear Japanese before you read it.
- **3 focused card types** - Listening, Reading, and Vocabulary Cloze. Each targets a different skill without overlap. Removed the Keigo Drill card type.
- **Interview section** - Tier 7 with 30 keigo sentences covering self-introduction, technical skills, achievements, and motivation for job interviews at Japanese companies.
- **Pitch accent** - Green/red furigana coloring shows Tokyo pitch accent patterns on key vocabulary.
- **Register badges** - Each card shows its formality level (polite/keigo) so you know when to use each expression.
- **Progress resets on upgrade** - The note type changed entirely. Anki cannot map old scheduling data to the new cards.

## What's Included

- 1075 IT vocabulary sentences across 8 tiers
- 3225 cards (Listening + Reading + Vocabulary Cloze)
- AI-generated Japanese audio (Microsoft Edge TTS KeitaNeural)
- Pitch accent display with green (high) / red (low) furigana coloring
- Register badges (polite/keigo) on card fronts
- Furigana readings for all kanji
- Dark mode support

## Card Types

**Listening** - Audio-only front. No text. Forces pure listening comprehension for meetings and standups.

**Reading** - Japanese text front, no audio. Trains reading for Slack, PRs, and documentation.

**Vocabulary Cloze** - Key word blanked in sentence with English hint. Tests one word at a time, not full sentence recall.

## Features

**Pitch Accent** - Green (high) / red (low) coloring on key word furigana. Learn correct Tokyo accent from the start.

**Register Badges** - Each card shows polite or keigo badge so you know when to use each sentence.

**100% Audio** - Neural TTS for every sentence (Microsoft Edge ja-JP-KeitaNeural).

## Tiers

| Tier | Count | Focus |
|------|-------|-------|
| 1 | 150 | Daily essentials, git, basic actions |
| 2 | 200 | Agile, APIs, databases, testing |
| 3 | 250 | Code review, architecture, AWS |
| 4 | 200 | Security, debugging, documentation |
| 5 | 100 | Communication, soft skills |
| 6 | 115 | Presentations (including formal keigo) |
| 7 | 30 | Job interview (full keigo register) |
| 8 | 30 | Problem-solving discussions |

## Build From Source

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and setup
git clone https://github.com/KakkoiDev/nihongo-it-anki.git
cd nihongo-it-anki
uv sync

# Generate audio
uv run python scripts/generate_audio.py --all

# Or generate with female voice
uv run python scripts/generate_audio.py --all --female

# Create deck
uv run python scripts/create_deck.py --combined

# Or create deck with female voice audio
uv run python scripts/create_deck.py --combined --female
```

## Scripts

| Script | Purpose |
|--------|---------|
| `generate_audio.py` | Generate TTS audio for sentences |
| `generate_conjugations.py` | Generate verb/adjective conjugation tables |
| `generate_pitch_accent.py` | Generate pitch accent data from UniDic |
| `create_deck.py` | Create Anki .apkg files |
| `validate.py` | Validate CSVs and audio files |
| `pronunciation.py` | Furigana extraction, English-to-katakana conversion |
| `add_key_meanings.py` | Generate English meanings for key words |
| `test_tts.py` | Quick TTS test for specific sentences |

## Customization

**Use female voice** — Add `--female` flag to commands

```bash
uv run python scripts/generate_audio.py --all --female
uv run python scripts/create_deck.py --combined --female
```

| Voice | Type | Flag |
|-------|------|------|
| `ja-JP-KeitaNeural` | Male | Default |
| `ja-JP-NanamiNeural` | Female | `--female` |

**Modify cards** — Edit CSS in `scripts/create_deck.py`

**Add vocabulary** — Edit `tier{N}-vocabulary.csv`, regenerate audio and deck

## Known Limitations

### Testing TTS Changes

Use `test_tts.py` to quickly test pronunciation changes without regenerating all audio:

```bash
# Test specific row(s) from a tier CSV
uv run python scripts/test_tts.py --tier 1 --row 5
uv run python scripts/test_tts.py --tier 1 --row 5,7,10

# Test arbitrary text with furigana
uv run python scripts/test_tts.py --text "問題【もんだい】を、見【み】つけました"
```

Output files are saved to the project root (`test_tier1_005.mp3` or `test_tts.mp3`).

## Credits

- [Edge TTS](https://github.com/rany2/edge-tts) - Text-to-speech (Microsoft Edge neural voices)
- [genanki](https://github.com/kerrickstaley/genanki) - Anki deck generation

## License

MIT
