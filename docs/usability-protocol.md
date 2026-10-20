# Usability test protocol

Five shoppers, three tasks each, in M5 once the app runs end to end. Then one layout change, then two more sessions on the changed layout. Raw results go in [usability.md](usability.md); nothing in the README is typed by hand.

## 1. Participants

- Five people who buy clothes online at least monthly (book seven in case of no-shows, R-10). At least three should have tried a camera search before (Google Lens, a retailer's app).
- Record only a code (S1–S5, S6–S7 for round 2), how often they shop online, and whether they've used visual search before. No names in git.
- Each uses their own phone, so the camera, screen size and browser are real.

## 2. Tasks

Set up before the session: a shirt and a pair of casual shoes that I bring (not in the catalogue, but their types are), one printed outfit photo with a top, jeans and shoes, and a saree or a watch.

| Task | Prompt read to the participant | What it tests |
| --- | --- | --- |
| T1 | "Here's a shirt. Find something like it in this shop." | The main flow: camera, results, open one (US-11, US-12) |
| T2 | "You like the shoes in this outfit photo. Find shoes like them." | Several garments in one photo: do they find the crop or the chips? (US-14, US-15) |
| T3 | "Find something like this." (hand them the saree or watch) | No close match: do they understand it, and what do they do next? (US-08) |

Order: T1 first always (it's the onboarding), then T2 and T3 alternating between participants.

## 3. Running a session (about 25 minutes)

1. Consent script: what we're testing (the app, not them), that they can stop at any time, that only a code is recorded, and that their photos aren't stored by the app (FR-15).
2. Open the app on their phone from a link. No walkthrough: first use is part of what's tested.
3. For each task, read the prompt and start the timer. Ask them to think aloud.
4. **Success** means they open a product they say is "like it" (T1, T2), or they say in their own words that the shop doesn't have it (T3).
5. Stop the timer at success, or at 3 minutes (a fail). If they're stuck for 90 seconds, note "assisted" and give one sentence of help. An assisted task counts as a fail.
6. Note the **rank of the first result they open** and whether they used crop, chips, retake or "Show closest anyway".
7. After each task: "How easy was that, from 1 (very hard) to 7 (very easy)?"
8. Closing questions:
   - Was there a moment you didn't trust the results? What caused it?
   - What did you expect to happen when nothing matched?
   - What would make you use this instead of typing a search?

## 4. What is recorded per task

Participant code, round, task, layout, success (y/n), time (mm:ss), rank of first click, ease (1–7), and notes on features used and anything said aloud worth quoting.

## 5. From round 1 to the layout change

After five sessions, read the notes and the PostHog click-by-rank for those sessions together. Pick **one** change to the results layout that addresses the most common problem, log it as a decision, build it, then run S6 and S7 on the changed layout with the same three tasks. One change, so the before/after says something about that change.

## 6. Analysis

- Task success per task: x of 5. Target: at least 4 of 5 on each (PRD §5).
- Median time per task, on successful attempts only, with all raw times shown.
- Median rank of first click.
- Themes from the closing questions, with participant codes.
- Limits: five people, one session each, my own catalogue and app, and the facilitator is the builder.
