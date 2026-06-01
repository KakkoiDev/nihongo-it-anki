# Anki Database Migration Guide

Two scripts in this repo edit a user's `collection.anki2` SQLite
database directly to fix state that can't be carried over by a plain
`.apkg` import. Both have been used successfully on real collections
(2026-04-21 GUID recovery, 2026-06-01 deck rename + orphan cleanup)
and the procedure below reflects what actually worked.

| Script | What it migrates | When to run |
|--------|------------------|-------------|
| `scripts/migrate_deck_names.py` | Subdeck names (`Tier 1` -> `Tier 01`) + orphan subdecks from older `deck.toml` revisions | Once, after a release that zero-pads or renames tier names |
| `scripts/migrate_guids.py` | Note GUIDs (random -> stable sentence-based) + model/notetype id retargeting | Once, if your existing collection was first imported before stable GUIDs landed in `create_deck.py` (pre-`30ddf37`), OR if importing produces duplicates / orphan notetypes |

Both scripts:

- Open `collection.anki2` (or zstd-compressed `collection.anki21b`) directly.
- Require Anki to be **closed**.
- Auto-back up the collection (`.bak-<timestamp>` sibling) before any write.
- Update `decks.usn` / `col.mod` so AnkiWeb sync detects the change.
- Write `graves` tombstones for any deletions so sync propagates them.
- Are **idempotent**: re-running after success is a no-op.

`.apkg` import on its own does NOT do any of the above. Anki matches
imported decks by name path and notes by GUID; mismatches on either
end create parallel decks / duplicate notes instead of updating in
place. These scripts close those gaps.

If you just installed Anki and have never imported this deck before,
**skip this guide**. Just import the latest `.apkg`; you'll get clean
state directly.

---

## Decision flow

Use this to pick the right script(s) for your situation:

1. **You see duplicate-looking subdecks** (`Tier 1` populated, `Tier 01`
   empty, side by side) or your tier subdecks sort as
   `1, 10, 2, 3, ...` instead of numerically.
   -> Run `migrate_deck_names.py`.

2. **Importing a new `.apkg` creates DUPLICATE notes** (same sentence
   appears twice), or your review history disappeared after import.
   -> Run `migrate_guids.py`. Read `REPORT-DECK-MIGRATION.md` for the
   full postmortem on this class of bug.

3. **Anki shows orphan tier subdecks** with weird old names (e.g. an
   old `Tier 9 - AI & Documentation` that doesn't match current
   `deck.toml`).
   -> Run `migrate_deck_names.py --delete-orphans` (it refuses if any
   orphan has reviews; resolve those manually first).

4. **None of the above** but you want a fresh release's audio / new
   sentences.
   -> No migration script needed. Just `File -> Import` the latest
   `.apkg`. Anki updates in place via stable GUIDs.

Steps 1, 2, 3 can all happen in sequence on the same collection if
needed. Run `migrate_guids.py` first, then `migrate_deck_names.py`,
then re-import the apkg.

---

## Shared prerequisites

- **Anki 2.1.50+** on desktop. The scripts use the modern SQL schema
  (`notetypes` table, `graves` tombstones, etc.).
- **`zstd` CLI** installed if your collection is in the newer
  `collection.anki21b` format. On macOS: `brew install zstd`. On
  Debian/Ubuntu: `sudo apt install zstd`.
- This **repo cloned**, with `uv` installed (see project README).
- **Anki closed**. Both scripts refuse if the DB is locked.

## Find your collection path

Default Anki collection lives at:

- **Linux**: `~/.local/share/Anki2/User 1/collection.anki2`
- **macOS**: `~/Library/Application Support/Anki2/User 1/collection.anki2`
- **Windows**: `%APPDATA%\Anki2\User 1\collection.anki2`

If you renamed your Anki profile, replace `User 1` with the profile
name shown in Anki's `File -> Switch Profile` dialog.

---

## Part 1: Subdeck rename + orphan cleanup (`migrate_deck_names.py`)

### What it does

1. Reads `decks/<slug>/deck.toml` for the NEW tier names.
2. Derives OLD names by undoing the zero-pad (`Tier 0N` -> `Tier N`).
3. `UPDATE decks SET name = ?, mtime_secs = ?, usn = -1` for each match.
4. Bumps `col.mod`.
5. Verifies each rename by `SELECT`ing the row back.
6. Detects orphan subdecks (under the parent but not in the current
   `deck.toml`). Reports by default; with `--delete-orphans`, removes
   them (cards, dependent-only notes, revlog, deck row) and writes
   `graves` tombstones.

Anki stores subdeck hierarchy as a single text column joined by ASCII
Unit Separator `U+001F`, NOT `::`. The double colon you see in Anki's
UI is a render convention. This script matches against `\x1f`.

### What it does NOT do

- Does not touch `cards.did` (deck ID stays the same; review history
  is preserved).
- Does not touch other decks (Minihongo, JLPT, Yomitan, etc.).
- Does not import new sentences or audio.
- Does not modify notes shared with other decks (when deleting
  orphans, only cards in the orphan deck are removed; the note
  survives if it has cards elsewhere).

### Procedure

1. **Close Anki.**

2. **Dry run** (always; never writes):

   ```bash
   uv run python scripts/migrate_deck_names.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --deck it-vocab --dry-run
   ```

   Expected output:

   ```
   Target renames (from deck.toml):
     'Japanese IT Vocabulary::Tier 1 - Foundational'
       -> 'Japanese IT Vocabulary::Tier 01 - Foundational'
     ... (9 lines for tiers 1-9; Tier 10 unchanged)
   Total decks scanned:  N
   Planned renames:      9
   Conflicts (skipped):  0
   Already correct:      0
   Orphans detected:     0..1
   Untouched (other):    ...
   ```

   If `Planned renames: 0`, see Troubleshooting before continuing.

3. **Real run for `it-vocab`** (drop `--dry-run`):

   ```bash
   uv run python scripts/migrate_deck_names.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --deck it-vocab
   ```

   Watch for:
   - `Backup created: collection.anki2.bak-<timestamp>`
   - `Verified after write: 9/9` (must match `Planned renames`).

4. **Real run for `it-kundoku`** (3 planned renames):

   ```bash
   uv run python scripts/migrate_deck_names.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --deck it-kundoku
   ```

5. **Optional: clean up orphan subdecks.** If a previous `deck.toml`
   revision had different tier names (e.g. `Tier 9 - AI & Documentation`
   was split into the current `Tier 09 - AI & Agents` + `Tier 10 -
   Documentation & Engineering Culture`), your collection may still
   hold the old subdeck as a dangling row.

   The rename run reports these as `Orphans detected`. Decide:

   - **Skip** if those decks have content you want to keep, OR if
     they have reviews you don't want to lose.
   - **Delete** with `--delete-orphans`:

     ```bash
     uv run python scripts/migrate_deck_names.py \
       "$HOME/.local/share/Anki2/User 1/collection.anki2" \
       --deck it-vocab --delete-orphans
     ```

     This removes the orphan deck, its cards, dependent-only notes,
     and any revlog rows. Writes `graves` tombstones so AnkiWeb sync
     propagates the deletion. **Refuses** if any orphan has
     `reviews > 0`; resolve those manually first
     (`Browse -> select -> Change Deck`).

6. **Open Anki and verify.** The Decks pane should now show:

   ```
   Japanese IT Vocabulary
     Tier 01 - Foundational
     Tier 02 - Basic Development
     ...
     Tier 10 - Documentation & Engineering Culture
   IT Kundoku
     Tier 01 - Grammar
     ...
   ```

   Click any subdeck. Card counts and review queues should match
   pre-migration exactly.

7. **(Optional) Reimport latest `.apkg`** to pick up new sentences /
   audio. Build first if needed:

   ```bash
   uv run python scripts/create_deck.py --deck it-vocab --combined
   ```

   Then in Anki: `File -> Import -> it-vocab-complete.apkg`. Anki
   matches by GUID so review history is preserved. New cards land in
   the renamed subdecks.

8. **(If you sync) Force-upload to AnkiWeb.** Direct DB edits do bump
   `usn` and `mtime_secs`, but the safest way to guarantee AnkiWeb
   accepts the rename instead of overwriting it on the next sync:

   `Preferences -> Syncing -> On next sync, force changes in one
   direction` -> select **Upload**. Then click `Sync`.

9. **On other devices** (phone, second desktop): `Sync` then
   `Download from AnkiWeb` on the conflict prompt. The clean state
   propagates down.

### CLI reference

```
usage: migrate_deck_names.py COLLECTION --deck SLUG
                             [--dry-run] [--no-backup] [--delete-orphans]

  COLLECTION         Path to collection.anki2 or collection.anki21b
  --deck SLUG        Deck slug from decks/<slug>/deck.toml (e.g. it-vocab)
  --dry-run          Report what would change without writing
  --no-backup        Skip auto-backup (only if you have your own)
  --delete-orphans   Also delete orphan subdecks (refuses on reviews > 0)
```

Exit codes:
- `0`: success (or dry-run; or nothing to do).
- `1`: bad arg, missing collection, locked DB, backup failed.
- `2`: zero decks matched (warning: probably wrong path or parent
  deck renamed).

---

## Part 2: GUID + model-id migration (`migrate_guids.py`)

### What it does

Before commit `30ddf37`, `create_deck.py` used random GUIDs per build.
Reimports never matched existing notes -> every release created
duplicates. Users who installed multiple releases ended up with
multiple copies of each sentence, random GUIDs, and review progress
scattered across them.

`create_deck.py` now derives GUIDs from `Sentence` text
(`genanki.guid_for(Sentence)`), so future builds update in place.
But existing collections still carry the old random GUIDs.

`migrate_guids.py`:

1. Reads notes filtered by `--source-mid` (your current notetype id).
2. Groups notes by `genanki.guid_for(Sentence)` (the stable GUID).
3. For each group:
   - **1 note, wrong GUID**: rewrite to stable.
   - **N duplicate notes**: pick winner by review activity
     (most reps / oldest nid as tiebreak), rewrite winner's GUID,
     delete losers' notes/cards/revlog.
4. With `--model-id`: retargets the notetype id (and `notes.mid`,
   `fields.ntid`, `templates.ntid`) to match the current
   `deck.toml`'s `model_id`. Required when `--force-style` builds
   created orphan notetypes in your collection.
5. `VACUUM` the database.

Also handles the same zstd `anki21b` decompression, the `unicase`
collation registration, and the safety backup as `migrate_deck_names.py`.

### What it does NOT do

- Does not touch `cards.did` (the deck a card belongs to is unchanged).
- Does not delete review history of the winning note.
- Does not modify decks not owned by the targeted `--source-mid`.

### When to run

If any of these are true:

- Importing the latest `.apkg` creates duplicate notes (same sentence
  appears twice in Browse).
- You see two parallel copies of the same deck after import.
- Tools -> Check Database complains about orphan notetypes after a
  `--force-style` build.
- Your review progress vanished after an import, with a "new" deck
  appearing.

If none of these apply and your normal `File -> Import` works fine,
you don't need this script.

### Procedure

The full procedure with diagnostics lives in
`REPORT-DECK-MIGRATION.md` (postmortem of the 2026-04-21 recovery).
The quick reference:

1. **Close Anki.**

2. **Backup explicitly** (the script also does this, but a manual
   copy makes recovery foolproof):

   ```bash
   cp "$HOME/.local/share/Anki2/User 1/collection.anki2" \
      "$HOME/.local/share/Anki2/User 1/collection.anki2.bak-pre-guids-$(date +%Y%m%d-%H%M%S)"
   ```

3. **Find your current model id** for the deck:

   ```bash
   sqlite3 "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     "SELECT mid, COUNT(*) FROM notes WHERE mid IN (
        SELECT id FROM notetypes WHERE name LIKE '%Japanese IT%'
      ) GROUP BY mid;"
   ```

   Pick the row with the most notes; that's your `<USER_MID>`.

4. **Dry run** to see what would change:

   ```bash
   uv run python scripts/migrate_guids.py \
     "$HOME/.local/share/Anki2/User 1/collection.anki2" \
     --in-place \
     --source-mid <USER_MID> \
     --model-id 1607392323 \
     --dry-run
   ```

   Look at `Duplicate groups`, `GUIDs to rewrite`, `Notes to delete`.

5. **Real run** (drop `--dry-run`).

6. **Open Anki -> Tools -> Check Database.** Expect "rebuilt and
   optimized" or similar success message.

7. **Import the latest build**: `File -> Import -> it-vocab-complete.apkg`.
   Dialog should say "N notes updated, ~M added", NOT "N duplicates".

8. **Force-upload to AnkiWeb** if you sync.

### CLI reference

```
usage: migrate_guids.py INPUT [-o OUTPUT.apkg]
                        [--dry-run] [--in-place]
                        [--source-mid MID] [--model-id MID]

  INPUT          .apkg / .colpkg / collection.anki2 (with --in-place)
  -o OUTPUT      Output .apkg path (default: INPUT-migrated.apkg)
  --dry-run      Report what would change without writing
  --in-place     Edit a raw collection.anki2 directly (no zip/repack)
  --source-mid   Only process notes with this model id (required when
                 the db has other decks)
  --model-id     Retarget the notetype id to this value, so a follow-up
                 import of a deck with the same model_id updates in
                 place instead of creating new cards
```

---

## Troubleshooting (both scripts)

### "Zero decks matched" / "Error: database is locked" / "Backup failed"

Same fixes for both scripts. Anki must be closed (no stray
`AnkiProgramFiles` process). Wrong collection path is the most
common cause; check `File -> Switch Profile` for your actual profile
name. Disk full / read-only causes backup failure.

### "Conflicts (NOT renamed)" (migrate_deck_names)

The script found a target name already on a different deck row. To
resolve: open Anki, delete the empty stub subdeck (verify 0 cards
first), then re-run the migration script.

### Database needs check on next Anki open

Anki detected a file change outside its own session. Run
`Tools -> Check Database`. Expect success. Then continue with the
force-upload step.

### AnkiWeb sync conflict prompt

If you skipped the force-upload step and synced normally, AnkiWeb may
say the local state diverged. Pick `Upload to AnkiWeb` on the conflict
dialog. **Never** pick `Download from AnkiWeb` here, or your migration
will be reverted.

### Roll back to a backup

Both scripts create timestamped backups in the same directory as the
collection. To roll back:

```bash
# Close Anki first.
cp "$HOME/.local/share/Anki2/User 1/collection.anki2.bak-<timestamp>" \
   "$HOME/.local/share/Anki2/User 1/collection.anki2"
```

Reopen Anki. You're back to pre-migration state.

---

## Why these scripts exist

Two things `.apkg` import cannot do on its own:

1. **Rename existing decks.** Anki matches decks by full name path on
   import. If the apkg's deck name differs from yours, you get a new
   parallel deck, not a rename.

2. **Reconcile GUIDs and notetypes from older builds.** If your
   existing notes use random GUIDs (pre-`30ddf37`) or a different
   notetype id (from `--force-style`), Anki creates fresh notes /
   notetypes instead of updating yours, scattering review progress.

The migration scripts close those gaps by editing
`collection.anki2` directly. The schema knowledge required (zstd
`anki21b`, `unicase` collation, `graves` tombstones, parent-child
separator `\x1f`, the difference between `decks.name` and `col.decks`
JSON, the `notetypes` / `fields` / `templates` triplet) was learned
the hard way and is captured in `REPORT-DECK-MIGRATION.md`.

## See also

- `REPORT-DECK-MIGRATION.md` for the full 2026-04-21 GUID recovery
  postmortem (zstd anki21b, unicase collation, orphan note types,
  AnkiWeb sync divergence pitfalls).
- `scripts/migrate_deck_names.py --help` and
  `scripts/migrate_guids.py --help` for CLI reference.
- `CLAUDE.md` "Full Rebuild Example" for the audio + apkg build flow.
