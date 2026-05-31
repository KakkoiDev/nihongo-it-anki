# Deck Migration: Dedup and Stable GUID Upgrade

How we recovered from duplicated notes + random-GUID history on a live Anki
collection without losing review schedules. Written after a real recovery
on 2026-04-21.

## Background

Before commit `30ddf37`, `scripts/create_deck.py` let genanki assign random
GUIDs on every build. Reimports never matched existing notes -> every new
release created a second copy. Users who imported multiple releases ended
up with 2-3x duplicates per sentence, random GUIDs, and progress scattered
across them.

Commit `30ddf37` switched to `genanki.guid_for(Sentence)` so future builds
update in place. That fixes new users and future updates, but existing
collections still have the random-GUID duplicates.

`scripts/migrate_guids.py` was built to resolve those existing collections.

## Problems Encountered in the Real Migration

### 1. Modern .apkg is zstd-compressed
Anki 2.1.50+ stores the collection as `collection.anki21b` (zstd-compressed
sqlite), keeping `collection.anki2` as a 1-note stub for backward compat.
Opening `anki21b` directly as sqlite fails ("file is not a database").

Fix (commit `07add28`): detect the zstd magic `\x28\xb5\x2f\xfd`, decompress
via the `zstd` CLI, operate on the sqlite, recompress when writing back.

### 2. `unicase` collation not registered
Anki registers a custom `unicase` collation at runtime. Python's sqlite3
doesn't know it, so any `VACUUM` or index touch on a collated column fails
with "no such collation sequence: unicase".

Fix: `conn.create_collation("unicase", ...)` with a case-insensitive
fallback.

### 3. Model ID mismatch silently loses scheduling
User's existing deck used model_id `1775480004557` (assigned by Anki at
some past import, likely via `--force-style`). Today's build uses
`1607392323` from `deck.toml`. Even with matching stable GUIDs, Anki
treats these as different note types. Importing the new build creates
parallel cards under the new model and leaves the old cards orphaned.
The user sees "progress reset".

Fix (commit `1b6fcb3`): `--model-id` flag rewrites `notetypes.id`,
`notes.mid`, `fields.ntid`, `templates.ntid` so the migrated collection's
note type id matches what future builds will import.

### 4. Multiple orphan note types
Repeated `--force-style` imports created note types like `(3-Card)+`,
`(3-Card)++`, `(3-Card)+++`. Only one had actual notes. The others were
empty but still occupied ids (including `1607392323` as an empty orphan).

Fix: `retarget_model` now detects when the target mid is an existing
empty orphan and deletes it (fields/templates/notetypes rows) before
renaming source -> target. Refuses if the target owns real notes.

### 5. .apkg roundtrip too invasive for a live collection
An import-migrated-apkg-on-top-of-existing-collection flow works for users
who haven't deleted their deck yet, but it's fragile: a wrong file or a
forgotten model_id retarget and scheduling is gone.

Fix (commit `4af1860`): `--in-place` and `--source-mid` flags. Script
operates directly on `~/.local/share/Anki2/User 1/collection.anki2`,
touches only notes with the given model id (so Minihongo / JLPT / Yomitan
decks are untouched), and skips the zip/repack entirely.

### 6. Wrong-file import (operator error, but worth flagging)
During recovery, importing `~/Share/export...apkg` (the original with
dupes) instead of `it-vocab-complete.apkg` (today's build) undid the
dedup. After the in-place migration + retarget, always import from the
*build output*, never from an older export.

### 7. AnkiWeb sync divergence
Direct db edits don't update Anki's `usn` (update sequence number).
AnkiWeb still has the pre-migration state. First sync after the edits
fails with "please use the Check Database function again".
Check Database alone won't resolve the divergence: you then need a
forced one-way sync (Preferences -> Syncing -> "force changes in one
direction" -> Upload) to push the clean local state up. Only then does
the phone sync down cleanly.

## Recovery Procedure (for future users upgrading this deck)

### Prerequisites
- Anki 2.1.50+ on desktop (needed for zstd anki21b format)
- `zstd` CLI installed
- Clone of this repo
- The user's `collection.anki2` file
- Anki closed

### Steps

1. **Safety backup.**
   ```
   cp "$HOME/.local/share/Anki2/User 1/collection.anki2" \
      "$HOME/.local/share/Anki2/User 1/collection.anki2.bak-$(date +%Y%m%d-%H%M%S)"
   ```

2. **Find the user's source model id.**
   ```
   sqlite3 "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     "SELECT id, name FROM notetypes WHERE name LIKE '%Japanese IT%';"
   ```
   Pick the one that has notes:
   ```
   sqlite3 "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     "SELECT mid, COUNT(*) FROM notes WHERE mid IN (SELECT id FROM notetypes WHERE name LIKE '%Japanese IT%') GROUP BY mid;"
   ```

3. **Dry-run the migration.**
   ```
   uv run python scripts/migrate_guids.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --in-place \
     --source-mid <USER_MID> \
     --model-id 1607392323 \
     --dry-run
   ```
   Expected: "Duplicate groups: ~N", "GUIDs to rewrite: ~M".

4. **Run for real.** Same command without `--dry-run`.

5. **Open Anki. Tools -> Check Database.** Expect "rebuilt and optimized".

6. **Import today's build to apply latest content.**
   File -> Import -> `/path/to/nihongo-it-anki/it-vocab-complete.apkg`
   Dialog should say "N notes updated, ~5 added".
   Do NOT import from a `-migrated.apkg` or the user's own export here;
   those have dupes.

7. **Force-upload to AnkiWeb.** Preferences -> Syncing -> "On next sync,
   force changes in one direction" -> Upload. Then click Sync.

8. **On phone: full sync -> Download from AnkiWeb.** Phone pulls clean
   state.

### Verification
- `トラブルシュート` card KeyMeaning shows "troubleshoot" (latest content)
- `このモジュールはすべての...` audio pronounces "subete" clearly
- A previously-reviewed card still shows its due date / interval

## What migrate_guids.py Does

1. Opens db (decompresses zstd if needed; registers unicase collation).
2. Reads notes filtered by `--source-mid` (or all if unset).
3. Groups by `genanki.guid_for(Sentence)` (field 0 is Sentence).
4. For each group:
   - If 1 note with the correct stable GUID: no-op.
   - If 1 note with a different GUID: update guid to stable.
   - If N notes: `pick_winner` chooses the one with most reps/revlog
     (tiebreak: lowest nid = oldest). Winner's GUID updates; losers'
     notes/cards/revlog get deleted.
5. If `--model-id` given: delete target orphan (if empty), then rename
   source_mid -> target_mid across notetypes/fields/templates/notes.
6. `VACUUM`.
7. Repack into apkg (unless `--in-place`).

## Pitfalls the Script Guards Against

- Won't retarget if the target model id already owns notes (refuses
  silent merge of distinct note types).
- Filters by `--source-mid` so Minihongo / Yomitan / other decks aren't
  touched when run against a live collection.
- Preserves `reps`, `ivl`, `factor`, `due`, `lapses` for winner cards
  (only writes `notes.guid` and `notes.mid`; cards/revlog untouched
  except for deleting rows tied to losing notes).

## Pitfalls the Script Does NOT Guard Against

- **Sentence field drift.** If the user's CSV and the current build disagree
  on the Sentence text (typo fix, wording change), GUIDs diverge and the
  import creates a fresh note. Commit `e72e4f4` deliberately reworded 5
  sentences - users on older exports will get 5 new notes (old ones remain
  empty and un-scheduled).
- **graves table.** Deletes don't leave tombstones. Syncing to AnkiWeb
  before force-uploading can resurrect deleted notes.
- **Custom styling from --force-style.** If the user's model CSS differs
  from today's build, today's build will overwrite styling on import. No
  data loss, just visual change.

## Key Commits

| Hash | What |
|------|------|
| `30ddf37` | Stable GUIDs in create_deck.py (root cause fix) |
| `795e21e` | Initial migrate_guids.py |
| `07add28` | zstd anki21b support |
| `1b6fcb3` | --model-id retarget flag |
| `4af1860` | --in-place and --source-mid flags |

## Quick Reference: The Working Command

For a user whose collection has Japanese IT Vocabulary notes under model
id `<MID>`, upgrading to `1607392323` (current `deck.toml`):

```
# 1. Close Anki. Backup.
cp "$HOME/.local/share/Anki2/User 1/collection.anki2" \
   "$HOME/.local/share/Anki2/User 1/collection.anki2.bak"

# 2. In-place migrate.
uv run python scripts/migrate_guids.py \
  "$HOME/.local/share/Anki2/User 1/collection.anki2" \
  --in-place --source-mid <MID> --model-id 1607392323

# 3. Open Anki -> Tools -> Check Database.
# 4. File -> Import it-vocab-complete.apkg.
# 5. Preferences -> Syncing -> force upload -> Sync.
# 6. Phone: sync, download from AnkiWeb.
```

## Subdeck Name Migration (Tier 1 -> Tier 01)

Separate one-time fix from the GUID migration above. The deck's tier
subdeck names were renamed from `"Tier N - ..."` to `"Tier 0N - ..."`
so Anki sorts them numerically instead of as `1, 10, 2, 3`.

### Why a script is needed

Anki does NOT auto-rename existing decks on `.apkg` import. It matches
decks by full name path. When an updated apkg ships with
`"Japanese IT Vocabulary::Tier 01 - Foundational"` and the user's
collection has `"Japanese IT Vocabulary::Tier 1 - Foundational"`, Anki
creates a NEW empty `"Tier 01"` subdeck and leaves the existing cards
in `"Tier 1"`. Result: duplicate-looking subdecks, half empty.

`scripts/migrate_deck_names.py` rewrites the `decks.name` rows directly
so future imports map to the same subdecks. Card history is untouched:
cards reference decks via `cards.did` (deck ID), which is unchanged by
a name rename.

### Procedure (per user)

1. **Close Anki.**
2. **Safety backup** (see step 1 of the GUID procedure above).
3. **Dry run:**
   ```
   uv run python scripts/migrate_deck_names.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --deck it-vocab --dry-run
   ```
   Expect 9 planned renames (Tier 1..9). Tier 10 already correct.
4. **Real run:** drop `--dry-run`. Repeat for `--deck it-kundoku`.
5. **Open Anki.** Subdecks should now show `Tier 01..Tier 10` in order.
6. **Force-upload to AnkiWeb** (same as pitfall #7 above): direct DB
   edits don't bump `usn`. First sync after this will fail with "use
   Check Database again". Then Preferences -> Syncing -> force changes
   one direction -> Upload.

### Idempotency and edge cases

- Rerunning after success is a no-op (matches new names, reports
  "already correct").
- If a user has manually renamed a subdeck to something else, the regex
  match falls through and that subdeck is left alone.
- Script only touches rows in the `decks` table whose name matches the
  configured deck's parent prefix. Other decks (Minihongo, Yomitan,
  etc.) are not affected.
- Handles zstd-compressed `collection.anki21b` the same way as
  `migrate_guids.py`.
