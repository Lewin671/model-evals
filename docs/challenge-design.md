# Challenge redesign: outcomes over one-step quizzes

**Status: design specification, not an implemented or calibrated suite. No model calls
were made for this redesign.** Existing adapters still run archived single-response prototypes.
The stateful environments, reference traces and new graders below must be implemented
and checked before a pilot. There is currently no validated model capability ranking.

## Why the prototypes were inadequate

Most checkpoints supplied both the relevant state and an almost explicit next step.
There was little information to discover, little need to revise a plan, and no delayed
consequence of an action. Changing IDs, prices and coordinates did not change the causal
structure. Three configurations saturated the full screen. Inspecting GLM's desktop
content after removing its extra array wrapper also yielded six correct actions.

The large-looking score gap primarily mixed response-contract failures with content
errors. It did not demonstrate a browser/computer-use capability gap. More repetitions
of the same easy templates would make that estimate more precise without fixing the task.

## Proposed four workflow families

Each task should require an artifact or a committed environment state. Prompts state the
user's goal and constraints, not the sequence of controls to press. Information is spread
across files, records or views; the model has to obtain it. Equivalent valid solutions pass.

### 1. Coding: incremental importer with existing consumers

Give the model a small synthetic repository containing a CSV importer, persistent record
store, report API and tests. Request retryable incremental imports while preserving the
existing full-file API and downstream totals. The bug is not labeled with its location.

The dependencies matter: fixing parsing but not persisted revision handling can double-count
records; correcting storage but leaving the report cache stale yields incorrect output.
The model must inspect and modify the relevant paths, then leave a runnable repository.

| Tier | Fixture variation | Observable check |
|:--|:--|:--|
| L1 | Unquoted rows split across arbitrary chunks | Same records and report as a full import |
| L2 | Quoted embedded newlines, retries crossing chunk boundaries, later invoice revisions | Parsing equivalence, no duplicate totals, latest revision retained |
| L3 | Failure after partial persistence, restart, then replay with an older revision interleaved | Correct final state after recovery; compatibility with existing API |

**Oracle:** a whole-file standard-library CSV parser plus an independently implemented
revision fold; compare final API results and stored records. Random chunk partitions test
the invariant `import(all_at_once) == import(partitions_with_retries)`. Hidden checks test
behavior, not whether the patch matches a reference diff. Parser correctness and end-to-end
consumer behavior are reported separately.

**Simple baselines that must fail:** split on newline; deduplicate only within each batch;
accept the last-arriving revision unconditionally. The reference implementation must pass
all tiers. Correctness checks must not depend on hardware timing.

### 2. Everyday work: revise a feasible plan after new information

Supply a short appointment brief, availability table, travel-time matrix, quote sheet and
two messages. Some documents are superseded; some choices are mutually exclusive. Ask for
a feasible plan and its actual cost, preserving fixed commitments and using stated priorities.

After the initial plan, reveal a realistic change: one appointment moves, a preferred quote
expires, or an arrival time changes. The model must revise the affected parts and preserve
unaffected commitments. Include an option whose missing price makes it unusable without a
specific clarification; do not reward inventing the missing value.

| Tier | Fixture variation | Observable check |
|:--|:--|:--|
| L1 | Static constraints with a feasible solution | No overlap, travel feasibility, correct costs |
| L2 | Superseded availability and a partial refund affecting the budget | Correct source precedence and net cost |
| L3 | A late change invalidates the original optimum | Revised plan remains feasible and respects priorities/fixed commitments |

**Oracle:** a small exhaustive constraint solver for the final plan and a separate ledger
for costs. Score hard-constraint satisfaction, attained objective, factual support and
unnecessary changes separately. Do not require one schedule or particular prose. A neat
explanation cannot substitute for an infeasible plan.

**Simple baselines that must fail:** use the newest document for every field; choose the
cheapest quote before travel/refund constraints; keep the first plan after the update.

### 3. Browser reasoning: comparison with incomplete views and changed quotes

Use a local deterministic web simulator, with text DOM observations for all models. The
user asks for a saved comparison of two eligible offers under a total budget and cancellation
constraint. Listings have incomplete prices; details contain fees and conditions. Relevant
offers are distributed across pages and filters. There is no real purchase or external site.

An agent action changes the world and returns the next observation. A quote update can
invalidate the apparent cheapest choice. IDs can change after navigation; a modal may block
the intended control. Conditions must be visible through observations, not hidden grader rules.

| Tier | Fixture variation | Observable check |
|:--|:--|:--|
| L1 | One view contains enough information | Saves an eligible offer and cites its actual conditions |
| L2 | Fees, terms and candidates are spread across detail views/pages | Compares all required evidence and selects the best feasible total |
| L3 | A changed quote or unavailable offer invalidates the initial choice | Re-observes, revises, saves a valid alternative and verifies saved state |

**Oracle:** inspect the actual saved shortlist, current quoted totals, eligibility and
evidence references. A final message saying "done" is insufficient. Partial credit comes
from actual achieved subgoals, not a prescribed click sequence. Extra observations are
allowed within a predeclared budget; equivalent navigation paths pass.

**Simple baselines that must fail:** cheapest listing price; first valid item; fixed click
sequence; reuse old IDs; always observe without progressing. Paired variants must change
which offer is best and whether re-observation is necessary, not just rename the same path.

### 4. Desktop reasoning: produce and verify an export artifact

Use a local deterministic desktop simulator with two open workbooks that have similar names
but different paths. The user requests an exact normalized export from one of them, preserving
an existing file. A filter may hide rows; locale settings change numeric/CSV interpretation.
The target folder and final filename are part of the requested outcome.

The model receives focused-window, control and table observations, then acts. Opening a
dialog, a conflicting filename or a resize changes subsequent state. A completed export
creates an inspectable virtual file. No user application or real files are touched.

| Tier | Fixture variation | Observable check |
|:--|:--|:--|
| L1 | Correct workbook, simple data, free destination | Expected file exists with correct rows and totals |
| L2 | Wrong window focused, active row filter, duplicate records or locale-sensitive numbers | Correct source, complete normalized output, existing file preserved |
| L3 | Filename conflict or resize during export | Correct recovery, correct destination and verified file contents |

**Oracle:** parse the exported file independently and compare rows, totals and destination;
also check preservation of the pre-existing file. Reports distinguish source selection,
transformation, destination, completion verification and action budget. The agent's written
summary is not evidence that the file exists.

**Simple baselines that must fail:** export the current window; export visible rows only;
reuse pre-resize geometry; report success when export merely starts. Text-state evaluation
must remain labeled as such; visual grounding needs a separate screenshot track.

## Acceptance before a model pilot

For each chosen workflow, implement at least two independent generated variants and obtain:

1. A reference trace that reaches the final goal within the proposed budget.
2. A separate final-state/artifact checker with hand-verified positive and negative cases.
3. Demonstrated failures of the simple baselines above.
4. A counterfactual variant that changes the required decision or recovery path.
5. A check that every scored requirement is stated or observable and that alternatives pass.

Reference success and baseline failure do **not** prove model discrimination. They only
qualify a task for a small pilot. The new workflow runner, observation adapter and bounded
feedback loop are required; the current independent-snapshot runner cannot measure this.

## Small calibration pilot before expanding the matrix

Start with one workflow family and two independent variants, using the two originally
requested Flash models at the same explicit effort: **four episodes**, not a full matrix.
Keep all attempts. Choose difficulty tiers before calling models; do not pick the level
that makes a preferred model win. If both models saturate, the task remains uncalibrated;
if both fail, inspect the task and budget before concluding either lacks capability.

A second variant helps distinguish a repeatable semantic failure from a one-off bad output.
Look for different attained subgoals, recovery behavior or verified artifacts, not just
format compliance. Ties are allowed. A calibrated task can still yield tied model results.

Interactive episodes can contain many model requests. Before starting, set a total
request/token allowance and per-episode model-turn/tool-action limits based on reference
trace lengths. **Four CLI sessions are not four model requests.** Record cached-input and
output tokens separately; a timeout/turn cap is not a dollar cap. Do not launch another
full campaign merely because the number of scenario files is small.

## Reporting requirements

- Primary: final goal attained, artifact correctness, hard-constraint violations, recovery
  after the change, and supported completion claims.
- Separate: output/schema compliance, tool/action counts and token usage. A trivial JSON
  wrapper must not masquerade as an underlying reasoning gap.
- Keep model, effort, harness, seed, initial state, transition log and checker revision.
- Publish ceiling/floor effects and incomplete/budget-limited runs without forcing a winner.
- Keep prototype scores in the archive. Do not promote them back into the main comparison.
