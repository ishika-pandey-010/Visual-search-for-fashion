# Eval plan

How the search is scored, written before any model has been run (M0). If this page changes after M2 starts, the change and its reason go in [decisions.md](decisions.md), because changing the rules after seeing results is the easiest way to fool yourself.

## 1. What we're trying to learn

1. On real phone photos of clothes, how often do the ten results include something relevant? (G1)
2. Does a fashion-trained model beat a generic one by enough to justify its extra cost on CPU? (D-04, D-08)
3. Does the similarity floor turn away photos the catalogue can't serve, without turning away ones it can? (G3)
4. How fast is a search on an ordinary laptop, and which stage takes the time? (G2)

## 2. The query set

| Kind | Target count | What it is |
| --- | --- | --- |
| `in_catalogue` | 60–80 | A real garment of one of the 10 catalogue types, photographed on a phone: flat on a bed, on a hanger, or worn (face cropped out). At least 4 per type in test |
| `out_of_catalogue` | 10–15 | A real garment of another type (saree, watch, sunglasses, scarf) |
| `not_fashion` | 10 | Anything else: a mug, a plant, a laptop |

Photos come from my own wardrobe and from friends who agree to it (NFR-07). Each is labelled with `article_type` and `base_colour` from the catalogue vocabulary, by looking at the garment, not at search results. Labelling before any search is run keeps the labels from bending toward what the model returns.

Real photos only. Catalogue images with added blur or noise make tidy test data, but they say nothing about how shoppers take photos. The only synthetic use is the blur and darkness tuning in §6.

**Split.** Each photo is assigned to dev (about 30%) or test (about 70%) once, by seed, stratified by `kind` (D-07). Dev is for tuning. Test is read once per milestone, after choices are frozen, and every read is logged (US-04 AC5).

## 3. Relevance rule

A result is **relevant** to a query when its `article_type` and `base_colour` both equal the query's label (D-06). This is the rule behind "top-10 match rate".

A second rule, **type-only**, counts a result as relevant when only `article_type` matches. It's always reported beside the strict rule, never in place of it. The gap between the two shows how much of the error is colour.

Known harshness: the source uses 46 colour names, and some are near-identical (`Navy Blue` and `Blue`, `Off White` and `White`). The strict rule counts those as misses. That makes the headline number conservative, which is the right direction to be wrong in (PRD Q5).

## 4. Metrics

For a query with ranked results r₁ … r₁₀:

| Metric | Definition | Why it's here |
| --- | --- | --- |
| **Recall@10** (top-10 match rate) | 1 if any of r₁ … r₁₀ is relevant, else 0; averaged over queries | The shopper's question: "is there anything here for me?" |
| **Precision@10** | Relevant results among the ten ÷ 10; averaged | How much of the grid is noise |
| **MRR** | 1 ÷ rank of the first relevant result (0 if none); averaged | Whether the good result is near the top, where shoppers look (A2) |

A naming note: "Recall@10" here is the hit rate at 10, the usual meaning in product-search write-ups. Classic recall would divide by every relevant product in the catalogue, which is hundreds per query and not what a shopper cares about.

Each metric carries a 95% bootstrap interval: resample the query photos with replacement 1,000 times with a fixed seed and take the 2.5th and 97.5th percentiles. With 60 or so test photos the intervals will be wide, and the README shows them so nobody reads a 3-point gap as real.

## 5. Rows in every results table

| Row | What it is |
| --- | --- |
| Random | Ten catalogue products drawn at random per query (fixed seed). Proves the metric isn't trivially high |
| OpenCLIP ViT-B-32 | Generic model, `laion2b_s34b_b79k` |
| Marqo-FashionCLIP | Fashion model, ViT-B-16 base |

Only in-catalogue photos are scored for these three metrics. Out-of-catalogue and non-fashion photos have no relevant products by definition, so they're scored only in §6.

## 6. Tuning on dev (the only place anything is tuned)

**Similarity floor (D-09).** Over the in-catalogue dev photos, take the top-1 score of each. The floor is the highest value that still leaves at least 90% of them above it. Then report, on test: the share of in-catalogue photos answered and the share of other photos rejected. If the rejection rate is poor, that's reported too. The floor isn't moved to fix it on test.

**Quality thresholds (US-09).** Blur: variance of the Laplacian on the 640 px grey image. Darkness: mean brightness on a 0–255 scale. Each threshold is set so that at most 1 in 10 sharp, well-lit dev photos trips it (US-09 AC4). The flagged photos are then checked by eye for false alarms. Here, and only here, dev photos with added blur and reduced brightness are used, to confirm the banner fires on the obvious cases.

**Model choice (D-08).** On dev, strict rule: FashionCLIP ships only if its Recall@10 beats OpenCLIP by at least 5 points and its p95 server time is within 500 ms. A script applies the rule (US-06).

## 7. Latency method

- Machine: Intel Core i7-10750H (6 cores, 12 threads), 23 GB RAM, on mains power. The GTX 1650 is not used; the benchmark forces CPU (US-05 AC3).
- Input: the query photos, already resized to 640 px as the phone would send them (D-11), cycled to make 200 requests.
- Warm-up: the first 10 requests are excluded (model load and first-call costs).
- Stages timed inside the server: decode, embed, search, and the total server time. End to end is timed by the benchmark client from sending the request to having parsed the JSON, on the same machine, so network is loopback. Phone-network time isn't included and is stated as a limit.
- Reported: p50 and p95 for each stage, per model. Torch thread count recorded.

## 8. Limits to state wherever the numbers appear

- Fewer than 100 photos, taken by a handful of people in a few homes, from a few wardrobes.
- Labels made by one person.
- Relevance by type and colour only; pattern and style aren't scored.
- The catalogue is one retailer's studio product shots on plain backgrounds, 10 types.
- Latency on one laptop over loopback; a hosted demo will differ, and if it's measured it's reported separately.
