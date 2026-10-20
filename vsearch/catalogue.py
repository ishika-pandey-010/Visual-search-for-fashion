"""Build the searchable catalogue from the two pinned Hugging Face copies (US-01).

Labels come from the ashraq copy, images from the ceyda copy, joined on product id (D-02).
`build()` does no I/O beyond writing its outputs, so tests can feed it a generated fixture (D-20).

Usage:  uv run python -m vsearch.catalogue [--data-dir data] [--seed 2026]
"""
import argparse
import io
import json
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, UnidentifiedImageError

# US-01: the 10 catalogue types and the 3 reserved out-of-catalogue types (D-03)
CATALOGUE_TYPES = [
    "Tshirts", "Shirts", "Tops", "Kurtas", "Dresses",
    "Jeans", "Trousers", "Shorts", "Casual Shoes", "Handbags",
]
RESERVED_TYPES = ["Sarees", "Watches", "Sunglasses"]
CATALOGUE_COLUMNS = ["product_id", "article_type", "base_colour", "gender", "name", "image_path"]
PER_TYPE = 500
SEED = 2026
MIN_SHORT_SIDE = 200

# Pinned to commit SHAs, never a branch (D-19). Checked 2026-10-20.
SOURCES = {
    "labels": {
        "repo": "ashraq/fashion-product-images-small",
        "revision": "3859c76db2f6f3d3b9a3863345e3ccdbff75879d",
        "files": [
            "data/train-00000-of-00002-6cff4c59f91661c3.parquet",
            "data/train-00001-of-00002-bb459e5ac5f01e71.parquet",
        ],
    },
    "images": {
        "repo": "ceyda/fashion-products-small",
        "revision": "ef520080129df6ec7fda0df347b5f7eacdf0dc1c",
        "files": [
            "data/train-00000-of-00002-357f4cbabe1a8ea6.parquet",
            "data/train-00001-of-00002-cbe936f1880f5e72.parquet",
        ],
    },
}
LABEL_COLUMNS = ["id", "gender", "articleType", "baseColour", "productDisplayName"]
DROP_REASONS = ["no_label", "no_image", "image_unreadable", "image_too_small"]
MANIFEST = Path("eval/catalogue-manifest.csv")
MANIFEST_COLUMNS = ["product_id", "article_type", "base_colour"]


def load_sources():
    """Download the pinned parquet files (cached by huggingface_hub) and return
    (labels, images): labels in the ashraq schema, images as product_id + image_bytes."""
    from huggingface_hub import hf_hub_download

    def read(name, columns):
        src = SOURCES[name]
        paths = [
            hf_hub_download(src["repo"], f, repo_type="dataset", revision=src["revision"])
            for f in src["files"]
        ]
        return pd.concat([pd.read_parquet(p, columns=columns) for p in paths], ignore_index=True)

    labels = read("labels", LABEL_COLUMNS)
    raw = read("images", ["id", "image"])
    images = pd.DataFrame({
        "product_id": raw["id"].astype(int),
        "image_bytes": [img["bytes"] for img in raw["image"]],
    })
    return labels, images


def _image_problem(data):
    """None if the image is usable, else the drop reason."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except (UnidentifiedImageError, OSError):
        return "image_unreadable"
    return "image_too_small" if min(width, height) < MIN_SHORT_SIDE else None


def _sample(rows, types, per_type, seed):
    """Up to `per_type` rows of each type, seeded; ordered by product id (US-01 AC2)."""
    parts = []
    for type_ in types:
        of_type = rows[rows["article_type"] == type_].sort_values("product_id")
        parts.append(of_type.sample(n=min(per_type, len(of_type)), random_state=seed))
    return pd.concat(parts).sort_values("product_id").reset_index(drop=True)


def build(labels, images, out_dir, seed=SEED, per_type=PER_TYPE):
    """Write catalogue.parquet, holdout.parquet, images/ and catalogue-report.json into out_dir.
    Unusable rows are dropped before sampling (OQ-04). Returns the report."""
    out_dir = Path(out_dir)
    (out_dir / "images").mkdir(parents=True, exist_ok=True)

    wanted = labels[labels["articleType"].isin(CATALOGUE_TYPES + RESERVED_TYPES)].copy()
    wanted["id"] = wanted["id"].astype(int)
    image_bytes = dict(zip(images["product_id"].astype(int), images["image_bytes"]))
    dropped = {reason: [] for reason in DROP_REASONS}

    usable = []
    for row in wanted.sort_values("id").itertuples(index=False):
        if pd.isna(row.baseColour) or pd.isna(row.productDisplayName):
            dropped["no_label"].append(row.id)
        elif row.id not in image_bytes:
            dropped["no_image"].append(row.id)
        elif problem := _image_problem(image_bytes[row.id]):
            dropped[problem].append(row.id)
        else:
            usable.append({
                "product_id": row.id,
                "article_type": row.articleType,
                "base_colour": row.baseColour,
                "gender": row.gender,
                "name": row.productDisplayName,
                "image_path": f"images/{row.id}.jpg",
            })
    usable = pd.DataFrame(usable, columns=CATALOGUE_COLUMNS)

    catalogue = _sample(usable, CATALOGUE_TYPES, per_type, seed)
    holdout = _sample(usable, RESERVED_TYPES, per_type, seed)
    for table in (catalogue, holdout):
        for row in table.itertuples(index=False):
            (out_dir / row.image_path).write_bytes(image_bytes[row.product_id])  # D-21: source bytes
    catalogue.to_parquet(out_dir / "catalogue.parquet", index=False)
    holdout.to_parquet(out_dir / "holdout.parquet", index=False)

    labelled_ids = set(labels["id"].astype(int))
    report = {
        "sources": SOURCES,
        "seed": seed,
        "per_type_limit": per_type,
        "catalogue": {
            "products": len(catalogue),
            "by_type": catalogue["article_type"].value_counts().to_dict(),
        },
        "holdout": {
            "products": len(holdout),
            "by_type": holdout["article_type"].value_counts().to_dict(),
        },
        "dropped": {reason: len(ids) for reason, ids in dropped.items()},
        "dropped_ids": {reason: [int(i) for i in ids] for reason, ids in dropped.items()},
        "images_without_labels": sum(1 for pid in image_bytes if pid not in labelled_ids),
    }
    (out_dir / "catalogue-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def write_manifest(catalogue_path, manifest_path=None):
    """The committed record of which products the catalogue holds, so anyone's rebuild can be
    checked against it (NFR-03). Small enough for git; the images and parquet aren't.
    Returns (added, removed) against the previous manifest, or None if there wasn't one."""
    catalogue = pd.read_parquet(catalogue_path, columns=MANIFEST_COLUMNS)
    manifest_path = Path(manifest_path or MANIFEST)
    change = None
    if manifest_path.exists():
        before = set(pd.read_csv(manifest_path)["product_id"])
        after = set(catalogue["product_id"])
        change = (len(after - before), len(before - after))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    catalogue.to_csv(manifest_path, index=False)
    return change


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    print("Downloading the pinned datasets (cached after the first run)…")
    try:
        labels, images = load_sources()
    except OSError as err:  # network errors from huggingface_hub are OSError subclasses
        print(f"Couldn't download the datasets ({err}). Check the internet connection and run "
              "make catalogue again; nothing was written.", file=sys.stderr)
        sys.exit(1)
    report = build(labels, images, args.data_dir, seed=args.seed, per_type=PER_TYPE)
    print(f"Catalogue: {report['catalogue']['products']:,} products "
          f"across {len(report['catalogue']['by_type'])} types")
    for type_, n in sorted(report["catalogue"]["by_type"].items()):
        print(f"  {type_:<14}{n:>5}")
    print(f"Holdout: {report['holdout']['products']:,} products ({', '.join(RESERVED_TYPES)})")
    print("Dropped: " + ", ".join(f"{k} {v}" for k, v in report["dropped"].items()))
    print(f"Wrote {args.data_dir}/catalogue.parquet, holdout.parquet, images/ and catalogue-report.json")
    if args.seed != SEED:
        print(f"Seed {args.seed} isn't the project seed, so {MANIFEST} was left alone.")
        return
    change = write_manifest(Path(args.data_dir) / "catalogue.parquet", MANIFEST)
    if change is None:
        print(f"Wrote {MANIFEST}. Commit it: it is the record of what was evaluated.")
    elif change == (0, 0):
        print(f"The catalogue matches the committed manifest ({MANIFEST}).")
    else:
        print(f"The catalogue differs from the committed manifest: {change[0]} added, {change[1]} removed. "
              f"Commit {MANIFEST} only if you meant to change the catalogue, and log why in docs/decisions.md.")


if __name__ == "__main__":
    main()
