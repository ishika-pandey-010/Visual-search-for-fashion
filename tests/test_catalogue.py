"""US-01 Build the catalogue. Each test name cites the UAT case it automates."""
import json
import re

import pandas as pd

from vsearch.catalogue import (
    CATALOGUE_COLUMNS,
    CATALOGUE_TYPES,
    RESERVED_TYPES,
    SOURCES,
    build,
)

PER_TYPE = 4  # below the fixture's 6 per type, so the cap is exercised


def run(sources, out, seed=2026):
    labels, images, _ = sources
    return build(labels, images, out, seed=seed, per_type=PER_TYPE)


def test_tc_cat_01_given_the_sources_when_built_then_columns_types_and_cap_hold(sources, tmp_path):
    """Given both sources, when the catalogue is built, then it has the contract's columns,
    only the 10 catalogue types, and no type over the per-type cap."""
    run(sources, tmp_path)
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    assert list(cat.columns) == CATALOGUE_COLUMNS
    assert set(cat["article_type"]) == set(CATALOGUE_TYPES)
    assert cat["article_type"].value_counts().max() <= PER_TYPE
    assert cat["product_id"].is_unique


def test_tc_cat_01_given_a_built_catalogue_then_each_image_is_the_source_bytes(sources, tmp_path):
    """Given a built catalogue, when its image files are read, then each is the source JPEG,
    byte for byte (D-21), at the path the row names."""
    _, images, _ = sources
    run(sources, tmp_path)
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    source = dict(zip(images["product_id"], images["image_bytes"]))
    for row in cat.itertuples():
        assert row.image_path == f"images/{row.product_id}.jpg"
        assert (tmp_path / row.image_path).read_bytes() == source[row.product_id]


def test_tc_cat_02_given_the_same_seed_when_built_twice_then_ids_and_order_match(sources, tmp_path):
    """Given the same inputs and seed, when built twice, then the product IDs and their order match."""
    run(sources, tmp_path / "a")
    run(sources, tmp_path / "b")
    a = pd.read_parquet(tmp_path / "a" / "catalogue.parquet")["product_id"].tolist()
    b = pd.read_parquet(tmp_path / "b" / "catalogue.parquet")["product_id"].tolist()
    assert a == b


def test_given_a_different_seed_when_built_then_the_sample_changes(sources, tmp_path):
    """Guards TC-CAT-02 from passing trivially: the seed must actually drive the sample."""
    run(sources, tmp_path / "a", seed=2026)
    run(sources, tmp_path / "b", seed=7)
    a = set(pd.read_parquet(tmp_path / "a" / "catalogue.parquet")["product_id"])
    b = set(pd.read_parquet(tmp_path / "b" / "catalogue.parquet")["product_id"])
    assert a != b


def test_tc_cat_03_given_unusable_products_when_built_then_dropped_and_counted(sources, tmp_path):
    """Given a product with no colour, one with no image, one with a 150 px image and one with
    broken bytes, when built, then none is in the catalogue and each is counted by reason."""
    _, _, bad = sources
    run(sources, tmp_path)
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    report = json.loads((tmp_path / "catalogue-report.json").read_text())
    for reason, pid in bad.items():
        assert pid not in set(cat["product_id"]), reason
        assert report["dropped"][reason] == 1, reason
        assert pid in report["dropped_ids"][reason], reason
    assert report["images_without_labels"] == 1


def test_tc_cat_04_given_reserved_types_when_built_then_only_in_the_holdout(sources, tmp_path):
    """Given the reserved types, when built, then none is in the catalogue and all are in the
    holdout, with their images written; types that are neither are in neither file."""
    run(sources, tmp_path)
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    hold = pd.read_parquet(tmp_path / "holdout.parquet")
    assert not set(cat["article_type"]) & set(RESERVED_TYPES)
    assert set(hold["article_type"]) == set(RESERVED_TYPES)
    assert list(hold.columns) == CATALOGUE_COLUMNS
    assert all((tmp_path / p).exists() for p in hold["image_path"])
    assert "Socks" not in set(cat["article_type"]) | set(hold["article_type"])


def test_report_records_counts_seed_and_pinned_sources(sources, tmp_path):
    """Given a build, then the report says what went in: source SHAs, seed, cap and counts by type."""
    report = run(sources, tmp_path)
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    assert report == json.loads((tmp_path / "catalogue-report.json").read_text())
    assert report["seed"] == 2026 and report["per_type_limit"] == PER_TYPE
    assert report["catalogue"]["products"] == len(cat)
    assert report["catalogue"]["by_type"] == cat["article_type"].value_counts().to_dict()
    assert report["sources"] == SOURCES


def test_sources_are_pinned_to_commit_shas():
    """D-19: both sources name a full 40-character commit SHA, never a branch."""
    assert set(SOURCES) == {"labels", "images"}
    for source in SOURCES.values():
        assert re.fullmatch(r"[0-9a-f]{40}", source["revision"])


def test_manifest_lists_the_catalogue_ids_types_and_colours(sources, tmp_path):
    """Given a built catalogue, when the manifest is written, then it holds exactly the catalogue's
    product IDs, types and colours, in catalogue order."""
    from vsearch.catalogue import write_manifest

    run(sources, tmp_path)
    write_manifest(tmp_path / "catalogue.parquet", tmp_path / "manifest.csv")
    cat = pd.read_parquet(tmp_path / "catalogue.parquet")
    manifest = pd.read_csv(tmp_path / "manifest.csv")
    assert manifest.to_dict("records") == cat[["product_id", "article_type", "base_colour"]].to_dict("records")


def test_given_the_download_fails_when_make_catalogue_runs_then_it_says_so_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    """Given no network, when `make catalogue` runs, then it prints one plain sentence with the
    next step, exits non-zero, and leaves the data directory untouched."""
    import pytest

    import vsearch.catalogue as catalogue

    def offline():
        raise OSError("Connection refused")

    monkeypatch.setattr(catalogue, "load_sources", offline)
    monkeypatch.setattr("sys.argv", ["catalogue", "--data-dir", str(tmp_path / "data")])
    with pytest.raises(SystemExit) as exit_:
        catalogue.main()
    assert exit_.value.code == 1
    assert "Couldn't download the datasets" in capsys.readouterr().err
    assert not (tmp_path / "data").exists()


def test_given_a_rebuild_when_it_matches_the_manifest_then_it_says_so(sources, tmp_path, monkeypatch, capsys):
    """Given a committed manifest, when the same catalogue is rebuilt, then the output says it
    matches; when the catalogue changes, it says by how many products."""
    import vsearch.catalogue as catalogue

    labels, images, _ = sources
    manifest = tmp_path / "manifest.csv"
    monkeypatch.setattr(catalogue, "load_sources", lambda: (labels, images))
    monkeypatch.setattr(catalogue, "MANIFEST", manifest)
    monkeypatch.setattr(catalogue, "PER_TYPE", PER_TYPE)
    monkeypatch.setattr("sys.argv", ["catalogue", "--data-dir", str(tmp_path / "data")])

    catalogue.main()
    assert "Wrote" in capsys.readouterr().out and manifest.exists()
    catalogue.main()
    assert "matches the committed manifest" in capsys.readouterr().out

    # Cap 4 -> 3 removes one product from each of the 9 full types; Tshirts has only 2 usable
    # rows in the fixture (all four bad rows are Tshirts), so it loses none.
    monkeypatch.setattr(catalogue, "PER_TYPE", PER_TYPE - 1)
    catalogue.main()
    out = capsys.readouterr().out
    assert "differs from the committed manifest: 0 added, 9 removed" in out
