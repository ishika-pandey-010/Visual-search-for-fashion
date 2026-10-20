# UAT plan

## 1. Purpose

Confirm, before v1 release, that every story's acceptance criteria hold in the running app and pipeline, and that every product risk's proving test passes. The UAT sheet is [`uat/test-cases.csv`](uat/test-cases.csv); counts in the README come from that file (CLAUDE.md rule 4).

UAT is a different thing from the eval. The eval measures how good the search is; UAT checks the product does what the stories say. A failing Recall@10 target isn't a UAT bug, but a results file missing the random row is.

## 2. Scope

| In | Out |
| --- | --- |
| Every story US-01 – US-18 and its AC | Load testing beyond the 200-request benchmark |
| Every product risk's proving test | Penetration testing (privacy is tested functionally) |
| Keyboard use, phone camera, contrast (NFR-04, NFR-05) | Out-of-scope features in PRD §8 |

## 3. Modules and cases

| Module | Covers | Stories |
| --- | --- | --- |
| CAT | Catalogue build, indexes | US-01, US-02 |
| EVAL | Query set, eval harness, benchmark, model rule | US-03 – US-06 |
| SRCH | Search API, photo input, crop, errors | US-07, US-11, US-13, US-15 |
| RES | Results grid, product page, chips, more like this | US-12, US-14, US-18 |
| FAIL | No close match, quality warnings | US-08, US-09 |
| ANLY | Analytics events, layout experiment | US-16, US-17 |
| NFR | Privacy, free tools only, devices, contrast, latency budget | US-10, US-05, NFR-04 – NFR-06 |

Live counts per module: [traceability.md](traceability.md#uat-sheet-status).

## 4. Environment and data

- **Where:** local (API and web app on the i7-10750H) for everything; phone cases (TC-NFR-05, TC-NFR-06) on real devices over the local network or on the hosted demo if PRD Q1 allows one.
- **Data:** the catalogue and indexes from `make catalogue` and `make index` at the release commit; the dev photos for FAIL cases, never the test photos.
- **Pipeline cases** (CAT, EVAL) run from the command line and record the command output in `actual`.

## 5. Entry and exit criteria

| | Criteria |
| --- | --- |
| **Entry** | All M1–M4 stories merged; automated tests green on `main`; indexes built at the release commit; UAT sheet reviewed |
| **Exit** | Every case executed (status not `Not run`); 100% of Critical and High cases `Pass`; no open Critical or High bugs; every Medium/Low failure has a bug with a decision (fix now / later) |

## 6. How to run a case

1. Set up the precondition.
2. Follow the steps exactly; don't improvise around a problem.
3. Write what actually happened in `actual`, even on a pass.
4. Set `status` to `Pass`, `Fail` or `Blocked`; fill `tested_by` and `tested_on` (YYYY-MM-DD).
5. On `Fail`, raise a bug (next section) and put its ID in `bug`.
6. Run `make docs` so the status counts update.

## 7. Bug workflow

| Severity | Meaning | Fix by |
| --- | --- | --- |
| **Critical** | A shopper's photo kept or leaked, a wrong metric in a results file, or the test split used for tuning | Before anything else; blocks release |
| **High** | A Must story's AC fails with no workaround | Within the milestone; blocks release |
| **Medium** | Fails with a workaround, or a Should story fails | Before release, or logged as a known issue with a decision |
| **Low** | Cosmetic or wording | Backlog |

Lifecycle: `Open → In progress → Fixed → Verified (re-run the case) → Closed`. A bug is `Closed` only when its TC passes on re-run. Every Critical and High fix also gets an automated test so it stays fixed, linked in the bug.

Bug fields (Jira, mirrored in the GitHub bug template): ID, TC ID, story, severity, steps, expected, actual, screenshot or API response, environment, model and index build, fixed in commit, verified on.

## 8. Sign-off

| Role | Name | Date | Result |
| --- | --- | --- | --- |
| Product owner | [TBD] | [TBD] | [TBD] |
| Tester | [TBD] | [TBD] | [TBD] |
