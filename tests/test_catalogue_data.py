"""US-01 checks on the real catalogue (make catalogue first). Run with `make test-data` (D-20)."""
import json
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from vsearch.catalogue import (
    CATALOGUE_COLUMNS,
    CATALOGUE_TYPES,
    MANIFEST,
    MIN_SHORT_SIDE,
    PER_TYPE,
    RESERVED_TYPES,
    SOURCES,
)

DATA = Path("data")
pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(not (DATA / "catalogue.parquet").exists(), reason="run make catalogue first"),
]


@pytest.fixture(scope="module")
def catalogue():
    return pd.read_parquet(DATA / "catalogue.parquet")


def test_tc_cat_01_real_catalogue_has_the_ten_types_capped_at_500(catalogue):
    """Given the real build, then it has the contract's columns, all 10 types, none over 500,
    and every image on disk is at least 200 px on its short side."""
    assert list(catalogue.columns) == CATALOGUE_COLUMNS
    assert set(catalogue["article_type"]) == set(CATALOGUE_TYPES)
    assert catalogue["article_type"].value_counts().max() <= PER_TYPE
    for path in catalogue["image_path"]:
        with Image.open(DATA / path) as img:
            assert min(img.size) >= MIN_SHORT_SIDE, path


def test_tc_cat_02_real_catalogue_matches_the_committed_manifest(catalogue):
    """Given the committed manifest, when compared with this machine's build, then the product
    IDs, types, colours and order are identical (NFR-03)."""
    manifest = pd.read_csv(MANIFEST)
    built = catalogue[list(manifest.columns)].reset_index(drop=True)
    pd.testing.assert_frame_equal(built, manifest, check_dtype=False)


def test_tc_cat_03_real_report_counts_every_drop():
    """Given the real build, then the report counts drops by reason and they match the ID lists."""
    report = json.loads((DATA / "catalogue-report.json").read_text())
    assert report["sources"] == SOURCES
    for reason, n in report["dropped"].items():
        assert n == len(report["dropped_ids"][reason])


def test_tc_cat_04_real_holdout_has_only_reserved_types(catalogue):
    """Given the real build, then reserved types are only in the holdout."""
    holdout = pd.read_parquet(DATA / "holdout.parquet")
    assert not set(catalogue["article_type"]) & set(RESERVED_TYPES)
    assert set(holdout["article_type"]) == set(RESERVED_TYPES)
    assert not set(catalogue["product_id"]) & set(holdout["product_id"])
