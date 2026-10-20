# Labelled query photos, 2026-10-21

## What the user needs
The product owner needs a set of real photographs, each labelled with what the garment is and what colour it is, so the eval can say how often the search finds the right kind of product for a photo that wasn't taken in the catalogue's studio.

## What the docs said
- FR-12 and NFR-07 ([PRD §6](../PRD.md#6-requirements)); US-03 AC1–AC4 ([user-stories.md](../user-stories.md#us-03-labelled-query-photos)); [eval-plan.md §2](../eval-plan.md#2-the-query-set): 60–80 in-catalogue photos (at least 4 per type in test), 10–15 out-of-catalogue, 10 not fashion; labels from the catalogue vocabulary; dev/test split assigned once.
- UAT cases TC-EVAL-01, -02, -03, -15, and TC-EVAL-16 (new, below).

## The owner's instruction, and why it isn't followed to the letter
On 2026-10-21 the owner asked me to "use freepik to obtain images and proceed", in place of their own phone photos. I read the terms before downloading anything:

- Freepik (now branded Magnific) §8.1(7): free content may not be used "for any machine learning and/or artificial intelligence purposes". Scoring CLIP models on those photos is exactly that. §2 also bans automated downloads outside its API, which needs a key.
- Pexels, the obvious second choice, §8: no scraping "for machine learning purposes" and no use of the service "for purposes of performance benchmarking".
- Openverse: a public API with no key (20 requests a minute, 200 a day anonymously), returning a licence per image. CC0, the public-domain mark, CC BY and CC BY-SA allow this use with credit.

So the photos come from Openverse under those four licences (D-26). This keeps the owner's intent (go ahead without their photos) without breaking anyone's terms. It changes what the eval measures: these are photos other people took for the web, often better framed and lit than a shopper's quick snap. That's a new risk (R-17), recorded in the eval plan's limits, and it has to be reflected in how the result is described anywhere it's quoted.

## Plan
1. Docs first: D-26 (source), D-27 (store as `/search` would receive it: crop, 640 px, re-encode), D-28 (I label, before any search); US-03 AC5 and TC-EVAL-16 (every web photo credited under an allowed licence); contract §5; eval plan §2 and §8; NFR-07 reworded; R-17.
2. Tests first for `vsearch/queries.py` (checks, split, image preparation, attribution, rebuilding photos from the labelling record) and `vsearch/openverse.py` (licence-filtered search, contact sheets).
3. Collect candidates for each type with a few search terms, review them on contact sheets, pick and label, then build `eval/queries/` and run `make eval-check`.

Left out on purpose: the eval itself (US-04), and running any model on the photos before they're labelled.

## Tests written
`tests/test_queries.py` builds a tiny query set in a temp folder; `tests/test_openverse.py` fakes the HTTP opener, so nothing touches the network (D-20).

- TC-EVAL-01: a complete set passes; eight broken versions each fail with an error naming the photo: photo missing, photo with no label, colour not in the vocabulary, a reserved type labelled in-catalogue, a catalogue type labelled out-of-catalogue, a not-fashion photo with a type, an unknown kind, a duplicated ID.
- TC-EVAL-02: a JPEG with GPS and camera EXIF is detected, and the prepared copy has no EXIF at all; a set containing a photo with EXIF fails the check.
- D-27 preparation: 640 px long side, crop by frame fractions, EXIF rotation applied before the metadata is dropped (a portrait photo stays portrait), small photos never upscaled.
- TC-EVAL-03: 40 in-catalogue and 10 not-fashion photos get exactly 12 and 3 dev; same seed, same answer; adding 5 photos leaves the first 20 untouched.
- TC-EVAL-15: counts by kind and type, and a warning for a type under 4 test photos.
- TC-EVAL-16: a `by-nc` licence fails naming the photo; a missing creator and a missing source row fail; a stale `ATTRIBUTION.md` fails.
- Building from the labelling record: photos, labels, sources and credits written; a crop shows in `changes`; rebuilding keeps splits.
- Openverse: the request asks only for the four licences, photographs, not mature; any other licence or a mature flag in the response is dropped anyway; contact sheets lay out numbered thumbnails.

First failures: against stubs that raised `NotImplementedError`, all 24 new tests failed or errored and the 21 from M1 still passed. After the real code, one failed: my own expected size for a cropped photo. I'd written 320 × 480 for the middle half of a 1600 × 1200 photo; the middle half is 800 × 1200, which shrinks to 427 × 640. The code was right and the test comment was wrong.

The first real `make eval-collect` died on its first request: Openverse took 56 s to answer an uncached query (the same query a second time took 0.25 s), past the 30 s timeout, and searches weren't guarded the way downloads were. Two tests came out of it, both failing before the fix: a search that times out is retried once and then skipped with a message while the rest of the terms run; and a resumed run after a crash that saved nothing doesn't write a second CSV header, which the old code would have done.

## What I built
- `vsearch/queries.py`: the vocabulary file, image preparation (D-27), the split (`assign_splits`), the check (`check`), the credit file, and `build_queries`, which rebuilds the whole set from the labelling record.
- `vsearch/openverse.py`: licence-filtered search with retry, resumable collection into `data/candidates/` (git-ignored), and contact sheets for review.
- `make eval-collect`, `make eval-sheets`, `make eval-queries`, `make eval-check`.
- `eval/queries/`: 84 photos (5.1 MB), `labels.csv`, `sources.csv`, `selections.csv` (the labelling record, with crop boxes) and `ATTRIBUTION.md`. `eval/vocabulary.csv` (10 catalogue types, 3 reserved types, 38 colours). `eval/openverse-terms*.csv` (the 43 searches).

How the set was made:

| | |
| --- | --- |
| Searches | 30 terms in round 1, 13 in round 2 (for Kurtas, Jeans, Trousers, Handbags); 6 failed twice and were skipped |
| Candidates downloaded | 771 (47 min, then 13 min; most of it waiting on Openverse) |
| Chosen | 84: 62 in-catalogue, 12 out-of-catalogue (4 each of sarees, watches, sunglasses), 10 not fashion (mugs, laptops, fruit) |
| Setting of the 62 in-catalogue photos | worn 42, studio 7, display 7, flat 5, hanger 1 |
| Source | Flickr 62, rawpixel 14, StockSnap 8 |
| Licence | CC BY 31, CC0 30, CC BY-SA 13, public-domain mark 10 |
| Cropped | 36 (faces out, or one garment out of several) |
| Split | in-catalogue 18 dev / 44 test (every type 4–6 test); out-of-catalogue 4 / 8; not fashion 3 / 7 |

What the candidates were like, because it says something about using web photos at all. Most results weren't usable. "kurta" and "kurti" returned mostly fish from iNaturalist and photos of a politician named Kurti. "jeans" returned scanned 19th-century cartoons and a long series of a man in a bathtub. The shorts and tops results carried many glamour and feet photos, all skipped. Searches for real garments in plain settings worked best (t-shirts, sneakers, watches, mugs). About 11% of what was downloaded made it into the set.

Rules I applied while choosing, so the set is consistent:
- One garment is clearly the subject; if there were two, crop to one.
- No face visible after cropping. Where the face couldn't be cropped out, the photo was skipped.
- No 3D renders, paintings, illustrations, collages or adverts with text in the frame.
- No more than two photos of the same physical garment (the Pinarello t-shirts appear in eight candidates; two were used).
- Skip anything the source vocabulary files under a different type than it looks like. Running shoes are `Sports Shoes`, not `Casual Shoes`; beaded clutches are `Clutches`, not `Handbags`; messenger bags are their own type. Labelling them as the nearest catalogue type would quietly reward the search for a match the catalogue's labels say is wrong.

Labelling (D-28): I labelled type and colour from the photo before any search existed in the code. Everything was reviewed twice: once on the candidate sheets, then again on contact sheets of the built 640 px photos. The second pass caught six problems. Four crops still showed part of a face, or caught advert text (q013, q020, q022, q030; q030 took two attempts). Two crops missed the garment entirely (q041 caught legs instead of shorts; q076 caught the skateboard instead of the jeans). Two colours changed on a closer look: q012 from Purple to Navy Blue (a navy and red check), and q076 from Black to Navy Blue.

## User review
- Main task (product owner): get from "no photos" to a checked, credited, split set, and know it's still valid after any change.
- Steps: `make eval-collect` → `make eval-sheets` → review → edit `selections.csv` → `make eval-queries` → `make eval-check`. Five commands and one file to edit. The review itself can't be automated without running a model on the photos, which would defeat labelling before searching.
- After any change, one command (`make eval-check`) says whether the set is still valid, and CI runs the same check on the committed set (`test_tc_eval_01_the_committed_query_set_passes_every_check`).
- The first real `make eval-check` failed on 11 photos with no creator. All were CC0 from rawpixel, which names none. CC0 doesn't require credit, so the rule changed to require a creator only for CC BY and BY-SA, and the credit line says "creator not named". Test first.
- The same run showed the split was lopsided by type (Tops 0 dev, three types at 3 test). Splits are now stratified by type with a floor of 4 test photos per type. The first split was cleared once, before anything had read it (D-29). Test first.
- Remaining friction: reviewing 771 candidates by eye took most of the session. A smaller, better-aimed search list would cut that more than any code would.

## Decisions
- D-26 Openverse with four licences, not Freepik or Pexels; D-27 store photos as `/search` would receive them; D-28 Claude Code labels before any search, owner spot-checks; D-29 per-type stratified split, first split cleared once.

## Doc changes
- PRD 0.2: NFR-07 covers licences; dependencies row. US-03 renamed "Labelled query photos", AC5 added, 3 points (was 2). TC-EVAL-16 added; TC-EVAL-01 wording. data-contracts §5 rewritten (files, `source`, licences, creator rule, splits). eval-plan §2 (where photos come from, how they were chosen and labelled) and §8 (limits). R-17 added; R-10 noted as mitigated for photos. OQ-05 (owner spot-check), OQ-06 (thin types). Feature map: US-03 done.

## Open questions
- OQ-05: the owner should spot-check 15 labels before the test split is first read.
- R-17 stands: 42 of 62 in-catalogue photos are worn, but many are posed brand or portfolio shots, better lit than a shopper's quick photo. The results must say "openly licensed web photos", never "phone photos".

## Next
US-04, the eval harness: metric functions with hand-worked tests first, then the random baseline, intervals and the results file. Dev only until OQ-05 is answered and the test target (PRD Q3) is set.
