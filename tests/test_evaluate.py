"""US-04 Retrieval eval harness. Fake embedders and a fixture catalogue, so no model loads (D-20)."""
import json

import pandas as pd
import pytest

from conftest import FakeEmbedder
from vsearch.evaluate import (
    SYSTEMS,
    bootstrap_interval,
    evaluate,
    metrics,
    random_ranking,
    relevant,
)
from vsearch.index import build_index
from vsearch.queries import LABEL_COLUMNS, prepare_image

KEYS = ["openclip", "fashionclip"]


def test_tc_eval_05_given_a_hand_built_ranking_then_the_metrics_match_the_hand_worked_values():
    """Three queries, ten results each, relevant (1) or not (0):
      q1 relevant at ranks 1 and 3   -> hit 1, precision 2/10, reciprocal rank 1
      q2 relevant at rank 4          -> hit 1, precision 1/10, reciprocal rank 1/4
      q3 nothing relevant            -> hit 0, precision 0,    reciprocal rank 0
    Recall@10 = 2/3, Precision@10 = 3/30 = 0.1, MRR = (1 + 0.25 + 0) / 3 = 0.41667."""
    ranked = [
        [1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    m = metrics(ranked)
    assert m["recall_at_10"] == pytest.approx(2 / 3)
    assert m["precision_at_10"] == pytest.approx(0.1)
    assert m["mrr"] == pytest.approx(1.25 / 3)
    per_query = metrics(ranked, per_query=True)
    assert per_query["mrr"] == pytest.approx([1.0, 0.25, 0.0])


def test_tc_eval_05_only_the_first_ten_results_count():
    """A relevant result at rank 11 is not a top-10 match."""
    assert metrics([[0] * 10 + [1]])["recall_at_10"] == 0


def test_relevance_rules_strict_needs_type_and_colour_type_only_needs_type():
    query = {"article_type": "Shirts", "base_colour": "Blue"}
    assert relevant(query, {"article_type": "Shirts", "base_colour": "Blue"}, "strict")
    assert not relevant(query, {"article_type": "Shirts", "base_colour": "Navy Blue"}, "strict")
    assert relevant(query, {"article_type": "Shirts", "base_colour": "Navy Blue"}, "type_only")
    assert not relevant(query, {"article_type": "Tshirts", "base_colour": "Blue"}, "type_only")


def test_tc_eval_06_given_the_same_seed_then_the_random_ranking_is_identical():
    ids = list(range(1000, 1500))
    a = random_ranking("q001", ids, seed=2026)
    assert a == random_ranking("q001", ids, seed=2026)
    assert a != random_ranking("q002", ids, seed=2026)
    assert a != random_ranking("q001", ids, seed=7)
    assert len(a) == 10 and len(set(a)) == 10 and set(a) <= set(ids)


def test_tc_eval_07_given_per_query_scores_then_the_interval_brackets_the_mean():
    scores = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1]
    low, high = bootstrap_interval(scores, seed=2026)
    assert low <= 0.7 <= high and 0 <= low < high <= 1
    assert (low, high) == bootstrap_interval(scores, seed=2026)
    assert bootstrap_interval([1] * 12, seed=2026) == (1.0, 1.0)


@pytest.fixture
def eval_setup(built_catalogue, tmp_path):
    """Fixture catalogue, both fake indexes, and a query set made from catalogue images, plus one
    out-of-catalogue and one not-fashion photo, split dev/test."""
    embedders = {k: FakeEmbedder(k) for k in KEYS}
    for e in embedders.values():
        build_index(built_catalogue, e)
    cat = pd.read_parquet(built_catalogue / "catalogue.parquet")
    queries = tmp_path / "queries"
    queries.mkdir()
    rows = []
    for n, r in enumerate(cat.sample(12, random_state=1).itertuples(), 1):
        qid = f"q{n:03d}"
        (queries / f"{qid}.jpg").write_bytes(prepare_image((built_catalogue / r.image_path).read_bytes()))
        rows.append({"query_id": qid, "kind": "in_catalogue", "article_type": r.article_type,
                     "base_colour": r.base_colour, "split": "", "source": "owner:Q1", "notes": "flat"})
    for qid, kind, type_ in (("q101", "out_of_catalogue", "Sarees"), ("q102", "not_fashion", "")):
        (queries / f"{qid}.jpg").write_bytes(prepare_image((built_catalogue / cat.image_path[0]).read_bytes()))
        rows.append({"query_id": qid, "kind": kind, "article_type": type_, "base_colour": "",
                     "split": "", "source": "owner:Q1", "notes": "display"})
    labels = pd.DataFrame(rows, columns=LABEL_COLUMNS)
    labels["split"] = ["dev" if n % 3 == 0 else "test" for n in range(len(labels))]  # 4 dev, 8 test in-catalogue
    labels.to_csv(queries / "labels.csv", index=False)
    return built_catalogue, queries, embedders, tmp_path / "results"


def test_tc_eval_04_given_indexes_and_photos_when_evaluated_then_the_file_has_every_row(eval_setup):
    """Given the indexes and labelled photos, when `make eval-test` runs, then the results file has
    the contract's fields and a row for each system × split × rule, scoring in-catalogue photos only."""
    data_dir, queries, embedders, results = eval_setup
    path = evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders, run_date="2026-10-21")
    data = json.loads(path.read_text())
    assert path.name == "2026-10-21.json"
    assert {"run_date", "commit", "catalogue", "queries", "rows"} <= set(data)
    assert data["catalogue"]["products"] == len(pd.read_parquet(data_dir / "catalogue.parquet"))
    keys = {(r["system"], r["split"], r["rule"]) for r in data["rows"]}
    assert keys == {(s, sp, ru) for s in SYSTEMS for sp in ("dev", "test") for ru in ("strict", "type_only")}
    labels = pd.read_csv(queries / "labels.csv")
    in_cat = labels[labels.kind == "in_catalogue"]
    for r in data["rows"]:
        assert r["n"] == (in_cat.split == r["split"]).sum()
        for metric in ("recall_at_10", "precision_at_10", "mrr"):
            low, high = r[f"{metric}_ci"]
            assert 0 <= low <= r[metric] <= high <= 1
    assert data["queries"] == {"dev": int((in_cat.split == "dev").sum()), "test": int((in_cat.split == "test").sum())}


def test_tc_eval_04_a_catalogue_image_as_query_scores_a_hit_for_the_models(eval_setup):
    """The fixture queries are catalogue images, so each model finds the product itself at rank 1
    and every metric is 1 under both rules, while the random row is not."""
    data_dir, queries, embedders, results = eval_setup
    data = json.loads(evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders).read_text())
    for r in data["rows"]:
        if r["system"] != "random":
            assert r["recall_at_10"] == 1 and r["mrr"] == 1
    random_mrr = [r["mrr"] for r in data["rows"] if r["system"] == "random"]
    assert min(random_mrr) < 1


def test_tc_eval_04_per_query_file_lists_each_querys_top_ten_and_first_relevant_rank(eval_setup):
    data_dir, queries, embedders, results = eval_setup
    path = evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders, run_date="2026-10-21")
    per_query = pd.read_csv(path.with_name("2026-10-21-queries.csv"))
    assert set(per_query.columns) >= {"query_id", "system", "split", "top_10", "first_relevant_rank_strict",
                                      "first_relevant_rank_type_only", "top_score"}
    assert len(per_query) == 3 * 12
    assert per_query["top_10"].str.split().map(len).eq(10).all()


def test_tc_eval_06_given_the_same_inputs_when_evaluated_twice_then_every_number_is_identical(eval_setup):
    data_dir, queries, embedders, results = eval_setup
    a = json.loads(evaluate(data_dir, queries, results, splits=["dev"], embedders=embedders, run_date="a").read_text())
    b = json.loads(evaluate(data_dir, queries, results, splits=["dev"], embedders=embedders, run_date="b").read_text())
    assert a["rows"] == b["rows"]


def test_tc_eval_08_given_a_test_read_when_evaluated_then_it_is_logged_and_a_dev_run_is_not(eval_setup):
    """Every look at the test split leaves a dated line in test-reads.log; dev-only runs leave none."""
    data_dir, queries, embedders, results = eval_setup
    evaluate(data_dir, queries, results, splits=["dev"], embedders=embedders, run_date="2026-10-21")
    log = results / "test-reads.log"
    assert not log.exists() or log.read_text() == ""
    evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders, run_date="2026-10-21")
    evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders, run_date="2026-10-22")
    lines = log.read_text().splitlines()
    assert len(lines) == 2 and lines[0].startswith("2026-10-21") and lines[1].startswith("2026-10-22")


def test_given_a_dev_run_then_no_test_row_is_written(eval_setup):
    data_dir, queries, embedders, results = eval_setup
    data = json.loads(evaluate(data_dir, queries, results, splits=["dev"], embedders=embedders).read_text())
    assert {r["split"] for r in data["rows"]} == {"dev"}
    assert "test" not in data["queries"]


def test_given_a_split_with_no_in_catalogue_photos_when_evaluated_then_its_rows_say_n_0(eval_setup):
    """An empty split gives rows with n = 0 rather than a crash, and no model is asked to embed nothing."""
    data_dir, queries, embedders, results = eval_setup
    labels = pd.read_csv(queries / "labels.csv", dtype=str, keep_default_na=False)
    labels["split"] = "test"
    labels.to_csv(queries / "labels.csv", index=False)
    data = json.loads(evaluate(data_dir, queries, results, splits=["dev"], embedders=embedders).read_text())
    assert {r["n"] for r in data["rows"]} == {0}


def test_given_a_query_whose_type_and_colour_the_catalogue_lacks_then_it_is_counted_as_unanswerable(eval_setup):
    """D-30: a query with no catalogue product of its type and colour can't score a strict hit. It
    stays in the metrics (a shopper photographs what they see, not what's stocked), and the results
    say how many such queries each split has; the per-query file says how many matches existed."""
    data_dir, queries, embedders, results = eval_setup
    labels = pd.read_csv(queries / "labels.csv", dtype=str, keep_default_na=False)
    labels.loc[0, "base_colour"] = "Lavender"  # no fixture product is Lavender
    labels.to_csv(queries / "labels.csv", index=False)
    path = evaluate(data_dir, queries, results, splits=["dev", "test"], embedders=embedders, run_date="x")
    data = json.loads(path.read_text())
    split = labels.loc[0, "split"]
    assert data["unanswerable_strict"] == {"dev": int(split == "dev"), "test": int(split == "test")}
    per_query = pd.read_csv(path.with_name("x-queries.csv"))
    assert per_query.set_index(["query_id", "system"]).loc[(labels.loc[0, "query_id"], "openclip"), "strict_matches_in_catalogue"] == 0
