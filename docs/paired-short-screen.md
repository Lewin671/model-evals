# Paired short diagnostic v1

This is a cheap discrimination probe, not a validated general capability benchmark.
Eight newly authored tasks form four counterfactual pairs. Changing one contractual
condition changes the correct result. Each model sees each case independently.
Authorship does not prove absence of training overlap with the underlying concepts.

| Domain | Pair change | Outcome checked |
|:--|:--|:--|
| Coding | Delivery identifiers global vs per-account | Execute candidate code on atomic retry, deduplication, cross-account and empty-batch cases |
| Everyday | A meeting-change email approved vs draft | Feasible cheapest itinerary, applicable meeting, timely refund and incremental cash cost |
| Browser simulation | A live checkout quote changes | Read requested pages, then save the eligible lowest all-in annual quote |
| Desktop simulation | Latest workbook approved vs draft | Read requested workbooks, export exact normalized grouped cents including filtered-out rows |

Both Flash models use explicit low reasoning effort. Coding/everyday cases require one
short final response; browser/desktop require two responses with an action-dependent
observation between them. Each response is a fresh CLI invocation; the second receives
the first action and simulator observation. This measures externally maintained text
context, not native browser/desktop tools, visual perception, or long-session memory.

Each episode permits at most two responses; no automatic retry. Total: 16 episodes,
24 main-loop model requests. CLI max turns is one per response, timeout 120 seconds.
The reported-output soft guard is 16,000 tokens and stops between episodes; in-flight
reasoning can overshoot. Short answer instructions are not a hard token cap. Raw CLI
streams stay private; sanitized prompts, responses, observations and artifacts are public.
ZDR is unset only for child processes. No personal effort defaults are changed.

Before inference, reference code must pass, the buggy starter must fail, and an otherwise
correct code solution with the opposite identifier scope must fail. Independent travel
plan enumeration checks feasibility/cost. Transplanting either paired answer must fail
its counterpart. These gates establish checker sensitivity, not model discrimination.

Report task completion and both-cases-correct per domain, actual usage and observed
identity/effort. Field/check counts are debugging evidence, not independent tasks. Give
each domain equal weight if showing an aggregate; do not claim significance or a general
model ranking. If all cases pass, report a ceiling and stop. If all fail, report a floor.
Mixed results are descriptive only. Do not tune cases/checkers after seeing responses.
Response-contract/CLI/identity failures are recorded separately and halt the run; they
are not capability zeroes. No Codex calls until this diagnostic establishes useful evidence.

The simulator is intentionally small: inspect/open may request all visible IDs, and
only a saved comparison or CSV is created. It does not test realistic navigation cost,
interaction recovery, real workbook preservation, or application control. These limits
must accompany any reported results.

```sh
python3 -m unittest tests/test_shortscreen.py
python3 -m evalkit.shortscreen.run --output .runs/paired-short-v1
# Consumes quota; inspect the printed plan first.
python3 -m evalkit.shortscreen.run --output .runs/paired-short-v1 --execute
```

## Explicit continuation after a response-contract failure

The first run halted when DeepSeek/browser-B attempted the denied native shell tool
instead of returning a simulator action. Its one request remains excluded from semantic
grades. A separately frozen adapter continuation can run **only never-attempted episodes**
with `--resume-unattempted`. It preserves the original manifest and all recorded outcomes,
including that failure; it refuses task/checker changes against the original commit.
There is no retry of the failed episode, substituted answer, or change to the grader.
The same cumulative request/output limits apply. The full four-domain comparison remains
incomplete even after the remaining independent samples finish.

## High-effort comparison

The follow-up repeats exactly the frozen eight tasks with both Flash models at **high**
reasoning effort. Model IDs, task order, prompts, grader, per-request timeout (120 s),
24-request limit, and 16,000 reported-output soft guard are unchanged. The CLI verifies
the requested effort in each model-request-end event. Use `--effort high` and a new output
folder; a continuation must retain that effort. No low-effort response is supplied to
the high-effort models. Personal defaults and parent ZDR remain unchanged. Report
per-model low/high transitions, usage and missing results. A single additional sample
cannot isolate effort from sampling variation.

## GPT-6 Luna through Codex

The added configuration is exactly `gpt-6-luna`, separately at low and high effort.
Each run repeats all eight frozen cases, with twelve Codex exec invocations and the same
120-second timeout and 16,000 reported-output soft guard. Task/checker and prompts are
unchanged. Each simulator response is a fresh exec supplied with the preceding action
and observation; no answer from another model or effort enters its context.

Codex uses explicit `--model` and `model_reasoning_effort` configuration, ignores personal
config/rules, runs ephemerally outside the checkout, and disables discovered tools and
integrations. No additional response schema is applied. Existing CLI authentication is
used; personal defaults are not changed. These controls use the existing tested Codex
adapter. See [official configuration documentation](https://learn.chatgpt.com/docs/config-file/config-reference).

Codex JSONL does not expose independent model/effort identity or underlying request/retry
counts. Record them as **configured via invocation**, not request-event verified. Usage
comes from turn.completed; budget Codex exec invocations, not claimed provider requests.
The one-turn response rule is checked through completion events and absence of tool items.
A CLI/protocol failure stops the run; an explicit continuation may execute only previously
unattempted episodes, without retrying failures or changing the task/checker/effort.

This is a cross-harness comparison: different system context and native tool presentation
may affect both outcomes and token overhead. Equal effort names do not imply equal
reasoning compute. Report model + effort + harness together, without attributing all
observed differences to the underlying base model.

```sh
python3 -m evalkit.shortscreen.run --harness codex --models gpt-6-luna --effort low --output .runs/luna-low --execute
python3 -m evalkit.shortscreen.run --harness codex --models gpt-6-luna --effort high --output .runs/luna-high --execute
```
