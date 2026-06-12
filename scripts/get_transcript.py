#!/usr/bin/env python3
"""Transcribe audio with whisper.cpp to verify TTS pronunciation accuracy.

Uses the whisper.cpp binary from skool-live-transcript to transcribe audio files
and optionally compare against expected text from tier CSVs.

Detects TTS errors like:
- Dropped syllables (話せますか read as "nasemasu ka" instead of "hanasemasu ka")
- Wrong particle reading (は read as "ha" instead of "wa" after nouns)
- Merged words (ピーアールレビュー run together)

Requirements:
- whisper.cpp built at ~/Code/skool-live-transcript/vendor/whisper.cpp/
- Japanese model: ggml-small-q5_1.bin (download with --download-model)

Usage:
    # Download the Japanese model first
    python scripts/get_transcript.py --download-model

    # Transcribe a single audio file
    python scripts/get_transcript.py --audio tier1-audio/tier1_001.mp3

    # Transcribe and compare against expected pronunciation for a tier row
    python scripts/get_transcript.py --tier 1 --row 5

    # Check all rows in a tier for TTS errors
    python scripts/get_transcript.py --tier 1 --all

    # Use a different language
    python scripts/get_transcript.py --audio file.mp3 --language en
"""

import argparse
import csv
import random
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import fugashi
import jaconv

from pronunciation import preprocess_for_tts, convert_english_terms

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config

_tagger = fugashi.Tagger()
_KATAKANA_RE = re.compile(r"[^゠-ヿ]+")
# Digit readings for surfaces fugashi can't parse (1 -> イチ); paired with
# the kanji-numeral normalization in normalize() this gives both sides an
# identical path (朝1 and 朝イチ both become アサイチ).
_DIGIT_READINGS = str.maketrans({
    '0': 'ゼロ', '1': 'イチ', '2': 'ニ', '3': 'サン', '4': 'ヨン',
    '5': 'ゴ', '6': 'ロク', '7': 'ナナ', '8': 'ハチ', '9': 'キュウ',
})
WHISPER_CLI = Path.home() / "Code/skool-live-transcript/vendor/whisper.cpp/build/bin/whisper-cli"
MODEL_DIR = WHISPER_CLI.parent.parent.parent / "models"
DOWNLOAD_SCRIPT = MODEL_DIR / "download-ggml-model.sh"

# Model per language. Japanese needs multilingual; English can use tiny.
LANG_MODELS = {
    "ja": "ggml-small-q5_1.bin",
    "en": "ggml-tiny.en-q5_1.bin",
}
DEFAULT_MODEL = "ggml-small-q5_1.bin"  # multilingual fallback


def get_model_path(language: str) -> Path:
    model_name = LANG_MODELS.get(language, DEFAULT_MODEL)
    return MODEL_DIR / model_name


def download_model(model_key: str = "small-q5_1"):
    """Download a whisper model using the bundled download script."""
    if not DOWNLOAD_SCRIPT.exists():
        print(f"Error: download script not found at {DOWNLOAD_SCRIPT}")
        sys.exit(1)

    print(f"Downloading ggml-{model_key}.bin ...")
    result = subprocess.run(
        ["bash", str(DOWNLOAD_SCRIPT), model_key],
        cwd=str(MODEL_DIR),
    )
    if result.returncode != 0:
        print("Download failed")
        sys.exit(1)
    print("Done")


def transcribe(audio_path: Path, language: str = "ja") -> str:
    """Transcribe an audio file using whisper.cpp. Returns the transcript text."""
    if not WHISPER_CLI.exists():
        print(f"Error: whisper-cli not found at {WHISPER_CLI}")
        print("Build it: cd ~/Code/skool-live-transcript && npm run setup")
        sys.exit(1)

    model_path = get_model_path(language)
    if not model_path.exists():
        print(f"Error: model not found: {model_path}")
        print("Download it: python scripts/get_transcript.py --download-model")
        sys.exit(1)

    cmd = [
        str(WHISPER_CLI),
        "-m", str(model_path),
        "-l", language,
        "-np",  # suppress everything except transcript
        "-nt",  # no timestamps
        "-f", str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"whisper error: {result.stderr[:200]}")
        return ""

    return result.stdout.strip()


def normalize(text: str) -> str:
    """Normalize Japanese text for fuzzy comparison.

    Strips punctuation, whitespace, and normalizes unicode so small
    transcript differences (spacing, punctuation) don't cause false alarms.
    """
    text = unicodedata.normalize("NFKC", text)
    for ch in "。、！？・「」『』（）(),.!? \t\n":
        text = text.replace(ch, "")
    # Kanji numerals -> ASCII digits so both sides take the same path
    # through to_kana (whisper writes 一点 where the CSV has 1点).
    text = text.translate(str.maketrans("〇一二三四五六七八九", "0123456789"))
    return text


def to_kana(text: str) -> str:
    """Convert mixed Japanese text to pure katakana.

    Uses fugashi+unidic to look up the katakana reading for each
    morpheme. Falls back to converting hiragana -> katakana for
    surfaces fugashi can't read (punctuation, ASCII, numbers etc.).
    Caller should follow with kana_only() to strip the non-katakana
    leftovers before comparing.
    """
    parts: list[str] = []
    for word in _tagger(text):
        kana = getattr(word.feature, "kana", None)
        if kana and kana != "*":
            parts.append(kana)
        else:
            surface = word.surface.translate(_DIGIT_READINGS)
            parts.append(jaconv.hira2kata(surface))
    return "".join(parts)


def kana_only(text: str) -> str:
    """Strip everything but katakana (incl. ー and small kana).

    Used to compare expected vs transcript at the kana level after
    to_kana() normalization. Kanji choice, punctuation, and stray
    ASCII/digits no longer cause false-positive mismatches.
    """
    return _KATAKANA_RE.sub("", text)


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance. Iterative two-row DP."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                curr[j - 1] + 1,
                prev[j] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            ))
        prev = curr
    return prev[-1]


def classify(distance: int, length_delta: int, expected_len: int = 0) -> str:
    """Categorize a comparison result.

    OK              distance == 0
    SHORT_CLIP      expected under 4 kana - whisper has nothing to anchor
                    on; verify by ear instead of trusting the transcript
    LIKELY_ELISION  characters missing in transcript (delta >= 2)
    MISMATCH        any other discrepancy
    """
    if distance == 0:
        return "OK"
    if expected_len and expected_len < 4:
        return "SHORT_CLIP"
    if length_delta >= 2:
        return "LIKELY_ELISION"
    return "MISMATCH"


def check_row(tier: int, row_num: int, sentences: list[dict], audio_dir: Path) -> dict:
    """Transcribe one tier row and compare against expected pronunciation.

    Comparison is at the kana-only level (kanji-choice differences from
    Whisper don't trigger false positives). Returns edit_distance and
    length_delta so callers can rank by likelihood of real bug.
    """
    if row_num < 1 or row_num > len(sentences):
        return {"tier": tier, "row": row_num, "error": f"out of range (1-{len(sentences)})"}

    row = sentences[row_num - 1]
    audio_path = audio_dir / f"tier{tier}_{row_num:03d}.mp3"

    if not audio_path.exists():
        return {"tier": tier, "row": row_num, "error": "audio file missing"}

    expected = preprocess_for_tts(row["Pronunciation"])
    transcript = transcribe(audio_path, "ja")

    # Apply the same English->katakana conversion to the transcript that
    # preprocess_for_tts applies to the expected text. Otherwise Whisper
    # writing 'API' (Latin) where the audio says エーピーアイ would look
    # like a 6-char elision when it's not. Same for %, version strings.
    transcript_normalized = transcript.replace("%", "パーセント")
    transcript_normalized = re.sub(
        r"(?<![A-Za-z])v(\d)", r"バージョン\1", transcript_normalized
    )
    transcript_normalized = convert_english_terms(transcript_normalized)

    kana_expected = kana_only(to_kana(normalize(expected)))
    kana_transcript = kana_only(to_kana(normalize(transcript_normalized)))

    dist = edit_distance(kana_expected, kana_transcript)
    length_delta = len(kana_expected) - len(kana_transcript)
    status = classify(dist, length_delta, len(kana_expected))

    return {
        "tier": tier,
        "row": row_num,
        "sentence": row["Sentence"],
        "expected": expected,
        "transcript": transcript,
        "kana_expected": kana_expected,
        "kana_transcript": kana_transcript,
        "edit_distance": dist,
        "length_delta": length_delta,
        "status": status,
    }


def print_result(r: dict):
    """Print a single row check result."""
    if "error" in r:
        print(f"  Row {r['row']}: ERROR - {r['error']}")
        return

    print(
        f"  Row {r['row']}: {r['status']}  "
        f"dist={r['edit_distance']}  delta={r['length_delta']:+d}"
    )
    if r["status"] != "OK":
        print(f"    Sentence:    {r['sentence']}")
        print(f"    Expected:    {r['expected']}")
        print(f"    Transcript:  {r['transcript']}")
        print(f"    Exp kana:    {r['kana_expected']}")
        print(f"    Trans kana:  {r['kana_transcript']}")


REPORT_FIELDS = [
    "tier", "row", "sentence", "expected", "transcript",
    "kana_expected", "kana_transcript",
    "edit_distance", "length_delta", "status",
]


def open_report(path: Path):
    """Open an incremental CSV writer. Caller must close the file.

    Writing per-row + flushing means we don't lose data if the audit is
    killed midway through a long run. The previous batch-at-end pattern
    would discard 12 hours of work on Ctrl-C.
    """
    f = open(path, "w", encoding="utf-8", newline="")
    writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
    writer.writeheader()
    f.flush()
    return f, writer


def append_row(file_handle, writer, result: dict) -> None:
    """Append one result to the CSV and flush so partial data survives."""
    if "error" in result:
        return
    writer.writerow({k: result.get(k, "") for k in REPORT_FIELDS})
    file_handle.flush()


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with whisper.cpp to verify TTS accuracy"
    )
    parser.add_argument("--deck", type=str, default="it-vocab",
                        help="Deck slug (default: it-vocab)")
    parser.add_argument("--audio", type=Path, help="Audio file to transcribe")
    parser.add_argument("--language", default="ja", help="Language code (default: ja)")
    parser.add_argument("--tier", type=int, help="Tier number")
    parser.add_argument("--row", type=str, help="Row number(s), comma-separated")
    parser.add_argument("--all", action="store_true", help="Check all rows in tier")
    parser.add_argument(
        "--all-tiers", action="store_true",
        help="Audit every tier in the deck. Implies --all. Slow.",
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="Write per-row results to this CSV path (sortable by edit_distance, length_delta).",
    )
    parser.add_argument(
        "--sample", type=int, default=None, metavar="N",
        help="Randomly sample N rows across the selected tiers instead of "
             "checking every row. Use with --all-tiers for a fast spot-check.",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for --sample (default: 42, for reproducibility).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-row stdout (still writes the CSV report).",
    )
    parser.add_argument(
        "--download-model",
        nargs="?",
        const="small-q5_1",
        metavar="MODEL",
        help="Download a whisper model (default: small-q5_1 for Japanese)",
    )

    args = parser.parse_args()

    if args.download_model:
        download_model(args.download_model)
        return

    # Simple transcription mode
    if args.audio:
        if not args.audio.exists():
            print(f"Error: {args.audio} not found")
            sys.exit(1)
        transcript = transcribe(args.audio, args.language)
        print(transcript)
        return

    # Tier comparison mode
    if not args.tier and not args.all_tiers:
        parser.print_help()
        sys.exit(1)

    config = load_deck_config(args.deck)
    tiers = list(config.tier_range()) if args.all_tiers else [args.tier]

    # Preload sentences per tier so sampling is cheap.
    sentences_by_tier: dict[int, list[dict]] = {}
    for tier in tiers:
        csv_path = config.csv_path(tier)
        if not csv_path.exists():
            print(f"Error: {csv_path} not found", file=sys.stderr)
            continue
        with open(csv_path, "r", encoding="utf-8") as f:
            sentences_by_tier[tier] = list(csv.DictReader(f))

    # Build (tier, row) work list.
    work: list[tuple[int, int]] = []
    if args.sample:
        # Flat random sample across all selected tiers (stratified would
        # underweight large tiers and overweight small ones; flat is fine).
        for tier, sentences in sentences_by_tier.items():
            work.extend((tier, r) for r in range(1, len(sentences) + 1))
        rng = random.Random(args.seed)
        if args.sample < len(work):
            work = rng.sample(work, args.sample)
        work.sort()  # process in tier-then-row order for predictable progress
    elif args.all_tiers or args.all:
        for tier, sentences in sentences_by_tier.items():
            work.extend((tier, r) for r in range(1, len(sentences) + 1))
    elif args.row:
        rows = [int(r.strip()) for r in args.row.split(",")]
        for tier in tiers:
            work.extend((tier, r) for r in rows)
    else:
        print("Error: specify --row, --all, --all-tiers, or --sample", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        scope = (
            f"sample of {len(work)}" if args.sample
            else f"{len(work)} row(s)"
        )
        print(f"Auditing {scope} across tiers {sorted(set(t for t, _ in work))}")

    report_file = None
    writer = None
    if args.report:
        report_file, writer = open_report(args.report)

    counts = {"OK": 0, "LIKELY_ELISION": 0, "MISMATCH": 0, "error": 0}

    try:
        for i, (tier, row_num) in enumerate(work, 1):
            sentences = sentences_by_tier[tier]
            audio_dir = config.audio_dir(tier)
            result = check_row(tier, row_num, sentences, audio_dir)
            if "error" in result:
                counts["error"] += 1
            else:
                counts[result["status"]] = counts.get(result["status"], 0) + 1
            if writer:
                append_row(report_file, writer, result)
            if not args.quiet:
                print_result(result)
            elif i % 10 == 0 or i == len(work):
                # Heartbeat in --quiet so the user can see progress.
                print(
                    f"  [{i}/{len(work)}] OK={counts['OK']} "
                    f"ELISION={counts['LIKELY_ELISION']} "
                    f"MISMATCH={counts['MISMATCH']}",
                    flush=True,
                )
    finally:
        if report_file:
            report_file.close()

    print()
    print("Summary:")
    print(f"  OK              {counts['OK']}")
    print(f"  LIKELY_ELISION  {counts['LIKELY_ELISION']}")
    print(f"  MISMATCH        {counts['MISMATCH']}")
    print(f"  errors          {counts['error']}")

    if args.report:
        print(f"\nCSV written: {args.report}")
        print(
            "Sort by edit_distance desc:\n"
            "  sort -t, -k9,9 -n -r " + str(args.report)
        )


if __name__ == "__main__":
    main()
