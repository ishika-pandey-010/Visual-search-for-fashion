# Risk log

Reviewed at every milestone review. **Likelihood** and **Impact** are 1 (low) to 3 (high); **Score** = L × I. A product risk is closed only when its proving test passes. A delivery risk is closed when its trigger date passes without the risk happening.

## Product risks

| ID | Risk | L | I | Score | Mitigation | Proving test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | The headline metric means nothing because random ranking would score almost as well | 1 | 3 | 3 | About 5,000 products, so ten results are 0.2% of the catalogue (D-03); the random row is in every results table | TC-EVAL-04, TC-EVAL-06 | Open |
| R-02 | Query labels use different words from the catalogue, so true matches score as misses | 2 | 3 | 6 | Labels chosen only from the catalogue's own vocabulary; `make eval-check` rejects anything else | TC-EVAL-01 | Open |
| R-03 | Phone photos of worn clothes look so unlike studio product shots that both models do poorly | 3 | 2 | 6 | Measured, not hidden: real phone photos only, plus the type-only rule, a fashion model and the crop | TC-EVAL-04, TC-SRCH-08 | Open |
| R-04 | Shoppers get confident-looking junk for items the catalogue doesn't carry | 3 | 2 | 6 | Similarity floor and no-match panel (D-09), tuned on dev | TC-FAIL-01, TC-FAIL-02, TC-FAIL-08 | Open |
| R-05 | Choices are tuned on the photos they're scored on, so the headline number is inflated | 2 | 3 | 6 | Fixed dev/test split; tuning on dev only; every test read logged (D-07) | TC-EVAL-03, TC-EVAL-08 | Open |
| R-06 | The fashion model is too slow on CPU for the latency budget | 3 | 2 | 6 | Pre-registered rule falls back to the generic model (D-08); phone-side resize (D-11) | TC-EVAL-14, TC-NFR-08 | Open |
| R-07 | A shopper's photo is stored, logged or sent to analytics | 1 | 3 | 3 | In-memory only (D-12); phone-side re-encode drops EXIF; tests check files, logs and payloads | TC-NFR-01 – TC-NFR-03, TC-SRCH-07 | Open |
| R-08 | The product images can't be shown on a public demo because their licence is unknown | 3 | 2 | 6 | Local demo and recorded GIF first; hosted demo only after PRD Q1 is answered; fall back to a demo without images if needed | TC-NFR-04 | Open |
| R-09 | The layout experiment gets too few searches to mean anything | 3 | 2 | 6 | Sample size computed in advance; result labelled directional when short (D-13); usability round as the fallback evidence | TC-ANLY-04, TC-ANLY-05 | Open |
| R-11 | Ad blockers drop PostHog events, so click-through is computed on a biased subset | 2 | 2 | 4 | Compare API search counts with `search_submitted` counts and report the gap beside the experiment | TC-ANLY-02 | Open |
| R-14 | The 60 × 80 px source images are too small to embed well | 3 | 3 | 9 | Images from the 384 × 512 copy, joined on id (D-02); minimum size checked at build | TC-CAT-03 | Open |
| R-17 | Web photos are cleaner than shoppers' phone photos, so the eval flatters the search | 3 | 2 | 6 | Prefer real-world settings over studio shots; record each photo's setting and report results by setting; add owner phone photos as a second source when they exist (D-26) | TC-EVAL-04, TC-EVAL-16 | Open |
| R-15 | Low-light and blurred photos quietly return worse results | 3 | 1 | 3 | Quality banner with retake (D-14); thresholds set on dev | TC-FAIL-04, TC-FAIL-05, TC-FAIL-07 | Open |

## Delivery risks

| ID | Risk | L | I | Score | Mitigation | Trigger date | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-10 | Fewer than five shoppers, or fewer than 60 query photos, can be found (photos: mitigated by D-26) | 2 | 3 | 6 | Ask in week 1; book seven shoppers for five; collect photos from friends' wardrobes with consent and no faces | End of M1 | Open |
| R-12 | Scope creep: text search, auto-detection, prices, accounts | 2 | 2 | 4 | Out-of-scope list in PRD §8 and CLAUDE.md; every new ask logged in decisions.md | Each milestone planning | Open |
| R-13 | Numbers on the resume can't be traced to a file | 2 | 3 | 6 | README Results generated from eval and session files only (CLAUDE.md rule 4); brackets on the resume until then | v1 release | Open |
| R-16 | Embedding 10,000 images (two models) is too slow on this laptop | 1 | 1 | 1 | CPU build reused when current (D-25); GPU or a free notebook as a fallback | M1 | Closed 2026-10-20: 46 min, once (D-25) |
