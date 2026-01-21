#!/usr/bin/env python3
"""Generate audio files for Kokoro TTS pause pattern experiment.

Tests different punctuation/pause patterns for Japanese particles and adverbs
to find optimal patterns for natural-sounding speech.
"""

import csv
import sys
from pathlib import Path

import lameenc
import numpy as np
from kokoro import KPipeline

# Experiment directory
EXPERIMENT_DIR = Path(__file__).parent
AUDIO_DIR = EXPERIMENT_DIR / "audio"
CSV_PATH = EXPERIMENT_DIR / "pause_variations.csv"

# Voice settings
VOICE = 'jm_kumo'  # Male voice


def generate_audio(pipeline: KPipeline, text: str, output_path: Path) -> bool:
    """Generate MP3 audio for given text.

    Args:
        pipeline: Initialized Kokoro pipeline
        text: Japanese text to synthesize
        output_path: Path for output MP3 file

    Returns:
        True if successful, False otherwise
    """
    try:
        audio_chunks = []
        for gs, ps, audio in pipeline(text, voice=VOICE):
            audio_chunks.append(audio.numpy() if hasattr(audio, 'numpy') else audio)

        if not audio_chunks:
            return False

        # Concatenate audio chunks
        if len(audio_chunks) == 1:
            audio_data = audio_chunks[0]
        else:
            audio_data = np.concatenate(audio_chunks)

        # Convert float32 audio to int16 for MP3 encoding
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Encode directly to MP3 using lameenc
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(24000)
        encoder.set_channels(1)
        encoder.set_quality(2)

        mp3_data = encoder.encode(audio_int16.tobytes()) + encoder.flush()

        with open(output_path, 'wb') as f:
            f.write(mp3_data)

        return True

    except Exception as e:
        print(f"    Error: {e}")
        return False


def main():
    # Ensure output directory exists
    AUDIO_DIR.mkdir(exist_ok=True)

    # Read variations
    if not CSV_PATH.exists():
        print(f"Error: {CSV_PATH} not found")
        sys.exit(1)

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        variations = list(reader)

    total = len(variations)
    print(f"Kokoro TTS Pause Pattern Experiment")
    print(f"====================================")
    print(f"Total variations: {total}")
    print(f"Output directory: {AUDIO_DIR}")
    print(f"Voice: {VOICE}\n")

    # Initialize pipeline
    print("Initializing Kokoro TTS pipeline...")
    pipeline = KPipeline(lang_code='j')
    print("Pipeline ready.\n")

    # Track statistics
    success = 0
    skipped = 0
    failed = 0

    # Generate audio for each variation
    for idx, row in enumerate(variations):
        num = idx + 1
        sentence_id = row['sentence_id']
        category = row['category']
        variation_id = row['variation_id']
        pattern = row['pattern']
        text = row['modified']
        filename = row['filename']

        output_path = AUDIO_DIR / filename

        # Skip if already exists
        if output_path.exists():
            print(f"[{num}/{total}] Skipping (exists): {filename}")
            skipped += 1
            continue

        # Display progress
        print(f"[{num}/{total}] {sentence_id}_{category}{variation_id} ({pattern})")
        print(f"         {text[:60]}{'...' if len(text) > 60 else ''}")

        if generate_audio(pipeline, text, output_path):
            success += 1
        else:
            failed += 1

    # Summary
    print(f"\n====================================")
    print(f"Generation complete!")
    print(f"  Success: {success}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {success + skipped}/{total}")

    # Verify files
    generated_files = list(AUDIO_DIR.glob("*.mp3"))
    print(f"\nAudio files in {AUDIO_DIR}: {len(generated_files)}")


if __name__ == "__main__":
    main()
