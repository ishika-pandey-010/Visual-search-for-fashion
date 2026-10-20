# Shop the look: one-page spec

Draft v0.1, 2026-10-20 · Owner @ishika-pandey-010 · Detail lives in the [PRD](PRD.md); this page is the summary a teammate reads first.

## The problem

A shopper sees a shirt on a friend, in a shop window or in a screenshot and wants something like it. They can't name it well enough for a text box: "blue checked shirt, slightly boxy" returns a page of anything blue. A photo carries the details words miss, but only if the results look right on the first screen. One obviously wrong result (a handbag for a shirt) and they stop trusting the rest. Both claims are hypotheses until the discovery interviews ([discovery-notes.md](discovery-notes.md)) confirm or cut them.

## User journey (v1)

1. Open the page on a phone. First visit shows three example photos to try and one line of advice: one item, good light, fill the frame.
2. Tap **Take or upload a photo**. The phone camera or photo library opens.
3. The photo is shrunk on the phone to 640 px and sent. A loading state shows at once.
4. Ten products appear, closest first, with the shopper's photo as a thumbnail above them. Category chips narrow the list. If the photo looked blurry or dark, a banner says so and offers a retake, without blocking the results.
5. Tap a product to see it larger, with "More like this". Back returns to the same ten.
6. If nothing is close, the page says "No close match in this catalogue" and offers a retake, a crop to one item, or "Show closest anyway".

The main task, photo to a product page, takes 3 taps on a phone: open the camera, take the photo, tap a result. Usability testing measures whether it really does.

## Data flow

```text
OFFLINE (make catalogue, make index)
  Fashion Product Images (labels: ashraq copy, 384 px images: ceyda copy, joined on id)
    → sample ≤500 per type × 10 types, seed 2026 → data/catalogue.parquet
    → embed each image (OpenCLIP ViT-B-32 and Marqo-FashionCLIP) → L2-normalise
    → FAISS IndexFlatIP per model + ids.npy

ONLINE (one request)
  phone photo → resize to 640 px, re-encode JPEG (EXIF gone) → POST /search
    → decode → quality check (blur, brightness) → embed with the chosen model
    → exact top-50 by cosine similarity → optional type filter → top 10
    → top score below the floor? → match: false
    → JSON back: results, scores, quality flags, timings → grid or no-match panel
    → PostHog: search_submitted, results_shown, result_clicked (rank, score), no_match_shown
  The photo is never written to disk or sent to analytics.
```

## Failure modes

| Failure | What the shopper sees | How we catch it | Test |
| --- | --- | --- | --- |
| Blurry photo | Results, with "This photo looks blurry, so results may be off. Retake?" | Variance of the Laplacian below a threshold set on dev photos | TC-FAIL-04 |
| Too dark | Same banner, worded for light | Mean brightness below a threshold set on dev photos | TC-FAIL-05 |
| Item not in the catalogue (a saree) | "No close match in this catalogue", plus "Show closest anyway" | Top similarity under the floor, tuned on dev photos | TC-FAIL-02 |
| Not clothing at all (a mug) | Same no-match panel | Same floor | TC-FAIL-01 |
| Several garments in one photo | Mixed results; a "Crop to one item" control on the thumbnail | Manual crop in v1 (D-10); measured in usability task 2 | TC-SRCH-08 |
| Worn on a person, catalogue shot on a plain background | Some lower-ranked results; nothing visible | The domain gap is measured, not hidden: Recall@10 on real phone photos | TC-EVAL-04 |
| Not an image, or too large | "That file isn't a photo. Use a JPG, PNG or WebP." | API returns 415 or 413 with a plain message | TC-SRCH-10 |
| API down or slow network | "Search is offline right now. Your photo is kept, so try again." | Client timeout at 10 s; Retry reuses the photo | TC-SRCH-11 |

## v1 scope: the accuracy-versus-speed call

Two choices drive both quality and speed, and v1 makes each one with data:

- **Model.** Generic OpenCLIP ViT-B-32 is the fast baseline. Marqo-FashionCLIP is trained on fashion but built on ViT-B-16, which works on 4× as many image patches and should be slower on CPU. The fashion model ships only if it beats the generic one by at least 5 points of Recall@10 on dev photos *and* stays inside the latency budget (D-08).
- **Search method.** At 5,000 products an exact scan over 512-number vectors costs well under a millisecond, so approximate indexes buy nothing here. Embedding the photo is where the time goes (D-05).

Budget (NFR-01): p95 under 500 ms inside the server and under 1,500 ms end to end, on an Intel i7-10750H laptop CPU, with no GPU.

Out of v1: automatic garment detection, text search, prices and checkout, accounts, model training.

## How we'll know it works

| Question | Measure | Where it's recorded |
| --- | --- | --- |
| Are the ten results relevant? | Top-10 match rate (Recall@10): share of test photos with at least one same-type, same-colour product in the ten. Shown beside a random baseline | `eval/results/` |
| Is it fast enough? | p50 and p95, server and end to end | `eval/results/bench-*.json` |
| Does "no close match" fire at the right time? | Share of non-catalogue photos rejected, and of catalogue photos still answered | `eval/results/` |
| Can shoppers use it? | Task success and time for five shoppers, three tasks | [usability.md](usability.md) |
| Which results layout gets more clicks? | Search click-through in a pre-registered A/B test | [ab-test.md](ab-test.md) |
