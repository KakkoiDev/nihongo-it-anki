# Kokoro TTS Pause Pattern Evaluation

Experiment to find optimal punctuation patterns for natural-sounding Japanese TTS.

## Test Methodology

- **TTS Engine**: Kokoro (jm_kumo voice)
- **Test sentences**: 13 IT-focused Japanese sentences
- **Variations tested**: 10 particle patterns, 6 adverb patterns

### Patterns Tested

| Pattern | Example | Description |
|---------|---------|-------------|
| baseline | `パスをテスト` | No modification |
| comma_before | `パス、をテスト` | Comma before particle |
| comma_after | `パスを、テスト` | Comma after particle |
| space_half | `パス を テスト` | Half-width spaces |
| space_full | `パス　を　テスト` | Full-width spaces |
| period_after | `パスを。テスト` | Period after particle |
| ellipsis_before | `パス...をテスト` | Ellipsis before |
| ellipsis_after | `パスを...テスト` | Ellipsis after |
| double_comma | `パス、、をテスト` | Double comma |
| ssml_break | `<break time="200ms"/>` | SSML tag |

## Results Summary

### Particles

| Particle | Baseline | Needs Comma | Notes |
|----------|----------|-------------|-------|
| を (object) | Unnatural | Yes | Always add comma after |
| が (subject) | Unnatural | Yes | Add comma after (context-aware) |
| は (topic) | Natural | No | Sounds good as-is |
| に (direction) | Natural | No | Sounds good as-is |
| で (location) | Natural | No | Sounds good as-is |

### Adverbs

| Adverb | Baseline | Needs Comma | Notes |
|--------|----------|-------------|-------|
| まず (first) | No pause | Yes | Comma creates good pause |
| 次に (next) | Acceptable | Yes | Comma sounds better |
| すぐに (immediately) | Natural | Optional | Either works |

### Special Characters

| Character | Status | Notes |
|-----------|--------|-------|
| っ (small tsu) | Works | Handled natively |
| ー (long vowel) | Works | Leave as-is, fixes make it worse |
| SSML tags | Broken | Kokoro reads tags aloud |

## Key Findings

1. **Spaces don't create pauses** - Half/full-width spaces have no effect
2. **SSML not supported** - Kokoro reads `<break>` tags as text
3. **Comma is the only reliable pause mechanism**
4. **Punctuation length is consistent** - Different punctuation creates similar pause lengths

## Implementation

Based on these findings, implemented in `scripts/`:

| Script | Rule |
|--------|------|
| `pronunciation.py` | `を` → `を、` (always) |
| `fix_ga_commas.py` | `が` → `が、` (when subject marker) |
| `fix_adverb_commas.py` | `まず` → `まず、` (sentence-initial adverbs) |

## Reproduction

```bash
# Generate test audio (creates audio/ folder)
uv run python experiments/kokoro-pause-test/generate_experiment.py

# Listen and compare variations
```
