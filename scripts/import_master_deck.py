#!/usr/bin/env python3
"""One-off importer: convert japanese-master-deck.csv into the jp-teaching deck.

Source CSV columns (Front, Back, Tags):
  Front = "<English><br><span>［context］</span>"
  Back  = "<Japanese sentence><br><span>＜full hiragana reading＞</span>"
  Tags  = "<category> <subtopic>"  (space-separated)

The Back reading keeps ASCII and katakana verbatim and converts ONLY kanji
runs to hiragana (with spaces as word separators). We exploit that ground
truth to generate accurate 漢字【かんじ】 furigana for the Pronunciation field
by aligning each kanji run against the reading between transparent anchors.

Produces decks/jp-teaching/tier{N}-vocabulary.csv with the 8 pipeline columns.
Cloze/KeyMeaning are filled by a curated map (see CLOZE_MAP); rows without an
entry get a heuristic fallback so the file is always valid. PitchAccent is left
empty for generate_pitch_accent.py to fill.
"""

import csv
import re
import sys
from pathlib import Path

SRC = Path("/Users/cyril/Downloads/japanese-master-deck.csv")
OUT_DIR = Path(__file__).parent.parent / "decks" / "jp-teaching"

KANJI = r"一-鿿㐀-䶿々"
KANJI_RE = re.compile(f"[{KANJI}]")
CJK_RE = re.compile(r"[぀-ヿ一-鿿]")

# Source category (first tag) -> tier number
CATEGORY_TIER = {
    "teaching_scaffolding": 1,
    "concept_explanation": 2,
    "life_lesson": 3,
}

# Curated key vocabulary per source row: index -> (Cloze, KeyMeaning).
# Cloze MUST appear verbatim in the sentence (Card 3 blanks it). For proverbs
# and four-character idioms the whole phrase is the cloze.
CLOZE_MAP: dict[int, tuple[str, str]] = {
    0: ("授業", "class / lesson"),
    1: ("続き", "continuation"),
    2: ("ゴール", "goal"),
    3: ("説明", "explanation"),
    4: ("まず", "first (of all)"),
    5: ("確認", "confirmation / check"),
    6: ("実際に", "actually / in practice"),
    7: ("大丈夫", "okay / all right"),
    8: ("一緒に", "together"),
    9: ("簡単に言うと", "simply put / in short"),
    10: ("のようなもの", "something like / akin to"),
    11: ("例えば", "for example"),
    12: ("大事", "important"),
    13: ("ポイント", "point / key point"),
    14: ("画面", "screen"),
    15: ("行", "line (of code)"),
    16: ("直し", "to fix / repair"),
    17: ("わざと", "on purpose / deliberately"),
    18: ("質問", "question"),
    19: ("遠慮なく", "without hesitation / feel free"),
    20: ("自分で", "by yourself"),
    21: ("いい質問", "good question"),
    22: ("もう一度", "once more"),
    23: ("つまり", "in other words / so"),
    24: ("その調子", "keep it up / that's the way"),
    25: ("間違えて", "to make a mistake"),
    26: ("良く", "better / well"),
    27: ("プロンプト", "prompt"),
    28: ("必ず", "always / without fail"),
    29: ("うまくいかない", "to not go well / not work out"),
    30: ("頼りすぎ", "to rely too much"),
    31: ("お疲れさま", "good work / thanks for your effort"),
    32: ("聞いて", "to ask / listen"),
    33: ("指示", "instruction / directive"),
    34: ("通りに", "exactly as / according to"),
    35: ("分かれて", "to be split / divided"),
    36: ("見える", "to be visible"),
    37: ("処理", "processing / handling"),
    38: ("返します", "to return (send back)"),
    39: ("仕組み", "mechanism / how it works"),
    40: ("骨組み", "framework / skeleton"),
    41: ("戻せる", "to be able to revert / go back"),
    42: ("理解", "understanding"),
    43: ("構造", "structure"),
    44: ("囲んで", "to wrap / enclose"),
    45: ("配置", "layout / placement"),
    46: ("要素", "element"),
    47: ("変数", "variable"),
    48: ("関数", "function"),
    49: ("値", "value"),
    50: ("条件", "condition"),
    51: ("繰り返せ", "to repeat"),
    52: ("配列", "array"),
    53: ("オブジェクト", "object"),
    54: ("形式", "format"),
    55: ("保存", "to save / store"),
    56: ("取ってくる", "to fetch / retrieve"),
    57: ("待ちます", "to wait"),
    58: ("窓口", "contact point / interface"),
    59: ("コミット", "commit"),
    60: ("実験", "experiment"),
    61: ("状態", "state / condition"),
    62: ("失敗", "failure"),
    63: ("よく", "carefully / thoroughly"),
    64: ("原因", "cause"),
    65: ("切り分けて", "to isolate / narrow down"),
    66: ("再利用", "reuse"),
    67: ("おかげで", "thanks to / owing to"),
    68: ("覚えて", "to remember / hold"),
    69: ("生まれます", "to be born / arise"),
    70: ("具体的に", "concretely / specifically"),
    71: ("情報", "information"),
    72: ("下書き", "draft"),
    73: ("信じすぎ", "to trust too much"),
    74: ("完璧", "perfection"),
    75: ("近道", "shortcut"),
    76: ("調べ方", "how to look things up"),
    77: ("こなす", "to handle / get through"),
    78: ("継続", "continuation / persistence"),
    79: ("積もれば", "if it piles up (accumulates)"),
    80: ("才能", "talent"),
    81: ("全力", "full effort / all one's strength"),
    82: ("一生懸命", "with all one's might"),
    83: ("成功", "success"),
    84: ("七転び八起き", "fall seven times, rise eight (resilience)"),
    85: ("身につける", "to master / acquire (a skill)"),
    86: ("引きずらない", "to not dwell on / drag around"),
    87: ("やり切る", "to see through / finish completely"),
    88: ("水に流し", "to let bygones be bygones"),
    89: ("艱難", "hardship / adversity"),
    90: ("賢く", "wise / smart"),
    91: ("決して", "never (with a negative)"),
    92: ("石の上にも三年", "perseverance prevails (3 years on a stone)"),
    93: ("単純明快", "simple and clear-cut"),
    94: ("複雑", "complex / complicated"),
    95: ("噛み砕いて", "to break down / simplify"),
    96: ("やさしく", "gently / in an easy way"),
    97: ("急いては事を仕損じる", "haste makes waste"),
    98: ("問題", "problem"),
    99: ("手を動かす", "to get to work (lit. move your hands)"),
    100: ("先手必勝", "seize the initiative to win"),
    101: ("率先垂範", "lead by example"),
    102: ("自分から", "on one's own initiative"),
    103: ("手を打ち", "to take action / take measures"),
    104: ("その場で", "on the spot / right then"),
    105: ("千里の道も一歩から", "a thousand-mile journey starts with one step"),
    106: ("好きこそ物の上手なれ", "you excel at what you love"),
    107: ("普通", "normal / ordinary"),
    108: ("集中", "focus / concentration"),
    109: ("恥", "shame / embarrassment"),
    110: ("恥ずかしがらずに", "without being embarrassed"),
    111: ("十分", "enough / sufficient"),
    112: ("一致団結", "unite as one / solidarity"),
    113: ("伝える力", "the ability to communicate"),
    114: ("無いのと同じ", "the same as not having it"),
    115: ("有言実行", "do what you say you'll do"),
    116: ("終わり良ければすべて良し", "all's well that ends well"),
    117: ("価値", "value / worth"),
    118: ("仕上げて", "to finish / polish off"),
    119: ("柔よく剛を制す", "flexibility overcomes strength"),
    120: ("変化", "change"),
    121: ("基礎", "fundamentals / basics"),
    122: ("急がば回れ", "more haste, less speed"),
    123: ("短距離走", "sprint / short-distance race"),
    124: ("無理", "overdoing it / strain"),
    125: ("使いこなし", "to master the use of"),
    126: ("判断", "judgment / decision"),
    127: ("愛", "love"),
    128: ("隣人", "neighbor"),
    129: ("接し", "to treat / deal with (people)"),
}


def split_front(front: str) -> tuple[str, str]:
    """Return (english, context_label). Context is the ［...］ hint, cleaned."""
    en, _, rest = front.partition("<br>")
    label = re.sub(r"<[^>]+>", "", rest).strip()
    label = label.strip("［］[]").strip()
    en = en.strip()
    # A few English glosses embed a Japanese usage example (e.g.
    # '"With all one's might." — use it: 一生懸命...'). The Translation field
    # must be English-only (validate.py rejects Japanese), so trim at the
    # first CJK char and drop a dangling "— use it:" style connector.
    m = CJK_RE.search(en)
    if m:
        en = en[: m.start()]
        en = re.sub(r"\s*[—–:-]+\s*(use it|e\.g\.|example)?:?\s*$", "", en, flags=re.I)
        en = en.strip()
    return en, label


def split_back(back: str) -> tuple[str, str]:
    """Return (japanese_sentence, full_hiragana_reading)."""
    jp, _, rest = back.partition("<br>")
    reading = re.sub(r"<[^>]+>", "", rest).strip()
    return jp.strip(), reading


def furigana(sentence: str, reading: str) -> str:
    """Build 漢字【かんじ】 notation by aligning kanji runs to the reading.

    Every non-kanji char (ASCII, katakana, hiragana, punctuation, 〜) appears
    verbatim in `reading`; only kanji runs are spelled out. Walk the sentence
    and, for each kanji run, take the reading slice up to the next transparent
    anchor. Raises ValueError on any alignment mismatch so callers can flag it.
    """
    # Reading uses ASCII spaces as word separators; drop them. The sentence's
    # own spaces (rare, around ASCII tokens like "await を") are handled below
    # by emitting them without consuming from the space-free reading.
    r = reading.replace(" ", "").replace("　", "")
    # Anchors used to bound a kanji run's reading must also be space-free.
    out = []
    i = 0
    j = 0
    n = len(sentence)
    while i < n:
        if KANJI_RE.match(sentence[i]):
            # Maximal kanji run
            k = i
            while k < n and KANJI_RE.match(sentence[k]):
                k += 1
            run = sentence[i:k]
            # Anchor: following non-kanji chars (until next kanji or end),
            # with sentence-internal spaces removed to match space-free reading.
            m = k
            while m < n and not KANJI_RE.match(sentence[m]):
                m += 1
            anchor = sentence[k:m].replace(" ", "")
            if anchor == "":
                run_reading = r[j:]
                j = len(r)
            else:
                # Each kanji is >=1 mora, so the run's reading is >=len(run)
                # kana. Start the anchor search past that to avoid matching an
                # anchor kana that also opens the reading (e.g. 良い -> いい,
                # where anchor 'い' also starts the reading 'い').
                idx = r.find(anchor, j + len(run))
                if idx < 0:
                    raise ValueError(
                        f"anchor {anchor!r} not found after pos {j} in {reading!r}"
                    )
                run_reading = r[j:idx]
                j = idx
            if not run_reading:
                raise ValueError(f"empty reading for run {run!r} in {sentence!r}")
            out.append(f"{run}【{run_reading}】")
            i = k
        elif sentence[i] == " ":
            # Real sentence space: emit it, don't consume the space-free reading
            out.append(" ")
            i += 1
        else:
            # Transparent char: must match the reading verbatim
            if j >= len(r) or sentence[i] != r[j]:
                raise ValueError(
                    f"mismatch at sentence[{i}]={sentence[i]!r} "
                    f"vs reading[{j}]={r[j:j+1]!r} in {sentence!r} / {reading!r}"
                )
            out.append(sentence[i])
            i += 1
            j += 1
    return "".join(out)


def register_of(sentence: str) -> str:
    """Heuristic speech register from sentence-final politeness markers."""
    s = sentence.rstrip("。！？")
    if re.search(r"(ございます|いたします|申し上げ|存じ|くださいませ|でしょうか)$", s):
        return "keigo"
    if re.search(r"(です|ます|ません|ましょう|ください|でした|ました|ですね|ますね|ますよ|でしょう)$", s):
        return "polite"
    # Anything ending plainly (だ/る/verb-plain/noun) reads as casual
    return "casual"


COLUMNS = ["Sentence", "Translation", "Cloze", "Pronunciation",
           "Note", "Register", "KeyMeaning", "PitchAccent"]


def main() -> None:
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    tiers: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    errors = []
    translations: dict[str, str] = {}

    for n, row in enumerate(rows):
        tags = row["Tags"].split()
        tier = CATEGORY_TIER.get(tags[0])
        if tier is None:
            errors.append(f"row {n}: unknown category {tags[0]!r}")
            continue
        english, label = split_front(row["Front"])
        sentence, reading = split_back(row["Back"])
        try:
            pron = furigana(sentence, reading)
        except ValueError as e:
            errors.append(f"row {n}: {e}")
            pron = sentence

        cloze, meaning = CLOZE_MAP.get(n, ("", ""))
        if not cloze:
            errors.append(f"row {n}: no CLOZE_MAP entry")
        elif cloze not in sentence:
            errors.append(f"row {n}: cloze {cloze!r} not in sentence {sentence!r}")
        if CJK_RE.search(english):
            errors.append(f"row {n}: translation still has Japanese: {english!r}")
        translations[cloze] = meaning

        tiers[tier].append({
            "Sentence": sentence,
            "Translation": english,
            "Cloze": cloze,
            "Pronunciation": pron,
            "Note": label,
            "Register": register_of(sentence),
            "KeyMeaning": meaning,
            "PitchAccent": "",
        })

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print("  ", e)
        sys.exit(1)
    print("All rows converted cleanly (furigana + cloze + translations).")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for tier, items in tiers.items():
        path = OUT_DIR / f"tier{tier}-vocabulary.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(items)
        print(f"  wrote {path.name}: {len(items)} rows")

    # translations.py (repo convention: KeyMeaning source keyed by Cloze)
    tpath = OUT_DIR / "translations.py"
    lines = ['"""KeyMeaning translations for the jp-teaching deck.',
             "",
             "Maps each Cloze key word to its English meaning. Generated by",
             "scripts/import_master_deck.py; edit there to regenerate.",
             '"""',
             "",
             "TRANSLATIONS = {"]
    for k in sorted(translations):
        v = translations[k].replace('"', '\\"')
        lines.append(f'    "{k}": "{v}",')
    lines.append("}")
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {tpath.name}: {len(translations)} entries")


if __name__ == "__main__":
    main()
