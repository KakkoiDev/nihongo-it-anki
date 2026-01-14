#!/usr/bin/env python3
"""Generate audio files for vocabulary sentences using Kokoro TTS."""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

# Project root
ROOT = Path(__file__).parent.parent

# Japanese voice options:
# - jf_alpha (female, best rated C+)
# - jm_kumo (male, C-)
VOICE = 'jm_kumo'


def generate_tier_audio(tier: int, voice: str = VOICE):
    """Generate audio files for a specific tier."""
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"
    output_dir = ROOT / f"tier{tier}-audio"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Read vocabulary
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sentences = list(reader)

    total = len(sentences)
    print(f"\nTier {tier}: {total} sentences")
    print(f"Output: {output_dir}")
    print(f"Voice: {voice}\n")

    # Initialize pipeline
    print("Initializing Kokoro TTS pipeline...")
    pipeline = KPipeline(lang_code='j')
    print("Pipeline ready.\n")

    # Generate audio for each sentence
    for idx, row in enumerate(sentences):
        japanese = row['Sentence']
        num = idx + 1

        # Output filename: tier1_001.wav, tier1_002.wav, etc.
        output_path = output_dir / f"tier{tier}_{num:03d}.wav"

        # Skip if already exists
        if output_path.exists():
            print(f"[{num}/{total}] Skipping (exists): {output_path.name}")
            continue

        print(f"[{num}/{total}] {japanese[:40]}{'...' if len(japanese) > 40 else ''}")

        try:
            # Generate audio
            audio_chunks = []
            for gs, ps, audio in pipeline(japanese, voice=voice):
                audio_chunks.append(audio)

            # Concatenate audio chunks
            if len(audio_chunks) == 1:
                audio_data = audio_chunks[0]
            else:
                audio_data = np.concatenate(audio_chunks)

            # Save audio file
            sf.write(str(output_path), audio_data, 24000)

        except Exception as e:
            print(f"    Error: {e}")
            continue

    print(f"\nDone! Audio files saved to: {output_dir}")

    # Count generated files
    generated = len(list(output_dir.glob("*.wav")))
    print(f"Total files: {generated}/{total}")


def main():
    parser = argparse.ArgumentParser(description="Generate audio for vocabulary tiers")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Tier number to generate (1-6)")
    parser.add_argument("--all", action="store_true",
                        help="Generate audio for all tiers")
    parser.add_argument("--voice", default=VOICE,
                        help=f"Voice to use (default: {VOICE})")

    args = parser.parse_args()

    if args.all:
        for tier in range(1, 7):
            generate_tier_audio(tier, args.voice)
    elif args.tier:
        generate_tier_audio(args.tier, args.voice)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
