# User stories

Each story names the requirement it delivers (FR/NFR in [PRD.md](PRD.md)) and the milestone it's planned for. Acceptance criteria (AC) use Given/When/Then. If an AC can't be written that way, the requirement is still ambiguous and goes back to the PRD.

Two personas appear. **Shopper** stories (E3–E5) are about the app. **Product owner** stories (E1–E2) are about the evidence needed to decide whether the app is good enough and which model to ship; they're written as stories so they get acceptance criteria and tests like everything else.

**Story format**

```text
US-nn  Title                                   FR-nn · Priority · Milestone · Points
As a <persona>, I want <capability>, so that <outcome>.
AC1  Given … When … Then …
```

Points are relative size estimates (1, 2, 3, 5, 8) set in M0 backlog refinement.

---

## Epic E1 — Catalogue and index

### US-01 Build the catalogue
FR-11, NFR-03 · Must · M1 · 3

As the product owner, I want a catalogue built from the public datasets in one command, so that anyone can rebuild exactly what was evaluated.

- **AC1** Given both Hugging Face datasets, when I run `make catalogue`, then `data/catalogue.parquet` has one row per product with the columns in [data-contracts.md](data-contracts.md) §2, only the 10 types in D-03, and at most 500 per type.
- **AC2** Given the same inputs and seed, when I run it twice, then both runs produce the same product IDs in the same order.
- **AC3** Given a product with no image, no label, or an image under 200 px on its short side, when the catalogue is built, then it's left out and counted by reason in `data/catalogue-report.json`.
- **AC4** Given the reserved types (D-03), when the catalogue is built, then none of them are in the catalogue and they're written to `data/holdout.parquet` instead.

### US-02 Build one index per model
FR-11 · Must · M1 · 3

As the product owner, I want one search index per model, so that both models are compared on exactly the same products.

- **AC1** Given the catalogue, when I run `make index`, then `data/index/openclip/` and `data/index/fashionclip/` each hold a FAISS index, an ID file of the same length as the catalogue, and `meta.json`.
- **AC2** Given any stored vector, when its length is computed, then it's 1 within 0.001 (L2-normalised).
- **AC3** Given 200 catalogue images used as queries, when each is searched against its own model's index, then at least 198 return themselves at rank 1. This is a sanity check on the wiring, not a quality claim.
- **AC4** Given the catalogue has changed since an index was built, when the API or `make eval` loads that index, then it refuses with "Index is out of date: run make index".

---

## Epic E2 — Evaluation and the ship decision

### US-03 Labelled phone photos
FR-12, NFR-07 · Must · M2 · 2

As the product owner, I want a checked set of real phone photos with labels, so that the metrics describe the photos shoppers will actually take.

- **AC1** Given photos in `eval/queries/` and `labels.csv`, when I run `make eval-check`, then every photo has exactly one label row, every row has a photo, and every `article_type` and `base_colour` is in the catalogue vocabulary.
- **AC2** Given any photo in `eval/queries/`, when its metadata is read, then it has no EXIF block.
- **AC3** Given labels without a split, when the split is assigned, then each photo gets `dev` or `test` by seed, the split is written to `labels.csv`, and a later run never changes an existing assignment.
- **AC4** Given the labelled set, when `make eval-check` runs, then it prints counts by `kind` and by type, and warns if any catalogue type has fewer than 4 test photos.

### US-04 Retrieval eval harness
FR-12, NFR-02, NFR-03 · Must · M2 · 5

As the product owner, I want one command that scores every system on the same photos, so that the model choice rests on numbers anyone can reproduce.

- **AC1** Given the indexes and labelled photos, when I run `make eval`, then `eval/results/<date>.json` matches [data-contracts.md](data-contracts.md) §6 and has rows for random, OpenCLIP and FashionCLIP, on dev and test, under the strict and type-only rules.
- **AC2** Given a hand-built ranking with known answers, when the metric functions score it, then Recall@10, Precision@10 and MRR equal the hand-worked values in the test.
- **AC3** Given the random baseline with its fixed seed, when `make eval` runs twice, then every number in the file is identical.
- **AC4** Given each metric, when the file is written, then it carries a 95% bootstrap interval (1,000 resamples of the photos, fixed seed).
- **AC5** Given `--split test`, when it's run, then the run is logged with its date in `eval/results/test-reads.log`, so every look at the test split is on the record.

### US-05 Latency benchmark
FR-13, NFR-01 · Must · M3 · 3

As the product owner, I want latency measured the same way every time, so that the speed claim holds up on a named machine.

- **AC1** Given the API running locally, when I run `make bench`, then 200 requests are sent and `eval/results/bench-<date>.json` records p50 and p95 for decode, embed, search, server and end to end, and the CPU model.
- **AC2** Given the first 10 requests, when percentiles are computed, then they're excluded as warm-up and the file records `"warmup": 10`.
- **AC3** Given a GPU is present, when the benchmark runs, then it forces CPU and says so in its output.

### US-06 Choose the model by the written rule
FR-16 · Must · M3 · 1

As the product owner, I want the model choice made by a rule written down before the numbers came in, so that I can't talk myself into the result I wanted.

- **AC1** Given dev results and a benchmark file, when the D-08 rule is applied, then the chosen model and a one-sentence reason with the numbers are written to the eval results file and to the API config.
- **AC2** Given FashionCLIP beats OpenCLIP by fewer than 5 points of dev Recall@10, when the rule runs, then OpenCLIP is chosen.
- **AC3** Given FashionCLIP's p95 server time is over 500 ms, when the rule runs, then OpenCLIP is chosen whatever the accuracy gap, and the reason says latency decided it.

---

## Epic E3 — Search

### US-07 Search API
FR-03 · Must · M3 · 5

As a shopper, I want my photo matched against the whole catalogue, so that I see the closest products first.

- **AC1** Given a JPEG of a shirt, when it's posted to `/search`, then the response has 10 results, ranks 1–10, sorted by score from highest to lowest.
- **AC2** Given any result, when the response is read, then it has `product_id`, `score`, `name`, `article_type`, `base_colour` and `image_url`, and the image URL loads.
- **AC3** Given a catalogue product's own image, when it's posted to `/search`, then that product is rank 1.
- **AC4** Given a request, when it completes, then `timings_ms` reports decode, embed, search and total.

### US-08 No close match
FR-05 · Must · M3 · 3

As a shopper, I want to be told when the catalogue has nothing like my photo, so that I don't waste time on junk results.

- **AC1** Given a photo of something that isn't clothing (a mug), when I search, then I see "No close match in this catalogue" with Retake and Crop to one item, and no product grid.
- **AC2** Given a photo of a garment type the catalogue doesn't carry (a saree), when I search, then I see the same panel.
- **AC3** Given the no-match panel, when I choose "Show closest anyway", then the ten closest products appear with a note that they're weak matches.
- **AC4** Given the floor in the API config, when it's set, then it came from the dev photos by the method in [eval-plan.md](eval-plan.md) §6, and the value and date are in `decisions.md`.

### US-09 Photo quality warning
FR-06 · Should · M3 · 3

As a shopper, I want to know when my photo is the reason results look off, so that I can retake it instead of blaming the search.

- **AC1** Given a blurry photo, when I search, then the results show with a banner: "This photo looks blurry, so results may be off." and a Retake button.
- **AC2** Given a dark photo, when I search, then the banner says "This photo is quite dark, so results may be off." with Retake.
- **AC3** Given a sharp, well-lit photo, when I search, then no banner shows.
- **AC4** Given the blur and brightness thresholds, when they're set, then they came from the dev photos and no more than 1 in 10 sharp dev photos triggers a banner.

### US-10 My photo isn't kept
FR-15, NFR-07 · Must · M3 · 2

As a shopper, I want my photo used only for this search, so that pictures from my phone don't end up stored somewhere.

- **AC1** Given a search, when it completes, then no new file exists in the API's working directory, data directory or system temp directory.
- **AC2** Given a search, when the API logs are read, then they contain no image bytes, no file name and no EXIF fields.
- **AC3** Given any analytics event, when its payload is inspected, then it has no image data, file name or EXIF field.

### US-11 Take or upload a photo
FR-01, FR-02, FR-18 · Must · M4 · 5

As a shopper, I want to search with the camera or a photo I already have, so that I can act on what I see or saved.

- **AC1** Given I'm on a phone, when I tap "Take or upload a photo", then the system picker offers the camera and the photo library.
- **AC2** Given I'm on desktop, when I choose a file or drop one on the page, then the search starts.
- **AC3** Given a 12-megapixel photo, when it's sent, then the uploaded image is at most 640 px on its long side and has no EXIF data.
- **AC4** Given I've chosen a photo, when the request starts, then a loading state with my photo's thumbnail appears within 100 ms.
- **AC5** Given my first visit, when the page loads, then I see three example photos I can tap to search and one line of advice: "One item, good light, fill the frame."

### US-12 Results and product page
FR-04, NFR-04, NFR-05 · Must · M4 · 3

As a shopper, I want to scan the results and look closer at one, so that I can tell quickly whether any is what I want.

- **AC1** Given results, when they show, then each has the product image, name, type and colour, under a thumbnail of my photo.
- **AC2** Given results, when I tap one, then its product page opens with a larger image and its details, and Back returns to the same results without a new search.
- **AC3** Given only a keyboard, when I search and open a result, then every step can be reached with Tab and Enter, focus is visible, and each image's alt text is the product name.
- **AC4** Given a 360 px wide screen, when results show, then nothing scrolls sideways and at least four results are visible without scrolling.

### US-13 Clear errors
FR-14 · Must · M4 · 2

As a shopper, I want errors to tell me what to do, so that I can get to results without starting over.

- **AC1** Given I choose a PDF, when the upload is tried, then I see "That file isn't a photo. Use a JPG, PNG or WebP." and nothing is sent.
- **AC2** Given the API is down, when I search, then I see "Search is offline right now. Your photo is kept, so try again." and Retry searches again with the same photo.
- **AC3** Given the API takes more than 10 s, when the timeout passes, then the request is cancelled and I see the same offline message with Retry.
- **AC4** Given an image file over 10 MB that can't be shrunk on the device, when I try to send it, then I see "That photo is too large. Try a screenshot of it instead." and nothing is sent.

### US-14 Narrow by category
FR-07 · Should · M4 · 2

As a shopper, I want to keep only one type of product in the results, so that a photo with a shirt and jeans can show me just shirts.

- **AC1** Given results, when they show, then chips list the article types among the top 50.
- **AC2** Given I tap the "Shirts" chip, when results reload, then all ten are Shirts, ranked by score.
- **AC3** Given a chip is selected, when I tap it again, then the unfiltered results return.

### US-15 Crop to one item
FR-08 · Should · M4 · 3

As a shopper, I want to crop my photo to one garment, so that an outfit photo searches for the piece I care about.

- **AC1** Given results, when I choose "Crop to one item" on my photo's thumbnail, then a crop box appears over the photo, starting at the full frame.
- **AC2** Given I drag the box around the shoes and choose Search, when results load, then only the cropped area was sent.
- **AC3** Given only a keyboard, when the crop box has focus, then the arrow keys move it and Shift + arrows resize it.

---

## Epic E4 — Measurement

### US-16 Analytics events
FR-09 · Must · M4 · 3

As the product owner, I want each search and click recorded, so that I can see which ranks shoppers use and where they give up.

- **AC1** Given a local session with PostHog configured, when I search and open the result at rank 3, then `search_submitted`, `results_shown` and `result_clicked` with `rank: 3` appear in PostHog with the properties in [data-contracts.md](data-contracts.md) §7.
- **AC2** Given PostHog is blocked or no key is set, when I search, then the app works normally and no error shows.
- **AC3** Given a no-match search, when the panel shows, then `no_match_shown` is sent with `top_score` and `floor`.

### US-17 Results layout experiment
FR-10 · Must · M5 · 3

As the product owner, I want visitors split between two results layouts, so that the layout we keep is the one shoppers click more.

- **AC1** Given a new visitor, when the page loads, then the PostHog flag assigns layout A or B, and a reload keeps the same layout.
- **AC2** Given either layout, when results show and a result is opened, then `results_shown` and `result_clicked` carry `layout_variant`.
- **AC3** Given the flag can't be fetched within 1 s, when results show, then layout A is used and events carry `layout_variant: "fallback"`, which the analysis leaves out.

---

## Epic E5 — Browsing

### US-18 More like this
FR-17 · Could · M4 · 2

As a shopper, I want to search again from a product I like, so that I can explore nearby styles without a new photo.

- **AC1** Given a product page, when I choose "More like this", then ten other products show, ranked by similarity to that product, and the product itself isn't among them.
- **AC2** Given a "More like this" search, when it's sent, then `search_submitted` has `source: "similar"`.
