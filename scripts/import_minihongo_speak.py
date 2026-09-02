#!/usr/bin/env python3
"""Build decks/minihongo-speak/tier*-vocabulary.csv from the minihongo repo.

The tiering axis is minihongo's own can-do list (`data/candos.csv`), work
can-dos first. Two kinds of row feed a tier:

  * the dialog lines of the can-do's dialog group (`data/dialogs.csv`) - whole
    utterances, and the reason a tier is a can-do rather than a word list;
  * the expression rows (`data/expressions.csv`) of the categories that can-do
    needs, mapped in CATEGORY_TIERS / CAT51_TIERS below.

`expressions.csv` is a lexicon, not a sentence corpus: 5 of its 1111 rows end in
a finite verb. So a tier leads with its dialog sentences and follows with the
vocabulary those sentences are built from. Categories with no can-do home - the
231 core words, the animal and nature sets, the not-in-base verb and adjective
lists - are out of scope here; they are comprehension material, and this deck is
the production set.

Every string written comes from minihongo. Nothing is authored here except the
category-to-can-do assignment and the mechanical derivations documented at each
call site.

    uv run python scripts/import_minihongo_speak.py --source ~/Code/minihongo

Regenerating overwrites the CSVs, including their PitchAccent column, so re-run
scripts/generate_pitch_accent.py afterwards.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import fugashi

sys.path.insert(0, str(Path(__file__).parent / "lib"))
from config import DECKS_DIR

tagger = fugashi.Tagger()

SLUG = "minihongo-speak"
FURIGANA = re.compile(r"【[^】]*】")

# Tier order: the six work can-dos first, then the daily-life ones. Within the
# work block the order is the order of a working day - you give a standup before
# you report the incident it turned up.
CANDO_TIERS = [
    "cando-eng-1",   # I can give a standup update
    "cando-eng-2",   # I can report an incident
    "cando-eng-3",   # I can explain a system
    "cando-eng-4",   # I can run a technical demo
    "cando-eng-5",   # I can plan a task
    "cando-eng-6",   # I can clarify a requirement
    "cando-1",       # I can introduce myself
    "cando-2",       # I can buy things at a shop
    "cando-3",       # I can order at a restaurant
    "cando-4",       # I can ask for directions
    "cando-5",       # I can buy a ticket and take the train
    "cando-6",       # I can describe pain to a doctor
    "cando-7",       # I can buy medicine at a pharmacy
    "cando-8",       # I can ask for help in an emergency
    "cando-9",       # I can make an appointment by phone
    "cando-10",      # I can register my address at city hall
    "cando-11",      # I can ask someone to repeat or slow down
    "cando-12",      # I can greet my neighbors
    "cando-13",      # I can make small talk about the weather
    "cando-14",      # I can understand and say prices in yen
    "cando-15",      # I can tell the time
]

# Expression categories, whole, to the can-do that needs them. A category absent
# here has no can-do it plausibly serves and is left out of the deck.
CATEGORY_TIERS = {
    "cat-115": "cando-eng-1",   # Circumlocutions: What we do
    "cat-117": "cando-eng-1",   # Circumlocutions: People and time
    "cat-114": "cando-eng-2",   # Circumlocutions: How it behaves
    "cat-118": "cando-eng-2",   # Circumlocutions: Talking about a problem
    "cat-122": "cando-eng-2",   # Engineering loanwords: Operations and incidents
    "cat-116": "cando-eng-3",   # Circumlocutions: Where it is
    "cat-120": "cando-eng-3",   # Engineering loanwords: Code and structure
    "cat-125": "cando-eng-3",   # Loan words: Technology & Media
    "cat-121": "cando-eng-4",   # Engineering loanwords: Build and delivery
    "cat-123": "cando-eng-5",   # Engineering loanwords: Planning and teamwork
    "cat-88": "cando-eng-6",    # Loan words: Work & School
    "cat-53": "cando-1",        # People & Relationships
    "cat-85": "cando-2",        # Loan words: Shopping
    "cat-86": "cando-2",        # Loan words: Daily Objects
    "cat-59": "cando-3",        # Food & Drink
    "cat-84": "cando-3",        # Loan words: Food & Drink
    "cat-56": "cando-4",        # Places & Buildings
    "cat-57": "cando-5",        # Transport & Travel
    "cat-83": "cando-5",        # Loan words: Signs & Transport
    "cat-60": "cando-6",        # Body & Health
    "cat-87": "cando-7",        # Loan words: Health
    "cat-55": "cando-10",       # Society & Culture
    "cat-50": "cando-12",       # Daily Life & Routines
    "cat-58": "cando-13",       # Nature & Weather
    "cat-54": "cando-13",       # Emotions & Personality
    "cat-112": "cando-13",      # Loan words: Leisure & Sports
    "cat-52": "cando-14",       # Numbers & Counting
    "cat-61": "cando-15",       # Time Expressions
}

# cat-51 "Work & School" is the one category that splits: its work half serves
# all six work can-dos and its school half serves none of them. Keyed by the
# real Japanese word so the assignment survives a reworded paraphrase.
CAT51_TIERS = {
    "仕事": "cando-eng-1", "会議": "cando-eng-1", "報告": "cando-eng-1",
    "資料": "cando-eng-1", "同僚": "cando-eng-1", "上司": "cando-eng-1",
    "部下": "cando-eng-1", "残業": "cando-eng-1", "出張": "cando-eng-1",
    "問題": "cando-eng-2", "解決": "cando-eng-2", "失敗": "cando-eng-2",
    "結果": "cando-eng-2", "理由": "cando-eng-2", "責任": "cando-eng-2",
    "説明": "cando-eng-3", "方法": "cando-eng-3", "技術": "cando-eng-3",
    "能力": "cando-eng-3", "研究": "cando-eng-3", "実験": "cando-eng-3",
    "発表": "cando-eng-4", "評価": "cando-eng-4", "成功": "cando-eng-4",
    "成績": "cando-eng-4",
    "目標": "cando-eng-5", "課題": "cando-eng-5", "努力": "cando-eng-5",
    "規則": "cando-eng-5", "許可": "cando-eng-5", "契約": "cando-eng-5",
    "意見": "cando-eng-6", "議論": "cando-eng-6", "会社": "cando-eng-6",
    "社長": "cando-eng-6", "社員": "cando-eng-6", "部長": "cando-eng-6",
    "客": "cando-eng-6", "給料": "cando-eng-6",
}

COLUMNS = [
    "Sentence", "Translation", "Cloze", "Pronunciation", "Note",
    "Register", "KeyMeaning", "PitchAccent", "RealJapanese", "Produce",
]


# minihongo writes the honorific-prefixed 金 both ways: お金【かね】 four times
# and お金【おかね】 twelve. The second repeats the お inside the reading, so the
# ruby and the TTS both come out おおかね. Normalised here rather than upstream -
# the minihongo checkout is read-only input.
DOUBLED_PREFIX = [("お金【おかね】", "お金【かね】")]


def fix_source(pron: str) -> str:
    for wrong, right in DOUBLED_PREFIX:
        pron = pron.replace(wrong, right)
    return pron


def plain(text: str) -> str:
    """Drop the 【】 readings, leaving the sentence as it is written."""
    return FURIGANA.sub("", text)


def read(source: Path, name: str) -> list[dict[str, str]]:
    with open(source / "data" / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def register_of(sentence: str) -> str:
    """polite when the utterance carries a polite ending, else casual.

    Derived, not authored: minihongo marks no register, and every dialog line is
    one or the other. Vocabulary rows are not utterances and get no badge.
    """
    body = sentence.rstrip("。？！」")
    if re.search(r"(です|ます|ません|でした|ました|ください|ましょう)か?$", body):
        return "polite"
    return "casual"


def build_lexicon(words: list[dict], expressions: list[dict]) -> list[tuple[str, str]]:
    """Surfaces that may serve as a sentence's key word, longest first.

    A dialog line needs a Cloze that occurs in it (card 3 blanks it) and a
    KeyMeaning for it. Both come from minihongo's own glosses rather than a
    guess: the longest core word or expression the line contains wins.
    """
    lexicon: dict[str, str] = {}
    for row in expressions:
        surface = plain(row["minihongo"])
        if surface and row["english"]:
            lexicon.setdefault(surface, row["english"])
    for row in words:
        surface = plain(row["minihongo"])
        if surface and row["english"]:
            lexicon[surface] = row["english"]
    return sorted(lexicon.items(), key=lambda kv: -len(kv[0]))


def key_word(sentence: str, lexicon: list[tuple[str, str]],
             fallback: str) -> tuple[str, str]:
    for surface, meaning in lexicon:
        if surface in sentence:
            return surface, meaning
    # 歩いて行けますか is built entirely of inflected core verbs, so no listed
    # surface occurs in it whole. The line itself is then the key word.
    return sentence.rstrip("。？！"), fallback


def collect(source: Path) -> dict[str, list[dict[str, str]]]:
    candos = {r["id"]: r for r in read(source, "candos.csv")}
    groups = {r["id"]: r for r in read(source, "dialog_groups.csv")}
    dialogs = read(source, "dialogs.csv")
    expressions = read(source, "expressions.csv")
    lexicon = build_lexicon(read(source, "words.csv"), expressions)

    missing = set(CANDO_TIERS) - set(candos)
    if missing:
        sys.exit(f"candos.csv has no {', '.join(sorted(missing))}")

    tiers: dict[str, list[dict[str, str]]] = {c: [] for c in CANDO_TIERS}

    group_tier = {
        candos[cando]["dialog_group_id"]: cando
        for cando in CANDO_TIERS
        if candos[cando]["dialog_group_id"]
    }
    for row in dialogs:
        cando = group_tier.get(row["dialog_group_id"])
        if cando is None:
            continue
        pronunciation = fix_source(row["minihongo"])
        sentence = plain(pronunciation)
        cloze, meaning = key_word(sentence, lexicon, row["english"])
        tiers[cando].append({
            "Sentence": sentence,
            "Translation": row["english"],
            "Cloze": cloze,
            "Pronunciation": pronunciation,
            "Note": groups[row["dialog_group_id"]]["title_english"],
            "Register": register_of(sentence),
            "KeyMeaning": meaning,
            "PitchAccent": "",
            # Same idea in ordinary Japanese. Blank when the two agree, so the
            # back does not print the sentence twice.
            "RealJapanese": row["japanese"] if row["japanese"] != sentence else "",
        })

    categories = {r["id"]: r for r in read(source, "categories.csv")}
    for row in expressions:
        cando = CATEGORY_TIERS.get(row["category_id"])
        if cando is None and row["category_id"] == "cat-51":
            cando = CAT51_TIERS.get(row["japanese"])
        if cando is None:
            continue
        pronunciation = fix_source(row["minihongo"])
        sentence = plain(pronunciation)
        tiers[cando].append({
            "Sentence": sentence,
            "Translation": row["english"],
            "Cloze": sentence,
            "Pronunciation": pronunciation,
            "Note": categories[row["category_id"]]["name_english"],
            "Register": "",
            "KeyMeaning": row["english"],
            "PitchAccent": "",
            "RealJapanese": row["japanese"] if row["japanese"] != sentence else "",
        })

    return resolve_production(dedupe(tiers))


def dedupe(tiers: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    """One note per sentence, in the earliest tier that wants it.

    Note GUIDs are derived from the sentence, so a sentence appearing twice is
    one note with two homes - Anki keeps whichever import lands last and the
    tier sizes stop describing the deck. minihongo repeats a surface freely:
    テスト is both a delivery step and a school word, and いつからですか is both
    an incident dialog line and the phrase card that teaches it.
    """
    seen: set[str] = set()
    for cando in CANDO_TIERS:
        kept = []
        for row in tiers[cando]:
            # Ignoring the final mark: a dialog writes いつからですか。 and the
            # phrase card teaching it writes いつからですか, and two cards that
            # differ by one character are one card the learner sees twice.
            key = row["Sentence"].rstrip("。？！")
            if key in seen:
                continue
            seen.add(key)
            kept.append(row)
        tiers[cando] = kept
    return tiers


def head_word(sentence: str) -> str:
    """The sentence's last noun, per the UniDic tagger the other scripts use.

    Empty when the sentence has no noun, or when the noun is the whole sentence
    and blanking it would say no more than blanking the line.
    """
    nouns = [token.surface for token in tagger(sentence)
             if token.feature.pos1 == "名詞"]
    if not nouns or nouns[-1] == sentence:
        return ""
    return nouns[-1]


def resolve_production(
    tiers: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    """Mark which rows may be asked for production, and merge the rest away.

    The Production front is the English gloss and the category, and nothing
    else - by design, since anything Japanese on it would be the answer. Two
    rows sharing that pair therefore ask one question with two right answers,
    and a self-graded card whose grade is arbitrary corrupts the scheduling of
    both notes. minihongo produces such a pair whenever a category carries both
    a core-word paraphrase and the loanword it paraphrases: 黒い飲み物 and
    コーヒー are both "coffee" under Food & Drink.

    The paraphrase is the production target - it is the construction from the
    231-word core set - and the loanword belongs on the recognition side, so it
    keeps its Listening, Reading and Vocabulary cards and loses only the fourth.
    Its surface moves onto the survivor's RealJapanese, which is why ランチ,
    フルーツ and ミルク are still met by a learner who is never asked to produce
    them. Derived rather than listed: the next such pair is marked without a
    code change.

    The Vocabulary front collides for the same reason and needs its own answer:
    a paraphrase row's cloze is the whole paraphrase, so blanking it leaves a
    bare ＿＿＿ beside the same gloss the loanword row blanks to. The survivor
    is given its head word as the cloze instead, which leaves 黒い＿＿＿ against
    コーヒー's ＿＿＿. Only the cloze moves: PitchAccent and KeyMeaning still
    describe the whole paraphrase, and 食べ物 does not mean "bread".
    """
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for cando in CANDO_TIERS:
        for row in tiers[cando]:
            row["Produce"] = "y"
            groups.setdefault((row["Translation"], row["Note"]), []).append(row)

    for rows in groups.values():
        if len(rows) == 1:
            continue
        winner = next((r for r in rows if r["RealJapanese"]), rows[0])
        real = [winner["RealJapanese"]] if winner["RealJapanese"] else []
        for row in rows:
            if row is winner:
                continue
            row["Produce"] = ""
            if row["Sentence"] not in real:
                real.append(row["Sentence"])
        winner["RealJapanese"] = "、".join(real)
        head = head_word(winner["Sentence"])
        if head:
            winner["Cloze"] = head
    return tiers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=Path.home() / "Code" / "minihongo",
                        help="minihongo checkout (read-only)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report tier sizes without writing")
    args = parser.parse_args()

    if not (args.source / "data" / "candos.csv").exists():
        sys.exit(f"No minihongo data under {args.source}")

    tiers = collect(args.source)
    out_dir = DECKS_DIR / SLUG
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for number, cando in enumerate(CANDO_TIERS, start=1):
        rows = tiers[cando]
        total += len(rows)
        print(f"  tier {number:2}  {cando:12} {len(rows):4} rows")
        if args.dry_run:
            continue
        with open(out_dir / f"tier{number}-vocabulary.csv", "w", encoding="utf-8",
                  newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    print(f"\n{len(CANDO_TIERS)} tiers, {total} rows")


if __name__ == "__main__":
    main()
