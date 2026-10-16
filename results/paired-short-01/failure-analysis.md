# What actually failed

These explanations interpret frozen grades; no task, expected answer, candidate response,
or checker has been changed. Strict artifact completion and content reasoning differ.

| Case | Observed result | Failure kind | Why |
|:--|:--|:--|:--|
| GLM / coding B | `key = b['delivery']` | Content/code defect | The contract makes IDs unique per account. Two cross-account cases fail because the key omits the account. |
| DeepSeek / everyday B | F3, cost 163, meeting 11:00 | Content/optimization defect | It applies the right meeting time, but F2 reaches the venue at 10:30, satisfies the 20-minute buffer, and costs 110 after refund. F3 costs 53 more. |
| DeepSeek / desktop A | Adds `cy,300` | Content/filter defect | Cy's reimbursement is pending, not approved. Filtering out voided rows alone is insufficient. |
| DeepSeek / desktop B | Correct data rows preceded by `employee,cents` | Output-contract/artifact defect | The numeric rows and chosen workbook are correct. The simulator's export schema expects data rows with integer cents; its CSV writer already supplies a header. The resulting CSV has two headers. Do not interpret this as incorrect arithmetic or source selection. |
| DeepSeek / browser B | Denied native `shell_command` with `echo`; no simulator action | Protocol failure, excluded | The single request hit the one-turn cap. No semantic grade or retry was assigned. |

On the **seven cases with semantic grades for both models**, strict task completion is
DeepSeek 4/7 and GLM 6/7. This is descriptive, not a balanced four-domain score: browser B
is missing and the domains therefore have unequal representation. One DeepSeek strict
failure is an output-contract issue despite correct numeric data. Do not turn these counts
into a claim that one model is generally stronger.

The paired probe is useful for cheaply exposing specific weaknesses. It has only one
sample per case and cannot distinguish persistent weaknesses from sampling variation.
The small structured browser task produced no content error in the graded samples;
it has not demonstrated difficulty or real browser-use skill.
