# Visual Search for Fashion

Take a photo of a piece of clothing and get the ten most similar products from a catalogue of about 5,000, or a plain "no close match" when nothing is close. Built with OpenCLIP and Marqo-FashionCLIP embeddings, a FAISS index, a FastAPI service and a React front end, over products from the open Fashion Product Images dataset.

> **Status: M0, docs only.** The spec, PRD, stories, eval plan, experiment plan and UAT sheet are written. No code yet, no photos labelled, no shoppers interviewed. The Results table below says so because it's generated from the files that will hold the numbers.

## For reviewers: where the proof is

| If you want to see… | Open |
| --- | --- |
| The one-page spec: journey, data flow, failure modes | [docs/spec-shop-the-look.md](docs/spec-shop-the-look.md) |
| The problem, users, goals and requirements (FR-/NFR- IDs) | [docs/PRD.md](docs/PRD.md) |
| User stories with Given/When/Then acceptance criteria | [docs/user-stories.md](docs/user-stories.md) |
| How quality and speed are scored, written before any model ran | [docs/eval-plan.md](docs/eval-plan.md) |
| The layout A/B test, pre-registered with its sample size | [docs/ab-test-plan.md](docs/ab-test-plan.md) |
| How every requirement traces to stories, UAT cases, tests and risks | [docs/traceability.md](docs/traceability.md) (generated) |
| Schemas for the catalogue, API, results files and analytics events | [docs/data-contracts.md](docs/data-contracts.md) |
| Decisions and their trade-offs | [docs/decisions.md](docs/decisions.md) |
| Risks, mitigations and the test that proves each one | [docs/risk-log.md](docs/risk-log.md) |
| Milestones and review notes | [docs/milestone-plan.md](docs/milestone-plan.md) |
| The UAT sheet | [docs/uat/test-cases.csv](docs/uat/test-cases.csv) · [UAT plan](docs/uat-plan.md) |
| Discovery guide and usability protocol | [docs/discovery-notes.md](docs/discovery-notes.md) · [docs/usability-protocol.md](docs/usability-protocol.md) |
| Similar products and what was taken from them | [docs/competitive-analysis.md](docs/competitive-analysis.md) |
| Terms used everywhere | [docs/glossary.md](docs/glossary.md) |

## The problem

Shoppers often know what they want only by sight, and a text box makes them put it into words. Photo search fixes that only if the first screen of results looks right. One handbag in a list of shirts and the shopper stops trusting the rest. These are hypotheses until the discovery conversations confirm them ([PRD §2](docs/PRD.md#2-problem)).

## What v1 will do

- **Search by photo:** camera, photo library or a dropped file. The phone shrinks the photo to 640 px before upload, which also strips its location data.
- **Ten results,** closest first, with type and colour on each card. Chips narrow the list to one type, a crop control isolates one item in an outfit photo, and "More like this" works from any product.
- **Say when nothing is close.** Under a similarity floor tuned on dev photos, the shopper sees "No close match in this catalogue" instead of junk, with the option to see the closest anyway.
- **Flag bad photos.** Blurry or dark photos get a banner offering a retake, without blocking the results.
- **Keep nothing.** Photos are processed in memory and discarded, and never reach the analytics.

**Not in v1, on purpose:** checkout and prices, text search, automatic multi-garment detection, accounts, model training ([why](docs/PRD.md#8-out-of-scope-v1-and-why)).

## How it's measured

| Question | Measure |
| --- | --- |
| Are the results relevant? | Top-10 match rate (Recall@10), Precision@10 and MRR on real phone photos, scored as same type and same colour. Random baseline, generic OpenCLIP and Marqo-FashionCLIP side by side, with 95% intervals |
| Is a fashion model worth its cost? | A rule written before any run: ship it only if it's ≥ 5 points better on dev **and** p95 stays within 500 ms (D-08) |
| Is it fast? | p50 and p95 per stage and end to end, 200 requests, on an Intel i7-10750H with no GPU |
| Does "no close match" work? | Share of off-catalogue photos turned away, and of catalogue photos still answered |
| Can shoppers use it? | Five shoppers, three tasks, success and time |
| Which layout gets clicked? | A pre-registered A/B test on search click-through in PostHog, labelled directional if it falls short of 388 searches per layout |

Thresholds and the model choice are tuned on dev photos only; the test split is read once per milestone and every read is logged.

## How the work is run

- **Docs before code.** A story isn't built until its acceptance criteria are written ([CLAUDE.md](CLAUDE.md)).
- **Tests before code.** Each acceptance criterion gets a failing test first.
- **Stable IDs everywhere:** FR → US → TC → automated test → code → R, checked by `make docs` and in CI on every push.
- **No hand-typed results.** The table below is generated from the eval results files, the usability and experiment raw tables, and the UAT sheet.

## Results

<!-- results:start -->
<!-- Generated by scripts/results.py from eval/results/, docs/usability.md, docs/ab-test.md and docs/uat/test-cases.csv. Run `make docs`; don't edit. -->

| Metric | Value | Produced by |
| --- | --- | --- |
| Catalogue searched | Not built yet (M1) | `eval/results/` |
| Top-10 match rate (Recall@10), test photos | Not run yet: no `eval/results/<date>.json` (needs labelled phone photos, M2) | `eval/results/` |
| Precision@10 and MRR, test photos | Not run yet (M2) | `eval/results/` |
| No close match (similarity floor) | Not run yet (M2–M3) | `eval/results/` |
| Model chosen by the D-08 rule | Not chosen yet (M3) | `eval/results/` |
| Latency p50 / p95 | Not run yet: no `eval/results/bench-<date>.json` (M3) | `eval/results/` |
| Usability test | Not run yet: no sessions in `docs/usability.md` (M5) | `docs/usability.md` |
| Layout experiment click-through (A vs B) | Not run yet (M5). Needs 388 searches with results per layout to detect a 10-point change in click-through | `docs/ab-test.md` |
| UAT cases executed / passed | Not run yet: 0 of 70 executed | `docs/uat/test-cases.csv` |
<!-- results:end -->

## Stack

Python 3.12 · open_clip · faiss-cpu · FastAPI · React + Vite + TypeScript · PostHog · pytest · Vitest · Playwright.

Data: product labels from [`ashraq/fashion-product-images-small`](https://huggingface.co/datasets/ashraq/fashion-product-images-small) and 384 × 512 images from [`ceyda/fashion-products-small`](https://huggingface.co/datasets/ceyda/fashion-products-small), joined on product ID (D-02). Both are copies of the Kaggle Fashion Product Images set; neither states a licence, so a public hosted demo waits on that question ([R-08](docs/risk-log.md)).

## Run locally

From M1. For now:

```bash
make docs    # rebuild docs/traceability.md and the Results table above
```
