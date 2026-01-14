#!/usr/bin/env python3
"""Generate sample audio files from tier 1 vocabulary."""

import csv
import os
from pathlib import Path

import soundfile as sf
from kokoro import KPipeline

# Project root
ROOT = Path(__file__).parent.parent

# Sample sentences to generate (indices from tier 1)
SAMPLE_INDICES = [0, 1, 2, 5, 10]  # First few sentences

# Japanese voice options:
# - jf_alpha (female, best rated C+)
# - jf_gongitsune, jf_nezumi, jf_tebukuro (female)
# - jm_kumo (male, C-)
VOICE = 'jm_kumo'  # Male Japanese voice


def main():
    """Generate sample audio files."""
    print("Initializing Kokoro TTS pipeline...")
    print("(First run downloads the model, this may take a minute)")
    print(f"Using voice: {VOICE}")

    # Initialize pipeline with Japanese language
    pipeline = KPipeline(lang_code='j')

    # Create output directory
    output_dir = ROOT / "samples"
    output_dir.mkdir(exist_ok=True)

    # Read tier 1 vocabulary
    tier1_path = ROOT / "tier1-vocabulary.csv"
    with open(tier1_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        sentences = list(reader)

    print(f"\nGenerating {len(SAMPLE_INDICES)} sample audio files...\n")

    for idx in SAMPLE_INDICES:
        if idx >= len(sentences):
            continue

        row = sentences[idx]
        japanese = row['Sentence']
        english = row['Translation']

        print(f"[{idx + 1}] {japanese}")
        print(f"    → {english}")

        # Generate audio
        # The pipeline returns a generator of (graphemes, phonemes, audio) tuples
        audio_chunks = []
        for gs, ps, audio in pipeline(japanese, voice=VOICE):
            audio_chunks.append(audio)

        # Concatenate audio chunks if multiple
        if len(audio_chunks) == 1:
            audio_data = audio_chunks[0]
        else:
            import numpy as np
            audio_data = np.concatenate(audio_chunks)

        # Save audio file
        output_path = output_dir / f"sample_{idx + 1:03d}.wav"
        sf.write(str(output_path), audio_data, 24000)
        print(f"    ✓ Saved: {output_path.name}\n")

    print(f"Done! Sample audio files saved to: {output_dir}")
    print("\nPlay them with:")
    print(f"  aplay {output_dir}/sample_001.wav")
    print("  # or")
    print(f"  mpv {output_dir}/sample_001.wav")


if __name__ == "__main__":
    main()
