# CLAUDE.md — Visual Search for Fashion ("shop the look")

Read this file, then `docs/spec-shop-the-look.md` and `docs/PRD.md`, before doing anything in this repo.

## Goal

A shopper uploads or takes a photo of a piece of clothing and gets the ten most similar products from a catalogue of about 5,000 items, or a plain "no close match" when nothing in the catalogue is close. Quality and speed are measured, not claimed: Recall@10, Precision@10 and MRR on real phone photos, and p50/p95 latency on a named CPU, for a random baseline, generic OpenCLIP and Marqo-FashionCLIP.

This is a **product-management portfolio piece**. The docs and the eval output are the main deliverable; the code exists to prove the docs were followed.

## Out of scope (do not build, even if asked casually)

- Checkout, cart, prices or stock (the catalogue has no prices)
- Text search or text-plus-image search
- Automatic detection of several garments in one photo (v1 uses a manual crop, D-10)
- Accounts, saved searches, personalised ranking
- Fine-tuning or training any model
- Storing shoppers' photos on the server (FR-15)

If a request falls outside this boundary, stop and ask, then log the answer in `docs/decisions.md`.

## Stack

Python 3.12 (managed by `uv`) · open_clip · faiss-cpu (exact inner product on L2-normalised vectors) · FastAPI · React + Vite + TypeScript · PostHog (events and the layout experiment) · pytest · Vitest · Playwright.

## Repo layout

```text
CLAUDE.md                     this file; keep under 200 lines
README.md                     for reviewers: problem, docs map, generated Results
docs/
  spec-shop-the-look.md       the one-page spec: journey, data flow, failure modes
  PRD.md                      problem, users, goals, requirements (FR-/NFR- IDs)
  user-stories.md             epics and stories (US- IDs) with Given/When/Then
  data-contracts.md           catalogue, index, API, eval and event schemas
  eval-plan.md                query set, relevance rule, metrics, splits, latency method
  decisions.md                one line per decision (D- IDs) and why
  risk-log.md                 risks (R- IDs), mitigation, the test that proves it
  milestone-plan.md           M0–M6 scope, done-when, review notes
  uat-plan.md                 UAT approach, entry/exit criteria, bug workflow
  uat/test-cases.csv          the UAT sheet (TC- IDs), one row per case
  discovery-notes.md          shopper interview guide, notes and synthesis
  usability-protocol.md       five shoppers, three tasks
  usability.md                raw session data (filled only after sessions)
  ab-test-plan.md             pre-registered layout experiment
  ab-test.md                  experiment export (filled only after it runs)
  competitive-analysis.md     similar products and what we took from them
  glossary.md                 terms used everywhere else
  traceability.md             FR → US → TC → R matrix (generated; never edit)
  build-prompt.md             how each feature is built, tested and reviewed
.github/                      issue/PR templates; CI runs the docs check
scripts/docs_check.py         builds traceability.md, fails on broken IDs
scripts/results.py            writes the README Results block from eval and test files
Makefile                      make docs | make docs-check (more targets from M1)
```

Code folders arrive from M1: `vsearch/` (Python package: catalogue, embedding, index, search, quality checks, API), `eval/` (harness, `queries/`, `results/`), `web/` (React app), `tests/` (pytest), `e2e/` (Playwright). `data/` holds downloaded and built files and is git-ignored.

## Commands

```text
make docs        rebuild docs/traceability.md and the README Results, check every ID
make docs-check  check only (CI)
make setup       uv sync: Python 3.12, CPU-only torch and every dependency
make catalogue   download the pinned datasets, build data/catalogue.parquet
make index       embed the catalogue with both models, one FAISS index each
make test        unit tests on the generated fixture (CI; no downloads)
make test-data   checks on the real catalogue and indexes
```

Planned for M2–M4: `make eval`, `make eval-check`, `make bench`, `make api`, `make web`, `make e2e`.

Run Python through `uv run`. Unit tests never download anything (D-20); a test that needs the real build is marked `@pytest.mark.data`.

## Data contracts

The schemas live in `docs/data-contracts.md` and are the source of truth. The ones code depends on most:

- Catalogue row: `product_id, article_type, base_colour, gender, name, image_path`.
- `POST /search` (multipart image) returns `{match, top_score, floor, quality: {blurry, dark}, model, timings_ms, results: [{rank, product_id, score, name, article_type, base_colour, image_url}]}`.
- Eval results: `eval/results/<YYYY-MM-DD>.json` and `eval/results/bench-<YYYY-MM-DD>.json`, written only by `make eval` and `make bench`.

## IDs and traceability (the core PM rule)

- Every requirement is `FR-nn` or `NFR-nn` in `docs/PRD.md`.
- Every story is `US-nn` and names the FR it delivers.
- Every UAT case is `TC-<MODULE>-nn` and names the US it checks.
- Every risk is `R-nn` and names the TC that proves the mitigation.
- Every decision is `D-nn`.
- Automated tests cite the TC they automate: TypeScript `it("TC-SRCH-01: …")`; Python `def test_tc_srch_01_…()`.
- Code cites the story it builds in a comment: `# US-07` or `// US-07`.
- When you add or change any of these, run `make docs` and commit `docs/traceability.md` in the same commit. CI fails if it's stale or an ID is broken.
- Commit messages cite the IDs they touch, e.g. `US-09: shoppers see "no close match" instead of junk`.

## Eval rules (never break these)

- Relevant means the same `articleType` and the same `baseColour` as the query's label (D-06). Type-only is reported second, never instead.
- Thresholds, the similarity floor and the model choice are tuned on the **dev** split only. The **test** split is read once per milestone, after choices are frozen (D-07).
- Every results table includes the random baseline row.
- Latency is measured end to end and per stage, after 10 warm-up requests, on the CPU named in the results file. GPU numbers are never reported as the latency result.
- The model choice is made by the rule in D-08, by a script, from the results files.

## Working rules

1. **Docs first.** No code for a story until its acceptance criteria exist in `docs/user-stories.md`.
2. **Plan, then wait.** For each milestone, propose a plan and wait for approval before writing code.
3. **Tests first.** Each acceptance criterion gets a failing test before the code that satisfies it.
4. **No metric typed by hand.** `make eval` and `make bench` write the results JSON; usability and A/B numbers come from the raw tables in `docs/usability.md` and `docs/ab-test.md`; the README Results block is generated from those files.
5. **No invented evidence.** Interviews, usability sessions, query photos and experiment results are recorded only after they happen. Leave `[TBD]` rather than plausible-looking numbers.
6. **Photos stay private.** Never write an uploaded photo to disk or send image data to PostHog. Query photos in `eval/queries/` have EXIF stripped and no faces (NFR-07).
7. **Commit at the end of each milestone**, and whenever a done-check passes.
8. Secrets live in `.env.local` (git-ignored). `.env.example` lists every key with no values.

## Definition of done

| Level | Done when |
| --- | --- |
| Story | AC pass as automated tests where possible; matching TC rows exist; traceability updated |
| Milestone | Every story in scope is done; review notes written in `docs/milestone-plan.md`; tagged commit (`m1`, `m2`, …) |
| Release (v1) | All Must FRs done; UAT exit criteria met (`docs/uat-plan.md` §5); README Results generated from real runs |

## Current status

M0 (docs) written 2026-10-20. Discovery interviews, query photos, usability sessions and the experiment haven't happened. M1 starts with a plan for approval.
