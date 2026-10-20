# Results layout experiment: plan

Written 2026-10-20, before any layout exists. Launch, if it happens, is after usability round 1 in M5. Results go in [ab-test.md](ab-test.md). Anything changed here after launch is logged in [decisions.md](decisions.md) with the reason, and the README says so.

## 1. Question

Does a denser results grid, with all ten results visible on a phone screen, get more shoppers to open a result than larger cards that show about four at a time?

## 2. Variants

| | Layout A (control) | Layout B |
| --- | --- | --- |
| Grid on a 360 px phone | 2 columns, large cards | 3 columns, compact cards |
| Card | Image, name, type and colour | Image, with the name on one line; type and colour on the product page |
| Results visible without scrolling | About 4 | About 9 |

**Why this pair.** If the first relevant result often sits below rank 4 (the eval's MRR will show this), larger cards hide it below the fold. Denser cards show more at once but give each one less detail. That trade-off is real, and either answer is useful.

Usability round 1 may show a different problem worth testing (for example, shoppers not trusting results without colour labels). If so, layout B is replaced before launch, and the replacement and its reason go in `decisions.md`. Nothing changes once the experiment is live.

## 3. Metrics

| Role | Metric | Definition |
| --- | --- | --- |
| **Primary** | Search click-through | Search sessions with `results_shown` (`match: true`) that have at least one `result_clicked`, ÷ all such sessions |
| Secondary | Rank of first click | Median `rank` of the first `result_clicked` in a session |
| Secondary | Clicks per search | Mean `result_clicked` per search session with results |
| Guardrail | "Show closest anyway" rate | Must not differ; the layout shouldn't change how no-match is handled |
| Guardrail | Event loss | API `/search` count vs. `search_submitted` count, per day (R-11) |

## 4. Assignment and exclusions

- PostHog feature flag, 50/50, by `distinct_id`, so one visitor always sees one layout (US-17).
- Excluded from analysis: `layout_variant: "fallback"`, my own `distinct_id`s and those of usability participants, and any visitor with more than 50 searches a day (bots or testing).
- Unit of analysis is the search session. Sessions from one visitor aren't independent, so click-through per visitor is also reported as a check.

## 5. Sample size

Inputs (assumed, since there is no baseline yet): control click-through 40%, smallest change worth acting on 10 points (to 50%), two-sided α = 0.05, power 0.80.

Two-proportion formula: **388 search sessions with results per layout**, 776 in all. `scripts/results.py` computes this from the same inputs, so the plan and the README can't drift. For reference, a 15-point change needs 173 per layout and a 5-point change needs 1,534.

## 6. Duration and stopping

Fixed at 14 days from launch, both weekends included. No early stop for a good-looking result and no peeking-based decisions. The test stops at day 14, or earlier only if a guardrail breaks (event loss over 30%, or an error in either layout).

## 7. Decision rule

| Outcome at day 14 | Decision |
| --- | --- |
| ≥ 388 per layout, B ahead with p < 0.05 | Ship B |
| ≥ 388 per layout, A ahead with p < 0.05, or no significant difference | Keep A, the simpler cards |
| Fewer than 388 per layout | **Directional only.** Report both rates, the n and the p-value as they are. The layout decision rests on the usability rounds, and the click data is supporting evidence |

## 8. What to expect

A portfolio demo shared with classmates, friends and a LinkedIn post will probably draw tens to low hundreds of searches in two weeks, not 776. The likely outcome is the third row. That's fine as long as it's labelled. What isn't fine is calling a 30-search difference a win. The README and the resume line will both carry the n and the "directional" label if that's what happens (D-13).

## 9. Where visitors come from

[TBD] (PRD Q4). Needs a hosted demo, which depends on PRD Q1 (image licence).
