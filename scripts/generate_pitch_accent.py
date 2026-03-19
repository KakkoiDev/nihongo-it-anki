#!/usr/bin/env python3
"""Generate pitch accent HTML for Anki cloze word display.

For each vocabulary entry, analyses the Cloze word using UniDic to get the
pitch accent type (aType), then generates colored ruby HTML where:
  - green spans = high mora
  - red spans   = low mora

Only processes single-token words with valid aType data (~50% coverage).
Multi-token compounds and words without pitch data get an empty field.

Output column: PitchAccent (HTML string, stored in CSV)
"""

import csv
import re
from pathlib import Path

import fugashi

ROOT = Path(__file__).parent.parent

tagger = fugashi.Tagger()

# Small kana that combine with the preceding character to form one mora
# Note: っ/ッ (geminate) is its OWN mora, not a combiner
SMALL_KANA = set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ')


def kata_to_hira(text: str) -> str:
    """Convert katakana to hiragana."""
    result = []
    for c in text:
        if 'ァ' <= c <= 'ン':
            result.append(chr(ord(c) - 0x60))
        else:
            result.append(c)
    return ''.join(result)


def split_moras(kana: str) -> list[str]:
    """Split kana string into moras, respecting digraphs."""
    moras = []
    i = 0
    while i < len(kana):
        if i + 1 < len(kana) and kana[i + 1] in SMALL_KANA:
            moras.append(kana[i:i + 2])
            i += 2
        else:
            moras.append(kana[i])
            i += 1
    return moras


def accent_pattern(num_moras: int, atype: int) -> list[str]:
    """Return H/L pattern for each mora given accent type.

    Tokyo dialect rules:
      Type 0 (heiban):    L H H H ... (flat, no drop)
      Type 1 (atamadaka): H L L L ... (drops after mora 1)
      Type N (N>=2):      L H H ... H L L ... (drops after mora N)
    """
    if num_moras == 0:
        return []
    if atype == 0:
        return ['L'] + ['H'] * (num_moras - 1)
    if atype == 1:
        return ['H'] + ['L'] * (num_moras - 1)
    # atype >= 2: low first, high up to atype, then low
    result = []
    for i in range(1, num_moras + 1):
        if i == 1:
            result.append('L')
        elif i <= atype:
            result.append('H')
        else:
            result.append('L')
    return result


def get_kana_reading(cloze: str, pronunciation: str) -> str | None:
    """Extract hiragana reading of cloze from Pronunciation field furigana.

    Falls back to cloze itself (hiragana/katakana) if no annotation found.
    """
    # Try 漢字【よみ】 annotation
    pattern = re.compile(re.escape(cloze) + r'【([^】]+)】')
    m = pattern.search(pronunciation)
    if m:
        return m.group(1)

    # No kanji in cloze - it IS the kana reading
    if not re.search(r'[\u4e00-\u9fff]', cloze):
        return kata_to_hira(cloze)

    return None


def pitch_html(cloze: str, kana: str, atype: int) -> str:
    """Generate ruby HTML with pitch-colored furigana for the cloze word."""
    moras = split_moras(kana)
    if not moras:
        return ''

    pattern = accent_pattern(len(moras), atype)
    colored_rt = ''.join(
        f'<span class="pitch-{p.lower()}">{m}</span>'
        for m, p in zip(moras, pattern)
    )

    has_kanji = bool(re.search(r'[\u4e00-\u9fff]', cloze))
    if has_kanji:
        return f'<ruby class="vocab">{cloze}<rt>{colored_rt}</rt></ruby>'
    else:
        return f'<span class="vocab">{colored_rt}</span>'


def get_pitch_html(cloze: str, pronunciation: str) -> str:
    """Return pitch-colored HTML for cloze word, or '' if not available."""
    tokens = list(tagger(cloze))

    # Only handle single-token words for reliable pitch data
    if len(tokens) != 1:
        return ''

    token = tokens[0]
    atype_raw = token.feature.aType if hasattr(token.feature, 'aType') else ''

    if not atype_raw or atype_raw == '*':
        return ''

    # Take first value if multiple variants listed (e.g. '1,0')
    try:
        atype = int(atype_raw.split(',')[0])
    except (ValueError, AttributeError):
        return ''

    kana = get_kana_reading(cloze, pronunciation)
    if not kana:
        # Fall back to UniDic kana field
        raw_kana = token.feature.kana if hasattr(token.feature, 'kana') else ''
        if not raw_kana or raw_kana == '*':
            return ''
        kana = kata_to_hira(raw_kana)

    return pitch_html(cloze, kana, atype)


def process_csv(tier: int) -> None:
    """Add PitchAccent column to a tier CSV."""
    csv_path = ROOT / f'tier{tier}-vocabulary.csv'
    if not csv_path.exists():
        print(f'  Skipping tier {tier}: file not found')
        return

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if 'PitchAccent' not in fieldnames:
        # Insert before Conjugations
        if 'Conjugations' in fieldnames:
            idx = fieldnames.index('Conjugations')
            fieldnames.insert(idx, 'PitchAccent')
        else:
            fieldnames.append('PitchAccent')

    filled = 0
    for row in rows:
        cloze = row.get('Cloze', '')
        pronunciation = row.get('Pronunciation', '')
        if cloze:
            html = get_pitch_html(cloze, pronunciation)
            row['PitchAccent'] = html
            if html:
                filled += 1
        else:
            row['PitchAccent'] = ''

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f'  Tier {tier}: {len(rows)} entries, {filled} with pitch accent')


def main() -> None:
    print('Generating pitch accent data...')
    for tier in range(1, 9):
        process_csv(tier)
    print('\nDone. Run create_deck.py to rebuild.')


if __name__ == '__main__':
    main()
