"""US-04 on the real indexes and query photos, dev split only (never test). Run with `make test-data`."""
import json
from pathlib import Path

import pytest

from vsearch.evaluate import SYSTEMS, evaluate

DATA = Path("data")
pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (DATA / "index").exists(), reason="run make index first"),
]


def test_tc_eval_04_and_06_real_dev_eval_has_every_row_and_repeats_exactly(tmp_path):
    """Given the real build, when the dev eval runs twice, then both files have a row for each
    system and rule, and every number is identical. The test split isn't read (no log line)."""
    a = json.loads(evaluate(DATA, results_dir=tmp_path, splits=["dev"], run_date="a").read_text())
    b = json.loads(evaluate(DATA, results_dir=tmp_path, splits=["dev"], run_date="b").read_text())
    assert {(r["system"], r["rule"]) for r in a["rows"]} == {(s, r) for s in SYSTEMS for r in ("strict", "type_only")}
    assert a["rows"] == b["rows"]
    assert not (tmp_path / "test-reads.log").exists()
