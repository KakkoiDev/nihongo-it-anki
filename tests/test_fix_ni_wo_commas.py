"""Tests for fix_ni_wo_commas.py script."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fix_ni_wo_commas import should_add_commas_in_ni_wo_pattern, add_ni_wo_commas


class TestShouldAddCommasInNiWoPattern:
    """Tests for should_add_commas_in_ni_wo_pattern function."""

    def test_basic_ni_wo_pattern(self):
        """Basic に...を pattern should add commas."""
        # フローに問題をみつけました - に at pos 3, を at pos 6
        sentence = "フローに問題をみつけました"
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, 3)
        assert should_add is True
        assert wo_pos == 6

    def test_already_has_comma_after_ni(self):
        """に already followed by comma should not add another."""
        sentence = "フローに、問題を見つけました"
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, 3)
        assert should_add is False

    def test_already_has_comma_after_wo(self):
        """を already followed by comma should not add."""
        sentence = "フローに問題を、見つけました"
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, 3)
        assert should_add is False

    def test_tameni_exclusion(self):
        """ために pattern should not add commas."""
        sentence = "テストのために準備をしました"
        # Find the に in ために
        ni_pos = sentence.find('に')
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False

    def test_passive_sareru_exclusion(self):
        """に...される passive pattern should not add commas."""
        sentence = "ユーザーにデータを削除される"
        ni_pos = sentence.find('に')
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False

    def test_no_wo_after_ni(self):
        """に without following を should not match."""
        sentence = "会議に参加します"
        ni_pos = sentence.find('に')
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False
        assert wo_pos is None

    def test_wo_followed_by_punctuation(self):
        """を followed by punctuation should not match."""
        sentence = "問題に答えを。"
        ni_pos = sentence.find('に')
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False

    def test_wo_followed_by_kanji(self):
        """を followed by kanji (not hiragana verb) should not match."""
        sentence = "コードにバグを発見した"
        ni_pos = sentence.find('に')
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False

    def test_ni_inside_furigana(self):
        """に inside furigana brackets should not match."""
        # 何【なに】- the に is inside the furigana, not a particle
        sentence = "何【なに】をする"
        # Find に inside furigana at position 3
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, 3)
        assert should_add is False

    def test_clause_boundary_ka(self):
        """か (question) between に and を stops the pattern."""
        sentence = "これが何をするか明確にしてください"
        # The に in 明確にして should not match を in 何をする (separated by か)
        ni_pos = sentence.find('明確にして')
        ni_pos = sentence.find('に', ni_pos)
        should_add, wo_pos = should_add_commas_in_ni_wo_pattern(sentence, ni_pos)
        assert should_add is False


class TestAddNiWoCommas:
    """Tests for add_ni_wo_commas function."""

    def test_adds_both_commas(self):
        """Should add comma after both に and を."""
        result = add_ni_wo_commas("フローに問題をみつけました")
        assert result == "フローに、問題を、みつけました"

    def test_preserves_tameni(self):
        """Should not add commas in ために pattern."""
        result = add_ni_wo_commas("テストのために準備をしました")
        # The ために should be preserved, but 準備を might still get comma
        assert "ために、" not in result

    def test_preserves_passive(self):
        """Should not add commas in passive pattern."""
        result = add_ni_wo_commas("ユーザーにデータを削除される")
        assert result == "ユーザーにデータを削除される"

    def test_already_has_commas(self):
        """Should not add duplicate commas."""
        result = add_ni_wo_commas("フローに、問題を、みつけました")
        assert result == "フローに、問題を、みつけました"

    def test_multiple_patterns(self):
        """Should handle multiple に...を patterns."""
        # Two separate patterns in one sentence
        result = add_ni_wo_commas("ファイルにデータをかき、サーバーにリクエストをおくる")
        assert "ファイルに、" in result
        assert "データを、" in result
        assert "サーバーに、" in result
        assert "リクエストを、" in result

    def test_with_furigana(self):
        """Should work with furigana annotations."""
        # Furigana in the text should not break pattern detection
        result = add_ni_wo_commas("フローに問題【もんだい】をみつけました")
        assert "フローに、" in result
        assert "を、みつけました" in result

    def test_no_change_when_no_pattern(self):
        """Should not modify text without に...を pattern."""
        original = "問題がありました"
        result = add_ni_wo_commas(original)
        assert result == original

    def test_ni_at_sentence_end(self):
        """Should handle に near end of sentence."""
        original = "会議に参加します"
        result = add_ni_wo_commas(original)
        assert result == original  # No を, so no change
