# Improvement Notes

Findings collected during the 2026-06-12 audit and remediation passes
(KeyMeaning gloss fixes, sentence naturalness rewrite, てください
diversification, tiers 11-12 authoring). Ordered by impact.

STATUS 2026-06-12 (second pass): items 1-9 are RESOLVED. Each section
keeps its original analysis with a status line. Resolutions:

- 1: `scripts/migrate_sentences.py` + `guid-migration-map.csv` +
  `tests/test_migrations.py` (headless Anki harness pins importer
  semantics; history-preserving rewrite migration verified by test)
- 2: `create_deck.py --combined --all` builds both
- 3: digit/kanji-numeral normalization on both ASR sides, SHORT_CLIP
  class; SOC 2 was a REAL TTS bug (audio said soku-ni), fixed via
  ソックツー substitution and regenerated
- 4: 121 duplicate keys removed (loaded dict verified identical);
  validate.py warns on new duplicates
- 5: validate.py prints the per-tier/total counts table
- 6: validate.py errors on Japanese/empty/letterless Translation cells
- 7: moved to audits/ with date prefix
- 8: regex accepts /
- 9: validate.py prints tekudasai density per tier

New finding from the test harness: Anki's importer skips notes whose
incoming mod equals the existing note's mod, even with update=ALWAYS;
and media imports are reference-driven with checksum-renaming on
conflict (cross-deck filename collisions are SAFE; no media
namespacing needed). Pinned in tests/test_migrations.py.

## 1. Note GUIDs are derived from sentence text (review-history loss)

`create_deck.py:375` uses `genanki.guid_for(row['Sentence'])`. Any edit to a
sentence creates a brand-new note on import; the old note stays in the user's
collection as an orphan holding the review history. The 2026-06-12 passes
changed 293 sentences; `guid-migration-map.csv` (repo root) maps
`old_guid -> new_guid` with both sentence texts for all of them.

- `migrate_guids.py` does NOT cover this case. It normalizes a collection's
  GUIDs to `guid_for(field[0])`, which only fixes random-GUID decks. When the
  sentence itself changed, old and new GUIDs both look "stable" and never
  match.
- Follow-up worth doing: a `migrate_sentences.py` that reuses
  migrate_guids.py's apkg/colpkg plumbing, takes `guid-migration-map.csv`,
  and rewrites matching notes' guid + Sentence field in the user collection
  BEFORE re-import. Until then: re-importing the rebuilt deck adds the 293
  rewritten cards as new and the old ones must be deleted by hand (searchable
  by old sentence text from the map). Scheduling on those cards resets.
- Alternative long-term scheme: `guid_for(f"{slug}-t{tier}-r{row}")` makes
  GUIDs survive sentence edits but makes row insertion/reordering destructive
  instead. Either way the tradeoff should be a documented decision, not an
  accident of `guid_for(Sentence)`.

## 2. `create_deck.py --combined --all` silently skips `--all`

`create_deck.py:446-513` is `if args.combined: ... elif args.all: ...`.
CLAUDE.md documents `--combined --all` as the typical invocation, but the
tier files are silently not built (their mtimes simply stay stale). Change
`elif` to a second `if`, or update the docs. Bit me on 2026-06-12: the
combined deck had the fixes, the tier .apkg files did not.

## 3. ASR audit false-positive classes (get_transcript.py)

Recurring noise classes seen across ~70 verified files; all are
normalization gaps, not audio defects:

- Digits: expected-side normalization of `1点` drops the digit (テン) while
  whisper writes 一点 (イチテン); also 朝イチ transcribed as 朝1. Normalize
  digits to kana on BOTH sides before comparing.
- Latin acronym + digit: whisper turned サンセット into 3セット and SOC 2
  into 即に. The SOC 2 one is worth an actual listen: TTS may be reading it
  as ソクニ rather than エスオーシーツー. If so, the fix is a spelled-out
  Pronunciation (`SOC 2` -> `エスオーシーツー`), same pattern as the
  existing TTS_KANJI_OVERRIDES work.
- Kana-vs-kanji representation: メモ係 -> メモがかり, バッチ -> 抜地.
  Reading is correct; edit distance fires on the script choice.
- Sub-second clips (e.g. りょ。) give whisper nothing to anchor on.
  Exclude clips under ~1s from MISMATCH classification or verify by ear.

## 4. translations.py has ~119 pre-existing duplicate keys

`TRANSLATIONS` contains ~119 keys defined twice (last-wins): マージ,
リリース, ロールバック, 方針, 改善, etc. Harmless at runtime but it hides
intent (which value was meant?). One-time dedup pass, then a guard in
validate.py or a unit check that fails on duplicate literals.

## 5. Hardcoded counts drift across docs

The 1265 -> 1176 stale-count fix took multiple commits; the deck is now 1376
and CLAUDE.md had to be touched again. Emit the deck table (tiers, sizes,
total) from `validate.py` or a tiny `counts.py` and paste, or generate the
CLAUDE.md table section.

## 6. No English-side quality check

The audit found EN fragments ("Real-time data processing.", "Just a heads up
notice.") and a Translation cell containing Japanese (tier3:141). validate.py
checks JP-side structure only. Cheap mechanical wins: flag Translation cells
containing kana/kanji, flag cells with no ASCII letters, flag single-word
cells. Semantic quality needs a periodic LLM pass; mechanical checks catch
the embarrassing class.

## 7. Untracked audit snapshots

`audio-audit.csv` and `audio-audit-v2.csv` sit untracked in the repo root
with TTS audit findings of unclear actioned status. Move under `audits/`
with a date in the filename and commit, or delete after cross-referencing
with the pronunciation.py fixes already merged.

## 8. add_key_meanings.py English-term regex

The "needs manual translation" report regex `^[A-Za-z0-9\s\-\.]+$` lacks
`/`, so `CI/CD` is flagged forever. validate.py's equivalent already has
`/`. One-character fix.

## 9. てください density (style regression guard)

Tiers 1-4 went from 60% てください endings to ~30% on 2026-06-12. New
sentence batches will drift back up if generated carelessly. If adding
sentences in bulk, check the distribution (a one-liner grep -c per tier)
against the ~30% ceiling before generating audio.

## 10. Deliberately NOT proposed

- CI pipelines, semantic-similarity validation, dict/CSV sync enforcement:
  dual-maintenance busywork for a single-maintainer repo; the
  fill-only-empty script change already removed the regression vector.
- Rewriting the kundoku deck's register: its kanbun style is the point.
- Female-voice audio for tiers 11-12: no tier*-audio-female dirs exist for
  any tier; generate for all 12 at once if ever wanted.

## Audit decisions kept (so they are not re-litigated)

- ページングされました (T3:245): kept; standard SRE-book Japanese. Only its
  KeyMeaning ("pagination") was wrong and is fixed to "paging (on-call)".
- 情報の腐敗 (T10:3): noun usage kept; T9:21 verb form was changed to the
  idiomatic ドキュメントは腐りやすい.
- Abbreviation-expansion clozes (AZ -> アベイラビリティゾーン, P99 ->
  パーセンタイル, Parameter Store -> パラメータストア): cloze word
  intentionally absent from the sentence; teaches the expansion.
- Doc-style instructions (SQL keyword rows, AWS how-tos, prohibitions like
  本番でテストしないでください) keep てください deliberately.
