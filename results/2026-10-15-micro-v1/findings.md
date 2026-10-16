# Findings: micro-v1

All four configurations used explicitly requested **high reasoning effort**, one answer per
task, and the same seed. There were **24 CLI invocations**: 12 through Command Code and
12 through Codex. No answer was regenerated. All final answers used valid JSON; no tools
were used. Command Code ZDR was not enforced for these runs.

## What separated the results

**GPT-6.1-Sol passed all six tasks.** DeepSeek V4.1 Flash passed five; GLM 5.3 Flash and
GPT-6-Luna passed four completely and one partially. The differences came from two tasks:

| Observation | DeepSeek V4.1 Flash | GLM 5.3 Flash | GPT-6.1-Sol | GPT-6-Luna |
|:--|:--|:--|:--|:--|
| Distinguishes integer `1` from Boolean `true` in the deletion marker | Yes | No | Yes | No |
| Identifies the parameterized query's missing tenant isolation | No | No | Yes | No |

All four passed the evaluated ledger, pagination, evidence-reconciliation, and constrained
selection inputs. This suite did not distinguish their performance on those tasks.

## A concrete implementation difference

The merge contract deletes a field only for the exact marker `{"$delete": true}`. For:

```json
[{"x": 9}, {"x": {"$delete": 1}}]
```

the expected result is `{"x": {"$delete": 1}}`. DeepSeek and Sol returned that object.
GLM and Luna returned `{}`. Their implementations used equality comparisons that inherit
Python's `1 == True` behavior. Each lost one of the 24 config-merge checks.

## A concrete security difference

Sol included the parameterized search query among tenant-isolation flaws. The other three
identified the interpolated SQL, unscoped document read, and tenant-blind cache key, but
omitted the parameterized query. Binding protects against injection; it does not add a tenant filter.

The initial oracle also omitted that query. A SQLite reproduction confirmed the leak,
and all four recorded responses were regraded under the same correction. See
[Adjudication 001](../../docs/adjudications/001-security-triage.md) for original scores,
the reproduction and the audit trail. No scoring weights or task wording changed.

This structured task uses exact-set scoring, so omitting one finding costs the whole task.
That accounts for 16.7 percentage points in a six-task mean; it is not evidence that every
security judgment in the other models' responses was wrong.

## How far the result goes

Sol was strongest **on this six-task screen at these settings**. The data does not establish
an overall model ranking or a statistically reliable gap. Cross-harness differences remain,
and the task count is small. The code checks cover specific generated inputs, not all legal programs.

Reported tokens are available in [the full results](report.md) and [JSON data](summary.json).
They are not directly comparable dollar costs: providers differ in caching, reasoning accounting,
and subscription metering. No speed or hardware-performance conclusion was measured.

[Inspect every final answer](responses.md) · [Per-task scores](report.md)
