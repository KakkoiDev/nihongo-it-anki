# nihongo-it-anki

Multi-deck Anki generator for IT Japanese. Each deck lives under `decks/<slug>/` with its own `deck.toml`, CSVs, translations, and audio.

## Decks

| Slug | Name | Tiers |
|------|------|-------|
| `it-vocab` | Japanese IT Vocabulary | 15 (1516 sentences) |
| `it-kundoku` | IT Kundoku | 3 (89 sentences) |
| `jp-teaching` | Japanese Teaching Phrases | 3 (130 sentences) |
| `accounting` | 会計・お金周り / Japanese Accounting | 9 (129 sentences) |
| `fudosan` | 不動産・住宅購入 / Japanese Home Ownership | 12 (180 sentences) |
| `agentic-lab` | Agentic Lab Priority Path | 12 (554 sentences) |

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
| `generate_furigana.py` | Fill Pronunciation column from UniDic, one 【】 group per kanji run. Fills only empty cells unless `--force`, and reports any token whose reading it could not align instead of guessing. Even with `--force` a non-empty cell is kept when a token in that row could not be aligned. UniDic answers out of context, so read the generated readings before trusting them: it gets rendaku and counter readings wrong (`予定通り` as とおり, `30分` as ぶん) |
| `generate_pitch_accent.py` | Fill PitchAccent column from UniDic |
| `add_key_meanings.py` | Fill KeyMeaning column from translations.py |
| `check_pronunciation.py` | Verify furigana readings against UniDic (standard pronunciation check; also run in advisory mode by `validate.py`). Whitelist legit divergences in `decks/<slug>/pronunciation_overrides.py`. It re-tags each token's bare surface, so most of what it reports is context loss rather than a wrong card: alone, UniDic reads 一つ as いちつ, 化 as ばけ, 多 as さわ. An override key must never be a substring of a longer word in the deck - a key of `行` also cuts 実行 and 進行 in half |
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

1. Register the deck in [jpanki](https://github.com/KakkoiDev/jpanki)'s `src/jpanki/ids.toml`, with a `model_id` and a `deck_base_id` range no other entry claims. That file spans every project, not just this repo — two decks sharing a base ID silently merge in a user's collection, which has already happened once (see the `jp-teaching` comment there). Then bump the `jpanki` rev pinned in `pyproject.toml`. `tests/test_id_registry.py` checks every `deck.toml` against the pinned registry, so a deck whose IDs are not registered in the pinned rev fails the suite. Bump the rev by editing the `jpanki` revision strings in `uv.lock` by hand, never by regenerating it: the committed lock is format `revision = 3` with per-entry `upload-time` metadata, and a uv older than 0.8.4 rewrites the whole file to drop both. `required-version` in `pyproject.toml` states that floor but only binds uv 0.5.14 and later, since older versions ignore the setting; `tests/test_lockfile_format.py` reads the lock itself and fails on a downgraded one whatever uv produced it. Verify with `uv sync --frozen`.
2. Create `decks/<slug>/deck.toml` with the IDs you just registered
3. Add `tier{N}-vocabulary.csv` files (columns: Sentence, Translation, Cloze, Pronunciation, Note, Register, KeyMeaning, PitchAccent)
   - If any sentence also appears in another deck, set `guid_namespace = "<slug>"` in `deck.toml`. Note GUIDs are derived from the sentence, so without it both decks mint the same GUID under different model IDs, and Anki rejects the second import as a notetype conflict: deck present, zero cards, no error. See `tests/test_import_into_anki.py`.
   - Known exception: `jp-teaching` predates this rule and sets no namespace, so its one sentence shared with `it-vocab` (ここまでで質問はありますか？) still collides. Left as-is because its GUIDs are published; do not read the rule as universally enforced.
4. Add `translations.py` with `TRANSLATIONS` dict for KeyMeaning — only if the CSVs don't already carry it; `fudosan` ships KeyMeaning filled in and has no `translations.py`
5. Fill PitchAccent: `uv run python scripts/generate_pitch_accent.py --deck <slug>`
6. Check readings: `uv run python scripts/check_pronunciation.py --deck <slug>`, whitelisting genuine divergences in `decks/<slug>/pronunciation_overrides.py`
7. Run the build pipeline: generate audio, build decks, release

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
