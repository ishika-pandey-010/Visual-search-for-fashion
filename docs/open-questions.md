# Open questions

Anything vague, missing or contradictory in the docs, with where it came from. An item marked **Assumption** is a call I made to keep building; it stays open until the product owner confirms or overturns it. Resolved items keep their row and say how they were resolved. The PRD's own questions (Q1–Q5) stay in [PRD §11](PRD.md#11-open-questions); this page holds what came up while building.

| ID | Source | Question | Status | Answer or working assumption |
| --- | --- | --- | --- | --- |
| OQ-01 | PRD §10 gate M0 → M1 | M1 is gated on a reviewed PRD, discovery and a confirmed relevance rule. None has happened. Start M1 anyway? | Open (accepted risk) | The owner approved the M1 plan on 2026-10-20. Building the catalogue and indexes doesn't depend on the relevance rule; the eval in M2 does. Discovery must land before M2 starts scoring, or M2 runs under the D-06 rule as written and says so. |
| OQ-02 | build-prompt §3.4 vs CLAUDE.md "traceability.md (generated; never edit)" | The build prompt asks for each test to be added to `docs/traceability.md`; CLAUDE.md forbids editing that file. | Resolved | `scripts/docs_check.py` reads TC IDs from test names and US tags from code and writes those columns itself. Nobody edits the file. |
| OQ-03 | data-contracts §2, D-03 | Should the catalogue be balanced by gender within each type? | Assumption | No. Sampling is uniform within each type, so the gender mix follows the source. Gender is kept as a column, so a filter or a balanced sample is cheap later. |
| OQ-04 | US-01 AC1 | The sample is "at most 500 per type". Is that before or after rows are dropped for missing images or labels? | Assumption | After. Unusable rows are dropped first, then up to 500 are sampled from what's left, so a type only falls short of 500 when the source has fewer usable products (Dresses). |
