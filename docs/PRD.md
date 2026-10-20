# PRD — Visual Search for Fashion

| | |
| --- | --- |
| **Status** | Draft v0.1 — in review (M0) |
| **Owner** | @ishika-pandey-010 (product + delivery) |
| **Last updated** | 2026-10-20 |
| **Related** | [One-page spec](spec-shop-the-look.md) · [User stories](user-stories.md) · [Data contracts](data-contracts.md) · [Eval plan](eval-plan.md) · [Risk log](risk-log.md) · [Decisions](decisions.md) · [Traceability](traceability.md) |

## 1. Summary

Shoppers often know what they want only by sight: a shirt a friend wore, a pair of shoes in a screenshot. Text search makes them translate that into words, and most can't do it well enough. Visual Search for Fashion takes a phone photo and returns the ten most similar products from a 5,000-item catalogue, or says plainly that nothing is close. The project's real output is evidence: how often the ten results contain a relevant product on real phone photos, how fast that happens on an ordinary laptop CPU, and whether shoppers can use it without help.

## 2. Problem

| # | Problem today | Consequence |
| --- | --- | --- |
| P1 | Shoppers can't describe pattern, cut or texture in a search box | Text search returns anything of the right colour, and they give up |
| P2 | Screenshots and photos of clothes pile up in camera rolls with no way to act on them | Intent to buy is lost |
| P3 | Visual search tools return loose matches with no signal when nothing is close | One absurd result (a bag for a shirt) and the shopper stops trusting the list |
| P4 | Real photos are messy: low light, blur, several garments, the item worn on a body | Results built for studio shots degrade quietly, and nobody measures by how much |
| P5 | Shoppers judge "similar" first by type and colour, then by details | A result of the wrong type or colour reads as wrong even when the pattern matches |

**Evidence.** These are hypotheses taken from how existing tools present visual search (see [competitive analysis](competitive-analysis.md)) and from the dataset itself. They're tested in M0 by:

- [TBD] five short conversations with people who shop for clothes online at least monthly, notes in [discovery-notes.md](discovery-notes.md)
- [TBD] a check of the camera roll: how many clothing screenshots each person has and what they did with them

A problem confirmed by fewer than two of the five moves to §8 (later), and the change is logged in `decisions.md`. P5 matters more than the others because the relevance rule (D-06) rests on it. If interviews show shoppers care more about pattern or style than colour, the rule changes before M2 and the change is logged.

## 3. Users

**Primary persona: the screenshot shopper.** 18–35, shops on a phone, saves outfit screenshots from Instagram and friends' photos, buys clothes online at least monthly. Has tried Google Lens or a retailer's camera search at least once. Wants "something like this, in my price range, without typing".

**Secondary persona: the in-person spotter.** Sees an item on a friend or in a shop and photographs it then and there. Photos are taken quickly, often in poor light, often with the item worn.

**Internal user: the product owner.** Needs to know whether the system is good enough to put in front of shoppers, and which model to ship. The eval and benchmark stories (E2) are written for this person.

**Not users (v1):** merchandisers curating the catalogue, retailers integrating the API, anyone who wants to buy (there is no checkout).

**Assumptions to validate**

| ID | Assumption | How we check |
| --- | --- | --- |
| A1 | Shoppers judge similarity first by type and colour (P5) | Discovery question 5; usability think-aloud |
| A2 | Shoppers look mostly at the first four to six results | PostHog click-by-rank in usability and the experiment |
| A3 | Shoppers prefer "no close match" over a list of weak matches | Usability task 3 |
| A4 | Most searches happen on a phone, with the camera or a screenshot | Discovery question 1; PostHog `source` |

## 4. Goals and non-goals

**Goals**

- G1. For a photo of an item the catalogue covers, put at least one same-type, same-colour product in the first ten results, and know how often that happens on real photos.
- G2. Return results fast enough on a laptop CPU that the shopper never waits on a blank screen.
- G3. When the catalogue has nothing close, say so instead of showing junk.
- G4. Let a first-time shopper go from photo to product in three taps without help.
- G5. Decide the results layout from shopper behaviour, not opinion.

**Non-goals.** See §8 for the full list and reasons. In short: no checkout, no text search, no automatic garment detection, no accounts, no model training.

## 5. Success metrics

Targets are set now, except where they need dev data first; results are filled in only from recorded data (CLAUDE.md rule 4).

| Metric | Definition | Target | Source of result |
| --- | --- | --- | --- |
| **Top-10 match rate (primary)** | Recall@10 on the test photos: share with at least one same-`articleType`, same-`baseColour` product in the top 10 | Set at the end of M2 from dev numbers, before test is read (Q3), and well above the random row | `eval/results/<date>.json` |
| Model lift | Recall@10 of FashionCLIP minus OpenCLIP on dev | ≥ 5 points to ship the fashion model (D-08) | `eval/results/<date>.json` |
| Precision@10, MRR | See [eval-plan.md](eval-plan.md) §4 | Reported, no target | `eval/results/<date>.json` |
| Latency | p95 time inside `/search`, and end to end, on the i7-10750H | Server ≤ 500 ms; end to end ≤ 1,500 ms | `eval/results/bench-<date>.json` |
| No-match accuracy | Share of out-of-catalogue and non-fashion photos told "no close match", and of in-catalogue photos still answered | ≥ 80% rejected while ≥ 90% answered | `eval/results/<date>.json` |
| Task success | Usability tasks finished without help | ≥ 4 of 5 shoppers on each task | [usability.md](usability.md) |
| Search click-through | Searches with results where the shopper opens at least one result | Experiment primary metric; decision rule in [ab-test-plan.md](ab-test-plan.md) | [ab-test.md](ab-test.md) |
| Rank of first click | Median rank of the first result opened | Reported (guardrail for the experiment) | PostHog export in [ab-test.md](ab-test.md) |

## 6. Requirements

Priority uses MoSCoW. **Must** = v1 cannot ship without it.

### 6.1 Functional

| ID | Requirement | Priority | Problem |
| --- | --- | --- | --- |
| FR-01 | A shopper can take a photo with the phone camera, choose one from the library, or drop a file on desktop. JPEG, PNG and WebP are accepted. | Must | P1, P2 |
| FR-02 | The photo is resized on the device to at most 640 px on its long side and re-encoded as JPEG before upload, which also drops EXIF data. | Must | — |
| FR-03 | `POST /search` returns the ten most similar catalogue products for a photo, ranked by cosine similarity, with score and rank. | Must | P1 |
| FR-04 | Results show as a grid with image, name, type and colour, under a thumbnail of the shopper's photo. Tapping a result opens a product page; Back returns to the same results without searching again. | Must | — |
| FR-05 | When the top score is below the similarity floor, the shopper sees "No close match in this catalogue" with next steps instead of results, and can choose "Show closest anyway". | Must | P3 |
| FR-06 | A blurry or dark photo gets a banner above the results that says so and offers a retake. It never blocks the results. | Should | P4 |
| FR-07 | Category chips list the article types present in the top 50; choosing one shows the top 10 of that type. | Should | P5 |
| FR-08 | The shopper can crop the photo to one item and search again. | Should | P4 |
| FR-09 | The app sends the analytics events in [data-contracts.md](data-contracts.md) §7 to PostHog, and works normally when PostHog is blocked or unconfigured. | Must | — |
| FR-10 | A PostHog feature flag assigns each visitor to results layout A or B, stable across visits, and every results and click event records the layout. | Must | — |
| FR-11 | `make catalogue` and `make index` build the catalogue and one FAISS index per model from the public datasets, from scratch, in one command each. | Must | — |
| FR-12 | `make eval` computes Recall@10, Precision@10 and MRR with confidence intervals for the random baseline, OpenCLIP and FashionCLIP on dev and test photos, and writes `eval/results/<date>.json`. | Must | P4 |
| FR-13 | `make bench` sends 200 photos to the running API and writes p50 and p95 per stage and end to end to `eval/results/bench-<date>.json`, naming the CPU. | Must | — |
| FR-14 | Every error (wrong file type, file too large, server down, timeout) is shown in plain words with a next step, and the shopper's photo is kept for a retry. | Must | — |
| FR-15 | Shoppers' photos are processed in memory and discarded. They're never written to disk, logged or sent to analytics. | Must | — |
| FR-16 | The served model is chosen by the pre-registered rule in D-08, applied by a script to the dev results and the benchmark, and recorded with its reasons. | Must | — |
| FR-17 | A product page offers "More like this", which searches with that product's stored vector and leaves the product itself out. | Could | P2 |
| FR-18 | On first visit the page shows three example photos the shopper can tap to try a search, and one line of advice on taking a good photo. | Should | — |

### 6.2 Non-functional

| ID | Requirement | Priority |
| --- | --- | --- |
| NFR-01 | p95 time inside `/search` ≤ 500 ms, and end to end ≤ 1,500 ms, for 640 px photos on an Intel i7-10750H with no GPU, after 10 warm-up requests. | Must |
| NFR-02 | Every reported metric comes from a results file written by `make eval` or `make bench`, or from a raw table of recorded sessions; the README Results block is generated from those files. | Must |
| NFR-03 | Catalogue sampling, the query split and the random baseline use fixed seeds; rebuilding from the same inputs gives the same product IDs and the same metrics. | Must |
| NFR-04 | The search flow works with a keyboard only; result images have the product name as alt text; text and controls meet WCAG 2.2 AA contrast. | Should |
| NFR-05 | Works at phone widths from 360 px, with camera capture in current Chrome on Android and Safari on iOS, and on desktop Chrome, Firefox and Safari. | Should |
| NFR-06 | Runs on free tools only: open models and data, CPU inference, PostHog free plan. No paid API is needed to build, evaluate or demo it. | Must |
| NFR-07 | Eval query photos have EXIF stripped and show no faces. Web photos carry a licence that allows this use and are credited (D-26); the owner's own photos are taken with consent and recorded by code only. | Must |

## 7. Key flows

1. **Photo search.** Take or choose a photo → resized on the phone → ten results → open one.
2. **Nothing close.** Photo of an item the catalogue doesn't cover → no-match panel → retake, crop, or show closest anyway.
3. **Messy photo.** Blurry or dark photo → results with a banner → retake.
4. **Several garments.** Outfit photo → mixed results → crop to one item → new results.
5. **Ship decision (internal).** `make index` → `make eval` (dev) → `make bench` → D-08 rule picks the model → `make eval` (test, once) → README Results.

## 8. Out of scope (v1) and why

| Item | Why not now |
| --- | --- |
| Checkout, prices, stock | The catalogue has none, and the problem is finding, not buying |
| Text or text-plus-image search | A different problem (P1 is about not having the words); doubles the eval |
| Automatic multi-garment detection | Needs a detection model and its own eval; a manual crop covers the case in v1 (D-10) |
| Accounts, history, personalisation | No persona needs them to test G1–G5, and they bring personal data |
| Fine-tuning a model | The experiment compares off-the-shelf generic and fashion models; training would need labelled pairs we don't have |
| Approximate nearest-neighbour indexes | Exact search is under a millisecond at 5,000 products (D-05); revisit above about 100,000 |
| Catalogues beyond the 10 article types | Keeps the relevance labels checkable by one person; reserved types test the no-match path |

## 9. Dependencies

| Dependency | Needed for | Risk link |
| --- | --- | --- |
| Hugging Face datasets (`ashraq/…`, `ceyda/…`) | Catalogue labels and images | R-08, R-14 |
| open_clip and the two model weights | Embeddings | — |
| PostHog free plan | Events, feature flag, experiment | R-11 |
| 60–100 labelled photos (Openverse since D-26) | Eval | R-02, R-10, R-17 |
| Five shoppers | Discovery and usability | R-10 |
| A hosted demo (for example a free Hugging Face Space) | The experiment needs outside visitors | R-09, R-08 |

## 10. Release gates

| Gate | Criteria |
| --- | --- |
| M0 → M1 | PRD reviewed; discovery done or explicitly deferred (logged); relevance rule confirmed |
| M2 → M3 | Eval runs on dev for all three systems; test-split target set and written down (Q3) |
| M3 → M4 | Model chosen by the D-08 rule; latency within NFR-01 or the gap logged with a decision |
| v1 release | UAT exit criteria met ([uat-plan.md](uat-plan.md) §5); usability round done; README Results generated |

## 11. Open questions

| # | Question | Owner | Due | Answer |
| --- | --- | --- | --- | --- |
| Q1 | Can the Myntra-sourced product images be shown on a public hosted demo? Neither Hugging Face card states a licence. | PM | Before M5 | [TBD] (R-08) |
| Q2 | Is "same type and same colour" the right relevance rule, or do shoppers weigh pattern more? | PM | End of M0 | [TBD] from discovery (A1) |
| Q3 | What Recall@10 target on test counts as good enough? | PM | End of M2 | **Proposed 2026-10-21, awaiting owner approval:** the shipped model's strict Recall@10 on the 44 test photos is at least 0.50, and its 95% interval sits wholly above random's. Reasoning: on 18 dev photos the two models scored 0.56 and 0.67 with lower bounds of 0.33 and 0.44, so 0.50 is reachable but not given; and "above random" is the minimum for the number to mean anything. The test split stays unread until this is approved (OQ-05 too). |
| Q4 | Where will the experiment's visitors come from, and how many are realistic in two weeks? | PM | Before M5 | [TBD] (R-09) |
| Q5 | Should the colour rule merge near-identical source colours (`Navy Blue` and `Blue`, `Off White` and `White`)? | PM | M2 | Not in v1: the strict rule stands, type-only is reported beside it (D-06) |

## 12. Change history

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-20 | First draft from the build plan, the resume bullet and dataset checks |
| 0.2 | 2026-10-21 | Query photos from Openverse instead of the owner's phone (D-26); NFR-07 reworded to cover licences |
| 0.3 | 2026-10-21 | Q3 test target proposed from the dev run |
