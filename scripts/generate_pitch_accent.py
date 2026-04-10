#!/usr/bin/env python3
"""Generate pitch accent HTML for Anki cloze word display.

For each vocabulary entry, analyses the Cloze word using UniDic/fugashi to
get the pitch accent type (aType), then generates colored ruby HTML where:
  - green (pitch-h) = high mora
  - red (pitch-l)   = low mora

Coverage strategy (achieves 100%):
  1. Single-token words with UniDic aType data -> colored pitch HTML
  2. Everything else -> plain furigana fallback (no colors, but still ruby)

Reading extraction for the fallback has 3 strategies (in order):
  1. Exact match: cloze word appears with 【reading】 annotation
  2. Contiguous match: cloze spans multiple annotated segments in sequence
     e.g. 実は in "実【じつ】はもっと" -> じつは
  3. Segment match: cloze is in dictionary form but pronunciation has inflected
     form. Breaks cloze into kanji/kana segments and looks up each kanji reading.
     e.g. 協力する vs 協力【きょうりょく】して -> きょうりょくする
  3b. Decompose: kanji block spans multiple annotations separated by particles.
     e.g. 重複排除 vs 重複【じゅうふく】を排除【はいじょ】 -> じゅうふくはいじょ

Display rules:
  - Kanji words: <ruby>漢字<rt>reading</rt></ruby>
  - Katakana words (e.g. ブロック): <ruby>ブロック<rt>pitch hiragana</rt></ruby>
    (shows katakana as base with hiragana pitch guide above)
  - Hiragana words: <span>colored moras</span> (pitch IS the guide)

All kanji regex patterns include \u3005 (々 repetition mark).
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


def parse_pronunciation(text: str) -> list[tuple[str, str]]:
    """Parse annotated text into (surface, reading) pairs.

    Input: 実【じつ】はもっと
    Output: [('実', 'じつ'), ('は', 'は'), ('も', 'も'), ...]
    """
    parts = []
    pos = 0
    while pos < len(text):
        m = re.match(r'([\u4e00-\u9fff\u3400-\u4dbf\u3005]+)【([^】]+)】', text[pos:])
        if m:
            parts.append((m.group(1), m.group(2)))
            pos += m.end()
        else:
            parts.append((text[pos], text[pos]))
            pos += 1
    return parts


def get_kana_reading(cloze: str, pronunciation: str) -> str | None:
    """Extract hiragana reading of cloze from Pronunciation field furigana.

    Handles compound cloze words by parsing the pronunciation annotations
    and matching against the surface text.
    """
    # Simple case: exact match with annotation
    pattern = re.compile(re.escape(cloze) + r'【([^】]+)】')
    m = pattern.search(pronunciation)
    if m:
        return m.group(1)

    # No kanji in cloze - it IS the kana reading
    if not re.search(r'[\u4e00-\u9fff\u3005]', cloze):
        return kata_to_hira(cloze)

    # Contiguous case: parse pronunciation and match the cloze word directly
    parts = parse_pronunciation(pronunciation)
    surface_str = ''.join(s for s, _ in parts)
    idx = surface_str.find(cloze)
    if idx >= 0:
        reading = []
        surface_pos = 0
        for s, r in parts:
            part_end = surface_pos + len(s)
            if part_end <= idx:
                surface_pos = part_end
                continue
            if surface_pos >= idx + len(cloze):
                break
            if surface_pos >= idx and part_end <= idx + len(cloze):
                reading.append(r)
            else:
                reading = []
                break
            surface_pos = part_end
        if reading:
            return ''.join(reading)

    # Segment case: cloze word not contiguous in pronunciation (dictionary form
    # vs inflected form). Break cloze into kanji/non-kanji segments and look up
    # each kanji segment's reading individually.
    # e.g. cloze=協力する, pronunciation has 協力【きょうりょく】して
    #      -> segments: [協力, する] -> [きょうりょく, する] -> きょうりょくする
    kanji_re = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3005]+')
    segments = re.findall(
        r'[\u4e00-\u9fff\u3400-\u4dbf\u3005]+|[^\u4e00-\u9fff\u3400-\u4dbf]+', cloze
    )
    reading_parts = []
    for seg in segments:
        if kanji_re.match(seg):
            seg_pattern = re.compile(re.escape(seg) + r'【([^】]+)】')
            seg_m = seg_pattern.search(pronunciation)
            if seg_m:
                reading_parts.append(seg_m.group(1))
            else:
                # Kanji block may span multiple annotations (e.g. 重複排除
                # annotated as 重複【じゅうふく】を排除【はいじょ】).
                # Greedily match longest annotated prefixes.
                sub_reading = _decompose_kanji(seg, pronunciation)
                if sub_reading:
                    reading_parts.append(sub_reading)
                else:
                    return None
        else:
            reading_parts.append(kata_to_hira(seg))
    return ''.join(reading_parts) if reading_parts else None


def _decompose_kanji(kanji_seg: str, pronunciation: str) -> str | None:
    """Find readings for a kanji segment spanning multiple annotations."""
    readings = []
    remaining = kanji_seg
    while remaining:
        found = False
        for length in range(len(remaining), 0, -1):
            prefix = remaining[:length]
            m = re.search(re.escape(prefix) + r'【([^】]+)】', pronunciation)
            if m:
                readings.append(m.group(1))
                remaining = remaining[length:]
                found = True
                break
        if not found:
            return None
    return ''.join(readings)


def has_katakana(text: str) -> bool:
    """Check if text contains katakana characters."""
    return bool(re.search(r'[\u30A0-\u30FF]', text))


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

    has_kanji = bool(re.search(r'[\u4e00-\u9fff\u3005]', cloze))
    if has_kanji or has_katakana(cloze):
        return f'<ruby class="vocab">{cloze}<rt>{colored_rt}</rt></ruby>'
    else:
        return f'<span class="vocab">{colored_rt}</span>'


def fallback_html(cloze: str, kana: str | None) -> str:
    """Generate plain ruby HTML (no pitch coloring) as fallback."""
    has_kanji = bool(re.search(r'[\u4e00-\u9fff\u3005]', cloze))
    if has_kanji and kana:
        return f'<ruby class="vocab">{cloze}<rt>{kana}</rt></ruby>'
    return f'<span class="vocab">{cloze}</span>'


def get_pitch_html(cloze: str, pronunciation: str) -> str:
    """Return pitch-colored HTML for cloze word, or plain furigana fallback."""
    kana_from_pron = get_kana_reading(cloze, pronunciation)
    tokens = list(tagger(cloze))

    # Try to get pitch accent data from single-token words
    if len(tokens) == 1:
        token = tokens[0]
        atype_raw = token.feature.aType if hasattr(token.feature, 'aType') else ''

        if atype_raw and atype_raw != '*':
            try:
                atype = int(atype_raw.split(',')[0])
            except (ValueError, AttributeError):
                atype = None
            else:
                kana = kana_from_pron
                if not kana:
                    raw_kana = token.feature.kana if hasattr(token.feature, 'kana') else ''
                    if raw_kana and raw_kana != '*':
                        kana = kata_to_hira(raw_kana)
                if kana:
                    return pitch_html(cloze, kana, atype)

    # Fallback: plain furigana without pitch coloring
    return fallback_html(cloze, kana_from_pron)


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
    for tier in range(1, 10):
        process_csv(tier)
    print('\nDone. Run create_deck.py to rebuild.')


if __name__ == '__main__':
    main()
