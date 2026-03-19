# Nihongo IT Anki - World Class Deck Improvements

## Goal
Make this deck the best resource for IT professionals working in Japanese: daily colleague communication, code reviews, standups, presentations, and job interviews.

Reference reports: REPORT-CARD-ARCHITECTURE.md, REPORT-CONJUGATIONS.md, REPORT-VOCABULARY-GAPS.md

---

## Phase 1 - Card Architecture Redesign
**Replaces the broken Card B. Highest immediate impact.**

### 1.1 Split Card A into Listening + Reading cards
- [ ] Rename current "Comprehension" template to "Listening"
- [ ] Remove `{{Sentence}}` text from Listening card front (audio only + category tag)
- [ ] Add new "Reading" template:
  - Front: `{{Sentence}}` text + category tag (no audio)
  - Back: furigana + English translation + key vocab highlight + conjugations
- [ ] Verify both templates render correctly in Anki preview
- [ ] Update card count documentation (was 2 cards/note → now 3)

**Acceptance:** Front of Listening card plays audio and shows nothing else. Reading card front shows Japanese text only.

### 1.2 Replace Card B with Vocabulary Cloze
- [ ] Rename current "Production" template to "Cloze"
- [ ] Implement JS blanking on front: replace `{{Cloze}}` word in `{{Sentence}}` with `＿＿＿`
- [ ] Show `{{Translation}}` as context hint on front (below the blanked sentence)
- [ ] Remove "How do you say this in Japanese?" prompt
- [ ] Remove the 2-char hint (`{{Hint}}` field)
- [ ] Back: full `{{Sentence}}` with `{{Cloze}}` highlighted in blue + audio plays + furigana + conjugations
- [ ] Add `.blank` CSS class (underline, fixed width)
- [ ] Add `.cloze-answer` CSS class (blue, bold) for the highlighted word on back

**Acceptance:** Front shows Japanese sentence with one word replaced by a blank, plus English translation. Back reveals the word highlighted in blue with audio.

Implementation note - JS for front template:
```javascript
var sentence = document.getElementById('sentence').textContent;
var cloze = '{{Cloze}}';
document.getElementById('sentence').innerHTML =
  sentence.split(cloze).join('<span class="blank">＿＿＿</span>');
```

### 1.3 Fix hint field
- [ ] Change `{{Hint}}` field in `create_deck.py` to use `{{KeyMeaning}}` instead of first 2 chars of sentence
- [ ] Remove `hint` field generation from `create_deck.py` (line ~309)
- [ ] Verify no card template references the old hint format

### 1.4 Add Keigo drill card (verbs only)
- [ ] Add "Keigo" template to model in `create_deck.py`
  - Front: English situation + "Your action (humble):" prompt
  - Back: Humble form + Respectful form + example sentence in formal register
- [ ] Suppress card generation for notes where `{{Conjugations}}` is empty (nouns/adjectives)
- [ ] Use Anki conditional rendering: `{{#Conjugations}}...{{/Conjugations}}`

**Acceptance:** Keigo cards only appear for entries that have a conjugation table. Front shows humble/respectful prompt, back shows both keigo forms.

---

## Phase 2 - Conjugation Table Redesign
**Reference: REPORT-CONJUGATIONS.md**

### 2.1 Trim and reorder forms in generate_conjugations.py
- [ ] Remove from all verb types: Causative, Caus-Pass, Conditional ば, Imperative, たい
- [ ] Replace `'Negative ない形'` → `'Polite Negative ません形'` (with correct form)
- [ ] Replace `'Past た形'` → `'Polite Past ました形'` (with correct form)

Changes per verb type:
- する verbs: ません = `{stem}しません`, ました = `{stem}しました`
- 五段 verbs: ません = `{stem}{i}ません`, ました = `{stem}{ta}+ました` (use た→ました)
- 一段 verbs: ません = `{stem}ません`, ました = `{stem}ました`

### 2.2 Add ている progressive form (critical missing form)
- [ ] Add `'Progressive ている形'` to `'basic'` section of all verb types:
  - する verbs: `f'{stem}しています'`
  - 五段 verbs: `f'{stem}{e["te"]}います'`
  - 一段 verbs: `f'{stem}ています'`
  - くる verb: `'来ています'`
- [ ] Verify: 完了する → 完了しています, 取り組む → 取り組んでいます

### 2.3 Add て形 compound reference
- [ ] Add a compact HTML reference block below the conjugation table in `generate_conjugation_html()`
- [ ] Show only for verb types (skip i-adj, na-adj)
- [ ] Compounds to include:

| Pattern | Meaning |
|---------|---------|
| ～てください | Please do (request) |
| ～ています | Ongoing / resultant state |
| ～ておく | Do in advance |
| ～ていただく | Receive the favor of (humble request) |
| ～てしまう | Completed (sometimes regrettable) |
| ～てもらう | Have someone do |

- [ ] Use collapsed `<details>` for the compound reference to avoid visual overload
- [ ] CSS: style differently from main conjugation table (lighter background)

### 2.4 Show conjugations on Cloze card back
- [ ] Add `{{Conjugations}}` to the back template of the Cloze card
- [ ] Wrap in conditional: `{{#Conjugations}}...{{/Conjugations}}`
- [ ] Verify it renders identically to how it appears on Reading card back

### 2.5 Regenerate all CSV conjugations
- [ ] Run `uv run python scripts/generate_conjugations.py`
- [ ] Spot-check tier 1: 完了する, 取り組む, 更新する
- [ ] Spot-check tier 4: キャッシュする, マウントする, ログアウトする
- [ ] Verify ている form appears correctly for godan verbs (音便 forms)

---

## Phase 3 - New Vocabulary Tiers
**Reference: REPORT-VOCABULARY-GAPS.md**

### 3.1 Job Interview tier (Tier 7)
- [ ] Create `tier7-vocabulary.csv` with headers matching existing tiers
- [ ] Generate ~30 sentences covering:
  - Self-introduction (専門、経験年数、担当業務)
  - Technical skills (得意、扱える、経験がある)
  - Past achievements (設計・実装、改善、リード)
  - Motivation and fit (興味、貢献、魅力)
  - Behavioral questions (課題に直面した、解決した経緯)
  - Questions for interviewer (教えていただけますか、よろしいでしょうか)
  - Handling difficulty (少し考えさせてください、確認ですが)
- [ ] All sentences at **keigo level** (いたします、でございます、〜いただく)
- [ ] Note field format: `Interview - {subcategory}` (e.g., `Interview - Self-Introduction`)
- [ ] Generate furigana for Pronunciation field
- [ ] Generate conjugations
- [ ] Generate audio: `uv run python scripts/generate_audio.py --tier 7`
- [ ] Build deck: `uv run python scripts/create_deck.py --tier 7`

### 3.2 Problem-Solving Discussion tier (Tier 8)
- [ ] Create `tier8-vocabulary.csv`
- [ ] Generate ~30 sentences covering:
  - Investigation (調査しています、ログを確認したところ)
  - Hypothesis (原因の可能性があります、考えられます)
  - Proposing solutions (対応できると思います、試してみましょう)
  - Tradeoff discussion (メリット・デメリット、リスクがあります)
  - Decision and alignment (方針を決めましょう、進めてよいですか)
  - Post-mortem language (再発防止、教訓、アラートを追加)
- [ ] Register: polite ます level with occasional humble forms for decision contexts
- [ ] Note field format: `Problem-Solving - {subcategory}`
- [ ] Generate furigana, conjugations, audio, deck

### 3.3 Presentation language augmentation
- [ ] Identify existing Presentation category sentences in tier CSVs
- [ ] Add ~15 sentences to an appropriate existing tier (or new tier) covering:
  - Formal opening (本日は〜についてご説明いたします)
  - Time allocation (〜分ほどお時間をいただきます)
  - Question handling (ご質問は最後にお受けします)
  - Data references (データが示すように、この結果から言えることは)
  - Closing (以上で私のプレゼンを終わります、ありがとうございました)
- [ ] All at formal keigo register
- [ ] Note field format: `Presentation - Formal`

---

## Phase 4 - Register Indicators
**Low effort, medium impact. Helps learners know when to use each sentence.**

### 4.1 Design register tag system
- [ ] Define register levels:
  - `casual` - close colleagues, Slack DMs
  - `polite` - standard work communication, standups, PR comments
  - `formal` - meetings with seniors, email to manager
  - `keigo` - presentations, client meetings, interviews
- [ ] Decide display: small badge on card front near category tag

### 4.2 Add register field to CSVs
- [ ] Add `Register` column to all tier CSV headers
- [ ] Write script to auto-classify based on sentence content:
  - Sentences containing いたします、でございます、〜いただく → keigo
  - Sentences containing ます/ません but no keigo markers → polite
  - Sentences containing casual ない/だ/よ → casual
  - Everything else → polite (safe default)
- [ ] Manual review pass on auto-classified rows (edge cases)

### 4.3 Display register badge on cards
- [ ] Add `{{Register}}` field to model in `create_deck.py`
- [ ] Add register badge HTML to card templates (front of Listening and Reading cards)
- [ ] CSS: color-coded badge (gray=casual, blue=polite, orange=formal, purple=keigo)
- [ ] Wrap in conditional: `{{#Register}}...{{/Register}}`

---

## Phase 5 - Pitch Accent (Backlog)
**Requires data pipeline before any display work. Do not start until Phase 1-2 are complete.**

### 5.1 Generate pitch accent data
- [ ] Research: check if `fugashi` with UniDic provides `aType` (accent type) for vocabulary words
- [ ] Test on sample words: 完了、問題、確認、バグ、エラー
- [ ] If UniDic data is insufficient, evaluate accent dictionary options:
  - OJAD (Online Japanese Accent Dictionary)
  - JMdict pitch accent extensions
  - suzuki-kun API
- [ ] Write `scripts/generate_pitch_accent.py`:
  - Input: Cloze word from each CSV row
  - Output: pitch pattern as mora-level H/L string (e.g., `LHHH` for 完了 if flat type 0)
  - Stores result in new `PitchAccent` CSV column

### 5.2 Modify to_ruby_html() to support pitch coloring
- [ ] Add optional `pitch` parameter to `to_ruby_html()` in `create_deck.py`
- [ ] Write mora splitter function (handles digraphs ゃゅょ etc., long vowel ー, っ)
- [ ] When pitch data present: split `<rt>` content into per-mora `<span>` elements
- [ ] CSS:
  ```css
  .pitch-h { color: #4caf50; }  /* green = high */
  .pitch-l { color: #f44336; }  /* red = low */
  /* no class = flat word, stays default gray */
  ```
- [ ] Apply only to Cloze word furigana (not full sentence pronunciation - too noisy)

### 5.3 Integrate into deck generation
- [ ] Pass `PitchAccent` field value when calling `to_ruby_html()` for Cloze word display
- [ ] Verify rendering on mobile Anki (small rt text, color distinction must be readable)
- [ ] Add `PitchAccent` field to genanki model

---

## Phase 6 - Audio Regeneration
**After all CSV and template changes are finalized.**

- [ ] Regenerate tiers 1-5 audio with `--force` to replace old files generated with TTSPronunciation field
  - Run: `uv run python scripts/generate_audio.py --tier N --force` for N in 1..5
- [ ] Verify sample sentences: 5分間、キャッシュミス時、更新時
- [ ] Verify numbers are audible: 80%、500ms、v2.0.0
- [ ] Verify K8s → クバネティス, a11y → アクセシビリティ
- [x] Generate audio for new tier 6 Presentation sentences (101-115)
- [x] Generate audio for tier 7 (Job Interview, 30 files)
- [x] Generate audio for tier 8 (Problem-Solving, 30 files)

---

## Phase 7 - Rebuild and Release

- [ ] Run `generate_conjugations.py` (after Phase 2 changes)
- [ ] Run `create_deck.py --all` (after Phase 1 template changes)
- [ ] Run `create_deck.py --combined`
- [ ] Import into Anki and review all 3 card types for each of tiers 1-8
- [ ] Check mobile rendering (iOS/Android Anki)
- [ ] Update README with new card architecture description
- [ ] Update ANKIWEB-README with new tier list
- [ ] Version bump: v2.0.0 (major - card model change, existing progress will reset)

---

## Dependency graph

```
Phase 2.1-2.4 (conjugation code)
    ↓
Phase 1.1-1.4 (card templates) ← Phase 2.4 (conjugations on cloze)
    ↓
Phase 3.1-3.3 (new vocabulary) ← depends on card templates being finalized
    ↓
Phase 4 (register indicators) ← can run in parallel with Phase 3
    ↓
Phase 6 (audio regen) ← depends on CSV finalization
    ↓
Phase 7 (rebuild + release)

Phase 5 (pitch accent) ← BACKLOG, independent, starts after Phase 1-2 complete
```

---

## Summary

| Phase | Description | Effort | Impact |
|-------|-------------|--------|--------|
| 1 | Card architecture (Listening / Reading / Cloze / Keigo) | Medium | Critical |
| 2 | Conjugation table (add ている, trim dead forms, te-compounds) | Medium | High |
| 3 | New vocabulary (Interview, Problem-Solving, Presentation) | High | High |
| 4 | Register indicators | Low | Medium |
| 5 | Pitch accent with green/red furigana coloring | High | Medium |
| 6 | Audio regeneration | Low | High |
| 7 | Rebuild and release | Low | - |

**Estimated total new cards after completion:** ~3800 (from current ~2000)
- 1000 existing sentences × 3 cards = 3000
- ~300 new sentences (tiers 7+8+presentation) × 3 = 900
- ~700 keigo drill cards (verbs only)
- Total: ~4600 cards
