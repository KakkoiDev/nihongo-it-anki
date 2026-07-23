# nihongo-it-anki

Multi-deck Anki generator for IT Japanese. Each deck lives under `decks/<slug>/` with its own `deck.toml`, CSVs, translations, and audio.

## Decks

| Slug | Name | Tiers |
|------|------|-------|
| `it-vocab` | Japanese IT Vocabulary | 15 (1516 sentences) |
| `it-kundoku` | IT Kundoku | 3 (89 sentences) |
| `jp-teaching` | Japanese Teaching Phrases | 3 (130 sentences) |
| `accounting` | 会計・お金周り / Japanese Accounting | 9 (129 sentences) |

## Build Pipeline

All scripts are in `scripts/` and accept `--deck <slug>` (defaults to `it-vocab`).

### 1. Generate audio (skips existing files)

```bash
uv run python scripts/generate_audio.py --deck <slug> --all
```

- Uses Edge TTS (ja-JP-KeitaNeural male voice)
- Audio saved to `decks/<slug>/tier{N}-audio/`
- `--force` regenerates all files (use after sentence changes)
- `--female` generates with NanamiNeural to `tier{N}-audio-female/`

### 2. Build decks

```bash
# Combined deck (all tiers in one .apkg)
uv run python scripts/create_deck.py --deck <slug> --combined

# Individual tier files
uv run python scripts/create_deck.py --deck <slug> --all

# Both (typical)
uv run python scripts/create_deck.py --deck <slug> --combined --all
```

Output: `<slug>-complete.apkg` and `<slug>-tier{N}.apkg` in project root.

### 3. Release

Each deck is released independently. Tags use `{slug}/{version}` namespace.

```bash
# Dry run first
uv run python scripts/release.py --deck <slug> --version <version> --dry-run

# Create release
uv run python scripts/release.py --deck <slug> --version <version> --title "Description"

# With release notes from file
uv run python scripts/release.py --deck <slug> --version <version> --notes-file RELEASE.md

# Draft release
uv run python scripts/release.py --deck <slug> --version <version> --draft
```

Attaches `<slug>-complete.apkg` + all `<slug>-tier{N}.apkg` files as release assets.

## Full Rebuild Example

To regenerate audio and rebuild for a single deck:

```bash
uv run python scripts/generate_audio.py --deck it-vocab --all
uv run python scripts/create_deck.py --deck it-vocab --combined --all
uv run python scripts/release.py --deck it-vocab --version v4.3 --title "Description" --dry-run
```

If sentences in a tier changed (e.g. tier split), force-regenerate that tier's audio:

```bash
uv run python scripts/generate_audio.py --deck it-vocab --tier 9 --force
```

## Other Scripts

| Script | Purpose |
|--------|---------|
| `generate_pitch_accent.py` | Fill PitchAccent column from UniDic |
| `add_key_meanings.py` | Fill KeyMeaning column from translations.py |
| `check_pronunciation.py` | Verify furigana readings against UniDic (standard pronunciation check; also run in advisory mode by `validate.py`). Whitelist legit divergences in `decks/<slug>/pronunciation_overrides.py` |
| `validate.py` | Validate CSVs and audio files |
| `test_tts.py` | Test TTS for specific rows or text |
| `pronunciation.py` | Shared TTS preprocessing (furigana, katakana conversion) |

## Config

Each deck has `decks/<slug>/deck.toml`:

```toml
[deck]
slug = "it-vocab"
name = "Japanese IT Vocabulary"
model_id = 1607392323       # Must be unique per deck
deck_base_id = 2059400110   # Must be unique per deck

[tiers]
count = 10
names = {1 = "Tier 1 - Foundational", ...}
sizes = {1 = 150, ...}
```

## Adding a New Deck

1. Create `decks/<slug>/deck.toml` with unique `model_id` and `deck_base_id`
2. Add `tier{N}-vocabulary.csv` files (columns: Sentence, Translation, Cloze, Pronunciation, Note, Register, KeyMeaning, PitchAccent)
3. Add `translations.py` with `TRANSLATIONS` dict for KeyMeaning
4. Run the build pipeline: generate audio, build decks, release
