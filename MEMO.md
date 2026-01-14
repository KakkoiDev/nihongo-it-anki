# Japanese Software Engineering Vocabulary Project

## Project Overview

Language learning resource for American software engineer learning Japanese workplace vocabulary. Created 1000-word master list with tiered organization and CSV exports for spaced repetition app import.

**Date Created**: 2025-12-01
**Learning Direction**: English → Japanese (user is native English speaker)
**Target Context**: American tech workplace with Japanese colleagues

## File Structure

```
japanese-software-engineering/
├── software-engineering-vocabulary-1000.md  (Master vocabulary)
├── tier1-vocabulary.csv  (Words 1-150)
├── tier2-vocabulary.csv  (Words 151-350)
├── tier3-vocabulary.csv  (Words 351-600)
├── tier4-vocabulary.csv  (Words 601-800)
├── tier5-vocabulary.csv  (Words 801-900)
├── tier6-vocabulary.csv  (Words 901-1000)
└── MEMO.md  (This file)
```

## Master Vocabulary File

**Path**: `/home/kakkoidev/Chat/japanese-software-engineering/software-engineering-vocabulary-1000.md`

### Organizational Structure

**6 Tiers by Frequency**:
- **Tier 1** (1-150): Daily essentials - communication, git, code actions, bugs/errors
- **Tier 2** (151-350): Project management, API/network, database, testing
- **Tier 3** (351-600): Code review, architecture/design, DevOps, AWS
- **Tier 4** (601-800): Caching/storage, security, frontend, backend, data processing
- **Tier 5** (801-900): Meetings/discussions, email/Slack communication
- **Tier 6** (901-1000): Presentations, career/professional vocabulary

### Format

Markdown tables with columns:
- **#**: Word number (1-1000)
- **Word**: English vocabulary term
- **日本語**: Japanese translation
- **Example Sentence**: English sentence demonstrating usage in tech context

## CSV Export Files

### Purpose
Formatted for import into spaced repetition language learning apps (Anki, Mochi, etc.) using cloze deletion method.

### CSV Format Specification

**5 Columns**:
1. **Sentence**: Japanese sentence (learning language)
2. **Translation**: English translation (native language)
3. **Cloze**: Japanese word to be blanked out in learning app
4. **Pronunciation**: Full Japanese sentence with furigana readings
5. **Note**: Category label for organization

### Column Details

**Sentence Column**:
- Full Japanese sentence with kanji
- Natural workplace context
- Example: `機能は完了しレビュー準備ができました。`

**Translation Column**:
- English equivalent
- Matches master vocabulary example sentences
- Example: `The feature is done and ready for review.`

**Cloze Column**:
- Target vocabulary word in Japanese
- Word to be hidden/blanked in study app
- Example: `完了` (the word being learned)

**Pronunciation Column**:
- Full Japanese sentence with furigana
- Readings in 【】brackets after kanji
- Format: `機能【きのう】は完了【かんりょう】しレビュー準備【じゅんび】ができました。`
- Helps learners read unfamiliar kanji

**Note Column**:
- Category/context label
- Examples: "Status - completed", "Git workflow", "Code review", "Security"
- Helps organize cards in learning app

### CSV File Breakdown

**tier1-vocabulary.csv** (150 words):
- Daily communication basics
- Git commands
- Status updates
- Bug/error terminology
- Most frequently used workplace phrases

**tier2-vocabulary.csv** (200 words):
- Project management vocabulary
- API and networking terms
- Database operations
- Testing terminology

**tier3-vocabulary.csv** (250 words):
- Code review feedback
- Architecture and design patterns
- DevOps terminology
- AWS cloud services

**tier4-vocabulary.csv** (200 words):
- Caching and storage
- Security concepts
- Frontend frameworks
- Backend services
- Data processing

**tier5-vocabulary.csv** (100 words):
- Meeting discussions
- Email and Slack communication
- Team collaboration phrases

**tier6-vocabulary.csv** (100 words):
- Presentation vocabulary
- Career development terms
- Professional advancement phrases

## Critical Learning Direction Insight

**Initial Error**: First CSV generation had language direction reversed (Japanese → English)

**Correction**: User is learning Japanese, so:
- ✅ **Sentence**: Japanese (target language)
- ✅ **Translation**: English (native language)
- ✅ **Cloze**: Japanese word (what's being learned)
- ✅ **Pronunciation**: Japanese with furigana

**Pattern for Similar Projects**:
Always confirm learning direction before generating language learning materials:
- "Learning X" = X is target language (goes in Sentence field)
- Native language = goes in Translation field
- Cloze deletion = target language vocabulary item

## Furigana Format Pattern

**Consistent Format**: `漢字【reading】`
- Bracket type: Japanese corner brackets 【】
- Placement: Immediately after kanji
- Style: Hiragana reading only

**Examples**:
- `機能【きのう】` = function/feature
- `完了【かんりょう】` = completion
- `問題【もんだい】` = problem/issue

**Complex Compounds**: Each kanji compound gets one reading
- `取【と】り組【く】む` = to work on (okurigana included)
- Not: `取り組む【とりくむ】`

## Vocabulary Organization Strategy

### Frequency-Based Tiering

Words organized by actual workplace usage frequency, not alphabetically or by topic.

**Tier 1 Priority**: Words used multiple times daily
- "done", "working on", "blocked", "update"
- Git basics: "commit", "push", "pull", "merge"
- Common responses: "thanks", "got it", "sounds good"

**Why This Works**:
- Learn highest-ROI vocabulary first
- Functional in workplace within days (Tier 1)
- Deep technical fluency over months (Tiers 1-4)
- Professional polish with Tiers 5-6

### Topic Clustering Within Tiers

Related vocabulary grouped together:
- Git workflow terms consecutive
- Status update phrases grouped
- Review feedback terminology clustered

**Benefit**: Contextual learning reinforcement

## Example CSV Entry Breakdown

```csv
機能は完了しレビュー準備ができました。,The feature is done and ready for review.,完了,機能【きのう】は完了【かんりょう】しレビュー準備【じゅんび】ができました。,Status - completed
```

**Field-by-Field**:
1. `機能は完了しレビュー準備ができました。` - Japanese sentence (what learner reads)
2. `The feature is done and ready for review.` - English meaning
3. `完了` - Target word to memorize (blanked out in app)
4. `機能【きのう】は完了【かんりょう】しレビュー準備【じゅんび】ができました。` - Pronunciation guide
5. `Status - completed` - Context category

## Import Recommendations

### Spaced Repetition Settings

**Recommended Schedule**:
- New cards: 20-30/day (sustainable pace)
- Review cards: No limit
- Start with Tier 1 only
- Add Tier 2 after 80% Tier 1 mastery

**Card Settings**:
- Learning steps: 1m 10m 1d
- Graduating interval: 4 days
- Easy interval: 7 days
- Cloze deletion mode

### Progressive Learning Path

1. **Week 1-2**: Tier 1 (1-150) - Daily workplace basics
2. **Week 3-4**: Tier 2 (151-350) - Technical depth
3. **Week 5-6**: Tier 3 (351-600) - Advanced tech topics
4. **Week 7-8**: Tier 4 (601-800) - Specialized domains
5. **Week 9**: Tier 5 (801-900) - Communication polish
6. **Week 10**: Tier 6 (901-1000) - Professional advancement

**Total Timeline**: 10 weeks to 1000-word fluency at 30 cards/day

## Transferable Patterns

### For Similar Vocabulary Projects

**Preparation Questions**:
1. What is the learner's native language?
2. What language are they learning?
3. What specific context? (workplace, medical, legal, etc.)
4. What learning app format? (Anki, Mochi, Quizlet, etc.)
5. Frequency-based or topic-based organization?

**CSV Format Best Practices**:
- Always confirm target/native language direction
- Include pronunciation guides for non-phonetic scripts
- Use cloze deletion for active recall
- Add category labels for organization
- Keep sentences practical and contextual

**Organizational Strategy**:
- Frequency beats alphabetical for usability
- Cluster related terms within frequency tiers
- Break into digestible chunks (150-250 words/file)
- Tier 1 should enable basic function ASAP

### Cloze Deletion Principles

**Target Selection**: Choose the most important word in sentence
- ✅ `機能は{{完了}}しレビュー準備ができました。` - Focuses on "completion"
- ❌ `{{機能}}は完了しレビュー準備ができました。` - Less useful (too specific)

**Sentence Quality**:
- Natural workplace usage
- Single clear context
- Target word is core meaning
- 10-20 words optimal length

## Technical Implementation Notes

### Character Encoding
- UTF-8 required for Japanese characters
- CSV files properly encoded
- Furigana brackets: 【】 (U+3010, U+3011)

### File Size Metrics
- Tier 1: 150 entries, ~15KB
- Tier 2: 200 entries, ~20KB
- Tier 3: 250 entries, ~25KB
- Tier 4: 200 entries, ~20KB
- Tier 5: 100 entries, ~10KB
- Tier 6: 100 entries, ~10KB
- Master file: ~200KB with formatting

## Future Enhancements

### Potential Additions
- Audio pronunciation files
- Verb conjugation tables
- Politeness level variations (casual vs keigo)
- Company-specific jargon sections
- Meeting phrase deep-dive

### Expansion Strategies
- Tier 7: Industry-specific terminology (fintech, healthcare, gaming)
- Domain supplements: 100-word modules per framework (React, AWS, SQL)
- Conversation flow templates
- Email template phrases

## Project Completion Checklist

- [x] Master vocabulary file (1000 words)
- [x] Tier-based organization (6 tiers)
- [x] CSV exports (6 files)
- [x] Correct language direction (Japanese → English)
- [x] Furigana pronunciation guides
- [x] Category labels for organization
- [x] Workplace-contextual example sentences
- [x] Documentation for future reference

## Related Resources

### External Learning Tools
- **Anki**: Free spaced repetition app (desktop + mobile)
- **Mochi**: Modern spaced repetition (better UX than Anki)
- **WaniKani**: Kanji learning system (complementary resource)
- **Jisho.org**: Japanese dictionary for additional context

### Complementary Study
- Grammar foundations: Genki I textbook
- Kanji recognition: RTK or WaniKani
- Listening practice: Podcasts for software engineers in Japanese
- Speaking practice: Language exchange with Japanese developers

## Success Metrics

**Short-term** (2 weeks):
- Comfortable with git vocabulary in Japanese
- Can give basic status updates
- Recognize common Slack messages

**Medium-term** (2 months):
- Participate in code reviews in Japanese
- Discuss technical architecture
- Read technical documentation

**Long-term** (6 months):
- Lead technical meetings in Japanese
- Write design documents
- Mentor junior developers

## Key Insights for Agent Learning

### Pattern Recognition
- **Frequency-based organization** more useful than alphabetical for learning
- **Contextual sentences** critical for workplace vocabulary retention
- **Tiered approach** allows progressive mastery
- **CSV format** enables tool-agnostic learning

### Framework Reality Gap
- Language learning apps expect specific CSV formats
- Furigana rendering varies by app (some need special markup)
- Cloze deletion must be in target language, not translation
- Category fields essential for large vocabulary sets

### Risk Mitigation
- **Language direction confirmation** prevents wasted generation time
- **Small tier batches** allow testing before full commitment
- **Master file preservation** enables CSV regeneration with different formats

### Cross-Project Transferability
- Template applies to any language pair
- Frequency-based organization universal principle
- CSV format pattern reusable for medicine, law, business vocabulary
- Workplace context model transferable to other professional domains
