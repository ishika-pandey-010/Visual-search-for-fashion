# Retrieval eval harness, 2026-10-21

## What the user needs
The product owner needs one command that scores every system on the same photos the same way, so the model choice in M3 rests on numbers anyone can reproduce, with honest error bars.

## What the docs said
- FR-12, NFR-02, NFR-03 ([PRD §6](../PRD.md#6-requirements)); US-04 AC1–AC5 ([user-stories.md](../user-stories.md#us-04-retrieval-eval-harness)); [eval-plan.md](../eval-plan.md) §3 (relevance: same type and colour; type-only beside it), §4 (Recall@10 as hit rate, Precision@10, MRR, 95% bootstrap, 1,000 resamples), §5 (random, OpenCLIP, FashionCLIP rows; only in-catalogue photos scored).
- data-contracts §6 (the results file).
- UAT cases TC-EVAL-04 to TC-EVAL-08.

## Plan
`vsearch/evaluate.py`: relevance rules, the three metrics as plain functions over ranked relevance flags, a seeded random ranker, bootstrap intervals, and `evaluate()`, which embeds each query photo, searches each model's index and writes `eval/results/<date>.json`. Also a per-query file, `eval/results/<date>-queries.csv`, with each query's top 10 and the rank of its first relevant result, so every number can be traced back to photos.

`make eval` scores dev only. `make eval-test` adds the test split and logs the read (US-04 AC5). Test stays unread in this session: the owner hasn't spot-checked the labels (OQ-05) and the test target isn't set (PRD Q3).

Left out on purpose: the similarity floor and no-match rates (US-08, M3) and the model choice (US-06, M3). The results file's `no_match` and `model_choice` fields stay absent until then; `scripts/results.py` already handles that.

## Tests written
`tests/test_evaluate.py`, on the fixture catalogue with both fake indexes and a query set made from catalogue images, plus one out-of-catalogue and one not-fashion photo:

- TC-EVAL-05: three hand-built rankings with the arithmetic in the docstring (Recall@10 2/3, Precision@10 0.1, MRR 1.25/3), and a relevant result at rank 11 doesn't count.
- Relevance rules: strict needs type and colour; type-only needs type.
- TC-EVAL-06: the random list is the same for the same seed and query, different for another query or seed, ten distinct catalogue products; two whole runs give identical rows.
- TC-EVAL-07: the bootstrap interval brackets the mean, repeats with the same seed, and is (1, 1) for all hits.
- TC-EVAL-04: the results file has every system × split × rule row with `n` equal to the in-catalogue count; catalogue images as queries give the models 1.0 on every metric while random doesn't; the per-query file has each query's top 10.
- TC-EVAL-08: a dev run leaves no test-read line; two test runs leave two dated lines.
- A dev run writes no test rows; an empty split gives rows with n = 0 instead of a crash; a query whose type and colour the catalogue doesn't stock is counted (D-30).

`tests/test_evaluate_data.py` (`make test-data`): the real dev eval, run twice, has every row and repeats exactly, without reading test.

First failures: 11 of 11 against a stub. After the real code, 4 failed for one reason. The fixture's 12 photos were spread over 10 types, and the per-type floor I'd just added in US-03 (D-29) sent all of them to test, so dev was empty and the code crashed on an empty split. Two fixes: the fixture sets dev and test explicitly, and an empty split now gives n = 0 rows (a new test), since a real set could have one too.

## What I built
- `vsearch/evaluate.py`: `relevant`, `metrics`, `bootstrap_interval`, `random_ranking` (seeded by run seed and query id, so adding photos doesn't reshuffle anyone else's list), `evaluate` and `make eval` / `make eval-test`.
- `scripts/results.py`: copes with a dev-only file; shows the dev numbers in their own row, labelled as the tuning split; says "query photos", not "phone photos".

## The dev run (`make eval`, 18 in-catalogue dev photos, 14 s including loading both models)

| System | Recall@10, strict (95% interval) | P@10 | MRR | Recall@10, type only |
| --- | --- | --- | --- | --- |
| Random | 0.06 (0.00–0.17) | 0.01 | 0.02 | 0.50 |
| OpenCLIP ViT-B-32 | 0.56 (0.33–0.78) | 0.16 | 0.29 | 0.94 |
| Marqo-FashionCLIP | 0.67 (0.44–0.89) | 0.23 | 0.39 | 1.00 |

A second run gave identical numbers.

What this says, and what it doesn't:
- Both models are far above random, so the metric is measuring something (R-01).
- Type is nearly solved: 17 of 18 dev photos get a same-type product in the top 10 with OpenCLIP, 18 of 18 with FashionCLIP. Almost every strict miss is a colour miss. I first wrote here that near-colours (navy against blue) explained most of them; checking the returned colours showed that was too strong. Of the 13 strict misses across both models, 6 are near colours: a navy dress returned black (both models), navy jeans returned blue, a tan bag returned brown (both), and a mustard kurta returned brown. The other 7 are real colour failures: a beige dress, pink sneakers and a grey tote came back mostly black or blue, plus OpenCLIP's one type miss, a multicoloured blouse. So the strict rule is harsh on near colours (PRD Q5), and the models also lose colour on some photos. Usability should ask whether shoppers accept "right type, near colour".
- FashionCLIP is 11 points ahead on dev, past the 5 points D-08 asks for. But the intervals overlap almost entirely: 18 photos can't separate the two models. D-08 was written knowing dev would be small, and the latency half of the rule still has to be measured (M3).
- Random's type-only score is 0.50 because ten random picks from ten roughly equal types often include one of the right type. That's why type-only is never the headline.

One photo can't score a strict hit at all: q015, a lavender shirt, and the catalogue has no lavender shirts. Five more have only 1 to 4 possible matches. They stay in, counted (D-30).

The test split was not read. `eval/results/test-reads.log` doesn't exist.

## User review
- Main task (product owner): see where the models stand on dev, and why.
- Steps: 1 command, `make eval`, 14 s. The printed table answers "where", and the per-query file answers "why" for each photo.
- Before review the per-query file had no way to tell "the model missed" from "there was nothing to find". After: `strict_matches_in_catalogue` per query, and `unanswerable_strict` per split in the results (D-30). Test first.
- Remaining friction: reading the per-query file means looking up product IDs. A small HTML report with thumbnails would make the misses visible at a glance. It's not in any story, so I've left it out.

## Decisions
- D-30 unanswerable queries stay in as misses, and are counted.

## Doc changes
- data-contracts §6: `rule`, `unanswerable_strict`, the per-query file, the test-read log; `no_match` and `model_choice` arrive in M3.
- eval-plan §3: how unanswerable photos count.
- PRD Q3: a proposed test target, awaiting the owner (0.3).
- feature-map: US-04 done.

## Open questions
- PRD Q3 needs the owner's approval before `make eval-test`.
- OQ-05 (label spot-check) also gates the test read.

## Next
M3: the search API (US-07), no-match floor (US-08), photo-not-kept (US-10), latency benchmark (US-05) and the D-08 model choice (US-06). M3 starts with a plan for approval.
