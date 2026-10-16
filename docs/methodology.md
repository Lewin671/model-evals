# Methodology

## Unit of comparison

A configuration is **model ID × reasoning effort × harness**. It is not just a model name.
Changing `high` to `medium`, or switching the same model between CLIs, creates a separate result.
The starter campaign compares four configurations, all with explicitly requested `high` effort.
The supported levels were checked in the local CLI model catalogs before running; catalogs
and account access can change. The same label need not represent the same compute budget.

This is a comparison of configured products. It cannot isolate the underlying model from
system prompts, routing, caching, tokenization, or harness behavior.

## Fixed task protocol

1. Freeze task generators and graders in a commit before calling a model.
2. Generate one seed per campaign; preserve it in the manifest. Do not reuse a seed from an example command.
3. Give every configuration identical prompt bytes. Keep reference implementations and test inputs out of context.
4. Rotate the first configuration across tasks and reverse alternate task orders.
5. Use a fresh CLI session for each task. Do not share answers, retry a wrong answer, or offer feedback.
6. Execute code answers or compare structured answers against a deterministic oracle.
7. Export all attempts, including failures. Never select the best result from repeated runs.

The suite fingerprint hashes the exact generator and grader source. Reports can combine
separate runs only when seed, fingerprint, task IDs, and prompt hashes match.
Duplicate configuration/task attempts are rejected rather than silently overwritten.

An objectively demonstrated oracle error can be corrected after acquisition only with a
public adjudication, an independent reproduction, a regression test, and uniform local
regrading of all saved answers. Preserve original scores and fingerprints; record the
corrected fingerprint and commit separately. Do not change prompts, retry models, or
adjust scoring weights. The first campaign has one such [adjudication](adjudications/001-security-triage.md).

## Scoring

Each of six tasks contributes equally to the overall mean. Each code task uses 24 inputs;
its score is the fraction returning the expected JSON-compatible value without changing the input.
Structured tasks require an exact answer, including field sets and specified ordering.
Markdown fences, commentary outside JSON, and incorrect schemas are format errors worth zero.

A model that returns invalid code or the wrong result gets a model failure/partial score.
A CLI, routing, identity, credit, or infrastructure failure has no model score. A configuration
needs every task scored before receiving an aggregate. Missing results are shown as dashes.
Individual code cases are correlated because the same generated program handles them all.

Reference solutions are checked against known hand-specified cases and incorrect solutions.
The ledger and pagination also use independent oracle implementations. All graders and
generators are public; "hidden" means excluded from the model's evaluation context.

## CLI adapters

### Command Code

- Runs headlessly with an explicit model, one-turn limit, no session persistence, and no skills.
- Uses a temporary directory outside this checkout. Project-local settings reject all tools,
  disable taste learning, and set `reasoningEffort[model]` explicitly.
- Avoids `--effort`, which can persist the model's default in personal configuration.
- Removes `CMD_ZDR` from the child environment without changing the parent or global files.
- Validates model and effort against `model_request_*` events; unexpected identity or tool use stops the campaign.
- User-level settings may still load. Check for personal hooks, MCP servers and mods first.

### Codex

- Uses `codex exec --json`, an explicit model and `model_reasoning_effort`, ephemeral sessions,
  an independent process, ignored user config/rules, and a read-only execution sandbox.
- Disables shell, browser, app, plugin, image, skill-search and hook features; suppresses
  discovered project instructions. The prompt requests one direct answer with no tools.
- Any action item in the JSONL stream is treated as forbidden tool use. Startup diagnostic
  `error` items are not tool calls; a successful completed turn is still required.
- Uses no output JSON Schema enforcement, so both CLIs must follow the same plain-text protocol.
- Codex JSONL reports completion, response text and token usage, but does not expose an
  independently verifiable model/effort identity. Reports mark these as configured values.
- There is no verified native model-turn cap in this adapter. Timeout is enforced by the runner.
  CLI-internal retries remain possible in both products.

If an adapter needs a correction during acquisition, `--resume-run` reuses every saved
response and invokes only slots that have never been attempted. It refuses a changed suite,
seed, variant list, CLI version or schedule. Adapter commits are recorded separately; graders
and task templates remain frozen. No existing model response is regenerated.

The built-in harness-instruction differences remain. No adapter is advertised as perfect isolation.

## Candidate execution

Model-generated Python is executed in a separate macOS `sandbox-exec` process with isolated
Python startup and standard-library access. It cannot open network connections, write files,
read user-home contents, or fork. CPU time is limited and the parent enforces a wall-clock timeout.
The runtime can inspect filesystem metadata and read system/Python installation files.
It is an OS sandbox, not a virtual machine; do not use this runner for arbitrary hostile submissions.
Other operating systems fail closed instead of executing candidate code unsandboxed.

## Usage accounting

Reports keep input, output, cached-input, cache-write, and reasoning counters when the CLI
exposes them. A missing counter is unknown, not zero. Input/output semantics differ by provider;
reasoning tokens may already be included in output, and cached input may be included in input.
Do not add these columns into a synthetic billable-token total or infer dollars from them.
Subscription quota and actual billed charges must be checked in the respective account.

## What this does and does not measure

The suite measures short-form implementation, state handling, design repair, security precision,
evidence handling, JSON compliance and constrained optimization. Six tasks are a low-cost screen.
It does not establish a broad model ranking, statistical significance, or contamination-free status.
All-perfect scores mean a tie on this suite, not equal overall capability. Do not invent a winner.

It does not evaluate multi-file repository navigation, sustained tool use, autonomous development,
vision, web research, or context-window limits. It does not make hardware-performance claims.
Generated data reduces memorization of exact outputs, but task templates can enter future training.
When adding harder tasks, define and freeze a new suite before testing, and retain the old results.

## References

- [Command Code headless protocol](https://commandcode.ai/docs/headless)
- [Command Code settings](https://commandcode.ai/docs/settings)
- [Command Code ZDR](https://commandcode.ai/docs/resources/zdr)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive/)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference/)
