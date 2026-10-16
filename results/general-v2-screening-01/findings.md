# Findings: general-v2 screening 01

All four configurations requested **high** reasoning effort. This round used **24 CLI
invocations**, including 12 through Command Code, with no repeated attempts. No security
task, real browser, real desktop, user calendar or actual invoice was used.

## What the strict outcome captures

DeepSeek V4.1 Flash, GPT-6.1-Sol and GPT-6-Luna satisfied every tested bundle in this round.
This is a tie on a small screen, not evidence of equal overall model capability.

GLM 5.3 Flash had two response-contract failures plus a bookkeeping error:

| Bundle | Observed result | Interpretation |
|:--|:--|:--|
| Config merge | Returned a malformed fragment and `def H(...): return {}` instead of the requested source object | No usable implementation was delivered; this is not a measured partial algorithm pass rate |
| Expense reconciliation | Returned 6,398 cents; the correct net is 6,398 − 9,379 = −2,981 cents | Approved negative credit was omitted from the arithmetic |
| Expense reconciliation | Excluded invoice IDs had the correct members but wrong order | Failed the explicitly requested sorted-output contract, not invoice membership selection |
| Desktop snapshots | Returned `[{"actions": [...]}]` instead of `{"actions": [...]}` | Wrong top-level shape; all six enclosed decisions were correct when inspected |

The published aggregate preserves the original strict grading rules. It must not be
read as a pure reasoning score or as proof that GLM cannot operate a desktop.

## UI reasoning reached a ceiling

| Model | Browser actions, original response | Desktop actions, original contract | Desktop content diagnostic |
|:--|--:|:--|:--|
| DeepSeek V4.1 Flash | 6/6 | 6/6 | 6/6; no repair |
| GLM 5.3 Flash | 6/6 | Contract failed | 6/6 after removing one outer array |
| GPT-6.1-Sol | 6/6 | 6/6 | 6/6; no repair |
| GPT-6-Luna | 6/6 | 6/6 | 6/6; no repair |

The desktop content diagnostic is **post-hoc and excluded from every official score**.
The same rule was applied to all four saved answers: if a response is a one-element
array containing an object, inspect that object; otherwise leave it unchanged. No
action, coordinate, text value or model response was edited. See [diagnostic data](diagnostics.json).

These basic snapshots did not distinguish the models' underlying action choices. That
ceiling is a result worth reporting; it is not a reason to invent a browser/computer-use
winner. The inputs were text/geometry rather than screenshots, and there was no interactive
observation/action loop or real application outcome.

## Everyday planning

All four models returned feasible schedules with the optimal priority total of **28**.
The grader accepts different schedules with that value. An independent pairwise check
of the generated instance also found an optimum of 28.

Three models reconciled every expense field correctly. GLM selected the right included
invoices and correctly identified the missing exchange rate, but omitted the approved
credit from the total and returned the excluded list unsorted.

## Implication for the next evaluation design

Keep three measurements distinct: **decision/content correctness**, **response-contract
reliability**, and **actual execution success**. This version reports strict outcomes and
failure reasons; the last measurement is not tested. The UI examples need harder independent
families or more paired state changes before they can support useful model separation.

A next suite could pair the same goal with focused/unfocused windows, fresh/stale geometry,
and partial/complete progress, then introduce a short simulated feedback loop. Those rules
must be fixed before new calls. No additional round was run to pursue a more convenient ranking.

[Every final response](responses.md) · [Strict scores](report.md) · [Task design](../../docs/general-v2.md)
