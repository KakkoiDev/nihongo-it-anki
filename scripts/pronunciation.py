#!/usr/bin/env python3
"""Pronunciation preprocessing for accurate TTS audio generation.

This module prepares Japanese text for Edge TTS (KeitaNeural/NanamiNeural).
It converts the Pronunciation field from the CSV into clean kana+katakana
text that Edge TTS can read correctly.

Pipeline (preprocess_for_tts):
  1. Symbol substitutions (%, version strings)
  2. Furigana extraction: 昼食【ちゅうしょく】 -> ちゅうしょく
  3. English term conversion: API -> エーピーアイ
  4. Cleanup leftover brackets

IMPORTANT lessons learned:
- Edge TTS reads the Pronunciation field, NOT TTSPronunciation.
  The TTSPronunciation column had artificial commas that caused unnatural
  pauses (e.g. "が、できました"). Never use it for audio generation.
- Katakana loanwords (レビュー etc.) are left as-is for TTS. Edge TTS
  handles them natively. But when preceded by spelled-out acronyms
  (ピーアール), TTS can merge them. Fix with a reading comma in the
  Pronunciation field (e.g. "PRは、レビュー...").
- Irregular counter words like 2日=ふつか must use kana directly in the
  Pronunciation field. The digit "2" gets read as "ni" by TTS, producing
  "ni futsuka" instead of just "futsuka".
- \b word boundary doesn't work at Japanese/ASCII boundaries. Use
  negative lookbehind (?<![A-Za-z]) instead.
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


def extract_furigana(text: str) -> str:
    """Extract furigana readings from annotated text.

    Converts: 昼食【ちゅうしょく】前【まえ】に → ちゅうしょくまえに
    Converts: 5分間【ふんかん】 → 5ふんかん (digits preserved)

    Pattern: [digits]kanji【reading】 → [digits]reading
    All other text is preserved as-is.

    GOTCHA: Digits before kanji are preserved (5分 -> 5ふん, TTS reads "go fun").
    This breaks for irregular counters where the reading includes the number
    (2日=ふつか -> "2ふつか" -> TTS says "ni futsuka"). For those, write the
    Pronunciation field with kana directly: おそらくふつかかかる instead of
    おそらく2日【ふつか】かかる.

    The \u3005 in the regex is the 々 repetition mark (e.g. 徐々【じょじょ】).
    """
    # [optional digits][kanji+々]【reading】 -> [digits]reading
    pattern = r'([0-9]*)([\u4e00-\u9fff\u3005]+)【([^】]+)】'

    def replace_with_reading(match):
        digits, _kanji, reading = match.group(1), match.group(2), match.group(3)
        return digits + reading

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


def replace_particle_ha(text: str) -> str:
    """Replace particle は with わ so Edge TTS reads it as "wa" not "ha".

    Must run BEFORE extract_furigana(), on the raw Pronunciation field where
    brackets still disambiguate word readings from particles:
      - 話【はな】せますか -> は inside brackets = word reading, untouched
      - 差分【さぶん】は -> は outside brackets = particle, replaced with わ

    Edge TTS handles へ and を correctly, so only は needs this fix.

    CAVEAT: Hiragana words starting with は (はず, はじめ, はっきり) would be
    wrongly replaced if written outside brackets. Currently no such words
    exist in the data. If one is added, wrap it in brackets or add it as
    an exception here.
    """
    parts = re.split(r'(【[^】]*】)', text)
    for i, part in enumerate(parts):
        if not part.startswith('【'):
            parts[i] = part.replace('は', 'わ')
    return ''.join(parts)


def preprocess_for_tts(text: str) -> str:
    """Preprocessing pipeline for TTS input.

    1. Substitute symbols Edge TTS can't pronounce (%, version strings)
    2. Replace particle は with わ (Edge TTS reads は as "ha" not "wa")
       Must happen before furigana extraction while brackets still disambiguate.
    3. Extract furigana readings
    4. Convert English terms to katakana
    5. Clean up any remaining brackets
    """
    # Step 1: Symbol substitutions
    text = text.replace('%', 'パーセント')
    # v2.0.0 style version strings: keep the number, drop the "v"
    # Can't use \b - doesn't work at Japanese/ASCII boundary
    text = re.sub(r'(?<![A-Za-z])v(\d)', r'バージョン\1', text)

    # Step 2: Replace particle は with わ (before furigana extraction)
    text = replace_particle_ha(text)

    # Step 3: Extract furigana
    text = extract_furigana(text)

    # Step 4: Convert English terms
    text = convert_english_terms(text)

    # Step 5: Clean up
    text = text.replace('「', '').replace('」', '')
    text = re.sub(r'【[^】]*】', '', text)
    text = ' '.join(text.split())

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
    ]

    print("Pronunciation Preprocessing Test\n")
    print("=" * 60)

    for original in test_cases:
        processed = preprocess_for_tts(original)
        print(f"\nOriginal:  {original}")
        print(f"Processed: {processed}")
