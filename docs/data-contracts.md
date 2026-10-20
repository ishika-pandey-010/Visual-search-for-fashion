# Data contracts

The schemas every part of the system agrees on. Code, tests and `scripts/results.py` follow this page; if they disagree, this page is changed first (with a decision in [decisions.md](decisions.md)) and the code second.

## 1. Sources

| Source | What we take | Rows | Image size | Licence |
| --- | --- | --- | --- | --- |
| [`ashraq/fashion-product-images-small`](https://huggingface.co/datasets/ashraq/fashion-product-images-small) | Labels: `id, gender, masterCategory, subCategory, articleType, baseColour, productDisplayName` | 44,072 | 60 × 80 px (too small to search on, D-02) | Not stated on the card (R-08) |
| [`ceyda/fashion-products-small`](https://huggingface.co/datasets/ceyda/fashion-products-small) | Images, by `id` | 42,700 | 384 × 512 px | Not stated on the card (R-08) |

Both are copies of the Kaggle "Fashion Product Images" set (Param Aggarwal, 2019), built from Myntra listings: the `link` column in the ceyda copy points at `assets.myntassets.com`. They share product IDs, so `id` is the join key. Checked through the Hugging Face dataset server on 2026-10-20.

## 2. Catalogue (`data/catalogue.parquet`, built by `make catalogue`)

One row per product in the searchable catalogue.

| Column | Type | Rule |
| --- | --- | --- |
| `product_id` | int | Unique. The shared `id` from both sources |
| `article_type` | str | One of the 10 catalogue types in D-03 |
| `base_colour` | str | Source vocabulary as written (46 values, e.g. `Navy Blue` is not `Blue`) |
| `gender` | str | `Men`, `Women`, `Unisex`, `Boys`, `Girls` |
| `name` | str | `productDisplayName` |
| `image_path` | str | `data/images/<product_id>.jpg`, 384 × 512, from the ceyda copy |

Build rules: at most 500 products per type, sampled with seed 2026; a product with no image, no label or an image under 200 px on its short side is dropped and counted in `data/catalogue-report.json`. Products of the reserved out-of-catalogue types (D-03) go to `data/holdout.parquet` and never into the catalogue.

## 3. Index (`data/index/<model>/`, built by `make index`)

| File | Content |
| --- | --- |
| `vectors.faiss` | `IndexFlatIP` over L2-normalised image embeddings (D-05) |
| `ids.npy` | `product_id` per index row, same order |
| `meta.json` | model name and pretrained tag, embedding dimension, catalogue file hash, build date |

Model keys: `openclip` = `ViT-B-32` / `laion2b_s34b_b79k`; `fashionclip` = `hf-hub:Marqo/marqo-fashionCLIP`. An index whose catalogue hash doesn't match the current catalogue is rebuilt, never reused.

## 4. API

### `POST /search`

Request: `multipart/form-data` with one field `image` (JPEG, PNG or WebP, up to 10 MB). Optional query parameters: `article_type` (filter, FR-07), `show_anyway=true` (return results even under the floor, FR-05).

Response `200`:

```json
{
  "match": true,
  "top_score": 0.31,
  "floor": 0.24,
  "quality": {"blurry": false, "dark": false},
  "model": "fashionclip",
  "timings_ms": {"decode": 4.1, "embed": 88.0, "search": 0.6, "total": 93.2},
  "results": [
    {"rank": 1, "product_id": 15970, "score": 0.31, "name": "Turtle Check Men Navy Blue Shirt",
     "article_type": "Shirts", "base_colour": "Navy Blue", "image_url": "/images/15970.jpg"}
  ],
  "types_in_top_50": ["Shirts", "Tshirts", "Tops"]
}
```

The numbers above show the shape only. When `match` is `false`, `results` is empty unless `show_anyway=true`. `results` has at most 10 items, sorted by `score` descending, ranks 1–10.

Errors: `415` not an image (`{"error": "not_an_image", "message": "That file isn't a photo. Use a JPG, PNG or WebP."}`), `413` over 10 MB, `422` image can't be decoded. Every error body has `error` (a stable code) and `message` (plain words shown to the shopper).

### `GET /products/{product_id}`

Returns one catalogue row plus `image_url`. `GET /products/{product_id}/similar` returns the same shape as `/search`, using the product's stored vector and excluding the product itself (FR-17).

### What the API never does

It never writes the uploaded image to disk, never logs image bytes or file names, and never forwards the image anywhere (FR-15).

## 5. Eval query set (`eval/queries/`)

| File | Content |
| --- | --- |
| `<query_id>.jpg` | A phone photo, EXIF stripped, no face visible (NFR-07) |
| `labels.csv` | `query_id, kind, article_type, base_colour, split, taken_by, notes` |

`kind` is `in_catalogue` (a garment of one of the 10 types), `out_of_catalogue` (a garment of another type) or `not_fashion` (a mug, a plant). `article_type` and `base_colour` must come from the catalogue vocabulary and are blank for `not_fashion`. `split` is `dev` or `test`, assigned once by seed and never changed (D-07). `taken_by` is a code (Q1, Q2…), never a name.

## 6. Eval results (`eval/results/<YYYY-MM-DD>.json`, written by `make eval`)

```json
{
  "run_date": "YYYY-MM-DD",
  "commit": "a1b2c3d",
  "catalogue": {"products": 0, "article_types": 10, "seed": 2026},
  "queries": {"dev": 0, "test": 0},
  "rows": [
    {"system": "random | openclip | fashionclip", "split": "dev | test", "rule": "strict | type_only",
     "n": 0, "recall_at_10": 0.0, "recall_at_10_ci": [0.0, 0.0], "precision_at_10": 0.0, "mrr": 0.0}
  ],
  "no_match": {"system": "fashionclip", "split": "test", "floor": 0.0,
               "in_catalogue_answered": 0.0, "n_in": 0, "out_of_catalogue_rejected": 0.0, "n_out": 0},
  "model_choice": {"chosen": "openclip | fashionclip", "rule": "D-08", "reason": "plain sentence with the numbers"}
}
```

### Latency (`eval/results/bench-<YYYY-MM-DD>.json`, written by `make bench`)

```json
{
  "run_date": "YYYY-MM-DD",
  "commit": "a1b2c3d",
  "cpu": "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz",
  "torch_threads": 6,
  "requests": 200,
  "warmup": 10,
  "query_long_side_px": 640,
  "models": [
    {"model": "fashionclip",
     "p50_ms": {"decode": 0.0, "embed": 0.0, "search": 0.0, "server": 0.0, "end_to_end": 0.0},
     "p95_ms": {"decode": 0.0, "embed": 0.0, "search": 0.0, "server": 0.0, "end_to_end": 0.0}}
  ]
}
```

`server` is the time inside `/search`; `end_to_end` is measured by the client from sending the request to having parsed the response, on the same machine.

## 7. Analytics events (PostHog)

Every event carries `layout_variant` (`A`, `B` or `fallback`) and `model`. No event carries image data, a file name or EXIF.

| Event | When | Properties |
| --- | --- | --- |
| `search_submitted` | Photo sent to `/search` | `source` (`camera`, `upload`, `example`, `crop`, `similar`), `filter` |
| `results_shown` | Results or the no-match panel rendered | `match`, `top_score`, `result_count`, `latency_ms`, `blurry`, `dark` |
| `result_clicked` | Shopper opens a result | `rank`, `product_id`, `score`, `article_type` |
| `no_match_shown` | No-match panel rendered | `top_score`, `floor` |
| `show_anyway_clicked` | Shopper asks to see the closest results anyway | `top_score` |
| `quality_warning_shown` | Blur or dark banner rendered | `blurry`, `dark` |
| `filter_used` | Category chip tapped or cleared | `article_type` (or `null`) |
| `search_failed` | Any error shown | `error` (the API error code, or `network`) |

A search session is one `search_submitted` and the events that follow it until the next `search_submitted`. Click-through for the experiment is defined in [ab-test-plan.md](ab-test-plan.md) §3.
