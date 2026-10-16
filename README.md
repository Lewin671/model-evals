# Model Evals

**Compare models and reasoning effort on small, checkable tasks.**

Inspect the prompts, answers, code, and failure cases behind each result. The current
screen covers coding, everyday decisions, browser reasoning, and desktop reasoning.

[![Checks](https://github.com/Lewin671/model-evals/actions/workflows/checks.yml/badge.svg)](https://github.com/Lewin671/model-evals/actions/workflows/checks.yml)
[![MIT](https://img.shields.io/badge/license-MIT-64748b)](LICENSE)

[Results](#results) · [Tasks](#tasks) · [Run locally](#run-locally) · [Data for agents](#data-for-agents)

## Results

**3 models · 2 reasoning efforts · 4 task pairs · 8 cases per configuration.**
One sample per case. All configurations use the same frozen tasks and checker.

| Model | Reasoning effort | Tasks completed | Reported output tokens |
|:--|:--|--:|--:|
| [DeepSeek v4.1 Flash](results/paired-short-01/report.md) | low | 4/7; 1 excluded | 4,603 |
| [DeepSeek v4.1 Flash](results/paired-short-high-01/report.md) | high | **8/8** | 10,892 |
| [GLM 5.3 Flash](results/paired-short-01/report.md) | low | 7/8 | 1,447 |
| [GLM 5.3 Flash](results/paired-short-high-01/report.md) | high | 6/8 | 2,302 |
| [GPT-6 Luna](results/luna-low-01/report.md) | low | 5/8 | 630 |
| [GPT-6 Luna](results/luna-high-01/report.md) | high | **8/8** | 1,643 |

DeepSeek and GLM run through **Command Code**, with model/effort observed in CLI request
events. Luna runs through **Codex**, with explicit invocation settings; its JSONL does
not independently expose model/effort. Token counts are CLI-reported, not verified charges.

**What went wrong:**

- [DeepSeek low](results/paired-short-01/failure-analysis.md): chose a more expensive itinerary and included a pending reimbursement. Another export had correct data but an extra header.
- [GLM high](results/paired-short-high-01/failure-analysis.md): referenced an undefined variable in code and invented workbook locator suffixes.
- [Luna low](results/luna-low-01/failure-analysis.md): got two itinerary/cost answers and one cents total wrong. Its high sample corrected all three.

[Full task matrix, input/output usage, and evidence →](results/three-model-comparison-01/report.md)

**Read the counts carefully:** completion means the final artifact passes every check.
Content and interface errors are distinguished in the linked analyses; excluded cases
are never scored zero. One run cannot establish reliability, a general ranking, or a
causal effort gain. Harness context and token accounting differ; equal effort names do
not imply equal compute. Luna high and DeepSeek high tie on task completion here.

## Tasks

Each pair changes a condition that changes the correct answer. Models see cases
independently; no other model's answer enters their context.

| Domain | What changes between A and B | What is checked |
|:--|:--|:--|
| Coding | Delivery IDs are global vs. per account | Execute submitted Python on retry, atomicity, and deduplication cases |
| Everyday | A meeting update is approved vs. draft | Feasible cheapest itinerary, applicable meeting, refund, and cash cost |
| Browser simulation | A checkout quote changes | Inspect requested pages, then save the cheapest eligible plan |
| Desktop simulation | The latest workbook is draft vs. approved | Open requested files, then export normalized, grouped cents |

Browser/desktop use **two-step text-state simulators**, not real browsers, applications,
or visual perception. Reference solutions and deliberately wrong baselines are checked
before paid runs; tasks/checkers stay frozen afterward. Newly authored cases may still
use concepts familiar from training.

[Task specification and limits](docs/paired-short-screen.md) · [Fixtures and checker](evalkit/shortscreen/tasks.py)

## Run locally

Requires Python 3.10+ and macOS for sandboxed code checks. No third-party Python packages.
These commands make **no model calls**:

```sh
git clone https://github.com/Lewin671/model-evals.git
cd model-evals
python3 -m unittest discover -s tests -q

# Qualify tasks and preview the Luna high plan.
python3 -m evalkit.shortscreen.run --harness codex \
  --models gpt-6-luna --effort high --output .runs/luna-high
```

Add `--execute` to spend quota using an existing CLI login. A full configuration has
8 episodes and up to 12 response invocations. The runner uses a 120-second timeout and
a 16,000 reported-output soft guard **per run**, shared when multiple models are selected.
The guard stops between episodes and can overshoot.
Codex's underlying request/retry count is not exposed. ZDR is unset only in evaluation
child processes; personal settings remain unchanged.

[Both harnesses, reproduction commands, and continuation rules →](docs/paired-short-screen.md)

## Data for agents

Start with **[results/index.json](results/index.json)**: exact model IDs, harnesses,
reasoning effort, verification source, completion counts, usage, and paths to each
manifest, per-case JSON, and report. Paths are relative to the repository root.
A null grade is excluded, not a failed task. For code changes, read [AGENTS.md](AGENTS.md).

<details>
<summary>Earlier experiments and larger workflow designs</summary>

<!-- RESULTS:START -->

- [Importer pilot](results/importer-native-calibration-01/report.md): one DeepSeek low artifact passed 11/11 checks; the paired pilot stopped at its token guard.
- [general-v2](results/general-v2-screening-01/findings.md) and [micro-v1](results/2026-10-15-micro-v1/report.md): archived development records; difficulty did not support a capability ranking.

<!-- RESULTS:END -->

[Larger workflow designs](docs/challenge-design.md) remain separate from the measured short screen. GPT-6.1 Sol has not run on the replacement tasks.

</details>

## Contribute

Suggest a small task with two plausible approaches and a checkable expected result.
Include the counterfactual that changes the answer. New model results should include
exact model ID, harness, effort, usage, and reproducible evidence. Keep credentials and
raw CLI transcripts private. See [AGENTS.md](AGENTS.md) for evaluation rules.

**Star this repo to keep the comparisons handy.** [MIT licensed](LICENSE).
