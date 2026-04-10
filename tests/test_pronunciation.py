"""Tests for pronunciation.py TTS preprocessing pipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pronunciation import (
    TTS_KANJI_OVERRIDES,
    convert_english_terms,
    extract_furigana,
    preprocess_for_tts,
    replace_particle_ha,
)


class TestExtractFurigana:
    """Strips furigana brackets, keeps kanji for TTS."""

    def test_standard_kanji_kept(self):
        assert extract_furigana("昼食【ちゅうしょく】前【まえ】に") == "昼食前に"

    def test_digits_preserved(self):
        assert extract_furigana("5分間【ふんかん】") == "5分間"

    def test_repetition_mark(self):
        assert extract_furigana("徐々【じょじょ】に") == "徐々に"

    def test_no_brackets_unchanged(self):
        assert extract_furigana("テストです") == "テストです"

    def test_override_uses_reading(self):
        """Kanji in TTS_KANJI_OVERRIDES get replaced with their reading."""
        assert "型" in TTS_KANJI_OVERRIDES
        assert extract_furigana("型【かた】エラー") == "かたエラー"

    def test_override_in_context(self):
        result = extract_furigana("型【かた】安全性【あんぜんせい】を向上【こうじょう】させます。")
        assert result == "かた安全性を向上させます。"

    def test_non_override_kanji_kept(self):
        result = extract_furigana("修正【しゅうせい】します。")
        assert result == "修正します。"


class TestReplaceParticleHa:
    """Replaces particle は with わ outside brackets."""

    def test_particle_replaced(self):
        assert replace_particle_ha("タスクは完了") == "タスクわ完了"

    def test_inside_brackets_preserved(self):
        assert replace_particle_ha("話【はな】せますか") == "話【はな】せますか"

    def test_multiple_particles(self):
        result = replace_particle_ha("テストは嘘【うそ】をつけません")
        assert result == "テストわ嘘【うそ】をつけません"

    def test_mixed_bracket_and_particle(self):
        result = replace_particle_ha("腐敗【ふはい】しやすいですがテストは嘘【うそ】をつけません")
        # は inside brackets preserved, は after テスト replaced
        assert "腐敗【ふはい】" in result
        assert "テストわ" in result


class TestConvertEnglishTerms:
    """Converts English acronyms and terms to katakana."""

    def test_acronym_map_lookup(self):
        assert "エーピーアイ" in convert_english_terms("API")

    def test_webhook_mapping(self):
        assert "ウェブフック" in convert_english_terms("webhook")

    def test_ai_mapping(self):
        assert "エーアイ" in convert_english_terms("AI")

    def test_uppercase_fallback_spelling(self):
        # Unknown 2-5 letter acronyms get spelled out
        result = convert_english_terms("XYZ")
        assert "エックス" in result
        assert "ワイ" in result
        assert "ゼット" in result

    def test_japanese_text_unchanged(self):
        assert convert_english_terms("テストです") == "テストです"


class TestPreprocessForTts:
    """Full pipeline integration tests."""

    def test_standard_sentence(self):
        result = preprocess_for_tts("昼食【ちゅうしょく】前【まえ】にこのバグを修正【しゅうせい】します。")
        assert result == "昼食前にこのバグを修正します。"

    def test_particle_ha_and_furigana(self):
        result = preprocess_for_tts("PRはレビュー準備【じゅんび】ができています。")
        assert "ピーアール" in result
        assert "わ" in result
        assert "レビュー準備ができています" in result

    def test_tts_override_in_pipeline(self):
        result = preprocess_for_tts("型【かた】エラーのためビルドが失敗【しっぱい】しました。")
        assert result.startswith("かた")
        assert "型" not in result

    def test_version_string(self):
        result = preprocess_for_tts("v2.0.0をリリースしました。")
        assert "バージョン" in result

    def test_percent_symbol(self):
        result = preprocess_for_tts("99%完了です。")
        assert "パーセント" in result

    def test_adds_trailing_punctuation(self):
        result = preprocess_for_tts("テスト")
        assert result.endswith("。")

    def test_existing_punctuation_kept(self):
        result = preprocess_for_tts("テストですか？")
        assert result.endswith("？")
        assert not result.endswith("？。")

    def test_bracket_cleanup(self):
        result = preprocess_for_tts("「テスト」です。")
        assert "「" not in result
        assert "」" not in result
