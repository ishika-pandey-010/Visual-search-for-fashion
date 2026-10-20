# Results layout experiment: results

Plan: [ab-test-plan.md](ab-test-plan.md). **Not run yet.** The export rows are added only after the experiment's 14 days end, copied from the PostHog experiment and insight exports, which are saved beside this file as CSV.

## Run details

| | |
| --- | --- |
| Launched | [TBD] |
| Ended | [TBD] |
| Flag key | [TBD] |
| Layout B tested | [TBD] (as planned, or the replacement logged in decisions.md) |
| Event loss (API searches vs `search_submitted`) | [TBD] |

## Export

Counts after the exclusions in the plan §4. `scripts/results.py` computes click-through, the p-value and whether the sample is large enough from this table.

| Variant | Visitors | Searches with results | Searches with a click | Median rank of first click | Clicks per search |
| --- | --- | --- | --- | --- | --- |

## What we decided

[TBD — the row of the decision rule (plan §7) that applied, and what shipped.]
