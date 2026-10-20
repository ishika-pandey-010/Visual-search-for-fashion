# Build the catalogue, 2026-10-20

## What the user needs
The product owner (me, wearing the PM hat) needs a catalogue that anyone can rebuild with one command and get exactly the same products, so every number later in the project is about a fixed, known set of things.

## What the docs said
- FR-11 and NFR-03 ([PRD §6](../PRD.md#6-requirements)): `make catalogue` builds from the public datasets in one command; fixed seeds give the same product IDs.
- US-01 ([user-stories.md](../user-stories.md#us-01-build-the-catalogue)): AC1 columns, 10 types, ≤ 500 each; AC2 same IDs in the same order on a rerun; AC3 bad rows dropped and counted by reason; AC4 reserved types only in the holdout.
- D-02 (labels from the ashraq copy, images from the ceyda copy, joined on id), D-03 (the 10 types and the reserved three), D-19 (pinned SHAs), D-21 (source bytes, not re-encoded).
- UAT cases TC-CAT-01 to TC-CAT-04.

## Plan
`vsearch/catalogue.py` with two halves. `load_sources()` downloads the four pinned parquet files and normalises them into a labels table and an images table. `build()` takes those two tables and writes the catalogue, the holdout, the images and the report. Keeping `build()` free of downloads means the tests can hand it a small generated fixture (D-20).

Left out on purpose: any image processing beyond reading the size (D-21), any balancing by gender (OQ-03), and the index, which is US-02.

## Tests written
Unit tests on a generated fixture (`tests/test_catalogue.py`, fixture in `tests/conftest.py`): 6 products for each of the 13 types, plus one of every bad row the build must drop (no colour, no image, a 150 × 200 image, bytes that aren't an image), an image with no label and a product of an unrelated type (Socks). The tests use a cap of 4 per type so the cap is exercised.

- TC-CAT-01: columns, only the 10 types, cap held; and each image file is the source bytes at the path the row names.
- TC-CAT-02: same seed twice gives the same IDs in the same order. A companion test checks that a different seed gives a different sample, because without it TC-CAT-02 would pass for a build that ignored the seed.
- TC-CAT-03: every bad row is missing from the catalogue and counted under its reason, with its ID listed.
- TC-CAT-04: reserved types only in the holdout, with images written; Socks in neither.
- The report records source SHAs, seed, cap and counts; both sources are pinned to 40-character SHAs.

Checks on the real build (`tests/test_catalogue_data.py`, marked `data`, run by `make test-data`): the same four cases against `data/`, including every image on disk being at least 200 px on its short side, and the build matching the committed manifest.

First failures: with no module, the conftest import failed. I then added the constants and a `build()` that raised `NotImplementedError`, so each test failed on its own: 7 failed, 1 passed. The one that passed was the SHA test. With `SOURCES` still empty it looped over nothing and passed. I changed it to require both sources first. A test that can pass on an empty input isn't testing anything.

## What I built
- `vsearch/catalogue.py`: `load_sources()` (pinned downloads via `huggingface_hub`), `build()` (filter to the 13 types, drop bad rows by reason, seeded sample of up to 500 per type, write source bytes, report) and `write_manifest()`.
- `eval/catalogue-manifest.csv`: product ID, type and colour for all 4,905 products, committed. It's the record of what every later number is about.
- `make catalogue`, `make test`, `make test-data`.

The real build (output of `make catalogue`):

| | |
| --- | --- |
| Catalogue | 4,905 products: 500 each of Casual Shoes, Handbags, Jeans, Kurtas, Shirts, Tops, Tshirts; Shorts 496, Trousers 472, Dresses 437 |
| Holdout | 1,426: Watches 500, Sunglasses 500, Sarees 426 |
| Dropped | no image 956, image too small 40, no label 0, unreadable 0 |
| Images with no label row | 274 |
| Image sizes kept | 4,883 at 384 × 512, 22 at 360 × 480 |
| First run | 2 min 56 s wall clock, peak memory 1.6 GB (mostly the 0.6 GB of image parquet) |
| Rerun, downloads cached | 7 s |

The missing images are spread across every type, heaviest in Shirts (301) and Tshirts (249), which have thousands to spare. All 40 small images are exactly 150 × 200, so the 200 px rule removes a batch of thumbnails rather than cutting into real photos. The catalogue came out at 4,905 rather than the "about 4,960" in D-03, logged as D-22.

Something to carry into US-02: 1,002 catalogue products share a display name with another product. Some may be the same photo listed twice, which would make "a catalogue image finds itself at rank 1" fail through a tie, not a bug.

## User review
- Main task: rebuild the catalogue on a fresh machine and know it's the one that was evaluated.
- Steps: 2 commands (`make setup`, `make catalogue`), no prompts or keys. I couldn't find one to remove.
- Errors, before review: with no network, `make catalogue` printed a long `huggingface_hub` traceback. After: one sentence, "Couldn't download the datasets (…). Check the internet connection and run make catalogue again; nothing was written.", exit code 1, and nothing in `data/`. Test first: `test_given_the_download_fails_…`.
- Knowing it's the same catalogue, before review: the manifest was overwritten silently, so you'd only find out from `git diff`. After: every run ends with "The catalogue matches the committed manifest" or "differs from the committed manifest: N added, M removed. Commit … only if you meant to change the catalogue". Test first: `test_given_a_rebuild_when_it_matches_…`.
- Feedback: the first run spends most of its 3 minutes in the download, which shows `huggingface_hub`'s own progress bars. The build step after it prints nothing for about 20 s.
- Remaining friction: no progress indicator during that 20 s. Not worth a dependency for a step that runs once.

## What went wrong
While writing the manifest test, its first run happened before I'd changed `main()`, and the old `main()` called `write_manifest()` with its default path, which is the repo's real `eval/catalogue-manifest.csv`. The test overwrote it with 56 fixture products. The next real rebuild then reported "4905 added, 56 removed", which is how I caught it. Fixes: `write_manifest()` now resolves its default path when called, not when defined, and an autouse fixture in `tests/conftest.py` points the manifest at a temp file for every unit test. I checked the real manifest's checksum before and after a full test run: unchanged. Then a rebuild reported "matches the committed manifest".

I also got one assertion wrong in the same test. I expected 10 products removed when the cap drops from 4 to 3, but the fixture's Tshirts has only 2 usable rows (all four bad rows are Tshirts), so the answer is 9. The test now says why.

## Decisions
- D-17 CPU-only torch; D-18 branch per feature; D-19 pinned SHAs, no `datasets` library; D-20 fixture tests in CI, real-data tests in `make test-data`; D-21 source bytes; D-22 accept 4,905.

## Doc changes
- data-contracts.md §2: `image_path` is relative to the data directory (it said `data/images/…`, which would break if the data directory moves); the drop-then-sample order; the manifest.
- feature-map.md: US-01 done, AC tightened to mention the manifest.
- decisions.md: D-22.

## Open questions
- OQ-03 (gender balance) and OQ-04 (drop before sampling) stay as assumptions.

## Next
US-02, one index per model. Nothing in M2 can run without it, and the duplicate-name question above needs an answer before the self-retrieval check means anything.
