#!/usr/bin/env python3
"""Generate verb/adjective conjugation tables for Anki cards.

This script analyzes the Cloze word from each vocabulary entry and generates
HTML conjugation tables for verbs and い-adjectives.

Uses fugashi for morphological analysis to identify word types.
"""

import csv
import re
from pathlib import Path

import fugashi

ROOT = Path(__file__).parent.parent

# Initialize tagger
tagger = fugashi.Tagger()


def get_word_info(word: str) -> dict:
    """Analyze a word and return its type and base form.

    Returns dict with:
        - type: 'suru_verb', 'godan_verb', 'ichidan_verb', 'kuru_verb', 'i_adj', 'na_adj', 'noun', 'other'
        - base: dictionary form
        - stem: stem for conjugation (if applicable)
    """
    # Parse the word
    tokens = list(tagger(word))
    if not tokens:
        return {'type': 'other', 'base': word, 'stem': ''}

    # Check for する compound verbs first (most common in IT vocab)
    if word.endswith('する'):
        stem = word[:-2]
        return {'type': 'suru_verb', 'base': word, 'stem': stem}

    # Check for conjugated する verbs
    suru_patterns = ['して', 'した', 'します', 'しない', 'される', 'させる', 'できる', 'しよう', 'すれば']
    for pattern in suru_patterns:
        if word.endswith(pattern):
            # Try to find the stem
            stem = word[:-len(pattern)]
            if stem:
                return {'type': 'suru_verb', 'base': stem + 'する', 'stem': stem}

    # Get the first token's part of speech
    token = tokens[0]
    pos = token.feature.pos1 if hasattr(token.feature, 'pos1') else ''
    pos2 = token.feature.pos2 if hasattr(token.feature, 'pos2') else ''

    # Check for verbs
    if pos == '動詞':
        lemma = token.feature.lemma if hasattr(token.feature, 'lemma') else word
        if lemma is None:
            lemma = word
        # Use original word if lemma contains hyphen (UniDic adds English for katakana)
        elif '-' in lemma:
            lemma = word

        # Check verb type
        if lemma in ['来る', 'くる']:
            return {'type': 'kuru_verb', 'base': '来る', 'stem': ''}
        if lemma in ['する']:
            return {'type': 'suru_verb', 'base': 'する', 'stem': ''}

        # Ichidan verbs (一段) - typically end in いる or える
        # Check conjugation type from UniDic
        conj_type = token.feature.cType if hasattr(token.feature, 'cType') else ''
        if '一段' in str(conj_type) or '上一段' in str(conj_type) or '下一段' in str(conj_type):
            stem = lemma[:-1] if lemma.endswith('る') else lemma
            return {'type': 'ichidan_verb', 'base': lemma, 'stem': stem}

        # Godan verbs (五段)
        if '五段' in str(conj_type):
            return {'type': 'godan_verb', 'base': lemma, 'stem': ''}

        # Default to godan if ends in う-row kana
        if lemma and lemma[-1] in 'うくすつぬふむゆる':
            return {'type': 'godan_verb', 'base': lemma, 'stem': ''}

        return {'type': 'godan_verb', 'base': lemma, 'stem': ''}

    # Check for い-adjectives
    if pos == '形容詞':
        lemma = token.feature.lemma if hasattr(token.feature, 'lemma') else word
        if lemma is None:
            lemma = word
        # Use original word if lemma contains hyphen (UniDic adds English for katakana)
        elif '-' in lemma:
            lemma = word
        if lemma.endswith('い'):
            stem = lemma[:-1]
            return {'type': 'i_adj', 'base': lemma, 'stem': stem}

    # Check for な-adjectives (形状詞)
    if pos == '形状詞' or pos2 == '形状詞':
        lemma = token.feature.lemma if hasattr(token.feature, 'lemma') else word
        return {'type': 'na_adj', 'base': lemma, 'stem': lemma}

    # Check for nouns that can form する verbs (サ変可能)
    if pos == '名詞':
        lemma = token.feature.lemma if hasattr(token.feature, 'lemma') else word
        if lemma is None:
            lemma = word
        # Use original word if lemma contains hyphen (UniDic adds English for katakana)
        elif '-' in lemma:
            lemma = word
        # Check if it's a サ変 (suru-able) noun
        pos3 = token.feature.pos3 if hasattr(token.feature, 'pos3') else ''
        pos4 = token.feature.pos4 if hasattr(token.feature, 'pos4') else ''
        if 'サ変可能' in str(pos2) or 'サ変可能' in str(pos3) or 'サ変可能' in str(pos4):
            return {'type': 'suru_verb', 'base': lemma + 'する', 'stem': lemma}
        return {'type': 'noun', 'base': lemma, 'stem': ''}

    return {'type': 'other', 'base': word, 'stem': ''}


def conjugate_suru_verb(stem: str) -> dict:
    """Generate all conjugations for a する verb compound."""
    return {
        'basic': {
            'Dictionary 辞書形': f'{stem}する',
            'Polite ます形': f'{stem}します',
            'Negative ない形': f'{stem}しない',
            'Te-form て形': f'{stem}して',
            'Past た形': f'{stem}した',
        },
        'advanced': {
            'Potential 可能形': f'{stem}できる',
            'Passive 受身形': f'{stem}される',
            'Causative 使役形': f'{stem}させる',
            'Caus-Pass 使役受身': f'{stem}させられる',
            'Conditional 仮定形': f'{stem}すれば',
            'Conditional たら形': f'{stem}したら',
            'Volitional 意向形': f'{stem}しよう',
            'Imperative 命令形': f'{stem}しろ',
            'Want to たい形': f'{stem}したい',
            'Should べき形': f'{stem}すべき',
        },
        'keigo': {
            'Respectful 尊敬語': f'{stem}なさる',
            'Humble 謙譲語': f'{stem}いたす',
        }
    }


# Godan verb ending mappings
GODAN_ENDINGS = {
    'う': {'a': 'わ', 'i': 'い', 'e': 'え', 'o': 'お', 'te': 'って', 'ta': 'った'},
    'く': {'a': 'か', 'i': 'き', 'e': 'け', 'o': 'こ', 'te': 'いて', 'ta': 'いた'},
    'ぐ': {'a': 'が', 'i': 'ぎ', 'e': 'げ', 'o': 'ご', 'te': 'いで', 'ta': 'いだ'},
    'す': {'a': 'さ', 'i': 'し', 'e': 'せ', 'o': 'そ', 'te': 'して', 'ta': 'した'},
    'つ': {'a': 'た', 'i': 'ち', 'e': 'て', 'o': 'と', 'te': 'って', 'ta': 'った'},
    'ぬ': {'a': 'な', 'i': 'に', 'e': 'ね', 'o': 'の', 'te': 'んで', 'ta': 'んだ'},
    'ぶ': {'a': 'ば', 'i': 'び', 'e': 'べ', 'o': 'ぼ', 'te': 'んで', 'ta': 'んだ'},
    'む': {'a': 'ま', 'i': 'み', 'e': 'め', 'o': 'も', 'te': 'んで', 'ta': 'んだ'},
    'る': {'a': 'ら', 'i': 'り', 'e': 'れ', 'o': 'ろ', 'te': 'って', 'ta': 'った'},
}


def conjugate_godan_verb(base: str) -> dict:
    """Generate all conjugations for a godan (五段) verb."""
    if not base:
        return {}

    ending = base[-1]
    stem = base[:-1]

    if ending not in GODAN_ENDINGS:
        return {}

    e = GODAN_ENDINGS[ending]

    return {
        'basic': {
            'Dictionary 辞書形': base,
            'Polite ます形': f'{stem}{e["i"]}ます',
            'Negative ない形': f'{stem}{e["a"]}ない',
            'Te-form て形': f'{stem}{e["te"]}',
            'Past た形': f'{stem}{e["ta"]}',
        },
        'advanced': {
            'Potential 可能形': f'{stem}{e["e"]}る',
            'Passive 受身形': f'{stem}{e["a"]}れる',
            'Causative 使役形': f'{stem}{e["a"]}せる',
            'Caus-Pass 使役受身': f'{stem}{e["a"]}せられる',
            'Conditional 仮定形': f'{stem}{e["e"]}ば',
            'Conditional たら形': f'{stem}{e["ta"]}ら',
            'Volitional 意向形': f'{stem}{e["o"]}う',
            'Imperative 命令形': f'{stem}{e["e"]}',
            'Want to たい形': f'{stem}{e["i"]}たい',
            'Should べき形': f'{base}べき',
        },
        'keigo': {
            'Respectful 尊敬語': f'{stem}{e["a"]}れる',
            'Humble 謙譲語': f'お{stem}{e["i"]}する',
        }
    }


def conjugate_ichidan_verb(base: str, stem: str) -> dict:
    """Generate all conjugations for an ichidan (一段) verb."""
    if not stem:
        stem = base[:-1] if base.endswith('る') else base

    return {
        'basic': {
            'Dictionary 辞書形': f'{stem}る',
            'Polite ます形': f'{stem}ます',
            'Negative ない形': f'{stem}ない',
            'Te-form て形': f'{stem}て',
            'Past た形': f'{stem}た',
        },
        'advanced': {
            'Potential 可能形': f'{stem}られる',
            'Passive 受身形': f'{stem}られる',
            'Causative 使役形': f'{stem}させる',
            'Caus-Pass 使役受身': f'{stem}させられる',
            'Conditional 仮定形': f'{stem}れば',
            'Conditional たら形': f'{stem}たら',
            'Volitional 意向形': f'{stem}よう',
            'Imperative 命令形': f'{stem}ろ',
            'Want to たい形': f'{stem}たい',
            'Should べき形': f'{stem}るべき',
        },
        'keigo': {
            'Respectful 尊敬語': f'{stem}られる',
            'Humble 謙譲語': f'お{stem}する',
        }
    }


def conjugate_kuru_verb() -> dict:
    """Generate all conjugations for 来る (kuru)."""
    return {
        'basic': {
            'Dictionary 辞書形': '来る',
            'Polite ます形': '来ます',
            'Negative ない形': '来ない',
            'Te-form て形': '来て',
            'Past た形': '来た',
        },
        'advanced': {
            'Potential 可能形': '来られる',
            'Passive 受身形': '来られる',
            'Causative 使役形': '来させる',
            'Caus-Pass 使役受身': '来させられる',
            'Conditional 仮定形': '来れば',
            'Conditional たら形': '来たら',
            'Volitional 意向形': '来よう',
            'Imperative 命令形': '来い',
            'Want to たい形': '来たい',
            'Should べき形': '来るべき',
        },
        'keigo': {
            'Respectful 尊敬語': 'いらっしゃる',
            'Humble 謙譲語': '参る',
        }
    }


def conjugate_i_adjective(stem: str) -> dict:
    """Generate all conjugations for an い-adjective."""
    return {
        'basic': {
            'Dictionary 辞書形': f'{stem}い',
            'Negative ない形': f'{stem}くない',
            'Past た形': f'{stem}かった',
            'Past Neg なかった': f'{stem}くなかった',
            'Te-form て形': f'{stem}くて',
            'Adverbial く形': f'{stem}く',
        }
    }


def generate_conjugation_html(word: str, conjugations: dict, word_type: str) -> str:
    """Generate HTML for conjugation table (single line for CSV compatibility)."""
    if not conjugations:
        return ''

    type_label = {
        'suru_verb': 'する動詞',
        'godan_verb': '五段動詞',
        'ichidan_verb': '一段動詞',
        'kuru_verb': 'カ変動詞',
        'i_adj': 'い形容詞',
    }.get(word_type, '')

    parts = [
        f'<details class="conjugation-section">',
        f'<summary>Conjugations for {word} ({type_label})</summary>',
        '<table class="conjugation-table">'
    ]

    for section_name, forms in conjugations.items():
        section_label = {
            'basic': 'Basic Forms',
            'advanced': 'Advanced Forms',
            'keigo': 'Keigo 敬語'
        }.get(section_name, section_name)

        parts.append(f'<tr><th colspan="2">{section_label}</th></tr>')
        for form_name, form_value in forms.items():
            parts.append(f'<tr><td>{form_name}</td><td>{form_value}</td></tr>')

    parts.append('</table>')
    parts.append('</details>')

    # Join without newlines for CSV compatibility
    return ''.join(parts)


def get_conjugations_for_word(word: str) -> str:
    """Main function to get HTML conjugation table for a word."""
    info = get_word_info(word)

    conjugations = {}

    if info['type'] == 'suru_verb':
        conjugations = conjugate_suru_verb(info['stem'])
    elif info['type'] == 'godan_verb':
        conjugations = conjugate_godan_verb(info['base'])
    elif info['type'] == 'ichidan_verb':
        conjugations = conjugate_ichidan_verb(info['base'], info['stem'])
    elif info['type'] == 'kuru_verb':
        conjugations = conjugate_kuru_verb()
    elif info['type'] == 'i_adj':
        conjugations = conjugate_i_adjective(info['stem'])
    else:
        # No conjugation for nouns, な-adjectives in this simple form, etc.
        return ''

    return generate_conjugation_html(word, conjugations, info['type'])


def process_csv(tier: int) -> None:
    """Process a tier CSV file and add conjugations column."""
    csv_path = ROOT / f"tier{tier}-vocabulary.csv"

    if not csv_path.exists():
        print(f"  Skipping tier {tier}: file not found")
        return

    # Read existing data
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # Add Conjugations field if not present
    if 'Conjugations' not in fieldnames:
        fieldnames.append('Conjugations')

    # Generate conjugations for each row
    processed = 0
    for row in rows:
        cloze = row.get('Cloze', '')
        if cloze:
            conjugation_html = get_conjugations_for_word(cloze)
            row['Conjugations'] = conjugation_html
            if conjugation_html:
                processed += 1
        else:
            row['Conjugations'] = ''

    # Write back
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Tier {tier}: {len(rows)} entries, {processed} with conjugations")


def main():
    """Process all tier CSV files."""
    print("Generating conjugation tables...")

    for tier in range(1, 7):
        process_csv(tier)

    print("\nDone! Run create_deck.py to rebuild the deck with conjugations.")


if __name__ == "__main__":
    main()
