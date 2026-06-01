# Subdeck Name Migration: How To Run

Step-by-step guide for running `scripts/migrate_deck_names.py` to rename
the tier subdecks in your Anki collection from `Tier 1`-style names to
zero-padded `Tier 01`-style names so they sort numerically.

This script edits your `collection.anki2` SQLite database directly. It
does not import an `.apkg` and does not touch your review history.

## When to run this

Run once, after pulling a version of this repo where the deck author has
zero-padded the tier names in `deck.toml`. You'll know to run it if:

- Your subdecks currently appear as `Tier 1, Tier 10, Tier 2, Tier 3, ...`
  (alphabetic order) and you want them in numeric order.
- You already imported the latest `.apkg` and now see duplicate-looking
  subdecks: a populated `Tier 1` next to an empty `Tier 01`.

If you don't already have the affected deck in Anki, skip this script.
Importing the latest `.apkg` into a fresh Anki profile produces the
correct names directly.

## What it does

1. Reads the deck's `decks/<slug>/deck.toml` to get the NEW tier names.
2. Derives the OLD names by undoing the zero-pad (`Tier 0N` to `Tier N`).
3. Updates `decks.name` for each matching row.
4. Bumps `decks.mtime_secs` and sets `decks.usn = -1` so AnkiWeb sync
   detects the change.
5. Bumps `col.mod` so Anki sees the collection as modified.
6. Verifies each rename by `SELECT`ing the row back.
7. Detects orphan subdecks (under the same parent but not in current
   `deck.toml`). Reports them by default. With `--delete-orphans`,
   also removes them (cards, dependent-only notes, revlog, deck row)
   with `graves` tombstones for sync. Refuses if any orphan has
   `reviews > 0`.

Before any write, it copies your collection to a `.bak-<timestamp>`
sibling and refuses to proceed if the backup fails.

## What it does NOT do

- Does not touch `cards`, `notes`, `revlog`, or media files.
- Does not change deck IDs. `cards.did` is unaffected, so all your
  review history (intervals, lapses, due dates, ease) is preserved.
- Does not import new sentences or audio. Run `create_deck.py` and
  `File -> Import` separately if you also want fresh content.
- Does not modify decks not listed in `decks/<slug>/deck.toml`. Your
  other Anki decks (Minihongo, JLPT, Yomitan, etc.) are untouched.

## Prerequisites

- **Anki 2.1.50+** on desktop. The script uses the modern schema.
- **`zstd` CLI** if your collection is in the newer `anki21b` format.
  On macOS: `brew install zstd`. On Debian/Ubuntu: `sudo apt install zstd`.
- This **repo cloned**, with `uv` installed (see project README).
- **Anki must be closed**. The script will refuse if the DB is locked.

## Find your collection path

The default Anki collection lives at:

- **Linux**: `~/.local/share/Anki2/User 1/collection.anki2`
- **macOS**: `~/Library/Application Support/Anki2/User 1/collection.anki2`
- **Windows**: `%APPDATA%\Anki2\User 1\collection.anki2`

If you renamed your Anki profile, replace `User 1` with the profile name
you see in Anki's `File -> Switch Profile` dialog.

## Procedure

### 1. Close Anki

Quit Anki entirely. On macOS, also check Activity Monitor to confirm no
`anki` process is still running.

### 2. Dry run

The dry run never writes. It reports what would change. Always run this
first.

```bash
uv run python scripts/migrate_deck_names.py \
  "$HOME/.local/share/Anki2/User 1/collection.anki2" \
  --deck it-vocab --dry-run
```

Expected output (truncated):

```
Target renames (from deck.toml):
  'Japanese IT Vocabulary::Tier 1 - Foundational'
    -> 'Japanese IT Vocabulary::Tier 01 - Foundational'
  ... (9 lines for tiers 1-9; Tier 10 unchanged)

Total decks scanned:  N
Planned renames:      9
Conflicts (skipped):  0
Already correct:      0
Untouched (other):    ...
```

If `Planned renames: 0`, see Troubleshooting below before continuing.

### 3. Real run for `it-vocab`

```bash
uv run python scripts/migrate_deck_names.py \
  "$HOME/.local/share/Anki2/User 1/collection.anki2" \
  --deck it-vocab
```

You should see:

- `Backup created: collection.anki2.bak-<timestamp>`
- The same planned renames as the dry run.
- `Verified after write: 9/9` (must match the planned count).

### 4. Real run for `it-kundoku`

```bash
uv run python scripts/migrate_deck_names.py \
  "$HOME/.local/share/Anki2/User 1/collection.anki2" \
  --deck it-kundoku
```

Expect 3 planned renames for the `IT Kundoku` decks.

### 4a. Optional: clean up orphan subdecks

If a previous `deck.toml` revision had different tier names (e.g.
`Tier 9 - AI & Documentation` was split into the current
`Tier 09 - AI & Agents` plus `Tier 10 - Documentation & Engineering Culture`),
your collection may still hold the old subdeck as a dangling row with
its own GUIDs.

The rename run reports these as `Orphans detected`. Decide:

- **Skip** if those decks contain content you still want as-is, OR if
  they have reviews you don't want to lose.
- **Delete** with `--delete-orphans`:

  ```bash
  uv run python scripts/migrate_deck_names.py \
    "$HOME/.local/share/Anki2/User 1/collection.anki2" \
    --deck it-vocab --delete-orphans
  ```

  This removes the orphan deck, its cards, dependent-only notes
  (notes shared with other decks are preserved), and any revlog rows.
  Writes `graves` tombstones so AnkiWeb sync propagates the deletion.

  The script **refuses** if any orphan has `reviews > 0`. Move those
  cards in Anki UI first (`Browse -> select -> Change Deck`), then
  delete the empty stub or re-run with `--delete-orphans`.

### 5. Open Anki and verify

The Decks pane should now show:

```
Japanese IT Vocabulary
  Tier 01 - Foundational
  Tier 02 - Basic Development
  ...
  Tier 09 - AI & Agents
  Tier 10 - Documentation & Engineering Culture
IT Kundoku
  Tier 01 - Grammar
  Tier 02 - Actions
  Tier 03 - Nouns, Descriptors & Patterns
```

Click any subdeck. The card count and review queue should be exactly
what they were before the migration.

### 6. Reimport latest `.apkg` (optional but recommended)

If the repo also has new sentences or audio for this version, build and
import:

```bash
uv run python scripts/create_deck.py --deck it-vocab --combined
```

In Anki: `File -> Import -> it-vocab-complete.apkg`. Anki matches notes
by GUID (derived from the Sentence field), so existing review history is
preserved. New cards land in the renamed subdecks.

### 7. Force-upload to AnkiWeb (if you sync)

Direct DB edits do bump `usn` and `mtime_secs`, but the safest way to
guarantee AnkiWeb takes the rename rather than overwriting it with the
old name on next sync is a forced one-way upload:

`Preferences -> Syncing -> On next sync, force changes in one direction`
-> select **Upload**. Then click `Sync`.

### 8. Pull on other devices

On your phone (or other desktops), `Sync` and pick `Download from AnkiWeb`
on the conflict prompt. The clean renamed state propagates down.

## Troubleshooting

### "Zero decks matched"

The script exits with code 2 and prints common causes. Check:

- **Wrong collection path**. If you have multiple Anki profiles, open
  Anki, look at `File -> Switch Profile`, and use the matching `User N`
  in the path arg.
- **Parent deck renamed**. If you renamed `Japanese IT Vocabulary` or
  `IT Kundoku` in Anki (the parent of all the tier subdecks), the
  script can't find the subdecks. Either rename the parent back in
  Anki (right-click -> Rename), or edit `decks/<slug>/deck.toml`'s
  `name = "..."` field to match what Anki shows.

### "Error: database is locked"

Anki (or another process) has the DB open. Close Anki fully. On macOS,
check Activity Monitor for any stray `anki` process.

### "Conflicts (NOT renamed)"

The script found that the target name already exists on a different
deck row, typically an empty `Tier 0N` stub created by a previous
`.apkg` import. The script does not guess merge intent. To resolve:

1. Open Anki.
2. For each conflict listed, right-click the empty `Tier 0N` subdeck in
   the Decks pane. Verify it has 0 cards (look at the card count
   column). Click `Delete`.
3. Close Anki.
4. Re-run the migration script.

If the "empty" stub actually has cards, you imported in a way that
split your reviews across two decks. Decide which one to keep, move
cards manually (`Browse -> select cards -> Change Deck`), then delete
the empty one, then re-run.

### "Backup failed"

The script refuses to proceed without a safety backup. Common causes:

- Disk full. Free up space, retry.
- Read-only filesystem or permission denied. Run the script as the user
  who owns the Anki profile directory.
- A backup with the same exact microsecond timestamp already exists.
  Wait 1 second and retry.

If you have your own backup already (e.g. `Time Machine`, `restic`,
manual `cp`), you can bypass with `--no-backup`:

```bash
uv run python scripts/migrate_deck_names.py \
  "$HOME/.local/share/Anki2/User 1/collection.anki2" \
  --deck it-vocab --no-backup
```

### After a successful run, Anki on open says "Database needs check"

Anki noticed the file was modified outside its own session. Run
`Tools -> Check Database`. Expect "rebuilt and optimized" (or similar
success message). Then continue with step 7 above.

### AnkiWeb sync conflict prompt

If you skipped the force-upload (step 7) and synced normally, AnkiWeb
may complain that the local state diverged. Pick `Upload to AnkiWeb`
on the conflict dialog. Never pick `Download from AnkiWeb` here, or
the rename will be reverted.

### Roll back to the backup

If anything goes wrong and you want the original state back:

```bash
# Close Anki first.
cp "$HOME/.local/share/Anki2/User 1/collection.anki2.bak-<timestamp>" \
   "$HOME/.local/share/Anki2/User 1/collection.anki2"
```

Reopen Anki. You're back to pre-migration state.

## Why this script exists

Anki stores deck hierarchy as a single text column in the `decks` table.
Parent and child names are joined with the ASCII Unit Separator U+001F,
not `::`. The double colon you see in Anki's UI is a render convention.
This was the cause of an earlier bug in this script that silently
matched zero rows; it now matches against `\x1f`.

When the deck author renames `Tier 1` to `Tier 01` in `deck.toml` and
ships a new `.apkg`, Anki on import does not auto-rename your existing
`Tier 1`. It sees `Tier 01` in the apkg, finds no matching deck, and
creates a new empty subdeck. Your cards stay in the original `Tier 1`.

This script bridges the gap by renaming your existing `decks.name` rows
directly. After running it, your next `.apkg` import maps to the now
correctly-named subdeck and your review history is preserved.

## See also

- `REPORT-DECK-MIGRATION.md` for broader migration topics (GUID
  stability, model ID retargeting, the original 2026-04-21 recovery
  postmortem).
- `scripts/migrate_deck_names.py --help` for the full CLI reference.
- `CLAUDE.md` "Full Rebuild Example" for the audio + apkg build flow.
