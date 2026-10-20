"""Score the random baseline and both models on the labelled query photos (US-04).

    make eval        dev split only
    make eval-test   dev and test; every test read is logged (US-04 AC5, D-07)

Writes eval/results/<date>.json (data-contracts §6) and eval/results/<date>-queries.csv, one row
per query and system with its top 10, so every number traces back to photos.
Relevance: same article type and colour (strict), or same type (type_only) (D-06).
"""
import argparse
import hashlib
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from vsearch.index import load_index
from vsearch.queries import QUERIES, SEED

# US-04: the three rows every results table carries (eval-plan §5)
SYSTEMS = ["random", "openclip", "fashionclip"]
RULES = ["strict", "type_only"]
K = 10
BOOTSTRAP = 1000
RESULTS = Path("eval/results")


def relevant(query, product, rule):
    if product["article_type"] != query["article_type"]:
        return False
    return rule == "type_only" or product["base_colour"] == query["base_colour"]


def metrics(ranked, per_query=False):
    """Recall@10 (hit rate), Precision@10 and MRR from ranked 0/1 relevance lists (eval-plan §4)."""
    hits, precisions, rrs = [], [], []
    for flags in ranked:
        top = list(flags)[:K]
        first = next((i for i, f in enumerate(top, 1) if f), None)
        hits.append(1.0 if first else 0.0)
        precisions.append(sum(top) / K)
        rrs.append(1 / first if first else 0.0)
    if per_query:
        return {"recall_at_10": hits, "precision_at_10": precisions, "mrr": rrs}
    return {"recall_at_10": float(np.mean(hits)), "precision_at_10": float(np.mean(precisions)),
            "mrr": float(np.mean(rrs))}


def bootstrap_interval(scores, seed=SEED, resamples=BOOTSTRAP):
    """95% percentile interval of the mean, resampling queries with replacement (eval-plan §4)."""
    scores = np.asarray(scores, dtype=float)
    rng = np.random.default_rng(seed)
    means = scores[rng.integers(0, len(scores), size=(resamples, len(scores)))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def random_ranking(query_id, product_ids, seed=SEED):
    """Ten distinct products, drawn from a generator seeded by the run seed and the query id, so a
    query's random list doesn't change when other queries are added."""
    key = int(hashlib.sha256(f"{seed}:{query_id}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(key)
    return [product_ids[i] for i in rng.choice(len(product_ids), size=K, replace=False)]


def _commit():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _model_rankings(data_dir, queries_dir, labels, embedder):
    index, ids, _ = load_index(data_dir, embedder.key)
    if labels.empty:
        return [], []
    images = [Image.open(Path(queries_dir) / f"{q}.jpg") for q in labels["query_id"]]
    vectors = embedder.embed(images)
    for img in images:
        img.close()
    scores, rows = index.search(np.ascontiguousarray(vectors, dtype=np.float32), K)
    return [[int(ids[r]) for r in row] for row in rows], scores[:, 0].tolist()


def evaluate(data_dir="data", queries_dir=QUERIES, results_dir=RESULTS, splits=("dev",), embedders=None,
             run_date=None, seed=SEED):
    """US-04: write the results file and the per-query file; return the results file's path."""
    data_dir, results_dir = Path(data_dir), Path(results_dir)
    run_date = run_date or date.today().isoformat()
    results_dir.mkdir(parents=True, exist_ok=True)
    if "test" in splits:
        with open(results_dir / "test-reads.log", "a") as log:
            log.write(f"{run_date} {datetime.now().isoformat(timespec='seconds')} commit {_commit()}\n")

    catalogue = pd.read_parquet(data_dir / "catalogue.parquet")
    products = catalogue.set_index("product_id")[["article_type", "base_colour"]].to_dict("index")
    product_ids = catalogue["product_id"].tolist()
    labels = pd.read_csv(Path(queries_dir) / "labels.csv", dtype=str, keep_default_na=False)
    labels = labels[(labels["kind"] == "in_catalogue") & labels["split"].isin(splits)].reset_index(drop=True)
    queries = labels.to_dict("records")
    stocked = catalogue.groupby(["article_type", "base_colour"]).size().to_dict()
    matches = [int(stocked.get((q["article_type"], q["base_colour"]), 0)) for q in queries]  # D-30

    rankings = {"random": ([random_ranking(q["query_id"], product_ids, seed) for q in queries], [None] * len(queries))}
    if embedders is None:
        from vsearch.embed import ClipEmbedder
        embedders = {key: ClipEmbedder(key) for key in SYSTEMS if key != "random"}
    for key in SYSTEMS[1:]:
        rankings[key] = _model_rankings(data_dir, queries_dir, labels, embedders[key])

    rows, per_query = [], []
    for system in SYSTEMS:
        ranked_ids, top_scores = rankings[system]
        flags = {rule: [[relevant(q, products[p], rule) for p in ranking] for q, ranking in zip(queries, ranked_ids)]
                 for rule in RULES}
        for q, ranking, top, strict, loose, n_match in zip(queries, ranked_ids, top_scores, flags["strict"],
                                                           flags["type_only"], matches):
            per_query.append({
                "query_id": q["query_id"], "system": system, "split": q["split"],
                "article_type": q["article_type"], "base_colour": q["base_colour"],
                "strict_matches_in_catalogue": n_match,
                "setting": q["notes"].split(";")[0].strip(),
                "first_relevant_rank_strict": next((i for i, f in enumerate(strict, 1) if f), ""),
                "first_relevant_rank_type_only": next((i for i, f in enumerate(loose, 1) if f), ""),
                "top_score": "" if top is None else round(float(top), 4),
                "top_10": " ".join(str(p) for p in ranking),
            })
        for split in splits:
            mask = [q["split"] == split for q in queries]
            for rule in RULES:
                chosen = [f for f, m in zip(flags[rule], mask) if m]
                per = metrics(chosen, per_query=True)
                row = {"system": system, "split": split, "rule": rule, "n": len(chosen)}
                for metric, values in per.items():
                    row[metric] = round(float(np.mean(values)), 4) if values else 0.0
                    row[f"{metric}_ci"] = [round(v, 4) for v in bootstrap_interval(values, seed)] if values else [0.0, 0.0]
                rows.append(row)

    result = {
        "run_date": run_date,
        "commit": _commit(),
        "catalogue": {"products": len(catalogue), "article_types": int(catalogue["article_type"].nunique()), "seed": SEED},
        "queries": {split: int((labels["split"] == split).sum()) for split in splits},
        "rule": "strict = same articleType and baseColour; type_only = same articleType (D-06)",
        "unanswerable_strict": {split: sum(1 for q, n in zip(queries, matches) if q["split"] == split and n == 0)
                                for split in splits},
        "rows": rows,
    }
    path = results_dir / f"{run_date}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    pd.DataFrame(per_query).to_csv(results_dir / f"{run_date}-queries.csv", index=False)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=["dev", "test"], default="dev",
                        help="test also scores the test split, and logs that it was read")
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args(argv)
    splits = ["dev", "test"] if args.split == "test" else ["dev"]
    if "test" in splits:
        print("Reading the test split. This read is logged in eval/results/test-reads.log (D-07).")
    path = evaluate(args.data_dir, splits=splits)
    data = json.loads(path.read_text())
    print(f"Wrote {path} and {path.with_name(path.stem + '-queries.csv')}")
    for split in splits:
        print(f"\n{split} ({data['queries'][split]} in-catalogue photos), strict rule:")
        print(f"  {'system':<12}{'Recall@10':>22}{'P@10':>8}{'MRR':>8}")
        for r in data["rows"]:
            if r["split"] == split and r["rule"] == "strict":
                lo, hi = r["recall_at_10_ci"]
                print(f"  {r['system']:<12}{r['recall_at_10']:>8.2f} ({lo:.2f}–{hi:.2f})   "
                      f"{r['precision_at_10']:>8.2f}{r['mrr']:>8.2f}")


if __name__ == "__main__":
    main()
