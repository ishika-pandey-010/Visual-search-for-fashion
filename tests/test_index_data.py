"""US-02 checks on the real indexes (make catalogue and make index first). Run with `make test-data`."""
import json
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import pytest

from vsearch.embed import MODELS
from vsearch.index import load_index

DATA = Path("data")
pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (DATA / "index").exists(), reason="run make index first"),
]


@pytest.mark.parametrize("key", list(MODELS))
def test_tc_cat_05_real_index_is_current_aligned_and_pinned(key):
    """Given the real build, then each model's index loads (so it matches this catalogue), has one
    row per product in catalogue order, and records the pinned model revision."""
    index, ids, meta = load_index(DATA, key)
    cat = pd.read_parquet(DATA / "catalogue.parquet")
    assert isinstance(index, faiss.IndexFlatIP)
    assert index.ntotal == len(ids) == len(cat) == meta["count"]
    assert ids.tolist() == cat["product_id"].tolist()
    assert (meta["repo"], meta["revision"]) == (MODELS[key]["repo"], MODELS[key]["revision"])


@pytest.mark.parametrize("key", list(MODELS))
def test_tc_cat_06_real_vectors_have_length_one(key):
    index, _, _ = load_index(DATA, key)
    lengths = np.linalg.norm(index.reconstruct_n(0, index.ntotal), axis=1)
    assert np.all(np.abs(lengths - 1) < 1e-3)


@pytest.mark.parametrize("key", list(MODELS))
def test_tc_cat_07_real_self_check_found_at_least_198_of_200(key):
    """Given the self-check `make index` ran on 200 freshly embedded catalogue images, then at
    least 198 found themselves at rank 1."""
    check = json.loads((DATA / "index" / key / "self-check.json").read_text())
    assert check["n"] == 200
    assert check["rank1"] >= 198, check["misses"]
