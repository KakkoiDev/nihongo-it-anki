# Documentation

Technical and operational documentation for this repo. The
project-level README is in the repo root.

| File | What it covers |
|------|----------------|
| [`tts-audio-debugging.md`](tts-audio-debugging.md) | How to audit, classify, and fix Edge TTS misreadings. ASR round-trip methodology, bug taxonomy, false-positive filtering, fix workflow. |
| [`MIGRATE-DECK-NAMES.md`](MIGRATE-DECK-NAMES.md) | Unified guide for the two DB-level Anki migration scripts (`migrate_deck_names.py` and `migrate_guids.py`). When to run which, full procedure, troubleshooting. |
| [`REPORT-DECK-MIGRATION.md`](REPORT-DECK-MIGRATION.md) | Postmortem of the 2026-04-21 GUID + model-id recovery on a live Anki collection. Anki schema notes (zstd anki21b, unicase collation, orphan notetypes, AnkiWeb sync divergence). |

The repo-root files:

- `README.md`: project overview, deck list, build commands.
- `ANKIWEB-README.md`: AnkiWeb deck submission text (title, tags,
  description block).
- `CLAUDE.md`: instructions for AI coding agents working on this
  repo.
- `RELEASE.md` (gitignored): scratch space for current release
  notes; used by `scripts/release.py --notes-file`.
