#!/usr/bin/env python3
"""Pronunciation preprocessing for accurate TTS audio generation.

This module converts the Pronunciation field (with furigana annotations)
into clean text that TTS engines can read correctly.

Handles:
1. Furigana extraction: 昼食【ちゅうしょく】 → ちゅうしょく
2. English acronyms: API → エーピーアイ
3. Common IT terms: bug → バグ (already in Japanese, but ensures consistency)
4. Particle pauses: を → を、 (for natural TTS rhythm)

## TTS Pause Pattern Notes (from Kokoro TTS experiments)

### Particles that need comma for natural pause:
- を (object marker): ALWAYS add comma after (を → を、)
  Scripted: を is always a particle, safe to auto-insert.

- が (subject marker): NEEDS comma after for natural pause, BUT requires
  LLM to determine if が is a particle vs. part of a word/grammar.
  Example particle: "バグが発生" → "バグが、発生" (sounds natural)
  Example non-particle: "ながら" (while) - don't insert comma

### Particles that sound fine without comma:
- は (topic marker): baseline sounds good
- に (direction/time): baseline sounds good
- で (location/means): baseline sounds good
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

# Common acronyms with special/preferred pronunciations
# (overrides letter-by-letter conversion)
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
    'websocket': 'ウェブソケット',
    'WebSocket': 'ウェブソケット',
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


def extract_furigana(text: str) -> str:
    """Extract furigana readings from annotated text.

    Converts: 昼食【ちゅうしょく】前【まえ】に → ちゅうしょくまえに
    Converts: 2日【ふつか】 → ふつか (handles numbers before kanji)

    Pattern: [digits]kanji【reading】 → reading
    All other text is preserved as-is.
    """
    # Pattern matches: optional digits + one or more kanji followed by 【reading】
    # Kanji range: \u4e00-\u9fff (CJK Unified Ideographs)
    # This handles cases like 2日【ふつか】, 3時【さんじ】, 10人【じゅうにん】
    pattern = r'([0-9]*[\u4e00-\u9fff]+)【([^】]+)】'

    def replace_with_reading(match):
        # Return just the reading (group 2), discard the kanji+digits (group 1)
        return match.group(2)

    return re.sub(pattern, replace_with_reading, text)


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


def insert_particle_pauses(text: str) -> str:
    """Insert commas after particles for natural TTS pauses.

    Based on Kokoro TTS experiments (see experiments/kokoro-pause-test/):
    - を (object marker): Always insert comma - を is always a particle
    - が (subject marker): Requires LLM - not handled here (see docstring notes)
    """
    # を is always the object marker particle in Japanese
    # Insert comma after を unless already followed by punctuation
    text = re.sub(r'を([^、。！？\s])', r'を、\1', text)

    return text


def preprocess_for_tts(pronunciation_field: str) -> str:
    """Full preprocessing pipeline for TTS input.

    1. Extract furigana readings
    2. Convert English terms to katakana
    3. Insert particle pauses (を → を、)
    4. Clean up any remaining issues

    Note: が (subject marker) also benefits from comma insertion but requires
    LLM context to distinguish particle vs. non-particle usage. See module
    docstring for details.
    """
    # Step 1: Extract furigana
    text = extract_furigana(pronunciation_field)

    # Step 2: Convert English terms
    text = convert_english_terms(text)

    # Step 3: Insert particle pauses for natural TTS rhythm
    text = insert_particle_pauses(text)

    # Step 4: Clean up
    # Remove any remaining brackets that might have been missed
    text = re.sub(r'【[^】]*】', '', text)

    # Normalize whitespace
    text = ' '.join(text.split())

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
        # Particle pause tests (を → を、)
        'ハッピーパスをテストしてください。',
        'データベースをバックアップしてください。',
        'コードレビューをお願いします。',
    ]

    print("Pronunciation Preprocessing Test\n")
    print("=" * 60)

    for original in test_cases:
        processed = preprocess_for_tts(original)
        print(f"\nOriginal:  {original}")
        print(f"Processed: {processed}")
