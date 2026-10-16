# Paired short diagnostic v1

Two models, **low reasoning effort**, Command Code CLI. Model and effort are observed in request events.
Eight independently presented cases across four domains; browser/desktop use two-step text-state simulators.
This is a diagnostic screen, not an overall capability leaderboard.

| Model | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Tasks complete | Pairs complete |
|:--|:--|:--|:--|:--|:--|:--|
| deepseek/deepseek-v4.1-flash | ✓ / ✓ | ✓ / ✗ | ✓ / — | ✗ / ✗ | 4/7 graded; 1 excluded/missing | 1/3 graded |
| z-ai/glm-5.3-flash | ✓ / ✗ | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | 7/8 graded | 3/4 graded |

## What this established

The four-domain screen is incomplete: one DeepSeek/browser case produced a denied native shell call instead of a simulator action. It is excluded, not scored zero. Only never-attempted episodes were continued, without retry or task/checker changes. Compare common graded cases descriptively; no full balanced aggregate is justified.

The paired cases change delivery-ID scope, approval of a meeting update, a live checkout quote, and workbook approval status. A pair counts only if both variants complete. All four domains have equal task weight. Partial field/check scores remain debugging evidence.

[Read the concrete failure analysis, including content versus output-contract defects →](failure-analysis.md)

## Actual usage

**23 observed model requests**, 6,050 reported output tokens; 355,773 reported input tokens and 170,752 reported cache-read tokens (CLI usage fields).
These are CLI-reported counts, not verified dollar charges. Earlier importer experiments are separate. ZDR was unset only in child processes.

## Per-task evidence

| Case | Model | Outcome | Evidence |
|:--|:--|:--|:--|
| coding-A | deepseek/deepseek-v4.1-flash | complete | [Prompt, response & observations](coding-A-deepseek-v4.1-flash/evidence.md) |
| coding-A | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](coding-A-glm-5.3-flash/evidence.md) |
| everyday-A | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](everyday-A-glm-5.3-flash/evidence.md) |
| everyday-A | deepseek/deepseek-v4.1-flash | complete | [Prompt, response & observations](everyday-A-deepseek-v4.1-flash/evidence.md) |
| browser-A | deepseek/deepseek-v4.1-flash | complete | [Prompt, response & observations](browser-A-deepseek-v4.1-flash/evidence.md) |
| browser-A | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](browser-A-glm-5.3-flash/evidence.md) |
| desktop-A | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](desktop-A-glm-5.3-flash/evidence.md) |
| desktop-A | deepseek/deepseek-v4.1-flash | incomplete | [Prompt, response & observations](desktop-A-deepseek-v4.1-flash/evidence.md) |
| coding-B | deepseek/deepseek-v4.1-flash | complete | [Prompt, response & observations](coding-B-deepseek-v4.1-flash/evidence.md) |
| coding-B | z-ai/glm-5.3-flash | incomplete | [Prompt, response & observations](coding-B-glm-5.3-flash/evidence.md) |
| everyday-B | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](everyday-B-glm-5.3-flash/evidence.md) |
| everyday-B | deepseek/deepseek-v4.1-flash | incomplete | [Prompt, response & observations](everyday-B-deepseek-v4.1-flash/evidence.md) |
| browser-B | deepseek/deepseek-v4.1-flash | adapter_or_response_contract_failure | [Prompt, response & observations](browser-B-deepseek-v4.1-flash/evidence.md) |
| browser-B | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](browser-B-glm-5.3-flash/evidence.md) |
| desktop-B | z-ai/glm-5.3-flash | complete | [Prompt, response & observations](desktop-B-glm-5.3-flash/evidence.md) |
| desktop-B | deepseek/deepseek-v4.1-flash | incomplete | [Prompt, response & observations](desktop-B-deepseek-v4.1-flash/evidence.md) |

## Limits

The tasks are small and explicitly specified. The simulator can open multiple IDs at once, has no real navigation cost, and exposes structured data. It does not establish visual perception, real browser/computer use, realistic recovery, or source-file preservation in an actual application. A simulated export creates a real CSV artifact but never opens a spreadsheet application.

Coding coverage is six fixed inputs, not exhaustive: the empty batch shares its account with a later valid batch, so it does not isolate zero-account creation. Cases are newly authored, but familiar underlying patterns may occur in training. One run per model/case cannot measure reliability. No checker or task was tuned after seeing responses. JSON fences are normalized; response-contract failures are separate from semantic grades and stop execution.

[Frozen task design and reproduction](../../docs/paired-short-screen.md)
