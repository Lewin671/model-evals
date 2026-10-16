# Model evaluation results

**Suite:** `general-v2` · **Seed:** `10569335738111803925` · **Attempts:** 1 per task/configuration

| Model | Reasoning effort | Source | Strict outcome | Format failures | Input / output tokens |
|:--|:--|:--|--:|--:|--:|
| `deepseek/deepseek-v4.1-flash` | `high` | Command Code | **100.0%** | 0/6 | 83,774 / 6,942 |
| `gpt-6.1-sol` | `high` | Codex | **100.0%** | 0/6 | 74,766 / 1,454 |
| `gpt-6-luna` | `high` | Codex | **100.0%** | 0/6 | 70,620 / 2,641 |
| `z-ai/glm-5.3-flash` | `high` | Command Code | **56.2%** | 2/6 | 103,138 / 4,149 |

Each domain has equal weight; tasks are averaged within a domain. A missing or failed infrastructure run receives no aggregate score.
Token accounting is CLI-reported; cache and reasoning counters differ between providers. No dollar costs are inferred.

## Domain breakdown

| Model | Effort | Coding | Everyday | Browser (sim.) | Desktop (sim.) |
|:--|:--|--:|--:|--:|--:|
| `deepseek/deepseek-v4.1-flash` | high | 100.0% | 100.0% | 100.0% | 100.0% |
| `z-ai/glm-5.3-flash` | high | 50.0% * | 75.0% | 100.0% | 0.0% * |
| `gpt-6.1-sol` | high | 100.0% | 100.0% | 100.0% | 100.0% |
| `gpt-6-luna` | high | 100.0% | 100.0% | 100.0% | 100.0% |

\* Includes a response-contract failure scored as zero under the frozen rules. Inspect the response before interpreting it as a reasoning failure.

Browser/desktop results measure independent structured-state decisions, not real browsing, visual perception, or interactive tool execution.

## Task breakdown

| Model | Effort | Source | Task | Score | Checks | Status |
|:--|:--|:--|:--|--:|--:|:--|
| `deepseek/deepseek-v4.1-flash` | high | Command Code | config-merge | 100.0% | 24/24 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | config-merge | 0.0% | — | format_error |
| `gpt-6.1-sol` | high | Codex | config-merge | 100.0% | 24/24 | graded |
| `gpt-6-luna` | high | Codex | config-merge | 100.0% | 24/24 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | snapshot-pagination | 100.0% | 24/24 | graded |
| `gpt-6-luna` | high | Codex | snapshot-pagination | 100.0% | 24/24 | graded |
| `gpt-6.1-sol` | high | Codex | snapshot-pagination | 100.0% | 24/24 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | snapshot-pagination | 100.0% | 24/24 | graded |
| `gpt-6.1-sol` | high | Codex | morning-planner | 100.0% | — | graded |
| `gpt-6-luna` | high | Codex | morning-planner | 100.0% | — | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | morning-planner | 100.0% | — | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | morning-planner | 100.0% | — | graded |
| `gpt-6.1-sol` | high | Codex | expense-reconciliation | 100.0% | 4/4 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | expense-reconciliation | 50.0% | 2/4 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | expense-reconciliation | 100.0% | 4/4 | graded |
| `gpt-6-luna` | high | Codex | expense-reconciliation | 100.0% | 4/4 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | browser-snapshots | 100.0% | 6/6 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | browser-snapshots | 100.0% | 6/6 | graded |
| `gpt-6.1-sol` | high | Codex | browser-snapshots | 100.0% | 6/6 | graded |
| `gpt-6-luna` | high | Codex | browser-snapshots | 100.0% | 6/6 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | desktop-snapshots | 100.0% | 6/6 | graded |
| `gpt-6-luna` | high | Codex | desktop-snapshots | 100.0% | 6/6 | graded |
| `gpt-6.1-sol` | high | Codex | desktop-snapshots | 100.0% | 6/6 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | desktop-snapshots | 0.0% | — | format_error |

## Reproducibility

| Run | Commit | CLI versions |
|:--|:--|:--|
| 1 | `e9f7162bac9355fa18cb482d4344b9c68fc9dbce` | {&quot;cmd&quot;: &quot;1.82.5&quot;, &quot;codex&quot;: &quot;codex-cli 0.162.1&quot;} |

Suite fingerprint: `e441a044a4ff69ef9e8d1a601ad1fc49f8f847e48cda5919fd90c69584f46014`.

Command Code model/effort identity is checked against request events. Codex JSONL does not expose those fields;
Codex entries report the explicitly configured model/effort, not an independently verified upstream identity.
Command Code ZDR enforcement is disabled only in evaluation child processes; this setting does not control Codex retention.

Six tasks are a screening sample, not a statistically established general ranking. A tied score is a tie on this suite.
Code cases within one task are correlated. Different harnesses remain a confound even with identical prompts and effort labels.
