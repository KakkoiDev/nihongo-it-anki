# nihongo-it-anki

<img src="demo.png" alt="Anki deck demo" width="600">

Japanese IT vocabulary for Anki. 1075 sentences with AI-generated audio, pitch accent coloring, and 4 card types designed for real workplace skill building. Open source.

## Download

**[AnkiWeb](https://ankiweb.net/shared/info/698107537)** - install directly from Anki app

**[GitHub Release](https://github.com/KakkoiDev/nihongo-it-anki/releases/latest/download/nihongo-it-vocab-complete.apkg)** - manual download

## What's Included

- 1075 IT vocabulary sentences across 8 tiers
- 3225+ cards (Listening + Reading + Vocabulary Cloze + Keigo Drill)
- AI-generated Japanese audio (Microsoft Edge TTS KeitaNeural)
- Pitch accent display with green (high) / red (low) furigana coloring
- Register badges (polite/keigo) on card fronts
- IT-optimized verb conjugation tables with te-form compound reference
- Furigana readings for all kanji
- Dark mode support

## Card Types

**Listening** - Audio-only front. Forces pure listening comprehension for meetings and standups.

**Reading** - Japanese text front, no audio. Trains reading for Slack, PRs, and documentation.

**Vocabulary Cloze** - Key word blanked in sentence with English hint. Tests one word at a time.

**Keigo Drill** - Humble form prompt (verbs only). Builds formal register for presentations and client meetings.

## Features

**Pitch Accent** - Green/red coloring on key word furigana shows Tokyo dialect accent pattern. Type 0 (flat), type 1 (atamadaka), and nakadaka patterns displayed.

**Register Badges** - Each card shows polite or keigo badge so you know when to use each sentence.

**IT-Optimized Conjugations** - 11 forms that matter at work:
- Daily speech: dictionary, polite, polite negative, te-form, polite past, progressive (ている)
- Work patterns: potential, passive, conditional, volitional, should
- Keigo: respectful, humble
- Te-form compound reference (ておく, ていただく, てしまう, etc.)

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
