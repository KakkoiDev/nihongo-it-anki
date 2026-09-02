# minihongo-speak: what feeds which tier

Generated deck. `scripts/import_minihongo_speak.py` builds every
`tier*-vocabulary.csv` here from a read-only checkout of
[minihongo](https://github.com/KakkoiDev/minihongo); nothing in them is authored
in this repo. Re-run it, then `generate_pitch_accent.py`, after any change
upstream.

## Why the tiers are can-dos

`data/candos.csv` is minihongo's own goal list, and each can-do names the dialog
group that teaches it. Word frequency would order the deck by what is common;
the can-dos order it by what the learner is trying to do, which is the only
ordering a production deck can defend. The six work can-dos come first.

## Why a tier is not only sentences

`data/expressions.csv` is a lexicon, not a sentence corpus - 5 of its 1111 rows
end in a finite verb. Tiering only on it would give no sentences at all; tiering
only on `data/dialogs.csv` would give the six work can-dos 4 cards each. So a
tier opens with the dialog lines for its can-do, which are whole utterances, and
continues with the expression categories those lines are built from.

An expression category is assigned whole to one can-do, or left out. Categories
with no can-do to serve - the 231 core words, animals, nature, the not-in-base
verb and adjective lists, false friends - are comprehension material and stay
out of this deck. `cat-51 Work & School` is the single exception: its work half
is split across the six work can-dos by meaning and its school half is dropped.

A sentence appears once, in the earliest tier that wants it. minihongo repeats a
surface freely across categories.

## Derived, not copied

Four values are computed rather than taken from a column, because minihongo has
no column for them:

- **Register** - `polite` when the utterance ends in a polite form, else
  `casual`. Vocabulary rows are not utterances and carry no badge.
- **Cloze / KeyMeaning** - the longest core word or expression the line
  contains, with minihongo's own gloss for it. A vocabulary row is its own
  cloze, except where that would make its blanked front identical to another
  row's: the row that keeps the Production front takes its last noun as the
  cloze instead, so 黒い飲み物 blanks to 黒い＿＿＿ rather than to ＿＿＿.
  KeyMeaning and PitchAccent stay on the whole paraphrase - 食べ物 does not
  mean "bread", and the compound heads have no gloss in minihongo to copy.
- **RealJapanese** - the row's `japanese` column, blank when it already equals
  the sentence, so the back never prints the same string twice.
- **Produce** - set on every row except one whose Production front, the
  `(Translation, Note)` pair, another row already claims. minihongo pairs a
  core-word paraphrase with the loanword it paraphrases eight times in Food &
  Drink - 黒い飲み物 and コーヒー are both "coffee" - and the Production front
  carries no Japanese to tell them apart. The paraphrase wins the flag, being
  the core-set construction the deck exists to drill; the loanword keeps its
  three recognition cards and its surface is appended to the paraphrase's
  RealJapanese, which is where ランチ, フルーツ and ミルク still live.

One value is corrected: minihongo writes `お金【おかね】` twelve times and
`お金【かね】` four, and the first repeats the honorific inside the reading, so
both the ruby and the TTS come out おおかね. Normalised on import.

## A known redundancy

On a vocabulary row the cloze is the whole paraphrase, because a minihongo
paraphrase is compositional and any sub-word chosen as the key would be an
invented one. Card 3 therefore blanks the entire sentence, which makes it ask
almost what card 4 asks: English in, Japanese out. Left as it is rather than
fixed with a heuristic - the alternative is guessing at a head word, and the
duplicate is at least a correct card. Dialog rows are unaffected; their cloze is
a single core word, and so is the cloze of the eight paraphrases that had to be
told apart from a loanword sharing their gloss.

## Tier sources

| Tier | Can-do | Dialog group | Expression categories |
|------|--------|--------------|-----------------------|
| 1 | I can give a standup update | Daily Standup (4) | What we do (5), People and time (5), Work & School, part (9) |
| 2 | I can report an incident | Incident Report (4) | How it behaves (5), Talking about a problem (5), Operations and incidents (5), Work & School, part (6) |
| 3 | I can explain a system | System Explanation (4) | Where it is (5), Code and structure (5), Technology & Media (11), Work & School, part (6) |
| 4 | I can run a technical demo | Technical Demo (4) | Build and delivery (5), Work & School, part (4) |
| 5 | I can plan a task | Task Planning (4) | Planning and teamwork (5), Work & School, part (6) |
| 6 | I can clarify a requirement | Requirement Clarification (4) | Work & School (15), Work & School, part (8) |
| 7 | I can introduce myself | Introducing Yourself (7) | People & Relationships (50) |
| 8 | I can buy things at a shop | At the Convenience Store (9) | Shopping (7), Daily Objects (30) |
| 9 | I can order at a restaurant | At a Restaurant (9) | Food & Drink (44), Food & Drink (36) |
| 10 | I can ask for directions | Asking for Directions (9) | Places & Buildings (49) |
| 11 | I can buy a ticket and take the train | At the Train Station (8) | Transport & Travel (39), Signs & Transport (18) |
| 12 | I can describe pain to a doctor | At the Doctor (9) | Body & Health (46) |
| 13 | I can buy medicine at a pharmacy | At the Pharmacy (8) | Health (5) |
| 14 | I can ask for help in an emergency | Emergency - Asking for Help (8) | - |
| 15 | I can make an appointment by phone | Making a Phone Appointment (6) | - |
| 16 | I can register my address at city hall | At City Hall (9) | Society & Culture (50) |
| 17 | I can ask someone to repeat or slow down | Asking Someone to Repeat (7) | - |
| 18 | I can greet my neighbors | The Neighbor (8) | Daily Life & Routines (58) |
| 19 | I can make small talk about the weather | Weather Small Talk (7) | Leisure & Sports (13), Emotions & Personality (49), Nature & Weather (40) |
| 20 | I can understand and say prices in yen | - | Numbers & Counting (23) |
| 21 | I can tell the time | - | Time Expressions (45) |

Counts are source rows before de-duplication, so a tier's CSV can be shorter
than the numbers above add up to. `[tiers.sizes]` in `deck.toml` is what the
CSVs actually hold.
