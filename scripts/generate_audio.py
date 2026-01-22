#!/usr/bin/env python3
"""Generate audio files for vocabulary sentences using Kokoro TTS.

Uses the TTSPronunciation field with preprocessing to ensure accurate readings:
- Extracts furigana: 昼食【ちゅうしょく】 → ちゅうしょく
- Converts acronyms: API → エーピーアイ
- Preserves TTS pause commas: が、, まず、, を、
"""

import argparse
import csv
import sys
from pathlib import Path

import lameenc
import numpy as np
from kokoro import KPipeline

from pronunciation import preprocess_for_tts

# Project root
ROOT = Path(__file__).parent.parent

# Japanese voice options:
# - jf_alpha (female, best rated C+)
# - jm_kumo (male, C-)
VOICE_MALE = 'jm_kumo'
VOICE_FEMALE = 'jf_alpha'


def generate_tier_audio(tier: int, voice: str = VOICE_MALE, force: bool = False, female: bool = False):
    """Generate audio files for a specific tier.

    Args:
        tier: Tier number (1-6)
        voice: Kokoro voice to use
        force: If True, regenerate even if files exist
        female: If True, use female voice and separate output directory
    """
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"

    # Use separate directory for female voice
    if female:
        output_dir = ROOT / f"tier{tier}-audio-female"
        voice = VOICE_FEMALE
    else:
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
        # Use TTSPronunciation field (has TTS pause commas) and preprocess for accurate TTS
        tts_pronunciation = row['TTSPronunciation']
        tts_input = preprocess_for_tts(tts_pronunciation)
        num = idx + 1

        # Output filename: tier1_001.mp3, tier1_002.mp3, etc.
        output_path = output_dir / f"tier{tier}_{num:03d}.mp3"

        # Skip if already exists (use --force to regenerate)
        if output_path.exists() and not force:
            print(f"[{num}/{total}] Skipping (exists): {output_path.name}")
            continue

        print(f"[{num}/{total}] {tts_input[:50]}{'...' if len(tts_input) > 50 else ''}")

        try:
            # Generate audio
            audio_chunks = []
            for gs, ps, audio in pipeline(tts_input, voice=voice):
                # Convert PyTorch tensor to numpy array
                audio_chunks.append(audio.numpy() if hasattr(audio, 'numpy') else audio)

            # Concatenate audio chunks
            if len(audio_chunks) == 1:
                audio_data = audio_chunks[0]
            else:
                audio_data = np.concatenate(audio_chunks)

            # Convert float32 audio to int16 for MP3 encoding
            audio_int16 = (audio_data * 32767).astype(np.int16)

            # Encode directly to MP3 using lameenc (no ffmpeg needed)
            encoder = lameenc.Encoder()
            encoder.set_bit_rate(128)
            encoder.set_in_sample_rate(24000)
            encoder.set_channels(1)
            encoder.set_quality(2)  # 2 = high quality, 7 = fast

            mp3_data = encoder.encode(audio_int16.tobytes()) + encoder.flush()

            with open(output_path, 'wb') as f:
                f.write(mp3_data)

        except Exception as e:
            print(f"    Error: {e}")
            continue

    print(f"\nDone! Audio files saved to: {output_dir}")

    # Count generated files
    generated = len(list(output_dir.glob("*.mp3")))
    print(f"Total files: {generated}/{total}")


def main():
    parser = argparse.ArgumentParser(description="Generate audio for vocabulary tiers")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Tier number to generate (1-6)")
    parser.add_argument("--all", action="store_true",
                        help="Generate audio for all tiers")
    parser.add_argument("--female", action="store_true",
                        help="Use female voice (jf_alpha) and save to tier*-audio-female/")
    parser.add_argument("--voice", default=VOICE_MALE,
                        help=f"Voice to use (default: {VOICE_MALE})")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate audio even if files exist")

    args = parser.parse_args()

    if args.all:
        for tier in range(1, 7):
            generate_tier_audio(tier, args.voice, args.force, args.female)
    elif args.tier:
        generate_tier_audio(args.tier, args.voice, args.force, args.female)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
