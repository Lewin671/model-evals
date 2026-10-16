# Incremental importer: bounded calibration

Coding only. Each episode is a fresh repository with actual native read/write/test tools.
The planned paired pilot uses **low reasoning effort**, with a **3 model-request cap**.
This measures performance within this tight budget; it is not an overall model ranking.

| Model | Starter | L1 | L2 | L3 | Total | Stop | Evidence |
|:--|:--|:--|:--|:--|:--|:--|:--|
| deepseek/deepseek-v4.1-flash | stream | 2/2 | 4/4 | 5/5 | 11/11 | stop_hook | [Checks](01-deepseek-v4.1-flash-stream/result.json) · [Source](01-deepseek-v4.1-flash-stream/workspace/ledger/api.py) · [Trace](01-deepseek-v4.1-flash-stream/tools.json) |

## Interpretation

Incomplete pilot. No paired model conclusion is justified.

The L1/L2/L3 checks cover baseline API/fragmentation, quoted streaming/replay, and coupled revision/atomicity/change behavior. Each scenario has equal weight; scenarios are correlated.

## Limits and accounting

Task/checker frozen before these calls. Final source is independently executed against eleven acceptance scenarios; prose is not scored. Identity and effort are verified from CLI events. ZDR was unset only in child processes.

Earlier adapter experiments are excluded from scores but included in usage. One interrupted prior request has unreported tokens, so reported totals are a lower bound. See [adapter incidents](../../docs/native-importer-pilot.md). Raw CLI streams and personal paths remain private.

Two independent source variants and one episode per model/variant were planned. Only the episode shown above completed. This does not establish reliability across seeds, maximum coding capability, browser use, desktop use, or everyday-task performance. Codex has not been run on this replacement task.

The first valid episode reported **12,047 output tokens**. Including invalid attempts, the
reported total reached **33,805**, exceeding the predeclared 32,000 soft guard during an
in-flight request. The runner then stopped before GLM; the planned four episodes were not completed.
No budget increase or automatic retry followed.
