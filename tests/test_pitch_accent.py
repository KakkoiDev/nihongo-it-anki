"""Tests for generate_pitch_accent.py reading extraction."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from generate_pitch_accent import get_kana_reading, get_pitch_html


def _reading(html: str) -> str:
    """Extract the rt reading kana from pitch HTML, stripping pitch spans."""
    m = re.search(r"<rt>(.*?)</rt>", html, re.S)
    inner = m.group(1) if m else html
    return re.sub(r"<[^>]+>", "", inner)


class TestSuffixCompoundReading:
    """A cloze that is a kanji suffix directly before a larger run's
    annotation must not inherit the whole compound's reading."""

    def test_bunrui_not_whole_compound(self):
        html = get_pitch_html("分類", "チケットの自動分類【じどうぶんるい】に導入【どうにゅう】。")
        assert _reading(html) == "ぶんるい"
        assert "じどうぶんるい" not in html

    def test_honyaku_not_whole_compound(self):
        html = get_pitch_html("翻訳", "ドキュメントの英語翻訳【えいごほんやく】が必要【ひつよう】です。")
        assert _reading(html) == "ほんやく"
        assert "えいごほんやく" not in html


class TestReadingStillResolves:
    """The lookbehind must not break legitimate reading extraction."""

    def test_standalone_annotation(self):
        assert get_kana_reading("協力", "他【ほか】のチームと協力【きょうりょく】して") == "きょうりょく"

    def test_intervening_kanji_uses_token_kana(self):
        html = get_pitch_html("自律", "エージェントを自律的【じりつてき】に稼働【かどう】。")
        assert _reading(html) == "じりつ"

    def test_decompose_split_annotation(self):
        # 重複排除 split as 重複【…】を排除【…】 still composes when clozed whole
        assert get_kana_reading("重複排除", "レコードの重複【じゅうふく】を排除【はいじょ】") == "じゅうふくはいじょ"
