# AnkiWeb Share Deck Submission

## Title
```
Japanese IT/Software Engineering Vocabulary With Audio
```

## Tags
```
japanese jlpt vocab sentences audio it software programming keigo interview pitch-accent
```

## Support Page
```
https://github.com/KakkoiDev/nihongo-it-anki/issues/new/choose
```

## Description

```markdown
<img src="https://raw.githubusercontent.com/KakkoiDev/nihongo-it-anki/refs/heads/master/demo.png" width="600">

**1075 IT vocabulary sentences** with AI-generated Japanese audio, furigana with pitch accent coloring, and 3 card types designed for real workplace skill building. Fully open source.

## Who Is This For?

- Software engineers working with Japanese teams
- Developers preparing for jobs at Japanese tech companies
- Anyone learning technical Japanese for IT industry
- Engineers who need keigo for presentations, interviews, and client meetings

## Card Types

Every sentence generates 3 cards, each targeting a different skill:

- **Listening** - Front plays audio with no text visible. You hear the sentence and must understand it before flipping. Trains for meetings, standups, and pair programming where you hear Japanese before you read it.
- **Reading** - Front shows raw Japanese text with no furigana and no audio. You read and parse the sentence yourself. Trains for Slack messages, pull requests, and documentation.
- **Vocabulary** - Front shows the sentence with one key word blanked out, plus the English translation as context. You identify the missing word. Builds vocabulary one word at a time instead of testing full sentence recall.

## Features

- **Pitch Accent** - Green (high) / red (low) coloring on key word furigana. Learn correct Tokyo accent from the start.
- **Register Badges** - Each card shows polite/keigo badge so you know when to use each sentence.
- **Furigana** - Ruby text readings for all kanji on answer cards.
- **100% Audio** - Neural TTS for every sentence (Microsoft Edge ja-JP-KeitaNeural).
- **Dark Mode** - Automatic system theme detection.
- **Open Source** - <a href="https://github.com/KakkoiDev/nihongo-it-anki">Build your own deck with the same tools</a>

## 8 Tiers

- **Tier 1** (150 sentences) - Daily essentials, git, basic actions
- **Tier 2** (200 sentences) - Agile, APIs, databases, testing
- **Tier 3** (250 sentences) - Code review, architecture, AWS
- **Tier 4** (200 sentences) - Security, debugging, documentation
- **Tier 5** (100 sentences) - Communication, soft skills
- **Tier 6** (115 sentences) - Presentations (including formal keigo openings/closings)
- **Tier 7** (30 sentences) - Job interview (full keigo register: self-intro, skills, achievements, motivation, questions)
- **Tier 8** (30 sentences) - Problem-solving discussions (investigation, hypothesis, tradeoffs, post-mortem)

## Example Sentences

**Tier 1 - Daily Essentials:**
> 機能は完了しレビュー準備ができました。
> *The feature is done and ready for review.*

**Tier 7 - Job Interview (keigo):**
> 御社の技術スタックと私のスキルが合致しており即戦力として貢献できると考えております。
> *My skills align with your tech stack and I believe I can contribute immediately.*

**Tier 8 - Problem Solving:**
> メモリリークが発生していると考えられます。
> *It is thought that a memory leak is occurring.*

**Total: 1075 notes / 3225 cards / 1075 audio files**

## For Existing Users

If you are upgrading from a previous version, please read this section.

### What Changed in v3.3

v3.3 is a complete overhaul from the original Kokoro TTS release. The card architecture, audio engine, and teaching methodology all changed.

- **Audio engine**: Switched from Kokoro TTS to Microsoft Edge TTS (KeitaNeural). Significantly more natural prosody and pronunciation.
- **Teaching method**: Cards now train listening comprehension first. The Listening card plays audio with no text on the front, forcing you to understand what was said before seeing the answer.
- **3 focused card types**: Listening, Reading, and Vocabulary Cloze replace the previous card layout.
- **Pitch accent**: Green/red furigana coloring shows Tokyo pitch accent patterns on key vocabulary.
- **Register badges**: Each card shows its formality level (polite/keigo) so you know when to use each expression.
- **New tiers**: Tier 7 (Job Interview, 30 keigo sentences) and Tier 8 (Problem-Solving Discussion, 30 sentences).
- **15 formal presentation sentences** added to Tier 6.

### Upgrading Notes

Installing this version will replace the old deck and **scheduling progress will reset**.

**Why it resets:** The note type changed entirely - different card templates, different fields, different model. Anki cannot map old scheduling data to the new cards.

**What to do:** The new audio-first approach means even sentences you knew before will challenge you differently. Starting fresh is recommended. If you want to skip tiers you already mastered, install the deck, then browse by tier and suspend those cards.

## Changelog

**v3.3** (Apr 2026)
- Complete overhaul from original release
- Switched from Kokoro TTS to Microsoft Edge TTS for significantly better audio
- New audio-first teaching methodology: Listening cards play audio with no text
- Streamlined to 3 card types: Listening, Reading, Vocabulary Cloze
- Pitch accent display with green/red furigana coloring
- Register badges (polite/keigo) on card fronts
- New Tier 7: Job Interview (30 keigo sentences)
- New Tier 8: Problem-Solving Discussion (30 sentences)
- 15 formal presentation sentences added to Tier 6
- Full audio regeneration with improved pronunciation pipeline

**v1.1.0** (Jan 2026)
- Initial public release (Kokoro TTS)

If you find this useful, please rate and comment!
```
