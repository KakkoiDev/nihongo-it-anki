"""Tests for fix_ga_commas.py script."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fix_ga_commas import should_add_comma_after_ga, add_ga_commas


class TestShouldAddCommaAfterGa:
    """Tests for should_add_comma_after_ga function."""

    def test_subject_marker_before_hiragana(self):
        """が as subject marker before hiragana verb should get comma."""
        # Script only adds comma when followed by hiragana (not kanji)
        assert should_add_comma_after_ga("問題がある", 2) is True
        assert should_add_comma_after_ga("時間があるとき", 2) is True

    def test_subject_marker_before_kanji(self):
        """が before kanji does not get comma (script limitation)."""
        # The script only matches hiragana after が, not kanji
        assert should_add_comma_after_ga("バグが発生", 2) is False

    def test_already_has_comma(self):
        """が already followed by comma should not add another."""
        assert should_add_comma_after_ga("バグが、発生", 2) is False

    def test_arigatou_exclusion(self):
        """ありがとう should not have comma inserted."""
        assert should_add_comma_after_ga("ありがとうございます", 3) is False

    def test_hou_ga_ii_exclusion(self):
        """方がいい pattern should not have comma."""
        assert should_add_comma_after_ga("方がいい", 1) is False
        assert should_add_comma_after_ga("ほうがいい", 2) is False

    def test_hou_ga_ii_with_furigana(self):
        """方【ほう】がいい should not have comma even with furigana annotation."""
        assert should_add_comma_after_ga("方【ほう】がいい", 5) is False
        assert should_add_comma_after_ga("聞いた方【ほう】がいい", 8) is False

    def test_nagara_exclusion(self):
        """ながら (while doing) should not have comma."""
        # が is at position 3 in 食べながら (食=0, べ=1, な=2, が=3, ら=4)
        assert should_add_comma_after_ga("食べながら", 3) is False
        assert should_add_comma_after_ga("ながら", 1) is False

    def test_verb_stem_agaru(self):
        """Verb stems like 上がる should not have comma."""
        assert should_add_comma_after_ga("上がる", 1) is False
        assert should_add_comma_after_ga("下がる", 1) is False

    def test_end_of_sentence(self):
        """が at end of sentence should not get comma."""
        assert should_add_comma_after_ga("問題が。", 2) is False
        assert should_add_comma_after_ga("問題が", 2) is False


class TestAddGaCommas:
    """Tests for add_ga_commas function."""

    def test_adds_comma(self):
        """Should add comma after subject marker が followed by hiragana."""
        assert add_ga_commas("問題がある") == "問題が、ある"
        assert add_ga_commas("準備ができた") == "準備が、できた"

    def test_preserves_exclusions(self):
        """Should not add commas in exclusion patterns."""
        assert add_ga_commas("ありがとうございます") == "ありがとうございます"
        assert add_ga_commas("方がいい") == "方がいい"
        assert add_ga_commas("方【ほう】がいい") == "方【ほう】がいい"
        assert add_ga_commas("食べながら") == "食べながら"

    def test_multiple_ga(self):
        """Should handle multiple が in same sentence."""
        result = add_ga_commas("問題があり時間がない")
        assert result == "問題が、あり時間が、ない"

    def test_mixed_patterns(self):
        """Should handle mix of comma and no-comma cases."""
        result = add_ga_commas("ありがとう、問題がある")
        assert result == "ありがとう、問題が、ある"

    def test_hou_ga_ii_in_sentence(self):
        """方がいい in full sentence should not get comma."""
        result = add_ga_commas("チームリードに聞いた方【ほう】がいいかもしれません")
        assert "方【ほう】が、いい" not in result
        assert "方【ほう】がいい" in result
