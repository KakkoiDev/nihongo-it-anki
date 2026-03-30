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
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from pronunciation import preprocess_for_tts

ROOT = Path(__file__).parent.parent
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
    return text


def check_row(tier: int, row_num: int, sentences: list[dict]) -> dict:
    """Transcribe one tier row and compare against expected pronunciation."""
    if row_num < 1 or row_num > len(sentences):
        return {"row": row_num, "error": f"out of range (1-{len(sentences)})"}

    row = sentences[row_num - 1]
    audio_path = ROOT / f"tier{tier}-audio/tier{tier}_{row_num:03d}.mp3"

    if not audio_path.exists():
        return {"row": row_num, "error": "audio file missing"}

    expected = preprocess_for_tts(row["Pronunciation"])
    transcript = transcribe(audio_path, "ja")
    exp_norm = normalize(expected)
    trans_norm = normalize(transcript)
    match = exp_norm == trans_norm

    return {
        "row": row_num,
        "sentence": row["Sentence"],
        "expected": expected,
        "transcript": transcript,
        "match": match,
    }


def print_result(r: dict):
    """Print a single row check result."""
    if "error" in r:
        print(f"  Row {r['row']}: ERROR - {r['error']}")
        return

    status = "OK" if r["match"] else "MISMATCH"
    print(f"  Row {r['row']}: {status}")
    print(f"    Sentence:   {r['sentence']}")
    print(f"    Expected:   {r['expected']}")
    print(f"    Transcript: {r['transcript']}")
    if not r["match"]:
        print(f"    Exp norm:   {normalize(r['expected'])}")
        print(f"    Trans norm: {normalize(r['transcript'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with whisper.cpp to verify TTS accuracy"
    )
    parser.add_argument("--audio", type=Path, help="Audio file to transcribe")
    parser.add_argument("--language", default="ja", help="Language code (default: ja)")
    parser.add_argument("--tier", type=int, choices=range(1, 9), help="Tier number")
    parser.add_argument("--row", type=str, help="Row number(s), comma-separated")
    parser.add_argument("--all", action="store_true", help="Check all rows in tier")
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
    if not args.tier:
        parser.print_help()
        sys.exit(1)

    csv_path = ROOT / f"tier{args.tier}-vocabulary.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        sentences = list(csv.DictReader(f))

    if args.all:
        rows = range(1, len(sentences) + 1)
    elif args.row:
        rows = [int(r.strip()) for r in args.row.split(",")]
    else:
        print("Error: specify --row or --all with --tier")
        sys.exit(1)

    mismatches = []
    total = len(list(rows))
    rows = range(1, len(sentences) + 1) if args.all else [int(r.strip()) for r in args.row.split(",")]

    print(f"Tier {args.tier}: checking {len(rows)} row(s)\n")

    for row_num in rows:
        result = check_row(args.tier, row_num, sentences)
        print_result(result)
        if not result.get("match", True) and "error" not in result:
            mismatches.append(result)
        print()

    if mismatches:
        print(f"\n{len(mismatches)} mismatch(es) found:")
        for m in mismatches:
            print(f"  Row {m['row']}: {m['sentence']}")
    elif len(rows) > 1:
        print(f"\nAll {len(rows)} rows match.")


if __name__ == "__main__":
    main()
