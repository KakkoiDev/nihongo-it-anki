# nihongo-it-anki

<img src="demo.png" alt="Anki deck demo" width="600">

Japanese IT vocabulary for Anki. 1000 sentences with AI-generated audio. Open source - build your own deck with the same tools.

## Download

**[AnkiWeb](https://ankiweb.net/shared/info/698107537)** - install directly from Anki app

**[GitHub Release](https://github.com/KakkoiDev/nihongo-it-anki/releases/latest/download/nihongo-it-vocab-complete.apkg)** (58 MB) - manual download

## What's Included

- 1000 IT vocabulary sentences across 6 difficulty tiers
- 2000 cards (comprehension + production for each sentence)
- AI-generated Japanese audio (Microsoft Edge TTS) - natural-sounding neural voices
- Furigana readings for all kanji
- Key vocabulary with English meanings
- Verb conjugation tables (collapsible, N1-level coverage)
- Dark mode support (automatic system theme detection)

## Card Types

**Comprehension** — Audio plays, read Japanese, reveal English translation + conjugation table

**Production** — See English, produce Japanese, check with audio

## Features

**Dark Mode** — Automatically matches your system theme preference

**Verb Conjugation Tables** — Collapsible tables on comprehension cards showing all conjugation forms:
- Basic forms (dictionary, polite, negative, te-form, past)
- Advanced forms (potential, passive, causative, conditional, volitional, imperative)
- Keigo forms (respectful, humble)
- Works for する verbs, godan/ichidan verbs, and い-adjectives

## Tiers

| Tier | Count | Level | Focus |
|------|-------|-------|-------|
| 1 | 150 | N5-N4 | Daily essentials, git, basic actions |
| 2 | 200 | N4-N3 | Agile, APIs, databases, testing |
| 3 | 250 | N3 | Code review, architecture, AWS |
| 4 | 200 | N3-N2 | Security, debugging, documentation |
| 5 | 100 | N2 | Communication, soft skills |
| 6 | 100 | N2-N1 | Presentations, advanced topics |

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
| `create_deck.py` | Create Anki .apkg files |
| `validate.py` | Validate CSVs and audio files |
| `pronunciation.py` | Furigana extraction, English→katakana conversion |
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
