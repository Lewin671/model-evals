# High-effort findings

Both Flash models were configured at high effort, verified from CLI request events.
The exact eight cases/checker, CLI version and resource caps match the low run.
All sixteen episodes finished with verified identity/effort and semantic grades.

| Model | Finding | Interpretation |
|:--|:--|:--|
| DeepSeek v4.1 Flash | 8/8 strict task completion | Corrected the low-run itinerary, pending-row inclusion and extra-header problems. Browser B now completed; its low result was excluded. |
| GLM 5.3 Flash | 6/8 strict task completion | Coding B and desktop A failed, for different reasons. |

GLM's coding-B solution now uses a per-account key, fixing the low-run root cause.
However, it references `accepted_dims`, which is never defined. Five nonempty inputs
raise NameError; only the empty input passes. This is an actual code-execution defect.

GLM's desktop-A first action invents locator suffixes: `r1.xlsx#revision1` and
`r2.xlsx#revision2`. Those are not manifest file IDs, so the simulator returns no
workbook data. It then selects r2 correctly but exports an empty table. This is a tool
argument/interface failure that propagates into the artifact, not evidence of bad cents
arithmetic. The frozen checker records the incomplete artifact; this explanation keeps
the failure kind distinct.

## Practical reading

For this high-effort run, DeepSeek is the better-performing configuration: no observed
content or interface failures, versus GLM's one code defect and one locator failure.
This reverses the low-run preference; it does not establish a general or reliable ranking.
Each case has only one sample per effort; effort effects and sampling variation cannot
be separated here. More reasoning is not a guarantee of a better answer.

## Consumption

High used 24 requests and 13,194 reported output tokens versus low's 23 requests and
6,050 reported output tokens. The input totals were 369,660 and 355,773 respectively.
These are reported usage fields, not verified account charges. High output is about
2.18 times the low total, but one low episode was incomplete.

Most high output came from DeepSeek (10,892 tokens versus GLM's 2,302). Its final
workbook response alone reported 6,900 output tokens while returning a short artifact.
Reasoning can consume quota even when the visible final answer is brief. Do not assume
this small task suite establishes a typical effort/cost multiplier.
