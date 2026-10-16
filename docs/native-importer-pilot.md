# Native-tool importer pilot

## Task and qualification

The [importer task, API contract and eleven acceptance scenarios](importer-calibration.md)
remain unchanged. Both reference implementations pass all scenarios. Five single-defect
strategies fail their intended scenarios. Tests verify the actual native-tool bridge,
serialized writes/tests and midpoint requirement injection without model calls.

Only coding is implemented. No result here is an overall ranking or a browser/desktop score.

## Native execution

Each episode is one Command Code CLI session in a fresh temporary repository. A local mod
registers three actual model-callable tools: repo_read, repo_write and repo_test. They use
the same bounded file operations and sandboxed checks as the reference controller. Readable
paths and editable files are enumerated in the tool schemas. There is no model-controlled
shell/network command or arbitrary checker path. Tool calls are serialized in emitted order.

The model reads and edits real Python files. Public tests return sample inputs, expected
and observed behavior; hidden inputs are separate. Final prose has no required JSON shape
and is not a correctness signal. The final repository is executed independently.

Starting at the third model request, a deterministic hook injects the extra conflicting-retry
requirement. If the model finishes earlier, a stop hook supplies that requirement and asks
it to continue. The public test tool adds the corresponding test once the change is active.

The CLI may expose its tool-discovery entry point in addition to the three repository tools.
Discovery calls count toward the request budget and are logged. This is Command Code's
native harness with restricted repository tools, not direct raw-model inference. Its
model-specific tool presentation remains a limitation when interpreting the result.

## Fixed pilot

Two models, both explicitly high effort: deepseek/deepseek-v4.1-flash and z-ai/glm-5.3-flash.
Two different starter implementations: stream and state. Order: DeepSeek/stream,
GLM/stream, GLM/state, DeepSeek/state. Identical goals, starting files and random seed
within a variant; subsequent observations depend on the model's actual actions.

Each episode has the same **five model-turn cap**. Four episodes therefore allow at most
20 further main-loop requests. The two adapter setup requests are included in the same
24-request budget, so at most 22 observed requests are planned in total. The initial
32,000 reported-output-token guard also includes setup cost and stops between turns;
an in-flight request can overshoot it. These limits do not establish a dollar cap.

Artifacts at a turn cap are still evaluated if the change was delivered; the cap exit is
reported separately. CLI failures, missing identity evidence or missing change delivery
are not model zero scores. No automatic model retry, continuation or effort change occurs.

Use the interpretation rules already declared for the importer family: report ceiling,
floor, consistent directional differences across both variants, or incomplete/inconsistent
evidence. Do not expand to more models or harder tasks within this pilot.

## Adapter incidents and budget accounting

Two setup requests ran before any repository read/edit/test reached the model's task:

1. Ordinary CLI filesystem tools remained visible under permission denial; read_file was rejected.
2. The active-tool filter reported an empty list, but the CLI still injected search_tools;
   that discovery call was rejected. Empty registered-tool state did not prove empty wire schemas.

Neither attempt delivered the midpoint change or edited source, and neither was graded.
Their combined reported usage—22,910 input, 184 output and 7,808 cache-read tokens—remains
in the total budget. The same task seed is retained, and the task/checker did not change.
The old controlled-response adapter is retired rather than repeatedly retried.

A GET of the official Provider API model endpoint returned HTTP 403, so no Provider API
inference was attempted and no account settings or subscription were changed. The pilot
uses the existing CLI account, with CMD_ZDR unset only in child processes and no change
to personal reasoning-effort defaults.

## Reproduce

```sh
# Local gates, no model calls.
python3 -m evalkit.workflows.calibrate --seed 481

# Actual native pilot. Inspect limits before executing; consumes account quota.
python3 -m evalkit.workflows.native_calibrate --seed SEED --output .runs/native-pilot --execute
```

Local setup-attempt folders can be supplied through --setup-attempts to include their
verified usage. Raw CLI event streams/stderr remain private. Public evidence should contain
the scenario counts, tool traces, final source artifacts, exact model/effort and all limits.
