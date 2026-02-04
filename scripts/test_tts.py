#!/usr/bin/env python3
"""Quick TTS test for specific sentences from tier CSVs.

Usage:
    python scripts/test_tts.py --tier 1 --row 5        # Test row 5 from tier1
    python scripts/test_tts.py --tier 1 --row 5,6,10   # Test multiple rows
    python scripts/test_tts.py --text "問題【もんだい】を、見【み】つけました"  # Direct text
"""

import argparse
import csv
import sys
from pathlib import Path

import lameenc
import numpy as np
from kokoro import KPipeline

from pronunciation import preprocess_for_tts

ROOT = Path(__file__).parent.parent
VOICE = 'jm_kumo'


def generate_single(pipeline, text: str, output_path: Path):
    """Generate audio for a single text."""
    tts_input = preprocess_for_tts(text)
    print(f"  TTS input: {tts_input}")

    audio_chunks = []
    for gs, ps, audio in pipeline(tts_input, voice=VOICE):
        audio_chunks.append(audio.numpy() if hasattr(audio, 'numpy') else audio)

    audio_data = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
    audio_int16 = (audio_data * 32767).astype(np.int16)

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(24000)
    encoder.set_channels(1)
    encoder.set_quality(2)

    with open(output_path, 'wb') as f:
        f.write(encoder.encode(audio_int16.tobytes()) + encoder.flush())

    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Test TTS for specific sentences")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Tier number")
    parser.add_argument("--row", type=str,
                        help="Row number(s) to test, comma-separated (1-indexed)")
    parser.add_argument("--text", type=str,
                        help="Direct text to test (with furigana annotations)")

    args = parser.parse_args()

    if not args.text and not (args.tier and args.row):
        parser.print_help()
        sys.exit(1)

    print("Initializing Kokoro TTS...")
    pipeline = KPipeline(lang_code='j')

    if args.text:
        generate_single(pipeline, args.text, Path("test_tts.mp3"))
    else:
        csv_path = ROOT / f"tier{args.tier}-vocabulary.csv"
        with open(csv_path, 'r', encoding='utf-8') as f:
            sentences = list(csv.DictReader(f))

        rows = [int(r.strip()) for r in args.row.split(',')]
        for row_num in rows:
            if row_num < 1 or row_num > len(sentences):
                print(f"Row {row_num} out of range (1-{len(sentences)})")
                continue

            row = sentences[row_num - 1]
            print(f"\nRow {row_num}: {row['Sentence']}")
            output_path = Path(f"test_tier{args.tier}_{row_num:03d}.mp3")
            generate_single(pipeline, row['TTSPronunciation'], output_path)


if __name__ == "__main__":
    main()
