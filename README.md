<div align="center">

# Model Evals

**Task-based evaluation experiments — difficulty calibration in progress.**

[![Checks](https://github.com/Lewin671/model-evals/actions/workflows/checks.yml/badge.svg)](https://github.com/Lewin671/model-evals/actions/workflows/checks.yml)
[![Status](https://img.shields.io/badge/status-recalibrating-b7791f?style=flat)](docs/challenge-design.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-64748b?style=flat)](LICENSE)

[Latest comparison](results/three-model-comparison-01/report.md) · [Challenge design](docs/challenge-design.md) · [Prototype records](#prototype-records) · [Local checks](#local-checks)

</div>

Evaluate general **coding, everyday work, browser reasoning and desktop reasoning** using
models available through Command Code and Codex. Model, reasoning effort, harness and
usage must accompany every measured result.

## Current status

**Luna high and DeepSeek high both complete 8/8 tasks; GLM high completes 6/8.**
This is one small paired diagnostic, not a validated general ranking. The same eight
frozen cases are repeated at low and high reasoning effort; each case has one sample.

| Model | Harness | Low effort | High effort | Identity / effort evidence |
|:--|:--|:--|:--|:--|
| DeepSeek v4.1 Flash | Command Code | 4/7 graded; 1 excluded | **8/8** | CLI request events |
| GLM 5.3 Flash | Command Code | **7/8** | 6/8 | CLI request events |
| GPT-6 Luna | Codex | 5/8 | **8/8** | Explicit invocation; not independently exposed in JSONL |

These are strict artifact counts. DeepSeek low has one output-header failure despite
correct numeric data; GLM high has one invalid workbook-locator failure and one code
runtime defect. Luna low makes two itinerary/cost errors and one cents-total error;
its high sample corrects all three. One run cannot separate effort effects from sampling.

| Configuration | Reported output tokens |
|:--|--:|
| DeepSeek high | 10,892 |
| GLM high | 2,302 |
| Luna high | 1,643 |
| Luna low | 630 |

Usage is CLI-reported, not verified charges. Harness contexts and token accounting differ;
equal effort names do not establish equal compute. Luna used twelve Codex exec invocations
per effort; underlying model requests/retries are not exposed. Both CLIs have native tools
restricted, but retain different system context and tool presentation.

[Full six-configuration matrix and usage](results/three-model-comparison-01/report.md) ·
[Luna high evidence](results/luna-high-01/report.md) ·
[Luna low evidence](results/luna-low-01/report.md) ·
[Flash low/high comparison](results/effort-comparison-01/report.md) ·
[Frozen task design](docs/paired-short-screen.md)

Browser/desktop results are small text-state simulations, not real application testing.
GPT-6.1 Sol has not run on these replacement tasks. Larger workflows remain specifications.
The earlier importer pilot and original prototypes remain archived below.

## Separate importer pilot (incomplete)

| Model | Harness | Reasoning effort | Importer result | Coverage |
|:--|:--|:--|:--|:--|
| DeepSeek v4.1 Flash | Command Code | low, observed | **11/11** | One starter; 3 requests |
| GLM 5.3 Flash | Command Code | low, planned | Not run | Budget guard stopped pilot |
| gpt-6.1-sol | Codex | Not yet selected for replacement run | Not run | Archived prototype only |
| gpt-6-luna | Codex | Not yet selected for replacement run | Not run | Archived prototype only |

The first valid episode reported 12,047 output tokens. Including invalid adapter attempts,
reported output reached 33,805; one interrupted request has unknown usage. The 32,000
soft guard stops between turns and can overshoot. Adapter failures are excluded from scores.

## Prototype records

<!-- RESULTS:START -->

| Prototype | What it established | Records |
|:--|:--|:--|
| general-v2 | Pipeline checks worked; task difficulty did not establish useful model separation | [Findings](results/general-v2-screening-01/findings.md) · [Raw responses](results/general-v2-screening-01/responses.md) · [Full record](results/general-v2-screening-01/report.md) |
| micro-v1 | Earlier, different-scope screen with a documented oracle correction | [Archived record](results/2026-10-15-micro-v1/report.md) |

These are development artifacts, not leaderboards. The replacement coding pilot is reported separately above.

<!-- RESULTS:END -->

## Replacement task design

The next tasks should require information gathering, coupled changes, adaptation and a
verified final artifact/state. Goals and constraints are provided; a sequence of obvious
buttons to press is not.

| Domain | Proposed workflow | What the checker must verify |
|:--|:--|:--|
| Coding | Add retryable incremental imports in a small existing repository | Parsing, persisted revisions, downstream totals and existing API behavior after interrupted replay |
| Everyday | Revise a constrained appointment/travel plan after new information | Feasibility, source precedence, net cost and preservation of fixed commitments |
| Browser reasoning | Compare offers across pages and detail views, then handle a changed quote | Current eligibility/total, saved comparison and evidence, after a real simulated state transition |
| Desktop reasoning | Export normalized data from the correct workbook despite filters/dialogs | Actual output rows, totals, destination and preservation of the existing file |

[Read the concrete fixtures, hidden-check plan, difficulty tiers and pilot gates →](docs/challenge-design.md)

The coding runner now supports repository reads/edits, public test feedback and a
mid-episode requirement change. Hidden checks execute the final files. It has no real
shell/network tool and uses three native repository tools through Command Code.
[Implementation, acceptance checks and bounded pilot →](docs/importer-calibration.md)

The browser/desktop track can use local deterministic simulators; no real accounts or
applications are needed. Action-dependent observations and final-state checks are required.
Text-state evaluation remains distinct from visual perception and real tool execution.

## Calibration before another full campaign

First implement the environments/checkers, obtain reference traces, and show that simple
baselines fail for the intended reason. Use counterfactual variants that change the required
decision, rather than only randomizing IDs.

Then pilot **one workflow family, two independent variants, two target Flash models** at
an explicit matched effort: four episodes, before expanding to Codex and the full matrix.
Episodes may contain multiple model requests. Set request/token and action limits from
reference traces; count actual usage rather than calling four sessions "four calls."

Publish ceiling/floor effects and ties. Do not keep trying tasks until a preferred model
wins. Keep semantic goal attainment separate from response-contract compliance.

## Local checks

Python 3.10+ and macOS sandbox-exec are required for prototype code checks. No third-party
Python packages are needed. These checks and dry-run plans do not call models:

```sh
python3 -m unittest discover -s tests -v
python3 -m evalkit.run --campaign configs/screening.json --max-calls 24

# New workflow qualification gates; also makes no model calls.
python3 -m evalkit.workflows.calibrate --seed 481
```

The current runner is the archived general-v2 prototype. Paid reproduction now requires
an explicit opt-in; it is not the replacement workflow runner:

```sh
# Archival reproduction only. Consumes quota.
python3 -m evalkit.run --campaign configs/screening.json --max-calls 24 \
  --execute --allow-prototype
```

Reports can still be exported into an archive, but prototype runs cannot overwrite the
main README comparison. Raw CLI logs, session IDs and personal settings remain private.
Command Code reproduction unsets CMD_ZDR only in child processes, preserving normal settings.

---

[MIT](LICENSE) · [Prototype methodology](docs/methodology.md) · [Challenge redesign](docs/challenge-design.md)
