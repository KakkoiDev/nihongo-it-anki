#!/usr/bin/env python3
"""Pronunciation preprocessing for accurate TTS audio generation.

This module prepares Japanese text for Edge TTS (KeitaNeural/NanamiNeural).
It converts the Pronunciation field from the CSV into clean kana+katakana
text that Edge TTS can read correctly.

Pipeline (preprocess_for_tts):
  1. Symbol substitutions (%, version strings)
  2. Strip furigana brackets, keep kanji: 昼食【ちゅうしょく】 -> 昼食
  3. English term conversion: API -> エーピーアイ
  4. Cleanup leftover brackets
  5. Post-particle-は comma fix (force pause so first mora isn't elided)
  6. Targeted katakana-after-conjugation fix (えばドキュメント)

CRITICAL: The Pronunciation field serves DUAL purpose:
  1. Card display: create_deck.py renders it with to_ruby_html() for
     furigana ruby annotations shown to the learner.
  2. TTS input: this module's preprocess_for_tts() processes it into
     text that Edge TTS reads aloud.

  NEVER replace kanji with kana directly in the CSV Pronunciation field
  to fix TTS issues. This destroys the kanji+furigana display on cards.
  Instead, add the kanji to TTS_KANJI_OVERRIDES so extract_furigana()
  substitutes the reading only in the TTS pipeline, while the CSV keeps
  漢字【reading】 format for card display.

  WRONG: Change CSV from 提出【ていしゅつ】 to ていしゅつ
  RIGHT: Add '提出' to TTS_KANJI_OVERRIDES, keep CSV as 提出【ていしゅつ】

----------------------------------------------------------------------
HOW TO FIX A TTS BUG
----------------------------------------------------------------------

Workflow:
  1. Reproduce: `uv run python scripts/test_tts.py --tier N --row M`
     The script reads CSV row M's Pronunciation field, runs it through
     preprocess_for_tts(), and writes test_tier{N}_{MMM}.mp3. Listen.
  2. Read the printed "TTS input:" line. That is the exact string Edge
     TTS receives. If it's already wrong (e.g. missing a mora), the
     bug is upstream of TTS (CSV or preprocessing). If it looks right
     but the audio is wrong, the bug is in Edge TTS itself.
  3. Classify the bug (see below), apply the matching fix, re-run
     test_tts.py. Compare hashes with the on-disk file:
        sha256sum test_tier{N}_{MMM}.mp3 \\
                  decks/it-vocab/tier{N}-audio/tier{N}_{MMM}.mp3
     Identical hashes mean Edge TTS produces the same audio: your fix
     hasn't changed the input, or the on-disk file was already fixed.
  4. When the audio is good, regenerate the affected tier with --force
     and rebuild the .apkg. See CLAUDE.md "Full Rebuild Example".

Bug classes and where to fix:

  A. KANJI MISREADING (Edge TTS reads the wrong kana for a known kanji).
     Symptom: a kanji is read in isolation or with a wrong pitch.
     Examples: 型 -> がた (should be かた), 既存 -> そん (drops き).
     Fix: add the kanji (or whole compound) to TTS_KANJI_OVERRIDES.
     extract_furigana() will substitute the bracketed reading in the
     TTS pipeline. CSV stays unchanged. See TTS_KANJI_OVERRIDES below.

  B. POST-PARTICLE-は PROSODIC ELISION (Edge TTS weakens or drops the
     first mora of any hiragana word immediately after particle は).
     Symptom: は + すべて -> "wa-bete", は + どの -> faint do,
              は + きそん -> "wa-son", は + もじれつ -> "wa-jiretsu".
     Fix: ALREADY HANDLED by the regex in preprocess_for_tts (search for
     "post-particle-は"). Inserts a comma when は is preceded by a
     content word (kanji/katakana) and followed by hiragana. No action
     needed for new sentences matching this pattern. If you find a case
     not covered (e.g. は preceded by hiragana like それは + word),
     extend the lookbehind class rather than adding a narrow replace.

  C. NEW PROSODIC GLITCH NOT COVERED BY (B). E.g. えばドキュメント -> ド
     elided. Treatment: targeted text.replace() at the end of
     preprocess_for_tts(), with a comment quoting the symptom. Keep
     these narrow: a broad regex risks regressing other sentences.

  D. ENGLISH/ACRONYM GARBLE. Symptom: an English word reads weirdly
     (e.g. SDK as "ess-deck"). Fix: add an entry to ACRONYM_MAP with
     the correct katakana. If the loanword should display as katakana
     on the card too (webhook -> ウェブフック), write katakana directly
     in the CSV Pronunciation field instead.

  E. DIGIT IRREGULARITY (counter words). Symptom: 2日 reads "ni futsuka"
     because "2" gets read as "ni" but the kanji is already irregular.
     Fix: write the kana directly in the CSV (ふつか), not 2日【ふつか】.

What to AVOID:
- Do NOT add commas (、) directly to the CSV Pronunciation field for
  TTS workarounds. They appear on the card. TTS-only commas go in
  preprocess_for_tts() via text.replace() or regex.
- Do NOT replace kanji with kana in the CSV. That breaks card display.
  Use TTS_KANJI_OVERRIDES.
- Do NOT use the TTSPronunciation column. It has artificial commas that
  cause unnatural pauses ("が、できました"). Audio gen reads Pronunciation.
- \\b word boundary doesn't work at Japanese/ASCII boundaries. Use a
  negative lookbehind (?<![A-Za-z]) instead.

Lessons learned (running log):
- Edge TTS handles particle は as "wa" without the old は->わ workaround.
  Commit 38567bd removed the workaround. The post-particle-は elision
  is a separate prosodic phenomenon, fixed by the comma regex.
- The 文字列 -> "jiretsu" bug initially looked like a kanji misreading
  (class A), but the underlying problem was actually post-は elision
  (class B). The kanji override gave us もじれつ, but Edge TTS still
  dropped the も because of particle は before it. Keep both fixes as
  defense-in-depth: override gets the right phonemes, comma forces the
  pause.
- The same root-cause confusion happened for 既存. If a kanji-override
  fix doesn't resolve a missing-first-mora bug, check if particle は
  precedes the word.
"""

import re

# English letter → Japanese katakana mapping
LETTER_MAP = {
    'A': 'エー',
    'B': 'ビー',
    'C': 'シー',
    'D': 'ディー',
    'E': 'イー',
    'F': 'エフ',
    'G': 'ジー',
    'H': 'エイチ',
    'I': 'アイ',
    'J': 'ジェー',
    'K': 'ケー',
    'L': 'エル',
    'M': 'エム',
    'N': 'エヌ',
    'O': 'オー',
    'P': 'ピー',
    'Q': 'キュー',
    'R': 'アール',
    'S': 'エス',
    'T': 'ティー',
    'U': 'ユー',
    'V': 'ブイ',
    'W': 'ダブリュー',
    'X': 'エックス',
    'Y': 'ワイ',
    'Z': 'ゼット',
}

# Common acronyms with special/preferred pronunciations.
# Words here are matched EXACTLY (case-sensitive) before the letter-by-letter
# fallback. The fallback only handles 2-5 uppercase letters (e.g. CI -> シーアイ)
# and LETTER+DIGIT patterns (e.g. EC2 -> イーシーツー).
# Words 6+ uppercase letters (DELETE, SELECT) MUST be here or they pass through raw.
ACRONYM_MAP = {
    'JSON': 'ジェイソン',
    'REST': 'レスト',
    'SQL': 'エスキューエル',
    'NULL': 'ヌル',
    'CRUD': 'クラッド',
    'GUI': 'ジーユーアイ',
    'CLI': 'シーエルアイ',
    'SSH': 'エスエスエイチ',
    'SSL': 'エスエスエル',
    'TLS': 'ティーエルエス',
    'DNS': 'ディーエヌエス',
    'TCP': 'ティーシーピー',
    'UDP': 'ユーディーピー',
    'VPN': 'ブイピーエヌ',
    'VPC': 'ブイピーシー',
    'IAM': 'アイエーエム',
    'AWS': 'エーダブリューエス',
    'GCP': 'ジーシーピー',
    'ORM': 'オーアールエム',
    'MVC': 'エムブイシー',
    'DRY': 'ドライ',
    'SOLID': 'ソリッド',
    'CORS': 'コース',
    'CSRF': 'シーエスアールエフ',
    'XSS': 'エックスエスエス',
    'JWT': 'ジェーダブリューティー',
    'OAuth': 'オーオース',
    'SAML': 'サムル',
    'SSO': 'エスエスオー',
    'MFA': 'エムエフエー',
    'RBAC': 'アールバック',
    'GDPR': 'ジーディーピーアール',
    'PCI': 'ピーシーアイ',
    'SOC': 'ソック',
    'WAF': 'ワフ',
    'DDoS': 'ディードス',
    'CDN': 'シーディーエヌ',
    'TTL': 'ティーティーエル',
    'SSD': 'エスエスディー',
    'IOPS': 'アイオプス',
    'EBS': 'イービーエス',
    'RDS': 'アールディーエス',
    'SQS': 'エスキューエス',
    'SNS': 'エスエヌエス',
    'ECS': 'イーシーエス',
    'EKS': 'イーケーエス',
    'ALB': 'エーエルビー',
    'NLB': 'エヌエルビー',
    'AMI': 'エーエムアイ',
    'KMS': 'ケーエムエス',
    'ETL': 'イーティーエル',
    'SSR': 'エスエスアール',
    'CSR': 'シーエスアール',
    'SEO': 'エスイーオー',
    'DOM': 'ドム',
    'CSS': 'シーエスエス',
    'ARIA': 'アリア',
    'npm': 'エヌピーエム',
    'yarn': 'ヤーン',
    'pip': 'ピップ',
    'git': 'ギット',
    'Slack': 'スラック',
    'Jira': 'ジラ',
    'cron': 'クーロン',
    'grep': 'グレップ',
    'sudo': 'スードゥー',
    'bash': 'バッシュ',
    'vim': 'ビム',
    'nginx': 'エンジンエックス',
    'Redis': 'レディス',
    'Kafka': 'カフカ',
    'React': 'リアクト',
    'Vue': 'ビュー',
    'Node': 'ノード',
    'async': 'エイシンク',
    'await': 'アウェイト',
    'props': 'プロップス',
    'state': 'ステート',
    'hook': 'フック',
    'hooks': 'フックス',
    'webpack': 'ウェブパック',
    'TypeScript': 'タイプスクリプト',
    'JavaScript': 'ジャバスクリプト',
    'Python': 'パイソン',
    'Prisma': 'プリズマ',
    'Docker': 'ドッカー',
    'Dockerfile': 'ドッカーファイル',
    'Kubernetes': 'クバネティス',
    'Terraform': 'テラフォーム',
    'CloudFormation': 'クラウドフォーメーション',
    'CloudWatch': 'クラウドウォッチ',
    'CloudTrail': 'クラウドトレイル',
    'CloudFront': 'クラウドフロント',
    'Lambda': 'ラムダ',
    'Fargate': 'ファーゲート',
    'Cognito': 'コグニート',
    'DynamoDB': 'ダイナモディービー',
    'Redshift': 'レッドシフト',
    'Athena': 'アテナ',
    'Glue': 'グルー',
    'Kinesis': 'キネシス',
    'EventBridge': 'イベントブリッジ',
    'CodeBuild': 'コードビルド',
    'CodeDeploy': 'コードデプロイ',
    'CodePipeline': 'コードパイプライン',
    'Datadog': 'データドッグ',
    'Grafana': 'グラファナ',
    'Prometheus': 'プロメテウス',
    'Splunk': 'スプランク',
    'Sentry': 'セントリー',
    'Okta': 'オクタ',
    'Memcached': 'メムキャッシュド',
    'RabbitMQ': 'ラビットエムキュー',
    'Parquet': 'パーケット',
    'Flexbox': 'フレックスボックス',
    'Lighthouse': 'ライトハウス',
    'RESTful': 'レストフル',
    'OAuth': 'オーオース',
    'GitHub': 'ギットハブ',
    'GitLab': 'ギットラブ',
    'DevOps': 'デブオプス',
    'DevTools': 'デブツールズ',
    'localhost': 'ローカルホスト',
    'frontend': 'フロントエンド',
    'backend': 'バックエンド',
    'fullstack': 'フルスタック',
    'middleware': 'ミドルウェア',
    'microservice': 'マイクロサービス',
    'microservices': 'マイクロサービス',
    'monolith': 'モノリス',
    'serverless': 'サーバーレス',
    'webhook': 'ウェブフック',
    'AI': 'エーアイ',
    'README': 'リードミー',
    'websocket': 'ウェブソケット',
    'WebSocket': 'ウェブソケット',
    # HTTP methods
    'GET': 'ゲット',
    'POST': 'ポスト',
    'PUT': 'プット',
    'PATCH': 'パッチ',
    'DELETE': 'デリート',
    'HEAD': 'ヘッド',
    'OK': 'オーケー',
    'HTTP': 'エイチティーティーピー',
    'HTTPS': 'エイチティーティーピーエス',
    'URL': 'ユーアールエル',
    # SQL keywords
    'SELECT': 'セレクト',
    'INSERT': 'インサート',
    'UPDATE': 'アップデート',
    'DELETE': 'デリート',
    'WHERE': 'ウェア',
    'ORDER': 'オーダー',
    'GROUP': 'グループ',
    'LIMIT': 'リミット',
    'BY': 'バイ',
    # Git terms
    'main': 'メイン',
    'origin': 'オリジン',
    'blame': 'ブレーム',
    'upstream': 'アップストリーム',
    'HEAD': 'ヘッド',
    'changelog': 'チェンジログ',
    'install': 'インストール',
    # Code keywords
    'null': 'ナル',
    'true': 'トゥルー',
    'false': 'フォールス',
    'undefined': 'アンデファインド',
    'boolean': 'ブーリアン',
    'default': 'デフォルト',
    'promise': 'プロミス',
    'console': 'コンソール',
    'log': 'ログ',
    'try': 'トライ',
    'catch': 'キャッチ',
    'save': 'セーブ',
    'limit': 'リミット',
    'id': 'アイディー',
    'env': 'エンブ',
    'components': 'コンポーネンツ',
    'utils': 'ユーティルズ',
    'users': 'ユーザーズ',
    'user': 'ユーザー',
    'isActive': 'イズアクティブ',
    # Tech products and frameworks
    'Safari': 'サファリ',
    'GraphQL': 'グラフキューエル',
    'Express': 'エクスプレス',
    'NoSQL': 'ノーエスキューエル',
    'ConfigMap': 'コンフィグマップ',
    'ElastiCache': 'エラスティキャッシュ',
    'lodash': 'ロダッシュ',
    'bcrypt': 'ビークリプト',
    # Abbreviations
    'TODO': 'トゥードゥー',
    'FIXME': 'フィックスミー',
    'E2E': 'イーツーイー',
    'IaC': 'アイエーシー',
    'for': 'フォー',
    'if': 'イフ',
    'else': 'エルス',
    'at': 'アット',
    'created': 'クリエイテッド',
    'User': 'ユーザー',
    'Secrets': 'シークレッツ',
    'Cookie': 'クッキー',
    'Grid': 'グリッド',
    'Blob': 'ブロブ',
    # AWS service components
    'Route': 'ルート',
    'Gateway': 'ゲートウェイ',
    'Ray': 'レイ',
    'Manager': 'マネージャー',
    'Parameter': 'パラメーター',
    'Store': 'ストア',
    'Step': 'ステップ',
    'Functions': 'ファンクションズ',
    'Cost': 'コスト',
    'Explorer': 'エクスプローラー',
    'New': 'ニュー',
    'Relic': 'レリック',
    'DTO': 'ディーティーオー',
    'API': 'エーピーアイ',
    'SDK': 'エスディーケー',
    'CSV': 'シーエスブイ',
    'XML': 'エックスエムエル',
    'UI': 'ユーアイ',
    'UX': 'ユーエックス',
    'QA': 'キューエー',
    'PR': 'ピーアール',
    'CI': 'シーアイ',
    'CD': 'シーディー',
    'DB': 'ディービー',
    'IP': 'アイピー',
    'ID': 'アイディー',
    'TDD': 'ティーディーディー',
    'APM': 'エーピーエム',
    'SLA': 'エスエルエー',
    'SLO': 'エスエルオー',
    'SLI': 'エスエルアイ',
    'OKR': 'オーケーアール',
    'KPI': 'ケーピーアイ',
    'ETA': 'イーティーエー',
    'DM': 'ディーエム',
    'AES': 'エーイーエス',
    # Alphanumeric abbreviations
    'K8s': 'クバネティス',
    'a11y': 'アクセシビリティ',
    'i18n': '国際化',
    'l10n': 'ローカライゼーション',
    # Units
    'ms': 'ミリ秒',
    'MB': 'メガバイト',
    'GB': 'ギガバイト',
    'TB': 'テラバイト',
    'KB': 'キロバイト',
    'Mbps': 'メガビーピーエス',
    'Gbps': 'ギガビーピーエス',
}

# Number pronunciations (English-style for tech context)
NUMBER_MAP = {
    '0': 'ゼロ',
    '1': 'ワン',
    '2': 'ツー',
    '3': 'スリー',
    '4': 'フォー',
    '5': 'ファイブ',
    '6': 'シックス',
    '7': 'セブン',
    '8': 'エイト',
    '9': 'ナイン',
}


# Kanji that Edge TTS misreads. extract_furigana() substitutes the
# bracketed reading instead of keeping the kanji for these entries.
#
# HOW TO FIX A TTS MISREADING:
#   1. Add the kanji to this set.
#   2. Keep the CSV Pronunciation field as 漢字【reading】 (do NOT edit CSV).
#   3. Regenerate audio.
#   That's it. The override handles TTS while preserving card display.
#
# DO NOT edit the CSV to replace kanji with kana. The Pronunciation field
# is shown on cards with furigana. Replacing kanji breaks card display.
#
# Known misreadings:
#   型     -> がた   (Edge TTS reads がた instead of かた in isolation)
#   既存   -> そん   (drops the き, reads as just "son")
#   文字列 -> じれつ (drops the も, reads as just "jiretsu")
#   一意   -> イ     (drops チイ; the post-は comma alone wasn't enough,
#                    Edge TTS only voiced the first kana. Override fixes
#                    it cleanly.)
#   行     -> こう   (Edge TTS picks the こう/コウ reading when context
#                    wants ぎょう ('database row/line'). The override
#                    only affects standalone 行【...】; compounds like
#                    銀行 / 移行 / 実行 are captured as multi-kanji
#                    matches and stay untouched.)
#   中     -> なか   (Edge TTS picks なか when context wants ちゅう
#                    ('mid-progress', '内に'). Same single-kanji
#                    scope rule: standalone 中【ちゅう】 only;
#                    compounds like 集中 / 中国 are unaffected.)
#   閾値   -> いきち (Edge TTS misreads the rare 閾 kanji. CSV has
#                    閾値【しきいち】; override forces that reading.)
#
# NOT overridden (TTS limitation, override doesn't help):
#   提出 -> ていしつ (Edge TTS drops しゅつ to しつ, but kana input
#           sounds identical. Keeping kanji preserves correct pitch.)
#   抽出 -> ちゅうしつ (same しゅつ pattern, same TTS limitation)
TTS_KANJI_OVERRIDES = {
    '型', '既存', '文字列', '一意',
    '行', '中', '閾値',
}


def extract_furigana(text: str) -> str:
    """Strip furigana brackets, keeping kanji for Edge TTS.

    Converts: 昼食【ちゅうしょく】前【まえ】に -> 昼食前に
    Converts: 5分間【ふんかん】 -> 5分間 (digits preserved)

    Exception: kanji in TTS_KANJI_OVERRIDES are replaced with their
    furigana reading instead of being kept, because Edge TTS misreads
    them. E.g. 提出【ていしゅつ】 -> ていしゅつ (not 提出).

    Edge TTS handles standard kanji readings correctly and produces better
    pronunciation than all-hiragana input (e.g. 話せます vs はなせますか
    where TTS misreads は as the particle). Keep kanji, just drop the
    bracket annotations.

    The \\u3005 in the regex is the 々 repetition mark (e.g. 徐々【じょじょ】).
    """
    # [optional digits][kanji+々]【reading】 -> [digits]kanji or [digits]reading
    pattern = r'([0-9]*)([\u4e00-\u9fff\u3005]+)【([^】]+)】'

    def keep_kanji_or_override(match):
        digits, kanji, reading = match.group(1), match.group(2), match.group(3)
        if kanji in TTS_KANJI_OVERRIDES:
            return digits + reading
        return digits + kanji

    return re.sub(pattern, keep_kanji_or_override, text)


def convert_acronym(match: re.Match) -> str:
    """Convert an English acronym/word to katakana."""
    word = match.group(0)

    # Check for exact match in acronym map (case-insensitive for some)
    if word in ACRONYM_MAP:
        return ACRONYM_MAP[word]
    if word.upper() in ACRONYM_MAP:
        return ACRONYM_MAP[word.upper()]

    # Check if it's an AWS service pattern like EC2, S3, etc.
    ec2_match = re.match(r'^([A-Z]+)(\d+)$', word)
    if ec2_match:
        letters, numbers = ec2_match.groups()
        letter_part = ''.join(LETTER_MAP.get(c, c) for c in letters)
        number_part = ''.join(NUMBER_MAP.get(c, c) for c in numbers)
        return letter_part + number_part

    # For unknown acronyms (2-5 uppercase letters), spell them out
    if re.match(r'^[A-Z]{2,5}$', word):
        return ''.join(LETTER_MAP.get(c, c) for c in word)

    # For mixed case or longer words, return as-is (TTS might handle it)
    return word


def convert_english_terms(text: str) -> str:
    """Convert English acronyms and terms to katakana pronunciation."""
    # Pattern to match English words/acronyms
    # Don't use \b as it doesn't work with Japanese text
    # Match sequences of ASCII letters/numbers that start with a letter
    pattern = r'[A-Za-z][A-Za-z0-9]*'

    return re.sub(pattern, convert_acronym, text)


def preprocess_for_tts(text: str) -> str:
    """Preprocessing pipeline for TTS input.

    1. Substitute symbols Edge TTS can't pronounce (%, version strings)
    2. Extract furigana readings (applies TTS_KANJI_OVERRIDES)
    3. Convert English terms to katakana
    4. Clean up any remaining brackets and excess whitespace
    5. Insert a comma after particle は to prevent first-mora elision
       on the following hiragana word (class B in the module docstring)
    6. Apply any narrow string fixes for prosodic glitches that are not
       particle-は (currently: えばドキュメント -> えば、ドキュメント)

    Edge TTS reads particle は as "wa" correctly without a は->わ
    substitution. The post-particle-は comma fix below (step 5) addresses
    a separate prosodic bug where the first mora of the next hiragana
    word is elided or weakened.
    """
    # Step 1: Symbol substitutions
    text = text.replace('%', 'パーセント')
    # v2.0.0 style version strings: keep the number, drop the "v"
    # Can't use \b - doesn't work at Japanese/ASCII boundary
    text = re.sub(r'(?<![A-Za-z])v(\d)', r'バージョン\1', text)

    # Step 2: Extract furigana
    text = extract_furigana(text)

    # Step 3: Convert English terms
    text = convert_english_terms(text)

    # Step 4: Clean up
    text = text.replace('「', '').replace('」', '')
    text = re.sub(r'【[^】]*】', '', text)
    text = ' '.join(text.split())

    # Edge TTS weakens or elides the first mora of the next word
    # immediately after particle は. Observed across an ASR audit of
    # 200 sampled audio files:
    #   は + hiragana: はすべて -> "wa-bete", はどの -> "wa-(faint)ono",
    #                  はきそん -> "wa-son", はもじれつ -> "wa-jiretsu"
    #   は + katakana: はユーザー -> "wa-zaa" (drops yu)
    #   は + kanji:    は一意 -> "wa-chii" (drops i of ichii)
    #   compound particles like には + content also affected:
    #                  にはコグニート -> "ni-wa-uneeto" (drops kogu)
    # Two passes handle this without false-positive on word-internal
    # は (e.g. 'はじめ', 'はず'):
    #   Pass A: は followed by katakana/kanji is unambiguous (no real
    #           Japanese word straddles a hiragana-に-or-other into
    #           katakana/kanji via は). Lookbehind is open.
    #   Pass B: は followed by hiragana requires a content word
    #           (kanji/katakana/々) before は to avoid splitting word-
    #           internal は like 今日はじめます.
    # CSV Pronunciation field stays clean for card display.
    text = re.sub(r'は(?=[゠-ヿ一-鿿々])', 'は、', text)
    text = re.sub(r'(?<=[一-鿿々゠-ヿ])は(?=[ぁ-ゖ])', 'は、', text)

    # Edge TTS elides ド in 使えばドキュメント (reads "tsukaeba-kyumento"
    # instead of "tsukaeba-dokyumento"). Same comma-pause workaround, but
    # not a particle-は case so handled separately.
    text = text.replace('えばドキュメント', 'えば、ドキュメント')

    # Ensure ends with punctuation for clean TTS delivery
    if text and text[-1] not in '。！？、':
        text += '。'

    return text


# For testing
if __name__ == '__main__':
    test_cases = [
        '昼食【ちゅうしょく】前【まえ】にこのバグを修正【しゅうせい】します。',
        'APIチームと同期【どうき】してください。',
        'PRはレビュー準備【じゅんび】ができています。',
        'EC2インスタンスで実行【じっこう】しています。',
        'S3にファイルを保存【ほぞん】してください。',
        'CIが通【とお】ったらマージできます。',
        'JSONをパースしてください。',
        'RESTful APIです。',
        'AWS Lambdaを使【つか】ってください。',
        'TypeScriptをJSにトランスパイルしてください。',
        'ハッピーパスをテストしてください。',
        'データベースをバックアップしてください。',
        'コードレビューをお願いします。',
        # Post-particle-は fix (now covers ANY next word, not just hiragana):
        # was first observed as は + hiragana elision (subete, dono, kison),
        # ASR audit later showed it also affects は + katakana and は + kanji.
        'このモジュールはすべてのデータベース操作【そうさ】を処理【しょり】します。',
        'この変更【へんこう】は既存【きそん】の機能【きのう】を壊【こわ】すかもしれません。',
        'IDは文字列【もじれつ】ではなく数値【すうち】であるべきです。',
        'このパラメータはどの型【かた】であるべきですか？',
        # は + katakana (new case caught by extended regex):
        'APIはユーザーデータをJSONで返【かえ】します。',
        'ユーザー認証【にんしょう】にはCognitoを使【つか】ってください。',
        # は + kanji (new case caught by extended regex):
        'メールフィールドは一意【いちい】であるべきです。',
        'リリースは金曜日【きんようび】に予定【よてい】されています。',
        # No fix expected: は preceded by hiragana (それは, これは)
        'それはまだ確定【かくてい】していません。',
        'これは新【あたら】しい機能【きのう】です。',
        # えばドキュメント narrow fix
        'テンプレートを使【つか】えばドキュメントの品質【ひんしつ】を均一【きんいつ】にできます。',
    ]

    print("Pronunciation Preprocessing Test\n")
    print("=" * 60)

    for original in test_cases:
        processed = preprocess_for_tts(original)
        print(f"\nOriginal:  {original}")
        print(f"Processed: {processed}")
