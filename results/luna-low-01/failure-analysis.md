# Luna low: concrete failures

GPT-6 Luna through Codex, configured at low effort, completed 5/8 tasks. There were no
excluded protocol cases. Model/effort are configured through explicit CLI arguments;
the JSONL stream does not independently expose them.

| Case | Observed | Expected | Failure kind |
|:--|:--|:--|:--|
| Everyday A | F3, cost 103 | F3, cost 163 | Incorrect cash-cost value; flight and meeting are correct |
| Everyday B | F3, cost 188 | F2, cost 110 | Non-minimal itinerary and incorrect cash-cost value |
| Desktop A | Ada 1130 cents | Ada 1030 cents | Incorrect arithmetic; selected workbook and Bo's 705 cents are correct |

For everyday A, the new flight + bag + transfer + hotel is 130 + 25 + 18 + 90 = 263;
subtracting the 100 refund gives 163. The response does not explain its 103, so the
specific internal cause is unknown. For everyday B, F2 arrives at the venue at 10:30,
satisfies the 20-minute buffer before the 11:00 meeting, and costs 180 + 30 - 100 = 110.
For desktop A, Ada's approved 10.10 + 0.20 USD is 1030 cents, not 1130.

Both coding cases, both browser simulation cases and desktop B passed. These are small
fixed cases, not proof of broad coding or browser-use ability. No task/checker was tuned.
