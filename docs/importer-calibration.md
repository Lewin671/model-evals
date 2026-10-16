# Incremental importer: bounded coding calibration

This is the first implemented replacement workflow. It covers **coding only**. Everyday,
browser and desktop workflows remain design specifications. No four-domain ranking can
be inferred from this pilot.

## What the model actually does

The model receives a repository contract and file tree, reads three Python modules,
edits their contents, runs public tests, receives an additional consumer requirement,
then revises the implementation. The final files execute against hidden scenarios.
An explanation or a claimed test pass cannot substitute for working code.

Command Code supplies the model through headless single-response invocations. Its native
tool schemas are removed by a per-invocation mod, and skill discovery is disabled.
The host verifies an empty active-tool list on every call. Permission-denial rules remain
as a fallback. The host implements bounded `read`, `write`,
`test` and `finish` actions through the response protocol. This tests model behavior
with a **controlled coding tool protocol**, not the stock Command Code agent's entire
tool environment. Source edits are real files, executed in an OS sandbox.

Common JSON fences, a unique actions object surrounded by prose, singleton-array envelopes,
bare action lists and single-action objects are accepted in advance. Other protocol
errors receive feedback and consume a response, but do not directly zero a semantic score.
The final artifact is tested even if the model forgets to say finish.

## Two different starter repositories

- **stream:** an incomplete CSV record splitter, incorrect revision ordering, premature
  persistence and a stale report cache interact.
- **state:** the CSV splitter already handles quoted records; global delivery bookkeeping,
  revision ordering, premature persistence and a stale report cache remain faulty.

The second variant changes which source paths need repair; it is not merely renamed IDs.
Both expose the same public API and acceptance contract. Both models receive identical
initial repositories within a variant. They may take different actions and therefore
receive different subsequent test observations.

## Mid-episode change

After the second model response, or an earlier finish request, the consumer adds a
requirement: a retry under an accepted delivery ID must compare **both payload and final
flag** with the original, persist that information across restart, and reject conflicting
retries atomically. The finish request that receives this change does not end the episode.
Every graded episode must have received the requirement before final assessment.

No migration of databases made by older code is required. No concurrency, power-failure
durability or raw-byte UTF-8 decoding is tested: fragments are Unicode strings.

## Independent checks

| Tier | Scenarios | Acceptance |
|:--|--:|:--|
| L1 | 2 | Full-file API compatibility; fragmented records survive restart |
| L2 | 4 | Quoted boundaries, partition/replay invariance, independent streams, EOF without newline |
| L3 | 5 | Revision/tombstone ordering; two rollback/retry cases; conflicting replay; incomplete-final rollback |

Each scenario checks actual API results and final records/totals. Some also inspect
intermediate states, accepted-revision counts and error types. The eleven scenarios
receive equal weight within this one family; tier counts are also reported. They are
correlated checks, not eleven independent tasks or a broad capability score.

The oracle uses whole-document `csv.DictReader` plus an independent maximum-revision
fold. The reference implementation uses an incremental scanner and transactional state
copy. Hand-checked examples cover a category move, negative credit, deletion and an old
revision arriving after deletion.

Public checks expose their operations, expected results and observed outputs so failures
are debuggable. They use separate sample identifiers and generation seeds. Hidden values
and operations are not exposed through the file tools before final grading.

## Local qualification gates

Before any model call, the runner verifies both reference artifacts, both failing starters,
five deliberately wrong strategies, and a four-response-equivalent reference trace that
uses exactly the same file tools and implements the change after it arrives.

The intended counterexamples are:

| Wrong strategy | Must fail |
|:--|:--|
| Split at physical newlines | Quoted-record boundaries |
| Last arrival wins | Old revisions arriving after a newer revision/tombstone |
| Mutate live state before all validation finishes | Corrected retry after an invalid row |
| Fingerprint payload but not the final flag | Conflicting replay after restart |
| Omit persistent replay detection | Replayed arbitrary partitions |

Reference success plus baseline failure qualifies a task for a pilot; it does not prove
model discrimination. Generators, graders, tool semantics, budgets and the following
interpretation rules are frozen in a commit before inference.

## Pilot and interpretation rules

Use DeepSeek V4.1 Flash and GLM 5.3 Flash, both explicitly **high** effort. Order: DeepSeek
then GLM on stream; GLM then DeepSeek on state. Each gets one fresh episode per variant.

- Both configurations complete all scenarios: ceiling remains; no separation established.
- Both fail essentially everything: investigate task/budget fit; do not publish a winner.
- Different verified functional failures on both variants: a calibration signal for this
  family, not a general ranking. Report exact failures and budget completion.
- Differences on only one variant, missing change delivery or infrastructure failures:
  insufficient/inconsistent evidence; retain all attempts without a combined ranking.

Envelope differences alone do not qualify as semantic separation. Examine actual edited
files and failed API behaviors. Do not resume, retry or select the best model attempt.

## Budget

The default is four episodes × at most six single-response CLI invocations = **at most
24 CLI invocations/main-loop turns**. There is a 180-second timeout per invocation.
An aggregate 32,000 reported-output-token guard prevents starting further requests after
the threshold is reached; a request already in flight may overshoot it. It is not a dollar
cap. CLI/provider-internal retries and unreported background work remain possible.

Record observed request-start events, CLI invocations, input/output/cache-read tokens,
episode responses, protocol errors, normalizations and stop reasons separately. Stop the
pilot on a CLI/identity failure. Unstarted episodes remain untested, not zero-scored.
No Codex expansion or automatic difficulty escalation occurs in this pilot.

Command Code ZDR enforcement is unset only for child processes; personal effort defaults
remain untouched. Raw NDJSON/stderr and temporary workspaces stay in `.runs/`. Publish
only reviewed synthetic source edits, action/test traces and sanitized summary fields.

## Commands

```sh
# Qualification only; no model calls.
python3 -m evalkit.workflows.calibrate --seed 481

# Paid pilot: random seed, four episodes, bounded feedback loop.
python3 -m evalkit.workflows.calibrate --execute
```

Actual results and their limits must be added after the first frozen pilot. A passing
preflight or an implemented runner is not an empirical capability comparison.

## Adapter qualification incident

The first real invocation was stopped before any repository action: native CLI `read_file`
remained visible despite permission denial. The model selected that native tool, received
no repository contents, and hit the one-turn cap. This was an adapter-only failure, not a
semantic coding result. Its raw evidence and cost remain in the private setup-attempt folder.

The adapter now uses [Command Code's active-tool filter](https://commandcode.ai/docs/mods)
to remove native schemas, rather than merely denying execution, with an empty-tool proof
checked for each invocation. The task, starter repositories and checker are unchanged.
The effective pilot reuses the original seed. Its total request and output-token ceilings
include the failed setup request through --setup-attempt; no scored or progressed episode
can be excluded through that option. There is no automatic retry of a model coding result.
