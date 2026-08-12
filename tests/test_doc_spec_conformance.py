"""docs/PRIORITY-PATH-agentic-lab.md is the specification for agentic-lab tiers 1-5.

Five phases become the first five tiers in the same order, with the same
sentences in the same order and the same readings. A re-selection or a
re-ordering of the doc's 179 rows is a spec violation no other test would catch.

Tiers 6+ are authored in this deck rather than selected from it-vocab, so the doc
does not specify them and tier_count is only floored, not fixed, here.
"""

import csv
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "lib"))

from config import load_deck_config

DOC = Path(__file__).parent.parent / "docs" / "PRIORITY-PATH-agentic-lab.md"
PHASE = re.compile(r"^## Phase (\d+) - (.+) \((\d+) sentences\)$")


def parse_doc() -> dict[int, list[tuple[str, str, str]]]:
    phases: dict[int, list[tuple[str, str, str]]] = {}
    current = None
    for line in DOC.read_text(encoding="utf-8").splitlines():
        header = PHASE.match(line)
        if header:
            current = int(header.group(1))
            phases[current] = []
            continue
        if current is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("Japanese", "---") or set(cells[0]) == {"-"}:
            continue
        phases[current].append(tuple(cells))
    return phases


DOC_PHASES = parse_doc()
CONFIG = load_deck_config("agentic-lab")


def csv_rows(tier: int) -> list[dict[str, str]]:
    with open(CONFIG.csv_path(tier), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_five_phases_become_the_first_five_tiers():
    assert sorted(DOC_PHASES) == [1, 2, 3, 4, 5]
    assert CONFIG.tier_count >= 5
    assert sum(len(rows) for rows in DOC_PHASES.values()) == 179


@pytest.mark.parametrize("tier", [1, 2, 3, 4, 5])
def test_tier_matches_its_phase_in_order(tier):
    doc = DOC_PHASES[tier]
    rows = csv_rows(tier)
    assert len(rows) == CONFIG.tier_sizes[tier] == len(doc)
    for position, ((sentence, english, reading), row) in enumerate(zip(doc, rows), start=1):
        assert row["Sentence"] == sentence, f"tier {tier} position {position} re-ordered"
        assert row["Translation"] == english
        assert row["Pronunciation"] == reading
