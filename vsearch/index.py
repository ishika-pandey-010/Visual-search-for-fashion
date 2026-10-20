"""One exact FAISS index per model over the catalogue (US-02).

Vectors are L2-normalised, so inner product equals cosine similarity (D-05). Each index records a
hash of the catalogue it was built from; loading one built from a different catalogue is refused.

Usage:  uv run python -m vsearch.index [--data-dir data] [--models openclip fashionclip] [--force]
"""
import argparse
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from PIL import Image

BATCH = 64
SELF_CHECK_N = 200
SELF_CHECK_SEED = 2026


class IndexOutOfDate(Exception):
    pass


def catalogue_hash(data_dir):
    """Hash of every product's id, labels and image bytes, so a changed image counts as a change."""
    data_dir = Path(data_dir)
    cat = pd.read_parquet(data_dir / "catalogue.parquet")
    h = hashlib.sha256()
    for row in cat.itertuples(index=False):
        image = hashlib.sha256((data_dir / row.image_path).read_bytes()).hexdigest()
        h.update(f"{row.product_id},{row.article_type},{row.base_colour},{image}\n".encode())
    return h.hexdigest()


def _embed_paths(embedder, paths, progress=None):
    out = []
    for start in range(0, len(paths), BATCH):
        images = [Image.open(p) for p in paths[start:start + BATCH]]
        out.append(embedder.embed(images))
        for img in images:
            img.close()
        if progress:
            progress(min(start + BATCH, len(paths)), len(paths))
    return np.concatenate(out).astype(np.float32)


def build_index(data_dir, embedder, progress=None):
    """US-02: embed every catalogue image and write index/<model>/{vectors.faiss, ids.npy, meta.json}."""
    data_dir = Path(data_dir)
    cat = pd.read_parquet(data_dir / "catalogue.parquet")
    started = time.perf_counter()
    vectors = _embed_paths(embedder, [data_dir / p for p in cat["image_path"]], progress)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)  # normalise again: cheap, and the index relies on it
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    folder = data_dir / "index" / embedder.key
    folder.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(folder / "vectors.faiss"))
    np.save(folder / "ids.npy", cat["product_id"].to_numpy(dtype=np.int64))
    meta = {
        **embedder.describe(),
        "count": int(index.ntotal),
        "catalogue_hash": catalogue_hash(data_dir),
        "built": date.today().isoformat(),
        "embed_seconds": round(time.perf_counter() - started, 1),
    }
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def load_index(data_dir, key):
    """(faiss index, product ids, meta). Refuses an index built from a different catalogue (US-02 AC4)."""
    folder = Path(data_dir) / "index" / key
    if not (folder / "meta.json").exists():
        raise FileNotFoundError(f"No {key} index: run make index")
    meta = json.loads((folder / "meta.json").read_text())
    if meta["catalogue_hash"] != catalogue_hash(data_dir):
        raise IndexOutOfDate(f"Index is out of date: run make index ({key} was built {meta['built']} "
                             "from a different catalogue)")
    return faiss.read_index(str(folder / "vectors.faiss")), np.load(folder / "ids.npy"), meta


def self_retrieval(data_dir, embedder, n=SELF_CHECK_N, seed=SELF_CHECK_SEED):
    """Sanity check on the wiring, not a quality claim (US-02 AC3): embed n catalogue images afresh
    and count how many come back as their own rank-1 result."""
    data_dir = Path(data_dir)
    index, ids, _ = load_index(data_dir, embedder.key)
    cat = pd.read_parquet(data_dir / "catalogue.parquet")
    sample = cat.sample(n=min(n, len(cat)), random_state=seed)
    vectors = _embed_paths(embedder, [data_dir / p for p in sample["image_path"]])
    _, rows = index.search(vectors, 1)
    top = ids[rows[:, 0]]
    misses = [(int(pid), int(got)) for pid, got in zip(sample["product_id"], top) if pid != got]
    return {"n": len(sample), "rank1": len(sample) - len(misses), "misses": misses}


def _is_current(data_dir, key):
    try:
        load_index(data_dir, key)
        return True
    except (FileNotFoundError, IndexOutOfDate):
        return False


def _load_real_model(key):
    from vsearch.embed import MODELS, ClipEmbedder

    print(f"{key}: loading {MODELS[key]['label']}…", flush=True)
    return ClipEmbedder(key)


def _report_check(key, check, source=""):
    verdict = "ok" if check["rank1"] >= 0.99 * check["n"] else "FAILED (expected at least 99%)"
    print(f"{key}: self-check {source}{check['rank1']} of {check['n']} catalogue images "
          f"found themselves at rank 1, {verdict}")
    for pid, got in check["misses"]:
        print(f"  {pid} returned {got} first")


def main(argv=None, make_embedder=None):
    """`make_embedder(key)` lets tests pass fakes; by default the real model is loaded, and only
    when its index has to be built."""
    from vsearch.embed import MODELS

    make_embedder = make_embedder or _load_real_model
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    parser.add_argument("--force", action="store_true", help="rebuild even if the index is up to date")
    args = parser.parse_args(argv)
    data_dir = Path(args.data_dir)
    if not (data_dir / "catalogue.parquet").exists():
        print(f"No catalogue in {data_dir}/: run make catalogue first.", file=sys.stderr)
        sys.exit(1)

    for key in args.models:
        folder = data_dir / "index" / key
        if _is_current(data_dir, key) and (folder / "self-check.json").exists() and not args.force:
            meta = json.loads((folder / "meta.json").read_text())
            print(f"{key}: up to date, reused (built {meta['built']}, {meta['count']:,} products)")
            _report_check(key, json.loads((folder / "self-check.json").read_text()), "(from the build) ")
            continue

        embedder = make_embedder(key)

        def progress(done, total):
            if done == total or done % (BATCH * 10) == 0:
                print(f"{key}: embedded {done:,} of {total:,}", flush=True)

        meta = build_index(data_dir, embedder, progress)
        print(f"{key}: built {meta['count']:,} vectors of {meta['dim']} in {meta['embed_seconds']} s")
        check = self_retrieval(data_dir, embedder)
        (folder / "self-check.json").write_text(json.dumps(check, indent=2) + "\n")
        _report_check(key, check)


if __name__ == "__main__":
    main()
