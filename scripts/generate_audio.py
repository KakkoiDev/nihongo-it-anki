#!/usr/bin/env python3
"""Generate audio files for vocabulary sentences using Edge TTS.

Uses the TTSPronunciation field with preprocessing to ensure accurate readings:
- Extracts furigana: 昼食【ちゅうしょく】 → ちゅうしょく
- Converts acronyms: API → エーピーアイ
- Preserves TTS pause commas: が、, まず、, を、
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

import edge_tts

from pronunciation import preprocess_for_tts

# Project root
ROOT = Path(__file__).parent.parent

# Japanese Edge TTS voices
VOICE_MALE = 'ja-JP-KeitaNeural'
VOICE_FEMALE = 'ja-JP-NanamiNeural'

# Rate limiting
DELAY_BETWEEN_REQUESTS = 0.3  # seconds
MAX_RETRIES = 3


async def tts_generate(text: str, voice: str, output_path: Path, retries: int = MAX_RETRIES):
    """Generate a single MP3 file using edge-tts with retry logic."""
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
            return
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"    retry in {wait}s ({e})")
                await asyncio.sleep(wait)
            else:
                raise


async def generate_tier_audio(tier: int, voice: str = VOICE_MALE, force: bool = False, female: bool = False):
    """Generate audio files for a specific tier.

    Args:
        tier: Tier number (1-6)
        voice: Edge TTS voice to use
        force: If True, regenerate even if files exist
        female: If True, use female voice and separate output directory
    """
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"

    if female:
        output_dir = ROOT / f"tier{tier}-audio-female"
        voice = VOICE_FEMALE
    else:
        output_dir = ROOT / f"tier{tier}-audio"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sentences = list(reader)

    total = len(sentences)
    print(f"\nTier {tier}: {total} sentences")
    print(f"Output: {output_dir}")
    print(f"Voice: {voice}\n")

    for idx, row in enumerate(sentences):
        tts_pronunciation = row['TTSPronunciation']
        tts_input = preprocess_for_tts(tts_pronunciation)
        num = idx + 1

        output_path = output_dir / f"tier{tier}_{num:03d}.mp3"

        if output_path.exists() and not force:
            print(f"[{num}/{total}] Skipping (exists): {output_path.name}")
            continue

        print(f"[{num}/{total}] {tts_input[:50]}{'...' if len(tts_input) > 50 else ''}")

        try:
            await tts_generate(tts_input, voice, output_path)
        except Exception as e:
            print(f"    Error: {e}")
            continue

    print(f"\nDone! Audio files saved to: {output_dir}")

    generated = len(list(output_dir.glob("*.mp3")))
    print(f"Total files: {generated}/{total}")


def main():
    parser = argparse.ArgumentParser(description="Generate audio for vocabulary tiers")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Tier number to generate (1-6)")
    parser.add_argument("--all", action="store_true",
                        help="Generate audio for all tiers")
    parser.add_argument("--female", action="store_true",
                        help="Use female voice (NanamiNeural) and save to tier*-audio-female/")
    parser.add_argument("--voice", default=VOICE_MALE,
                        help=f"Voice to use (default: {VOICE_MALE})")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate audio even if files exist")

    args = parser.parse_args()

    if args.all:
        for tier in range(1, 7):
            asyncio.run(generate_tier_audio(tier, args.voice, args.force, args.female))
    elif args.tier:
        asyncio.run(generate_tier_audio(args.tier, args.voice, args.force, args.female))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
