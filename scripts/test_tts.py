#!/usr/bin/env python3
"""Quick TTS test for specific sentences from tier CSVs.

Usage:
    python scripts/test_tts.py --tier 1 --row 5        # Test row 5 from tier1
    python scripts/test_tts.py --tier 1 --row 5,6,10   # Test multiple rows
    python scripts/test_tts.py --text "問題【もんだい】を、見【み】つけました"  # Direct text
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

import edge_tts

from pronunciation import preprocess_for_tts

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import load_deck_config

VOICE = 'ja-JP-KeitaNeural'
DELAY_BETWEEN_REQUESTS = 0.3
MAX_RETRIES = 3


async def generate_single(text: str, output_path: Path):
    """Generate audio for a single text."""
    tts_input = preprocess_for_tts(text)
    print(f"  TTS input: {tts_input}")

    for attempt in range(MAX_RETRIES):
        try:
            communicate = edge_tts.Communicate(tts_input, VOICE)
            await communicate.save(str(output_path))
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            print(f"  Saved: {output_path}")
            return
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                print(f"    retry in {wait}s ({e})")
                await asyncio.sleep(wait)
            else:
                raise


def main():
    parser = argparse.ArgumentParser(description="Test TTS for specific sentences")
    parser.add_argument("--deck", type=str, default="it-vocab",
                        help="Deck slug (default: it-vocab)")
    parser.add_argument("--tier", type=int,
                        help="Tier number")
    parser.add_argument("--row", type=str,
                        help="Row number(s) to test, comma-separated (1-indexed)")
    parser.add_argument("--text", type=str,
                        help="Direct text to test (with furigana annotations)")

    args = parser.parse_args()

    if not args.text and not (args.tier and args.row):
        parser.print_help()
        sys.exit(1)

    if args.text:
        asyncio.run(generate_single(args.text, Path("test_tts.mp3")))
    else:
        config = load_deck_config(args.deck)
        csv_path = config.csv_path(args.tier)
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
            asyncio.run(generate_single(row['Pronunciation'], output_path))


if __name__ == "__main__":
    main()
