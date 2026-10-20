"""US-02 Build one index per model. Uses FakeEmbedder (tests/conftest.py) so no model is loaded (D-20)."""
import json

import faiss
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from conftest import FakeEmbedder
from vsearch.index import IndexOutOfDate, build_index, load_index, main, self_retrieval

KEYS = ["openclip", "fashionclip"]


def test_tc_cat_05_given_a_catalogue_when_indexed_then_each_model_has_aligned_files(built_catalogue):
    """Given the catalogue, when both models are indexed, then each folder holds vectors.faiss,
    ids.npy in catalogue order, and meta.json naming the model, dimension and count."""
    cat = pd.read_parquet(built_catalogue / "catalogue.parquet")
    for key in KEYS:
        build_index(built_catalogue, FakeEmbedder(key))
        folder = built_catalogue / "index" / key
        index = faiss.read_index(str(folder / "vectors.faiss"))
        ids = np.load(folder / "ids.npy")
        meta = json.loads((folder / "meta.json").read_text())
        assert index.ntotal == len(cat) == len(ids)
        assert ids.tolist() == cat["product_id"].tolist()
        assert meta["model"] == key and meta["dim"] == 6 and meta["count"] == len(cat)
        assert isinstance(index, faiss.IndexFlatIP)  # exact inner product (D-05)


def test_tc_cat_05_given_an_index_then_row_i_is_the_vector_of_product_i(built_catalogue):
    """Given an index, when row i is read back, then it equals the embedding of product ids[i]'s
    image, so a search hit maps to the right product."""
    embedder = FakeEmbedder("openclip")
    build_index(built_catalogue, embedder)
    index, ids, _ = load_index(built_catalogue, "openclip")
    cat = pd.read_parquet(built_catalogue / "catalogue.parquet").set_index("product_id")
    for i in (0, len(ids) // 2, len(ids) - 1):
        expected = embedder.embed([Image.open(built_catalogue / cat.loc[ids[i], "image_path"])])[0]
        np.testing.assert_allclose(index.reconstruct(i), expected, atol=1e-6)


def test_tc_cat_06_given_an_index_then_every_vector_has_length_one(built_catalogue):
    """Given an index, when every stored vector's length is computed, then it is 1 within 0.001."""
    build_index(built_catalogue, FakeEmbedder("openclip"))
    index, _, _ = load_index(built_catalogue, "openclip")
    lengths = np.linalg.norm(index.reconstruct_n(0, index.ntotal), axis=1)
    assert np.all(np.abs(lengths - 1) < 1e-3)


def test_tc_cat_07_given_catalogue_images_as_queries_then_they_find_themselves(built_catalogue):
    """Given catalogue images searched against their own model's index, then at least 99% return
    themselves at rank 1, and the check reports any that don't."""
    embedder = FakeEmbedder("openclip")
    build_index(built_catalogue, embedder)
    check = self_retrieval(built_catalogue, embedder, n=20, seed=1)
    assert check["n"] == 20
    assert check["rank1"] >= 0.99 * check["n"]
    assert check["misses"] == []


def test_tc_cat_08_given_the_catalogue_changed_when_the_index_loads_then_it_refuses(built_catalogue):
    """Given an index built before the catalogue changed, when it is loaded (as the API and the
    eval will), then it refuses with 'Index is out of date: run make index'."""
    build_index(built_catalogue, FakeEmbedder("openclip"))
    cat = pd.read_parquet(built_catalogue / "catalogue.parquet")
    cat.iloc[:-1].to_parquet(built_catalogue / "catalogue.parquet", index=False)
    with pytest.raises(IndexOutOfDate, match="Index is out of date: run make index"):
        load_index(built_catalogue, "openclip")


def test_tc_cat_08_given_an_image_changed_when_the_index_loads_then_it_refuses(built_catalogue):
    """Same refusal when a product's image file changes but the product list doesn't."""
    build_index(built_catalogue, FakeEmbedder("openclip"))
    first = pd.read_parquet(built_catalogue / "catalogue.parquet")["image_path"].iloc[0]
    (built_catalogue / first).write_bytes((built_catalogue / first).read_bytes() + b"\0")
    with pytest.raises(IndexOutOfDate):
        load_index(built_catalogue, "openclip")


def test_given_no_index_when_it_loads_then_it_says_which_command_to_run(built_catalogue):
    with pytest.raises(FileNotFoundError, match="No openclip index: run make index"):
        load_index(built_catalogue, "openclip")


class Factory:
    """Records which models `make index` actually loads."""

    def __init__(self):
        self.loaded = []

    def __call__(self, key):
        self.loaded.append(key)
        return FakeEmbedder(key)


def test_given_up_to_date_indexes_when_make_index_runs_again_then_no_model_is_loaded(built_catalogue, capsys):
    """Given both indexes are current, when `make index` runs again, then no model is loaded or
    run, and the output reports each index as reused with its stored self-check."""
    factory = Factory()
    main(["--data-dir", str(built_catalogue)], make_embedder=factory)
    assert factory.loaded == KEYS
    capsys.readouterr()

    rerun = Factory()
    main(["--data-dir", str(built_catalogue)], make_embedder=rerun)
    out = capsys.readouterr().out
    assert rerun.loaded == []
    for key in KEYS:
        assert f"{key}: up to date, reused" in out
        assert f"{key}: self-check (from the build) " in out


def test_given_force_when_make_index_runs_then_both_are_rebuilt(built_catalogue, capsys):
    main(["--data-dir", str(built_catalogue)], make_embedder=Factory())
    again = Factory()
    main(["--data-dir", str(built_catalogue), "--force"], make_embedder=again)
    assert again.loaded == KEYS
    assert capsys.readouterr().out.count(": built ") == 4


def test_given_no_catalogue_when_make_index_runs_then_it_says_to_build_one(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_:
        main(["--data-dir", str(tmp_path)], make_embedder=Factory())
    assert exit_.value.code == 1
    err = capsys.readouterr().err
    assert "No catalogue in" in err and "run make catalogue first" in err
