# Adjudication 001: parameter binding does not provide tenant isolation

**Task:** `security-triage` · **Campaign seed:** `4367184791228143466`

## Finding

The original oracle marked this snippet as safe:

```python
def search(db, q):
    return db.execute("SELECT * FROM docs WHERE title = ?", (q,))
```

Parameter binding prevents SQL injection through `q`. It does not restrict results
to the authenticated tenant. The unchanged question explicitly specifies a multi-tenant
API, no other authorization layer, no DB-enforced tenant access, and asks about both
tenant isolation and SQL injection. A tenant predicate is missing from this query.

This is an oracle error, not an additional rule introduced after evaluating a response.

## Independent reproduction

Run with Python's standard-library SQLite implementation:

```python
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE docs (tenant TEXT, title TEXT)")
db.executemany("INSERT INTO docs VALUES (?, ?)", [
    ("tenant_a", "shared"), ("tenant_b", "shared")
])
print(db.execute("SELECT * FROM docs WHERE title = ?", ("shared",)).fetchall())
# [('tenant_a', 'shared'), ('tenant_b', 'shared')]
```

The same condition is now covered by a regression test. The SQL source and prompt did
not change; only the oracle's classification of this snippet changed from safe to vulnerable.

## Uniform application

For this seed, the original vulnerable-ID set was `[636, 670, 771]`.
The corrected set is `[636, 670, 712, 771]`.

| Model | Original task score | Corrected task score | Returned ID set |
|:--|--:|--:|:--|
| DeepSeek V4.1 Flash | 1 | 0 | `[636, 670, 771]` |
| GLM 5.3 Flash | 1 | 0 | `[636, 670, 771]` |
| GPT-6.1-Sol | 0 | 1 | `[636, 670, 712, 771]` |
| GPT-6-Luna | 1 | 0 | `[636, 670, 771]` |

Every saved answer was regraded locally under the same correction. No model was asked
to revise its answer, and no new model call was made for adjudication. The original
results are retained privately; public data includes the prior score and adjudication ID.
The original acquisition fingerprint and corrected grading fingerprint are both recorded.

The existing all-or-nothing scoring rule for structured answers is unchanged. Missing
one finding makes this task score zero; the report does not imply that every finding
in the other models' answers was wrong. This coarse score has a large impact in a six-task suite.
