# Model evaluation results

**Suite:** `micro-v1` · **Seed:** `4367184791228143466` · **Attempts:** 1 per task/configuration

**Ground truth correction:** tenant-isolation classification in security triage was corrected for every saved answer, without new model calls. [Adjudication and original scores](../../docs/adjudications/001-security-triage.md).

| Model | Reasoning effort | Source | Score | Full passes | Input / output tokens |
|:--|:--|:--|--:|--:|--:|
| `gpt-6.1-sol` | `high` | Codex | **100.0%** | 6/6 | 73,486 / 1,797 |
| `deepseek/deepseek-v4.1-flash` | `high` | Command Code | **83.3%** | 5/6 | 82,457 / 6,069 |
| `z-ai/glm-5.3-flash` | `high` | Command Code | **82.6%** | 4/6 | 101,812 / 3,074 |
| `gpt-6-luna` | `high` | Codex | **82.6%** | 4/6 | 69,314 / 2,121 |

Equal task weights. A missing or failed infrastructure run receives no aggregate score.
Token accounting is CLI-reported; cache and reasoning counters differ between providers. No dollar costs are inferred.

## Task breakdown

| Model | Effort | Source | Task | Score | Checks | Status |
|:--|:--|:--|:--|--:|--:|:--|
| `deepseek/deepseek-v4.1-flash` | high | Command Code | config-merge | 100.0% | 24/24 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | config-merge | 95.8% | 23/24 | graded |
| `gpt-6.1-sol` | high | Codex | config-merge | 100.0% | 24/24 | graded |
| `gpt-6-luna` | high | Codex | config-merge | 95.8% | 23/24 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | reservation-ledger | 100.0% | 24/24 | graded |
| `gpt-6-luna` | high | Codex | reservation-ledger | 100.0% | 24/24 | graded |
| `gpt-6.1-sol` | high | Codex | reservation-ledger | 100.0% | 24/24 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | reservation-ledger | 100.0% | 24/24 | graded |
| `gpt-6.1-sol` | high | Codex | snapshot-pagination | 100.0% | 24/24 | graded |
| `gpt-6-luna` | high | Codex | snapshot-pagination | 100.0% | 24/24 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | snapshot-pagination | 100.0% | 24/24 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | snapshot-pagination | 100.0% | 24/24 | graded |
| `gpt-6.1-sol` | high | Codex | security-triage | 100.0% | 1/1 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | security-triage | 0.0% | 0/1 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | security-triage | 0.0% | 0/1 | graded |
| `gpt-6-luna` | high | Codex | security-triage | 0.0% | 0/1 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | evidence-reconciliation | 100.0% | 1/1 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | evidence-reconciliation | 100.0% | 1/1 | graded |
| `gpt-6.1-sol` | high | Codex | evidence-reconciliation | 100.0% | 1/1 | graded |
| `gpt-6-luna` | high | Codex | evidence-reconciliation | 100.0% | 1/1 | graded |
| `deepseek/deepseek-v4.1-flash` | high | Command Code | release-selection | 100.0% | 1/1 | graded |
| `gpt-6-luna` | high | Codex | release-selection | 100.0% | 1/1 | graded |
| `gpt-6.1-sol` | high | Codex | release-selection | 100.0% | 1/1 | graded |
| `z-ai/glm-5.3-flash` | high | Command Code | release-selection | 100.0% | 1/1 | graded |

## Reproducibility

| Run | Commit | CLI versions |
|:--|:--|:--|
| 1 | `a0eb82407b4adb8735c7ec09897a866266403b2e` | {&quot;cmd&quot;: &quot;1.82.5&quot;, &quot;codex&quot;: &quot;codex-cli 0.162.1&quot;} |

Adapter revisions: `a0eb82407b4adb8735c7ec09897a866266403b2e`, `f67b0bf85a0d8d0958814e3fefee8855b4d4520d`.

During acquisition, the Codex adapter initially counted startup diagnostic items as tool actions. The parser was corrected and the saved response was graded without another model call. During that adapter correction, task generators and graders were unchanged. The later ground truth adjudication is documented separately.

Suite fingerprint: `262029ebc66445ac7afc28242bb3570b91c14bffee93afea7827df4d485d6440`.

Command Code model/effort identity is checked against request events. Codex JSONL does not expose those fields;
Codex entries report the explicitly configured model/effort, not an independently verified upstream identity.
Command Code ZDR enforcement is disabled only in evaluation child processes; this setting does not control Codex retention.

Six tasks are a screening sample, not a statistically established general ranking. A tied score is a tie on this suite.
Code cases within one task are correlated. Different harnesses remain a confound even with identical prompts and effort labels.

Corrected grading fingerprint: `2b3b787106756639508e841516606c6bab36dc0388778695a9991a8fb1b0900c`.
Adjudication commit: `42971895d08e2a304e43e9a33c520fe763754d32`.
