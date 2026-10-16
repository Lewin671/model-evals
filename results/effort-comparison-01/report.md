# Low versus high reasoning effort

Same eight cases, model IDs, task order, CLI version, checker, 120-second request timeout, one-turn response cap, 24-request budget and 16,000-output soft guard. Only effort is deliberately changed. Each episode starts fresh and receives no previous-run answer.
Reasoning effort and identity are observed in CLI request events. ZDR is unset only in child processes.

| Model | Effort | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Strict completion |
|:--|:--|:--|:--|:--|:--|:--|
| deepseek/deepseek-v4.1-flash | low | ✓ / ✓ | ✓ / ✗ | ✓ / — | ✗ / ✗ | 4/7 graded |
| deepseek/deepseek-v4.1-flash | high | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 8/8 graded |
| z-ai/glm-5.3-flash | low | ✓ / ✗ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 7/8 graded |
| z-ai/glm-5.3-flash | high | ✓ / ✗ | ✓ / ✓ | ✓ / ✓ | ✗ / ✓ | 6/8 graded |

✓ strict artifact completion · ✗ incomplete artifact · — excluded/missing, never a semantic zero.

The low DeepSeek/desktop-B failure is specifically an extra header with otherwise correct data. Strict completion is not a pure reasoning score. The low DeepSeek/browser-B case is a denied native shell call; it is excluded. See the [low-run failure analysis](../paired-short-01/failure-analysis.md).

For this high-effort run, **DeepSeek completed all eight tasks**, while GLM had one
code-execution defect and one invalid workbook-locator failure. The latter is an
interface error, not a demonstrated arithmetic weakness. [Detailed findings](../paired-short-high-01/failure-analysis.md).

## Within-model transitions

| Model | Case | Low → high |
|:--|:--|:--|
| deepseek/deepseek-v4.1-flash | everyday-B | ✗ → ✓ |
| deepseek/deepseek-v4.1-flash | browser-B | — → ✓ |
| deepseek/deepseek-v4.1-flash | desktop-A | ✗ → ✓ |
| deepseek/deepseek-v4.1-flash | desktop-B | ✗ → ✓ |
| z-ai/glm-5.3-flash | desktop-A | ✓ → ✗ |

## Measured usage

| Effort | Model requests | Reported input tokens | Reported output tokens | Reported cache-read tokens |
|:--|--:|--:|--:|--:|
| low | 23 | 355,773 | 6,050 | 170,752 |
| high | 24 | 369,660 | 13,194 | 193,600 |

Counts are CLI usage fields, not verified billing. Input context includes native CLI overhead. A soft guard can overshoot during an in-flight request. Missing/failed cases make total-usage ratios imperfect comparisons.

## Evidence and limits

[Low run](../paired-short-01/report.md) · [High run](../paired-short-high-01/report.md)

This is one sample per configuration/case. Changes can reflect sampling variation as well as effort; do not claim a causal effort gain, statistical significance, or a universal model ranking. The structured browser/desktop tasks do not measure real application control. No task or grader was tuned after either run.

Frozen task/checker SHA256: `40b1f6f999afa65ee0836e90f3133b7f8af8b5f347c78112600233176c811180`.
