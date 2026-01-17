# nihongo-it-anki

Japanese IT vocabulary for Anki. 1000 sentences with native audio.

## Download

**[nihongo-it-vocab-complete.apkg](https://github.com/KakkoiDev/nihongo-it-anki/releases/latest/download/nihongo-it-vocab-complete.apkg)** (166 MB)

Import directly into Anki. No setup required.

## What's Included

- 1000 IT vocabulary sentences across 6 difficulty tiers
- 2000 cards (comprehension + production for each sentence)
- Native Japanese audio (Kokoro TTS)
- Furigana readings for all kanji
- Key vocabulary with English meanings

## Card Types

**Comprehension** — Audio plays, read Japanese, reveal English translation

**Production** — See English, produce Japanese, check with audio

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

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/), espeak-ng, and ffmpeg.

```bash
# Install dependencies
sudo apt-get install espeak-ng ffmpeg  # Ubuntu/Debian
brew install espeak ffmpeg              # macOS

# Clone and setup
git clone https://github.com/KakkoiDev/nihongo-it-anki.git
cd nihongo-it-anki
uv sync

# Generate audio (~2 hours for all tiers)
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
| `create_deck.py` | Create Anki .apkg files |
| `validate.py` | Validate CSVs and audio files |
| `pronunciation.py` | Furigana extraction, English→katakana |
| `add_key_meanings.py` | Generate English meanings for key words |

## Customization

**Use female voice** — Add `--female` flag to commands

```bash
uv run python scripts/generate_audio.py --all --female
uv run python scripts/create_deck.py --combined --female
```

| Voice | Type | Flag |
|-------|------|------|
| `jm_kumo` | Male | Default |
| `jf_alpha` | Female | `--female` |

**Modify cards** — Edit CSS in `scripts/create_deck.py`

**Add vocabulary** — Edit `tier{N}-vocabulary.csv`, regenerate audio and deck

## Known Limitations

Kokoro TTS sometimes links particles (を, に, が) to the following word instead of the preceding word. Audio is comprehensible but may sound slightly unnatural.

## Credits

- [Kokoro TTS](https://github.com/hexgrad/kokoro) — Text-to-speech
- [genanki](https://github.com/kerrickstaley/genanki) — Anki deck generation

## License

MIT
