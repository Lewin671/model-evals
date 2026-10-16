# Paired short diagnostic v1

Configurations use **low reasoning effort**, Codex CLI. Model/effort are configured through the invocation; Codex JSONL does not independently expose them.
Eight independently presented cases across four domains; browser/desktop use two-step text-state simulators.
This is a diagnostic screen, not an overall capability leaderboard.

| Model | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Tasks complete | Pairs complete |
|:--|:--|:--|:--|:--|:--|:--|
| gpt-6-luna | ✓ / ✓ | ✗ / ✗ | ✓ / ✓ | ✗ / ✓ | 5/8 graded | 2/4 graded |

## What this established

The table shows observed task differences in this small run. Treat them as hypotheses for follow-up, not a general ranking or statistical significance.

The paired cases change delivery-ID scope, approval of a meeting update, a live checkout quote, and workbook approval status. A pair counts only if both variants complete. All four domains have equal task weight. Partial field/check scores remain debugging evidence.

[Read the concrete findings](failure-analysis.md)

## Actual usage

**12 Codex exec invocations** (underlying model requests/retries not exposed), 630 reported output tokens; 162,835 reported input tokens and 84,864 reported cache-read tokens (CLI usage fields).
These are CLI-reported counts, not verified dollar charges. Earlier importer experiments are separate. ZDR was unset only in child processes.

## Per-task evidence

| Case | Model | Outcome | Evidence |
|:--|:--|:--|:--|
| coding-A | gpt-6-luna | complete | [Prompt, response & observations](coding-A-gpt-6-luna/evidence.md) |
| everyday-A | gpt-6-luna | incomplete | [Prompt, response & observations](everyday-A-gpt-6-luna/evidence.md) |
| browser-A | gpt-6-luna | complete | [Prompt, response & observations](browser-A-gpt-6-luna/evidence.md) |
| desktop-A | gpt-6-luna | incomplete | [Prompt, response & observations](desktop-A-gpt-6-luna/evidence.md) |
| coding-B | gpt-6-luna | complete | [Prompt, response & observations](coding-B-gpt-6-luna/evidence.md) |
| everyday-B | gpt-6-luna | incomplete | [Prompt, response & observations](everyday-B-gpt-6-luna/evidence.md) |
| browser-B | gpt-6-luna | complete | [Prompt, response & observations](browser-B-gpt-6-luna/evidence.md) |
| desktop-B | gpt-6-luna | complete | [Prompt, response & observations](desktop-B-gpt-6-luna/evidence.md) |

## Limits

The tasks are small and explicitly specified. The simulator can open multiple IDs at once, has no real navigation cost, and exposes structured data. It does not establish visual perception, real browser/computer use, realistic recovery, or source-file preservation in an actual application. A simulated export creates a real CSV artifact but never opens a spreadsheet application.

Coding coverage is six fixed inputs, not exhaustive: the empty batch shares its account with a later valid batch, so it does not isolate zero-account creation. Cases are newly authored, but familiar underlying patterns may occur in training. One run per model/case cannot measure reliability. No checker or task was tuned after seeing responses. JSON fences are normalized; response-contract failures are separate from semantic grades and stop execution.

[Frozen task design and reproduction](../../docs/paired-short-screen.md)
