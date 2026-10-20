# Milestone plan

Seven milestones following the build plan's Project 2 sequence, with M0 added for the spec and discovery. The board lives in Jira (D-16); this page is the plan of record and holds the review notes.

**Capacity.** One builder at about 12 hours a week. Velocity is unknown until M1 ends, so later scope is re-checked at each milestone planning. **Cut line:** if a milestone is over capacity, drop Could stories first, then Should, never Must (R-12).

**People work runs alongside the build.** Interviews land before the relevance rule is relied on (M2), query photos before the eval (M2), and shoppers are booked by the end of M1 for the usability round in M5 (R-10).

## Overview

| Milestone | Dates (planned) | Goal | Stories | Points | Done when |
| --- | --- | --- | --- | --- | --- |
| M0 | 2026-10-20 → 10-23 | Spec, PRD, eval plan; check the problem with shoppers | — (docs + discovery) | — | PRD reviewed; relevance rule confirmed or changed; photo collection started |
| M1 | 2026-10-24 → 10-30 | Catalogue and one index per model | US-01, US-02 | 6 | `make index` builds both indexes; TC-CAT-01 – 08 automated and passing |
| M2 | 2026-10-31 → 11-06 | Eval harness on real photos | US-03, US-04 | 7 | Recall@10, P@10 and MRR for random, OpenCLIP and FashionCLIP on dev; test target set (PRD Q3) |
| M3 | 2026-11-07 → 11-13 | API, latency, the ship decision | US-05 – US-10 | 17 | p50/p95 from a 200-request benchmark; model chosen by D-08; floor set |
| M4 | 2026-11-14 → 11-24 | React app and PostHog events | US-11 – US-16, US-18 | 20 | Events visible in PostHog from a local session; every M4 AC automated where possible |
| M5 | 2026-11-25 → 12-08 | Usability round and the layout experiment | US-17 | 3 + sessions | [usability.md](usability.md) has five sessions and one layout change; experiment run for its full 14 days |
| M6 | 2026-12-09 → 12-11 | README, demo GIF, failure cases shown | — | — | Results generated from real files; UAT exit criteria met |

M3 is the heaviest. If it runs over, US-09 (Should) moves to M4 first.

## M0 — Spec and discovery

| # | Task | Output | Done |
| --- | --- | --- | --- |
| 1 | One-page spec | [spec-shop-the-look.md](spec-shop-the-look.md) | [x] |
| 2 | PRD, stories, data contracts, eval plan, risk log, UAT sheet | `docs/` | [x] |
| 3 | Five shopper conversations ([discovery-notes.md](discovery-notes.md)) | Notes; P1–P5 and A1–A4 confirmed or cut | [ ] |
| 4 | Answer PRD Q2 (relevance rule) from discovery | Answer in PRD §11; decision logged if it changes | [ ] |
| 5 | Start collecting query photos (target 60–80 in-catalogue, 20–25 others) | Photos with consent, no faces, held locally until labelled | [ ] |
| 6 | Book five (aim for seven) shoppers for M5 | Codes and slots, kept private (not in git) | [ ] |
| 7 | Backlog refinement: point every story | Points in user-stories.md | [x] |
| 8 | Jira board: epics E1–E5, stories, M1 sprint | Board link in README | [ ] |
| 9 | PRD review | PRD status → Approved v1.0 | [ ] |

## M1 — Catalogue and index

| Story | Points | Notes |
| --- | --- | --- |
| US-01 Build the catalogue | 3 | Join on id; seeded sample; drop and count bad rows |
| US-02 Build one index per model | 3 | CPU build (D-17); self-retrieval check |

### M1 build plan (approved by the owner 2026-10-20)

1. Scaffold on `chore/m1-scaffold`: `uv` project on Python 3.12, CPU-only torch, open_clip, faiss-cpu, huggingface_hub, pyarrow, pandas, Pillow, pytest; Makefile targets; CI job for the unit tests; this plan, the feature map and the open-questions log.
2. US-01 on `feature/US-01-catalogue`: tests for TC-CAT-01 – 04 on a generated fixture first, confirmed failing; then `vsearch/catalogue.py` and `make catalogue` against the pinned datasets (D-19); then the same checks on the real build.
3. US-02 on `feature/US-02-index`: tests for TC-CAT-05 – 08 with a fake embedder first, confirmed failing; then `vsearch/embed.py`, `vsearch/index.py` and `make index` for both models; then the self-retrieval check on the real indexes.
4. Each feature gets a session log; M1 review notes; tag `m1`.

Downloads: about 0.9 GB of parquet and 1.2 GB of model weights, into `data/` and the Hugging Face cache.

## M2 — Eval harness

| Story | Points | Notes |
| --- | --- | --- |
| US-03 Labelled phone photos | 2 | Needs the photos from M0 task 5 |
| US-04 Retrieval eval harness | 5 | Metric tests with hand-worked values come first |

## M3 — API, latency and the ship decision

| Story | Points | Notes |
| --- | --- | --- |
| US-07 Search API | 5 | |
| US-08 No close match | 3 | Floor tuned on dev |
| US-10 My photo isn't kept | 2 | File, log and payload tests |
| US-05 Latency benchmark | 3 | CPU forced |
| US-06 Choose the model by the written rule | 1 | Runs after US-04 and US-05 |
| US-09 Photo quality warning | 3 | Should; first to move |

## M4 — React app and PostHog

| Story | Points | Notes |
| --- | --- | --- |
| US-11 Take or upload a photo | 5 | Phone-side resize |
| US-12 Results and product page | 3 | |
| US-13 Clear errors | 2 | |
| US-16 Analytics events | 3 | |
| US-14 Narrow by category | 2 | Should |
| US-15 Crop to one item | 3 | Should |
| US-18 More like this | 2 | Could; first to cut |

## M5 — Usability and experiment

| Item | Notes |
| --- | --- |
| Usability round 1 | Five shoppers, three tasks ([usability-protocol.md](usability-protocol.md)) |
| One layout change | Chosen from round 1 and click-by-rank; logged as a decision |
| Usability round 2 | Two sessions on the changed layout |
| US-17 Results layout experiment | 3 points; runs 14 days on the hosted demo, pending PRD Q1 and Q4 |
| UAT run | Every case in [uat/test-cases.csv](uat/test-cases.csv) ([uat-plan.md](uat-plan.md)) |

## Ceremonies

| Ceremony | When | Length | Output |
| --- | --- | --- | --- |
| Milestone planning | First day | 30 min | Scope confirmed against capacity; plan approved before code |
| Daily check | Each working day | 5 min, written | One line in the milestone's Jira comment: done / next / blocked |
| Milestone review | Last day | 30 min | Demo + review notes below |
| Retro | After review | 15 min | One thing to keep, one to change |
| Risk review | In the review | 10 min | [risk-log.md](risk-log.md) scores updated |

## Milestone review notes

Filled in at the end of each milestone.

### M0 review
- Problems confirmed / cut: [TBD]
- Relevance rule: [TBD]
- Photos collected: [TBD]
- Shoppers booked: [TBD]
- Retro — keep: [TBD] · change: [TBD]

### M1 review (2026-10-20)
- Planned: 6 pts · Done: 6 pts (US-01, US-02). Both built on 2026-10-20, ahead of the planned 10-24 start.
- Demo: `make catalogue` → 4,905 products across 10 types, matching the committed manifest; `make index` → one 4,905 × 512 index per model, each finding 200 of 200 catalogue images at rank 1. Unit tests 21 passing; real-data checks 10 passing.
- Not done: the M0 people tasks. No interviews, photos or bookings yet, so OQ-01 stays open.
- Risks: R-06 up from 4 to 6 (FashionCLIP embeds at 2.7× OpenCLIP's time per image in batch, see the index session log); R-16 closed.
- What went wrong: a unit test overwrote the committed manifest once (caught by the rebuild's own check, guarded since); the CPU index build took 46 minutes, not minutes (D-25).
- Retro — keep: checking the real data before writing a check about it (duplicate images before the self-check). Change: write the "fails first" stub before the test file, so a vacuous assertion shows up as a pass straight away.

### M2 review
- Planned: 7 pts · Done: [TBD]

### M3 review
- Planned: 17 pts · Done: [TBD]

### M4 review
- Planned: 20 pts · Done: [TBD]

### M5 review
- Planned: 3 pts + sessions · Done: [TBD]
