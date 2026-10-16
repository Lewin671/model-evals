# Three models, two reasoning efforts

The same eight frozen cases are evaluated independently at low and high effort. These are model + harness + effort configurations, not isolated base models. Each configuration/case has one sample.
Browser/desktop are action-dependent text-state simulations, not real application control.

| Model | Harness | Effort | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Strict completion |
|:--|:--|:--|:--|:--|:--|:--|:--|
| deepseek/deepseek-v4.1-flash | Command Code | low | ✓ / ✓ | ✓ / ✗ | ✓ / — | ✗ / ✗ | 4/7 graded |
| z-ai/glm-5.3-flash | Command Code | low | ✓ / ✗ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 7/8 graded |
| deepseek/deepseek-v4.1-flash | Command Code | high | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 8/8 graded |
| z-ai/glm-5.3-flash | Command Code | high | ✓ / ✗ | ✓ / ✓ | ✓ / ✓ | ✗ / ✓ | 6/8 graded |
| gpt-6-luna | Codex | low | ✓ / ✓ | ✗ / ✗ | ✓ / ✓ | ✗ / ✓ | 5/8 graded |
| gpt-6-luna | Codex | high | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 8/8 graded |

✓ strict artifact complete · ✗ incomplete artifact · — excluded or missing; never a semantic zero.

A strict failure may reflect a content defect or interface/format error. DeepSeek low desktop-B has correct numeric data but an extra header; GLM high desktop-A invents file-ID suffixes. Read the failure analyses before treating strict counts as reasoning scores. The excluded DeepSeek low browser-B case prevents a complete balanced comparison at low effort.

Luna **high completes 8/8**, tied with DeepSeek high; Luna low completes 5/8.
The three low-run content failures (two itinerary/cost cases and one cents total) are
corrected in the high sample. [Luna low failure analysis](../luna-low-01/failure-analysis.md) ·
[Luna high findings](../luna-high-01/findings.md). These are observations from one run, not causal effort estimates.

## Identity and inference controls

| Harness | Model and effort evidence | Request-count evidence |
|:--|:--|:--|
| Command Code | Observed in CLI request events | Model-request-start events; provider retries may still be opaque |
| Codex | Explicit invocation/configuration; not independently exposed in JSONL | Exec invocations and turn completion; underlying model requests/retries not exposed |

Both CLIs run in fresh temporary directories with personal project context disabled and tool use forbidden. Codex additionally disables discovered tools/integrations through its existing adapter. System prompts and native tool presentation remain harness-specific, and can affect correctness and token overhead. Same effort names do not imply equal compute.

The task/checker, first prompts, 120-second timeout, response constraints and 16,000-output soft guard are retained. Each model/effort has eight episodes and at most twelve response invocations. A missing/protocol-failed episode is not retried. There is no additional constrained-output schema for Codex. ZDR is unset only in evaluation child processes.

## Reported usage per configuration

| Model | Harness | Effort | CLI invocations | Reported input tokens | Reported output tokens | Reported cache-read tokens |
|:--|:--|:--|--:|--:|--:|--:|
| [deepseek/deepseek-v4.1-flash](../paired-short-01/report.md) | Command Code | low | 11 | 151,450 | 4,603 | 72,832 |
| [z-ai/glm-5.3-flash](../paired-short-01/report.md) | Command Code | low | 12 | 204,323 | 1,447 | 97,920 |
| [deepseek/deepseek-v4.1-flash](../paired-short-high-01/report.md) | Command Code | high | 12 | 165,455 | 10,892 | 79,360 |
| [z-ai/glm-5.3-flash](../paired-short-high-01/report.md) | Command Code | high | 12 | 204,205 | 2,302 | 114,240 |
| [gpt-6-luna](../luna-low-01/report.md) | Codex | low | 12 | 162,835 | 630 | 84,864 |
| [gpt-6-luna](../luna-high-01/report.md) | Codex | high | 12 | 139,195 | 1,643 | 23,552 |

Usage totals are summed from each configuration’s recorded response steps. Usage fields come from different CLIs and are not verified account charges. Input includes harness overhead; the missing low case and different contexts prevent direct cost-efficiency inference. Raw CLI events remain private.

## Per-task evidence

- [Command Code low: deepseek/deepseek-v4.1-flash, z-ai/glm-5.3-flash](../paired-short-01/report.md)
- [Command Code high: deepseek/deepseek-v4.1-flash, z-ai/glm-5.3-flash](../paired-short-high-01/report.md)
- [Codex low: gpt-6-luna](../luna-low-01/report.md)
- [Codex high: gpt-6-luna](../luna-high-01/report.md)

## Interpretation limits

These are eight small, freshly authored cases. Familiar concepts may occur in training. One sample cannot establish reliability, significance, causal effort gains or a universal ranking. The code checker uses six fixed inputs and does not exhaust the contract. Per-field checks are correlated debugging evidence, not additional independent tasks. The simulators do not measure visual perception or real navigation/recovery.

Frozen task/checker SHA256: `40b1f6f999afa65ee0836e90f3133b7f8af8b5f347c78112600233176c811180`.
