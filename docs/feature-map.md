# Feature map

One row per feature, in build order. The user is the screenshot shopper from PRD §3 unless the row says product owner. Acceptance criteria are the ones in [user-stories.md](user-stories.md), shortened here; where I tightened one, the story file has the full wording and [decisions.md](decisions.md) has the reason. Status is one of `not started`, `in progress`, `done`.

| Story | Feature | The job the user is doing | Acceptance criteria (short) | Priority | Milestone | Status |
| --- | --- | --- | --- | --- | --- | --- |
| US-01 | Build the catalogue | Product owner: rebuild exactly what was evaluated | One command; 10 types, ≤ 500 each; same seed gives the same IDs, checked against the committed manifest; bad rows dropped and counted; reserved types only in the holdout | Must | M1 | done |
| US-02 | One index per model | Product owner: compare models on the same products | Both indexes with aligned IDs; vectors of length 1; ≥ 198 of 200 catalogue images find themselves at rank 1; stale index refused | Must | M1 | done |
| US-03 | Labelled phone photos | Product owner: score on the photos shoppers really take | Every photo labelled from the catalogue vocabulary; no EXIF; split assigned once and never changed | Must | M2 | not started |
| US-04 | Eval harness | Product owner: choose a model on reproducible numbers | Results file with random, OpenCLIP, FashionCLIP × dev, test × two rules; hand-worked metric tests; bootstrap intervals; test reads logged | Must | M2 | not started |
| US-07 | Search API | Find the closest products to a photo | Ten results sorted by score with every field; a catalogue image finds itself; stage timings | Must | M3 | not started |
| US-08 | No close match | Not waste time on junk | Mug and saree get the no-match panel; "Show closest anyway"; floor from dev | Must | M3 | not started |
| US-10 | My photo isn't kept | Trust that camera-roll photos aren't stored | No file written, nothing logged, nothing in analytics | Must | M3 | not started |
| US-05 | Latency benchmark | Product owner: back the speed claim | 200 requests, 10 warm-up, p50/p95 per stage, CPU named and forced | Must | M3 | not started |
| US-06 | Model choice by rule | Product owner: not pick the result I wanted | D-08 applied by a script; small gap or slow model keeps OpenCLIP | Must | M3 | not started |
| US-09 | Photo quality warning | Know when the photo is the problem | Blurry or dark gets a banner with Retake; sharp gets none; ≤ 1 in 10 false alarms on dev | Should | M3 | not started |
| US-11 | Take or upload a photo | Act on what I see or saved | Camera or library on phone, file or drop on desktop; ≤ 640 px, no EXIF; loading within 100 ms; three examples on first visit | Must | M4 | not started |
| US-12 | Results and product page | Tell quickly whether any result is it | Cards with image, name, type, colour; product page; Back without re-search; keyboard; 360 px | Must | M4 | not started |
| US-13 | Clear errors | Get to results without starting over | Non-photo refused in plain words; offline and timeout keep the photo for Retry; oversize refused | Must | M4 | not started |
| US-16 | Analytics events | Product owner: see which ranks get used | Events with §7 properties; app works with PostHog blocked; no-match event | Must | M4 | not started |
| US-14 | Narrow by category | Keep only one type in the results | Chips from the top 50; chip shows ten of that type; tap again to clear | Should | M4 | not started |
| US-15 | Crop to one item | Search for one piece of an outfit | Crop box from the full frame; only the crop is sent; keyboard moves and resizes | Should | M4 | not started |
| US-18 | More like this | Explore nearby styles | Ten others by similarity, not the product itself; tagged `similar` | Could | M4 | not started |
| US-17 | Layout experiment | Product owner: keep the layout shoppers click | Stable A/B by visitor; layout on every event; fallback to A, excluded | Must | M5 | not started |
