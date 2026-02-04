"""Tests for fix_heno_commas.py script."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fix_heno_commas import (
    count_katakana_morae,
    get_preceding_katakana,
    should_add_comma_after_heno,
    add_heno_commas,
)


class TestCountKatakanaMorae:
    """Tests for count_katakana_morae function."""

    def test_simple_katakana(self):
        """Regular katakana characters count as 1 mora each."""
        assert count_katakana_morae("アクセス") == 4
        assert count_katakana_morae("チーム") == 3
        assert count_katakana_morae("ユーザー") == 4

    def test_long_vowel(self):
        """Long vowel mark ー counts as 1 mora."""
        assert count_katakana_morae("データ") == 3  # デ-ー-タ
        assert count_katakana_morae("サーバー") == 4  # サ-ー-バ-ー

    def test_small_katakana(self):
        """Small katakana don't add extra morae."""
        assert count_katakana_morae("ファイル") == 3  # ファ-イ-ル (ァ part of ファ)
        assert count_katakana_morae("フィルター") == 4  # フィ-ル-タ-ー

    def test_long_compound(self):
        """Long compound katakana words."""
        assert count_katakana_morae("ステージング") == 6
        assert count_katakana_morae("データベース") == 6
        assert count_katakana_morae("ステージングデータベース") == 12

    def test_empty_string(self):
        """Empty string has 0 morae."""
        assert count_katakana_morae("") == 0


class TestGetPrecedingKatakana:
    """Tests for get_preceding_katakana function."""

    def test_extracts_katakana(self):
        """Should extract katakana word before position."""
        text = "ステージングデータベースへの"
        assert get_preceding_katakana(text, 12) == "ステージングデータベース"

    def test_stops_at_non_katakana(self):
        """Should stop at non-katakana characters."""
        text = "新しいサーバーへの"
        pos = text.find("への")
        assert get_preceding_katakana(text, pos) == "サーバー"

    def test_empty_when_no_katakana(self):
        """Should return empty when no katakana precedes."""
        text = "日本への"
        pos = text.find("への")
        assert get_preceding_katakana(text, pos) == ""


class TestShouldAddCommaAfterHeno:
    """Tests for should_add_comma_after_heno function."""

    def test_long_katakana_triggers_comma(self):
        """Long katakana word (≥6 morae) should trigger comma."""
        sentence = "ステージングデータベースへのアクセス"
        pos = sentence.find("への")
        assert should_add_comma_after_heno(sentence, pos) is True

    def test_short_katakana_no_comma(self):
        """Short katakana word (<6 morae) should not trigger comma."""
        sentence = "ユーザーへの影響"
        pos = sentence.find("への")
        assert should_add_comma_after_heno(sentence, pos) is False

    def test_already_has_comma(self):
        """Should not add comma if already present."""
        sentence = "ステージングデータベースへの、アクセス"
        pos = sentence.find("への")
        assert should_add_comma_after_heno(sentence, pos) is False

    def test_inside_furigana_brackets(self):
        """Should not match への inside furigana brackets."""
        # Artificial case - への wouldn't normally be in furigana
        sentence = "何【への】テスト"
        pos = sentence.find("への")
        assert should_add_comma_after_heno(sentence, pos) is False

    def test_no_katakana_before(self):
        """Should not add comma when no katakana precedes."""
        sentence = "日本への旅行"
        pos = sentence.find("への")
        assert should_add_comma_after_heno(sentence, pos) is False


class TestAddHenoCommas:
    """Tests for add_heno_commas function."""

    def test_adds_comma_after_long_katakana(self):
        """Should add comma after への when preceded by long katakana."""
        result = add_heno_commas("ステージングデータベースへのアクセスが必要です。")
        assert result == "ステージングデータベースへの、アクセスが必要です。"

    def test_preserves_short_katakana(self):
        """Should not add comma for short katakana words."""
        original = "ユーザーへの影響は何ですか？"
        result = add_heno_commas(original)
        assert result == original

    def test_already_has_comma(self):
        """Should not add duplicate commas."""
        original = "ステージングデータベースへの、アクセス"
        result = add_heno_commas(original)
        assert result == original

    def test_multiple_heno(self):
        """Should handle multiple への in sentence."""
        result = add_heno_commas("プロダクションサーバーへのアクセスとステージングサーバーへの接続")
        # Both should get commas (both are 9 morae)
        assert "プロダクションサーバーへの、" in result
        assert "ステージングサーバーへの、" in result

    def test_no_change_when_no_pattern(self):
        """Should not modify text without への pattern."""
        original = "問題がありました"
        result = add_heno_commas(original)
        assert result == original

    def test_mixed_content(self):
        """Should only affect long katakana + への patterns."""
        original = "ユーザーへの通知とステージングデータベースへのアクセス"
        result = add_heno_commas(original)
        assert "ユーザーへの通知" in result  # No comma (short)
        assert "ステージングデータベースへの、アクセス" in result  # Has comma (long)
