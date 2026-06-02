# TTS Audio Debugging Guide

How to find, classify, and fix Edge TTS misreadings in this deck's
1176-sentence Japanese audio set. This is the methodology document;
the inline bug taxonomy and per-class fix instructions live in
`scripts/pronunciation.py`'s module docstring (HOW TO FIX A TTS BUG).
Cross-reference both when working on audio.

## Contents

- [When you should read this](#when-you-should-read-this)
- [Quick start: I have a bug right now](#quick-start-i-have-a-bug-right-now)
- [The detection pipeline](#the-detection-pipeline)
- [Running an audit](#running-an-audit)
- [Bug taxonomy](#bug-taxonomy) (Classes A-E, with examples)
- [The fix workflow](#the-fix-workflow) (Steps 1-6, end to end)
- [False positives to filter](#false-positives-to-filter)
- [Tools reference](#tools-reference)
- [Concrete fixes shipped in v4.3](#concrete-fixes-shipped-in-v43)
- [Lessons learned](#lessons-learned)

## When you should read this

- You hear a card whose audio sounds wrong (missing syllable,
  weird prosody, kanji read with the wrong on/kun).
- You're prepping a release and want a pre-flight audit.
- You added new sentences and want to make sure no new patterns
  break in TTS.
- A user reports a specific audio bug and you need to verify whether
  it's TTS-side (fixable here) or pure ASR-side (Whisper noise we
  can't address).

Skip if you just want to regenerate audio that's already known to
be wrong; the CLAUDE.md "Full Rebuild Example" covers that.

---

## Quick start: I have a bug right now

You hear a specific card's audio sound wrong. The fastest path
from "this sounds broken" to "fixed in your local Anki":

1. **Identify the row.** Note the deck + tier + row index.
2. **See what TTS actually received:**
   ```bash
   uv run python scripts/test_tts.py --tier N --row R
   ```
   Print is the exact string Edge TTS got. If that looks wrong,
   the bug is upstream (CSV or preprocessing); see
   [Step 1: Diagnose](#step-1-diagnose). If it looks right but
   the audio sounds wrong, Edge TTS is the culprit.
3. **Classify** against [Bug taxonomy](#bug-taxonomy) (Classes A-E).
4. **Apply the matching fix** to `scripts/pronunciation.py` per
   [Step 3](#step-3-apply-fix).
5. **Regenerate only the affected row(s)** ([Step 4](#step-4-regenerate-only-affected-rows)),
   verify the new audio ([Step 5](#step-5-verify)).
6. **Re-import the apkg into Anki.** This is the step that
   actually puts the fix in front of you. See
   [Step 6](#step-6-re-import-the-apkg-into-anki).
   **Copying mp3s into `collection.media/` directly does NOT work** -
   Anki uses content-addressed filenames and your plain-named drops
   are invisible to existing cards. Skipping this step is the
   single most common reason "my fix didn't take".

If you're not sure the bug is real (e.g. you only have one
listener's report), run the audit on a sample first:

```bash
uv run python scripts/get_transcript.py \
  --deck it-vocab --all-tiers --sample 200 --seed 42 \
  --quiet --report audio-audit.csv
```

See [Running an audit](#running-an-audit) for details.

---

## The detection pipeline

Edge TTS is a closed neural model. The only way to know what it
actually produced for a given input is to listen, or to run the
audio through a different model (ASR) and compare. We do the
latter, automatically, across many sentences.

The pipeline lives in `scripts/get_transcript.py` and is built on
five ideas, each justified below.

### 1. ASR round-trip with whisper.cpp

For each row: feed the on-disk mp3 to `whisper.cpp` (Japanese small
model `ggml-small-q5_1.bin`), get a transcript, compare to the
expected text the TTS pipeline was supposed to read.

Whisper's job here isn't to be perfect. It's to be a second-source
listener. Mismatches between expected and transcript are candidate
bugs.

`whisper.cpp` binary path is hard-coded to
`~/Code/skool-live-transcript/vendor/whisper.cpp/build/bin/whisper-cli`
because it's an existing build on this machine. Different setup:
update the constants at the top of `scripts/get_transcript.py`.

### 2. Kana normalization via fugashi

Whisper output is mixed kanji + kana. Same with the expected text
from `preprocess_for_tts`. Direct string compare produces false
positives whenever Whisper picks different kanji than the expected
text. For example, the audio voices `ぎょう` and Whisper writes
`業` while the expected text has `行`. Different kanji, same
pronunciation, but a naive string compare flags it as a mismatch.

Fix: fold both to katakana via `fugashi` before comparing. fugashi
uses UniDic, gets each morpheme's `kana` feature, falls back to
`jaconv.hira2kata(surface)` for tokens with no kana reading.
Then `kana_only()` strips everything not in the katakana Unicode
block, removing punctuation and ASCII leftovers.

Implementation in `get_transcript.py`:

```python
def to_kana(text):
    parts = []
    for word in tagger(text):
        kana = getattr(word.feature, "kana", None)
        parts.append(kana if (kana and kana != "*")
                     else jaconv.hira2kata(word.surface))
    return "".join(parts)

def kana_only(text):
    return KATAKANA_RE.sub("", text)  # strips non-katakana
```

### 3. Latin-acronym normalization on the transcript

Whisper transcribes Japanese audio of "エーピーアイ" as the literal
ASCII string `API`. Same for `JSON`, `SQS`, `OAuth`, etc. Our
expected text already went through `convert_english_terms()` which
maps `API` -> `エーピーアイ` per `ACRONYM_MAP`. Without the same
treatment on the transcript side, the kana comparison sees `API`,
strips it via `kana_only`, and reports the transcript as 6-9 chars
shorter than expected: a fake "elision".

Fix: apply the same `convert_english_terms` (plus `%` and version
substitutions) to the Whisper transcript before to_kana runs. In
`get_transcript.py:check_row`:

```python
transcript_normalized = transcript.replace("%", "パーセント")
transcript_normalized = re.sub(
    r"(?<![A-Za-z])v(\d)", r"バージョン\1", transcript_normalized
)
transcript_normalized = convert_english_terms(transcript_normalized)
```

This alone dropped the 200-sample audit's LIKELY_ELISION count
from 33 to 9 in this session, with the remaining 9 being actual
TTS bugs.

### 4. Edit distance + length delta classifier

Just OK/MISMATCH was too coarse. We need to know how big the gap
is (high edit distance = lots of disagreement = either a major TTS
bug or major ASR mishearing) AND in which direction (transcript
shorter than expected = characters dropped, which is the elision
signature).

```python
def edit_distance(a, b): ...  # plain Levenshtein, two-row DP
def classify(distance, length_delta):
    if distance == 0:        return "OK"
    if length_delta >= 2:    return "LIKELY_ELISION"
    return                          "MISMATCH"
```

`LIKELY_ELISION` is the high-value bucket: characters that should
be in the audio aren't being transcribed. Half of those turn out to
be real TTS bugs, half are ASR errors. Triaging both is much faster
than triaging undifferentiated MISMATCH noise.

### 5. CSV report with incremental flush

A full audit at 38s per file across 1176 files would take 12 hours.
Even a 200-sample run takes 2-3 hours. The first version of the
script wrote the CSV only at the end; if killed midway you lost
everything.

Fix: open the report file at start of run, write a row + `flush()`
per result. Partial results survive Ctrl-C, machine reboot, hook
errors, anything.

```python
def open_report(path):
    f = open(path, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
    writer.writeheader(); f.flush()
    return f, writer
```

---

## Running an audit

### Full-tier audit (one tier)

```bash
uv run python scripts/get_transcript.py --tier 1 --all
```

Outputs per-row OK / LIKELY_ELISION / MISMATCH inline, summary at
the end. ~95 minutes for tier 1 (150 sentences at ~38s each on
4-core CPU).

### Cross-deck audit with sampling (the bread-and-butter mode)

```bash
uv run python scripts/get_transcript.py \
  --deck it-vocab --all-tiers \
  --sample 200 --seed 42 \
  --quiet --report audio-audit.csv
```

Picks 200 random rows across all tiers, with a fixed seed so reruns
are reproducible. Writes a CSV report. `--quiet` suppresses per-row
stdout (a heartbeat line still prints every 10 rows).

Runtime: ~2-3 hours on 4-core CPU.

### Single-row sanity check (for verifying a fix)

```bash
uv run python scripts/get_transcript.py --tier 2 --row 51
```

~40 seconds. Use this to confirm a fix actually worked after
regenerating that row's audio.

### Reading the report CSV

Columns: `tier, row, sentence, expected, transcript, kana_expected,
kana_transcript, edit_distance, length_delta, status`.

To rank by elision-likelihood (most-missing first):

```bash
sort -t, -k9,9 -n -r audio-audit.csv | head -30   # by edit_distance desc
```

Or programmatically:

```python
import csv
with open("audio-audit.csv") as f:
    rows = [r for r in csv.DictReader(f) if r["status"] != "OK"]
for r in rows:
    r["edit_distance"] = int(r["edit_distance"])
    r["length_delta"] = int(r["length_delta"])
rows.sort(key=lambda r: (-r["length_delta"], -r["edit_distance"]))
```

The Japanese `sentence` field contains ASCII commas so naive
`awk -F,` doesn't work; use Python's `csv` module.

---

## Bug taxonomy

The five classes documented in `scripts/pronunciation.py` module
docstring (HOW TO FIX A TTS BUG section). Quick reference here;
that file is the canonical inline source.

### Class A: kanji misreading

**Symptom**: Edge TTS reads a kanji with the wrong on/kun reading.

**Examples found this session**:

| Kanji | Wrong | Right | Notes |
|-------|-------|-------|-------|
| `型`  | がた  | かた  | Edge TTS picks がた in isolation |
| `既存`| そん  | きそん | drops the き mora |
| `文字列`| じれつ| もじれつ | drops the も mora |
| `一意`| イ   | いちい | only voices the first kana |
| `行`  | こう  | ぎょう | Edge picks こう when context needs ぎょう (row/line) |
| `中`  | なか  | ちゅう | Edge picks なか when context needs ちゅう (mid-progress) |
| `閾値`| いきち| しきいち | uncommon 閾 kanji |

**Fix**: add the kanji or compound to `TTS_KANJI_OVERRIDES` in
`pronunciation.py`. The override system fires only on the FULL
captured kanji compound. So `'行' in TTS_KANJI_OVERRIDES` matches
only standalone `行【...】` patterns; multi-kanji compounds like
`銀行` / `移行` / `実行` are captured as their own compound and
stay untouched. Same for `中` (doesn't break `中国` / `集中`).

The CSV `Pronunciation` field provides the correct reading via the
furigana brackets; the override system substitutes the bracketed
reading instead of feeding the kanji to TTS. Do NOT edit the CSV
to remove the kanji.

### Class B: post-particle-は first-mora elision

**Symptom**: the first mora of any word right after particle `は`
is weakened or dropped entirely.

**Examples found this session**:

| Pattern  | What you hear |
|----------|---------------|
| `はすべて` | "wa-bete" (drops す) |
| `はどの`  | "wa-(faint)ono" (weakens ど) |
| `はきそん`| "wa-son" (drops き) |
| `はもじれつ`| "wa-jiretsu" (drops も) |
| `はユーザー`| "wa-zaa" (drops ユー) |
| `にはコグニート`| "ni-wa-uneeto" (drops コグ) |
| `は一意`  | "wa-chii" (drops イチ) |

**Fix**: ALREADY HANDLED by the two-pass regex in
`preprocess_for_tts`. Inserts a comma after `は` when the position
is unambiguously a particle. Two passes because the disambiguation
of "is this `は` a particle or part of a word (はじめ, はず)" varies
with the next char's script:

```python
# Pass A: は + (katakana | kanji) is unambiguously a particle.
text = re.sub(r'は(?=[゠-ヿ一-鿿々])', 'は、', text)

# Pass B: は + hiragana needs the previous char to be a content
# word, to avoid splitting word-internal は like 'はじめ'.
text = re.sub(r'(?<=[一-鿿々゠-ヿ])は(?=[ぁ-ゖ])', 'は、', text)
```

If you find a new post-は case the regex misses (would be rare;
the regex covers all observed patterns plus all reachable ones in
the current corpus), broaden the lookahead / lookbehind classes
rather than adding a narrow string replace.

### Class C: other prosodic glitch (not post-は)

**Symptom**: TTS elides a mora at a position the post-は rule
doesn't cover, AND it's not a kanji-misreading.

**Example found this session**: `テンプレートを使えばドキュメント...`
voiced as "tsukaeba-kyumento" (drops ド). The `えば` -> `ドキュメント`
transition is the trigger; not a particle is involved.

**Fix**: narrow `text.replace()` at the end of `preprocess_for_tts`,
with a comment quoting the symptom:

```python
# Edge TTS elides ド in 使えばドキュメント. Comma-pause workaround.
text = text.replace('えばドキュメント', 'えば、ドキュメント')
```

Keep these narrow. A broad pattern risks regressing other
sentences. Add one targeted line per observed case.

### Class D: English/acronym garble

**Symptom**: an English word in the source comes out wrong in
audio.

**Fix**: add or correct the entry in `ACRONYM_MAP`. Examples:
`SDK -> エスディーケー`, `webhook -> ウェブフック`. If the loanword
is common enough that learners should see it written in katakana
on the card too, prefer writing it as katakana directly in the CSV
Pronunciation field instead of relying on ACRONYM_MAP conversion.

### Class E: digit irregularity (counter words)

**Symptom**: `2日` voiced as "ni-futsuka" instead of "futsuka". The
"2" digit gets read as `ni`, the kanji is independently irregular.

**Fix**: write the kana directly in the CSV (`ふつか`), not as
`2日【ふつか】`. Numbers that have regular Japanese readings
(`100`, `400`, etc.) are fine; only the counter-word irregulars
need this treatment.

---

## The fix workflow

End to end, when you find a candidate bug in the audit CSV:

### Step 1: Diagnose

Read the "TTS input" line that `test_tts.py` prints. That's the
exact string Edge TTS receives.

```bash
uv run python scripts/test_tts.py --tier 2 --row 51
```

Output:
```
Row 51: APIはユーザーデータをJSONで返します。
  TTS input: エーピーアイは、ユーザーデータをジェイソンで返します。
  Saved: test_tier2_051.mp3
```

If the TTS input already looks wrong (missing a mora, wrong kanji
reading), the bug is upstream of TTS: either the CSV's
Pronunciation field is wrong, or the preprocess pipeline mangled
it. Fix there.

If the TTS input looks right but the audio still sounds wrong, the
bug is in Edge TTS itself. Pick the class (above), apply the
matching fix.

### Step 2: Classify

Match the symptom to one of the 5 classes. The bug taxonomy table
above has concrete signatures. If unsure: post-は plus first-mora
drop is Class B; kanji reading is Class A; rare loanword garble is
Class D; everything else is probably Class C (or ASR noise).

### Step 3: Apply fix

Edit `scripts/pronunciation.py`:

- Class A: add to `TTS_KANJI_OVERRIDES` set
- Class B: extend the post-は regex (rare; usually already covered)
- Class C: narrow `text.replace()` near the existing fixes
- Class D: edit `ACRONYM_MAP`
- Class E: edit the CSV's Pronunciation field

### Step 4: Regenerate only affected rows

Don't `--force` regen the entire deck (12 minutes of Edge TTS
calls). Instead, identify the affected rows and delete just those
mp3s, then run `generate_audio.py` without `--force`. It skips
existing files and only generates the deleted ones.

To identify affected rows for a given regex change, scan with old
vs new preprocess outputs:

```python
def preprocess_with_old(text): ...  # mirror current pipeline but
                                    # with the OLD version of the rule
                                    # you're changing
for path in csv_files:
    for n, row in enumerate(rows, 1):
        if preprocess_with_old(row['Pronunciation']) \
           != preprocess_for_tts(row['Pronunciation']):
            affected.append((tier, n))
```

For kanji overrides, the scan is similar but using the OLD
`TTS_KANJI_OVERRIDES` set against the new.

Delete and regen:

```bash
for tier row in $affected; do
    rm "decks/it-vocab/tier${tier}-audio/tier${tier}_${row:03d}.mp3"
done
uv run python scripts/generate_audio.py --deck it-vocab --all
```

`generate_audio.py` iterates every row of every tier but skips
existing files. Only the deleted ones get generated (rate-limited
to ~1.5s each).

### Step 5: Verify

Re-audit the single fixed row:

```bash
uv run python scripts/get_transcript.py --tier 2 --row 51
```

Expect `OK dist=0 delta=+0`. If still flagged: re-listen and decide
if it's ASR-side (irreducible noise) or if your fix is incomplete.

Cross-check that your fix actually changed the audio bytes:

```bash
uv run python scripts/test_tts.py --tier 2 --row 51
sha256sum test_tier2_051.mp3 decks/it-vocab/tier2-audio/tier2_051.mp3
```

If the two hashes match, the fix didn't change the TTS input (or
they were already identical). If they differ, the fix produced
different audio bytes; combined with the audit pass, you've
confirmed the fix.

### Step 6: Re-import the apkg into Anki

**Do not copy files into `~/.local/share/Anki2/User 1/collection.media/`.**
That is a no-op and will silently fail.

Why: on apkg import, Anki content-addresses media filenames to
avoid collisions. The plain `tier1_134.mp3` you packaged with
genanki gets renamed in the media folder to
`tier1_134-<sha1-of-content>.mp3`, and the card's field is
rewritten from `[sound:tier1_134.mp3]` to
`[sound:tier1_134-<sha1>.mp3]`. So when the audio bytes change,
the SHA1 changes, the filename changes, and any plain-named files
you drop in by hand are not referenced by any card. They look
unused. `Tools -> Check Media -> Delete Unused` then moves them
to `media.trash/`, and the card keeps playing the old SHA1-suffixed
file that was there before.

Symptoms of this gotcha:

- You fixed and regenerated the audio, the file on disk sounds
  right when played directly, but Anki still plays the broken
  version.
- After `Check Media -> Delete Unused`, your "fixed" files land
  in `media.trash/` even though their filenames look correct.
- `ls collection.media/ | grep tier1_NNN` shows
  `tier1_NNN-<long hex>.mp3` instead of plain `tier1_NNN.mp3`.

Correct flow after any audio fix:

1. Build the apkgs:
   ```bash
   uv run python scripts/create_deck.py --deck it-vocab --combined --all
   ```
2. In Anki: File -> Import -> select
   `it-vocab-complete.apkg` (or per-tier file).
3. Genanki uses stable GUIDs via `guid_for(Sentence)`, so cards
   are matched and **updated in place** rather than duplicated.
   The new audio bytes land in `collection.media/` under a fresh
   SHA1-suffixed filename, and each card's Audio field is rewritten
   to reference the new filename.
4. After import, optionally run `Tools -> Check Media -> Delete
   Unused` to clean up orphaned old-SHA1 files from prior imports.
   This is safe now because cards no longer reference them.

How to confirm Anki is actually playing the new audio:

```bash
ls "/home/<user>/.local/share/Anki2/User 1/collection.media/" \
    | grep "^tier1_134-"
```

The SHA1 in the filename should be the SHA1 of the file in your
repo's `decks/it-vocab/tier1-audio/tier1_134.mp3`. Compute it
with `sha1sum decks/it-vocab/tier1-audio/tier1_134.mp3` and
compare. If they match, Anki is on the new audio. If they
differ, you have not re-imported since the fix.

---

## False positives to filter

These show up in audit output as MISMATCH or LIKELY_ELISION but
the audio is actually correct. Knowing which classes to ignore
saves hours of triage.

### Latin acronym preserved by Whisper

Whisper transcribes Japanese audio voicing `エーピーアイ` as the
ASCII `API`. The audit pipeline now applies `convert_english_terms`
to the transcript before kana comparison, so these are normalized
away. If you see `エーピーアイ` vs `API` style mismatches, the
script is out of date; the fix is in `get_transcript.py:check_row`.

### Digit-as-Japanese-number

Whisper transcribes `イチイ` (the Japanese reading of `一意`) as
`1位`. The "1" is the digit, "位" is "rank/position", together they
read "ichi-i" exactly like 一意. Our pipeline's `to_kana` doesn't
have rules for converting bare digits to Japanese readings, so
"1位" becomes just "イ" after fugashi tokenization and kana_only
filtering.

The audio is fine. This is an audit-script limitation. Listed in
the v4.3 release notes' "Known limitations" section.

### Homophone kanji

Audio voices `ぎょう`. Whisper writes `業`. fugashi defaults to the
`ゴウ` reading of `業` in isolation. Result: `ギョウ` (expected) vs
`ゴウ` (transcript) edit distance = 1, status = MISMATCH.

The audio voices the right thing. Whisper just picked a different
kanji that happens to share the reading; fugashi's reading
inference for that kanji defaults to the on-yomi (`ゴウ`) rather
than the kun-yomi (`ぎょう`) without context.

Can't fix in the audit pipeline cleanly. Manual listen to confirm
audio is correct; ignore the MISMATCH flag.

### Whisper hallucinations on rare loanwords

`bcrypt` -> "beeclipped". `DDoS` -> "リードス". `RAG` -> "RAZ".
Whisper-small is unfamiliar with these and hallucinates plausible
phonemes. The audio voices the right kana (per `ACRONYM_MAP`); the
transcript is wrong.

Listen to the original `decks/it-vocab/tier${N}-audio/...mp3` to
confirm. If the audio is fine, ignore the flag. If the audio is
also wrong, the bug is in `ACRONYM_MAP` (Class D).

### Length-mark vs explicit-vowel

Audio voices `シキイチ` (s-h-k-i-i-c-h-i with explicit i-i),
Whisper writes `シキーチ` (with a long-mark instead of two i's).
Same pronunciation, different writing. Edit distance = 1.

Not a bug. fugashi's reading vs Whisper's writing preference for
long vowels diverges.

---

## Tools reference

### `scripts/get_transcript.py`

ASR-based audit tool. CLI options that matter:

| Flag | Purpose |
|------|---------|
| `--tier N` | Single tier |
| `--row N[,N...]` | Specific rows in that tier |
| `--all` | All rows in the tier |
| `--all-tiers` | Every tier in the deck |
| `--sample N --seed N` | Random sample across selected tiers |
| `--report PATH` | Incremental CSV output |
| `--quiet` | Suppress per-row stdout (still heartbeats every 10) |
| `--audio FILE` | One-off, just transcribe a file |
| `--download-model [NAME]` | Fetch the whisper.cpp model |

### `scripts/test_tts.py`

Quick TTS test for one or more rows. Writes
`test_tier{N}_{NNN}.mp3` so it doesn't overwrite production audio.
Use after a `pronunciation.py` change to hear the output:

```bash
uv run python scripts/test_tts.py --tier 1 --row 5
uv run python scripts/test_tts.py --tier 1 --row 5,6,10
uv run python scripts/test_tts.py --text "問題【もんだい】を見【み】つけました"
```

Reads the CSV's `Pronunciation` field (matching production), runs
the full `preprocess_for_tts` pipeline, calls Edge TTS, writes the
mp3. Prints the post-preprocess "TTS input:" string so you can see
exactly what TTS received.

### `scripts/pronunciation.py`

The preprocessing pipeline itself. Has a self-test at the bottom:

```bash
uv run python scripts/pronunciation.py
```

Prints a built-in set of test sentences with their original CSV
form and the post-preprocess output. Useful for confirming a regex
change does what you expect across a range of inputs (post-は cases,
acronym conversion, kanji overrides, etc.).

### sha256 hash trick

Edge TTS is deterministic for the same input. To verify a fix
changed the produced audio:

```bash
sha256sum old.mp3 new.mp3
```

Same hash: same audio bytes. Different hash: the change had effect.
Use this to confirm a regex extension actually fires on the rows
you expect, before listening or before running the full audit.

---

## Concrete fixes shipped in v4.3

For history-tracking and to inform future similar work.

### Post-は regex extension

The pre-v4.3 regex matched only `(content) + は + hiragana`. The
v4.3 audit found that `は + katakana` and `は + kanji` cases were
equally affected. The regex became two passes (Pass A open
lookbehind for non-hiragana next-char; Pass B narrow lookbehind for
hiragana). 32 -> 240 sentences benefit from the comma fix.

Location: `scripts/pronunciation.py` near the bottom of
`preprocess_for_tts`. See git commit `29696c0` for the patch.

### Kanji overrides added

`既存`, `文字列`, `一意`, `行`, `中`, `閾値` added to
`TTS_KANJI_OVERRIDES`. `型` was already present from v3.5.

Each override matches the full kanji compound captured by the
furigana regex, so single-kanji entries (`行`, `中`) affect only
standalone `行【...】` / `中【...】` patterns, not multi-kanji
compounds.

See commits `00df0d2`, `29696c0`, `844f2a4`.

### えばドキュメント narrow fix

One sentence (tier 10 row 29) had Edge TTS drop the ド from
ドキュメント after えば. Targeted string replacement next to the
post-は regex.

Commit: `00df0d2`.

---

## Lessons learned

### Audit time is much higher than expected

Planned for "2-5 seconds per file" running whisper.cpp on a small
Japanese model on 4 cores. Actual was ~38 seconds per file. The
small model uses about 2.6 of 4 cores per file; parallelizing
across files would barely help. A full 1176-file audit at this
rate is ~12 hours.

Don't try to do a full sweep without a strong reason. The 200-row
sample (with `--sample 200 --seed 42`) runs in ~2 hours and
surfaces the same bug patterns as a full sweep would.

### Sampling beats completeness at this scale

Bugs cluster around recurring patterns (post-は elision, specific
kanji). A representative sample catches the patterns. Going from
200 to 1176 sentences mostly adds more examples of the same
patterns plus a long tail of one-off ASR errors. Diminishing
returns.

### "Missing first mora" has multiple causes

Symptom "first mora is missing from the audio" can be:

- Class A kanji misreading (Edge TTS drops a mora when reading a
  specific kanji).
- Class B post-は elision (Edge TTS drops the next word's first
  mora after particle は).
- Audit-pipeline artifact (Whisper writes a digit, our pipeline
  strips it).

These can compound. `IDは文字列ではなく数値であるべきです` had
two simultaneous issues: `文字列` kanji misreading dropped `も`
from `もじれつ`, AND post-は elision (after `アイディーは`) was
weakening whatever came next. The kanji override alone didn't
help; needed the regex extension too.

Diagnose both axes when triaging.

### Don't conflate ASR errors with TTS bugs

The first audit before Latin-acronym normalization reported 33
LIKELY_ELISION cases; 13 of the top 15 turned out to be Whisper
writing `API` as Latin while the audio voiced
`エーピーアイ` correctly. Fixing the audit pipeline (apply
`convert_english_terms` to transcript) dropped the count to 9,
all of which were real TTS bugs.

Whenever the audit produces a long list, suspect script bugs
before TTS bugs. Confirm by listening to a few flagged files
manually.

### Edge TTS is deterministic given identical input

Same input string -> same MP3 bytes. Confirmed via sha256
comparison. This means a "did my fix actually do anything"
verification is cheap: hash before vs after.

But: Edge TTS prosody IS context-sensitive within a single
utterance. Same word in different sentences can voice differently
because the neural prosody model sees more surrounding context.
That's why `ドキュメント` in one sentence (after `えば`) drops the
ド but in another sentence (after `を`) voices it cleanly. Both
the input string AND surrounding context drive the audio output.

### Hash-based scanning for what to regen

When extending a regex that affects N sentences, you don't want to
regenerate all 1176 audio files. Identify which rows would produce
different `preprocess_for_tts` output under the new regex, delete
just those mp3s, then run `generate_audio.py` without `--force`.
The script skips existing files and only regenerates the missing
ones.

In this session that meant 121 then 85 then 14 targeted regens
instead of three full 1176-file sweeps; total real time ~10
minutes instead of ~36.

### Document the bug taxonomy inline

The single most useful thing I added (more useful than the audit
tool itself) was the "HOW TO FIX A TTS BUG" section in
`pronunciation.py`'s module docstring. Bug classes A-E with
diagnosis cues + fix instructions. Anyone touching this code in
the future has a decision tree right where they're already
reading.

This file (`docs/tts-audio-debugging.md`) is the long-form
narrative. The inline docstring is the in-context reference.
Both serve different purposes.

### Anki uses content-addressed media filenames

Cost me hours this session. The "obvious" sync workflow (copy
fixed mp3s into `collection.media/`) is silently a no-op because
Anki renames imported media to `<name>-<sha1>.mp3` and rewrites
the card field to match. After audio bytes change, the SHA1
changes, the filename changes, plain-named drops are orphans.

The correct invalidation step is `File -> Import` of the rebuilt
apkg. Anki manages the renaming and field rewriting itself; stable
genanki GUIDs ensure cards update rather than duplicate.

See Step 6 of the fix workflow for the diagnostic and the full
recipe.

---

## See also

- `scripts/pronunciation.py` module docstring: canonical inline
  bug taxonomy + HOW TO FIX A TTS BUG decision tree.
- `scripts/get_transcript.py`: implementation of the audit
  pipeline described above.
- `docs/MIGRATE-DECK-NAMES.md`: separate concern, DB-level Anki
  migrations.
- `docs/REPORT-DECK-MIGRATION.md`: 2026-04-21 GUID recovery
  postmortem; includes Anki schema notes (zstd anki21b, unicase
  collation, model_id retargeting) that are tangentially relevant
  if you're poking at audio via SQL.
