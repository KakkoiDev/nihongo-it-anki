# Documentation

Technical and operational documentation for this repo. The
project-level README is in the repo root.

| File | What it covers |
|------|----------------|
| [`tts-audio-debugging.md`](tts-audio-debugging.md) | How to audit, classify, and fix Edge TTS misreadings. ASR round-trip methodology, bug taxonomy, false-positive filtering, fix workflow. |
| [`MIGRATE-DECK-NAMES.md`](MIGRATE-DECK-NAMES.md) | Unified guide for the two DB-level Anki migration scripts (`migrate_deck_names.py` and `migrate_guids.py`). When to run which, full procedure, troubleshooting. |
| [`REPORT-DECK-MIGRATION.md`](REPORT-DECK-MIGRATION.md) | Postmortem of the 2026-04-21 GUID + model-id recovery on a live Anki collection. Anki schema notes (zstd anki21b, unicase collation, orphan notetypes, AnkiWeb sync divergence). |
| [`IMPROVEMENTS.md`](IMPROVEMENTS.md) | Findings from the 2026-06-12 content audit: GUID-from-sentence history loss (+ `guid-migration-map.csv`), build/script bugs, ASR false-positive classes, and audit decisions deliberately kept. |
| [`PRIORITY-PATH-agentic-lab.md`](PRIORITY-PATH-agentic-lab.md) | The specification for `agentic-lab` tiers 1-5: which 179 `it-vocab` sentences they re-use, in which of the five phases, and why that order. Tiers 6-12 are authored in the deck itself and are not specified here. |

The repo-root files:

- `README.md`: project overview, deck list, build commands.
- `ANKIWEB-README.md`: AnkiWeb deck submission text (title, tags,
  description block).
- `AGENTS.md`: instructions for AI coding agents working on this
  repo. `CLAUDE.md` is a symlink to it.
- `RELEASE.md` (gitignored): scratch space for current release
  notes; used by `scripts/release.py --notes-file`.
