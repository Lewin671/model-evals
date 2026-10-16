# Luna high: findings

GPT-6 Luna through Codex, configured at high reasoning effort, completed **8/8** tasks.
All twelve exec invocations finished, no native tools were used, and no case was excluded.
The task/checker and prompts are byte-identical to the Flash and Luna-low runs.
Model/effort are explicit invocation settings, not independently verified JSONL identity.

All three low-run failures are corrected: everyday A chooses F3 at 163, everyday B
chooses F2 at 110, and desktop A exports Ada at 1030 cents. Both coding variants and
all simulated final artifacts also pass their frozen checks.

The run reported 1,643 output tokens, including 1,113 reported reasoning tokens, versus
630 output tokens and zero reported reasoning tokens at low effort. Counts are CLI
usage fields, not independently verified billing or evidence of actual effort identity.
One sample per case cannot separate effort effects from sampling variation.

On this task suite, Luna high and DeepSeek high tie at 8/8; GLM high completes 6/8.
Luna high reports fewer output tokens than DeepSeek high (1,643 versus 10,892) and GLM
high (2,302). Harness contexts, tokenizers, subscription accounting and model pricing
differ: do not treat this as a verified dollar-cost or pure base-model comparison.
