# General-v2: constructing a useful small evaluation

The current scope is **general coding, everyday tasks, browser workflow reasoning and
desktop workflow reasoning**. Security is excluded from new campaigns. Earlier micro-v1
results remain an archive and must not be compared numerically with this suite.

## Six bundles, four equally weighted domains

| Domain | Bundles | Local checks | Domain contribution |
|:--|:--|:--|--:|
| Coding | Config merge; pagination repair | 24 inputs per generated program | 25% |
| Everyday | Morning planner; expense reconciliation | Feasibility/optimality; four independently checked fields | 25% |
| Browser reasoning | Six independent DOM checkpoints | One next action per checkpoint | 25% |
| Desktop reasoning | Six independent structured-screen checkpoints | One next action or valid click region per checkpoint | 25% |

Average bundle scores within a domain, then average the four domain scores. Six UI
checkpoints are one bundle, not six extra calls. Code inputs within one program and UI
decisions within one answer are correlated, not independent trials. Four configurations
therefore cost 24 CLI invocations, including 12 through Command Code.

## Coding: execute the answer

The model implements a layered config function and repairs a pagination design. Hidden
inputs test recursive object semantics, exact Boolean deletion markers, falsy values,
filter ordering, tied sort keys, cursor exclusion, page endings and input mutation.
The program runs in an OS sandbox; its actual outputs determine the score.

These are small implementation/repair tasks. They do not measure multi-file navigation,
test-driven iteration, repository setup or autonomous development. Those need a separate
interactive track and should not be inferred from this score.

## Everyday tasks: check the user's outcome

**Morning planner.** The input contains five optional jobs, allowed start times, durations,
priorities, fixed busy intervals and a recovery buffer. The model returns a schedule and
the omitted jobs. Exhaustive enumeration finds the best achievable priority total. Any
equally good schedule is accepted. A feasible lower-value plan receives selected priority
divided by optimum; overlaps, invalid starts or incorrect omitted-job accounting score zero.
Buffers are explicitly required between selected jobs, not next to fixed busy intervals.

**Expense reconciliation.** Synthetic records contain repeated copies, later revisions,
pending/rejected items, an approved credit and a foreign-currency item without an exchange
rate. Only the latest revision is relevant. Four fields are checked separately: total,
included IDs, excluded IDs and invoices requiring a rate. The model must neither double-count
nor silently invent conversion data. Amounts are integer cents with tax already included.

These tasks measure structured planning, factual bookkeeping and following instructions.
They do not assess writing style, interpersonal judgment or open-ended recommendations.

## Browser: choose from the current DOM

Every checkpoint supplies a goal and a synthetic DOM-like observation. The model selects
one next action, using visible IDs or observe/wait/finish. Checkpoints are shuffled and
independent; selecting an action does not cause a subsequent model observation.

| Checkpoint | Distractor or state change | Behavior being tested |
|:--|:--|:--|
| Product choice | Lower sticker price with higher shipping, wrong size, unavailable stock | Combine constraints; compare total cost |
| Filters | Draft category differs from applied category; old results remain visible | Commit the filter before using stale results |
| Overlay | Background link remains in the observation but is occluded | Dismiss the modal; accept either valid dismissal |
| Navigation error | Previous node IDs exist but a stale-element error is shown | Obtain fresh state rather than retry old IDs |
| Unsaved form | Text matches the requested value but is not committed | Perform the save instead of declaring completion |
| Saved form | Server confirmation, matching value and no pending changes | Recognize completion without unnecessary actions |

No real browsing, buying, login, site account or browser extension is used by these tasks.
The scores concern grounding and workflow decisions from structured state, not browser tool proficiency.

## Desktop: focus, coordinates and asynchronous state

Observations describe windows, focused controls, dialogs, geometry and progress. They
contain **no screenshots or pixels**. This is structured-state reasoning, not a vision test.

| Checkpoint | Distractor or state change | Behavior being tested |
|:--|:--|:--|
| Window focus | Spreadsheet focused while the goal refers to a notes document | Focus the correct window before editing |
| Save dialog | Filename field still contains a default name | Replace the filename rather than save the wrong copy |
| Coordinate frame | Window-local bounds, nonzero screen origin and DPR=2 | Convert to global logical coordinates without double-scaling |
| Unsaved edits | Modal blocks the intended background action | Resolve the modal while preserving edits |
| Copy progress | One file is 100% but only one of four has completed | Observe/wait instead of reporting overall completion |
| Resized window | Geometry is older than the latest resize event | Reacquire state rather than click an obsolete coordinate |

Clicks are accepted anywhere at least three logical pixels inside the target control.
The grader does not require the center point. Multiple valid observations/waits and modal
dismissals are accepted where they advance the same goal.

## Score the behavior, not the wording

The output protocol is small JSON, not an essay or a tool implementation. Schedules may
have multiple optimal solutions; actions may have equivalent valid alternatives; click
coordinates are checked as regions. No LLM judge is used. Case-level and field-level outcomes
are exported so a partial score can be traced to a concrete decision.

Code outputs and UI action schemas still impose a structured-output requirement. A lower
score may reflect that interface constraint. Keep the response evidence visible rather
than attributing every failure to general intelligence.

## What to add only if this screen is insufficient

A separate **interactive** track could return the next state after each action, introduce
an unannounced popup or layout change, and check recovery and final environment state.
A **visual** track would supply rendered screenshots, hide textual geometry, and test hit
regions at different scales. Both require different adapters and additional calls.

Neither is claimed by general-v2. If these simple snapshots saturate, publish that ceiling
effect and design a fresh harder suite before running it; do not add post-hoc traps to
distinguish the models already tested.
