"""Tests for generate_furigana.py alignment and --force behaviour."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from generate_furigana import annotate, fill_tier, furigana

FIELDS = ["Sentence", "Translation", "Cloze", "Pronunciation"]


class FakeConfig:
    def __init__(self, path: Path):
        self._path = path

    def csv_path(self, tier: int) -> Path:
        return self._path


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestAnnotate:
    def test_okurigana_stays_outside_brackets(self):
        assert annotate("聞き取", "ききと") == "聞【き】き取【と】"

    def test_two_kanji_runs_split_lazily(self):
        assert annotate("話し合", "はなしあ") == "話【はな】し合【あ】"

    def test_reading_that_does_not_line_up(self):
        assert annotate("聞き取", "はなす") is None


class TestFurigana:
    def test_multi_run_okurigana(self):
        assert furigana("聞き取れません") == ("聞【き】き取【と】れません", [])

    def test_lazy_split_across_two_runs(self):
        assert furigana("話し合いをします") == ("話【はな】し合【あ】いをします", [])

    def test_whitespace_between_tokens_is_kept(self):
        annotated, failures = furigana("git log を確認します")
        assert annotated == "git log を確認【かくにん】します"
        assert failures == []

    def test_unalignable_token_reported_not_guessed(self):
        annotated, failures = furigana("コード冗也")
        assert failures == ["冗也"]
        assert annotated == "コード冗也"


class TestFillTier:
    def test_fills_empty_cell(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [{"Sentence": "聞き取れません", "Translation": "", "Cloze": "", "Pronunciation": ""}])
        filled, unresolved = fill_tier(FakeConfig(path), 1, force=False, dry_run=False)
        assert (filled, unresolved) == (1, 0)
        assert read_rows(path)[0]["Pronunciation"] == "聞【き】き取【と】れません"

    def test_force_does_not_clobber_hand_reading_of_unalignable_row(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [{"Sentence": "コード冗也", "Translation": "", "Cloze": "",
                          "Pronunciation": "コード冗也【じょうなり】"}])
        filled, unresolved = fill_tier(FakeConfig(path), 1, force=True, dry_run=False)
        assert (filled, unresolved) == (0, 1)
        assert read_rows(path)[0]["Pronunciation"] == "コード冗也【じょうなり】"

    def test_force_rewrites_an_alignable_row(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [{"Sentence": "聞き取れません", "Translation": "", "Cloze": "",
                          "Pronunciation": "聞き取れません"}])
        filled, unresolved = fill_tier(FakeConfig(path), 1, force=True, dry_run=False)
        assert (filled, unresolved) == (1, 0)
        assert read_rows(path)[0]["Pronunciation"] == "聞【き】き取【と】れません"

    def test_empty_cell_on_unalignable_row_still_written(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [{"Sentence": "コード冗也", "Translation": "", "Cloze": "", "Pronunciation": ""}])
        filled, unresolved = fill_tier(FakeConfig(path), 1, force=False, dry_run=False)
        assert (filled, unresolved) == (1, 1)
        assert read_rows(path)[0]["Pronunciation"] == "コード冗也"

    def test_written_csv_stays_lf(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [
            {"Sentence": "聞き取れません", "Translation": "", "Cloze": "", "Pronunciation": ""},
            {"Sentence": "話し合いをします", "Translation": "", "Cloze": "", "Pronunciation": ""},
        ])
        fill_tier(FakeConfig(path), 1, force=False, dry_run=False)
        assert b"\r\n" not in path.read_bytes()

    def test_dry_run_writes_nothing(self, tmp_path):
        path = tmp_path / "tier1-vocabulary.csv"
        write_csv(path, [{"Sentence": "聞き取れません", "Translation": "", "Cloze": "", "Pronunciation": ""}])
        before = path.read_bytes()
        fill_tier(FakeConfig(path), 1, force=False, dry_run=True)
        assert path.read_bytes() == before
