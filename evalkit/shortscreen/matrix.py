"""Publish cross-harness configuration outcomes with explicit provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def build(runs,out):
    records=[];frozen=None
    for run in runs:
        manifest=json.loads((run/'manifest.json').read_text())
        source=subprocess.check_output(['git','show',manifest['commit']+':evalkit/shortscreen/tasks.py'])
        if frozen is not None and source!=frozen:raise ValueError('task/checker differs')
        frozen=source
        if manifest['suite']!='paired-short-v1':raise ValueError('different suite')
        records.append((run,manifest,json.loads((run/'results.json').read_text()),json.loads((run/'usage.json').read_text())))
    lines=['# Three models, two reasoning efforts','',
        'The same eight frozen cases are evaluated independently at low and high effort. These are model + harness + effort configurations, not isolated base models. Each configuration/case has one sample.',
        'Browser/desktop are action-dependent text-state simulations, not real application control.','',
        '| Model | Harness | Effort | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Strict completion |',
        '|:--|:--|:--|:--|:--|:--|:--|:--|']
    for run,m,rows,u in records:
        for model in m['models']:
            selected={r['task']:r for r in rows if r['model']==model}
            cells=[];passed=graded=0
            for domain in ('coding','everyday','browser','desktop'):
                symbols=[]
                for variant in ('A','B'):
                    r=selected.get(domain+'-'+variant)
                    if not r or r['grade'] is None:symbols.append('—')
                    else:
                        graded+=1;ok=r['grade']['complete'];passed+=ok;symbols.append('✓' if ok else '✗')
                cells.append(' / '.join(symbols))
            lines+=['| '+' | '.join([model,m['harness'],m['effort'],*cells,f'{passed}/{graded} graded'])+' |']
    lines+=['','✓ strict artifact complete · ✗ incomplete artifact · — excluded or missing; never a semantic zero.','',
        'A strict failure may reflect a content defect or interface/format error. DeepSeek low desktop-B has correct numeric data but an extra header; GLM high desktop-A invents file-ID suffixes. Read the failure analyses before treating strict counts as reasoning scores. The excluded DeepSeek low browser-B case prevents a complete balanced comparison at low effort.','',
        '## Identity and inference controls','',
        '| Harness | Model and effort evidence | Request-count evidence |',
        '|:--|:--|:--|',
        '| Command Code | Observed in CLI request events | Model-request-start events; provider retries may still be opaque |',
        '| Codex | Explicit invocation/configuration; not independently exposed in JSONL | Exec invocations and turn completion; underlying model requests/retries not exposed |','',
        'Both CLIs run in fresh temporary directories with personal project context disabled and tool use forbidden. Codex additionally disables discovered tools/integrations through its existing adapter. System prompts and native tool presentation remain harness-specific, and can affect correctness and token overhead. Same effort names do not imply equal compute.','',
        'The task/checker, first prompts, 120-second timeout, response constraints and 16,000-output soft guard are retained. Each model/effort has eight episodes and at most twelve response invocations. A missing/protocol-failed episode is not retried. There is no additional constrained-output schema for Codex. ZDR is unset only in evaluation child processes.','',
        '## Reported usage per configuration','',
        '| Model | Harness | Effort | CLI invocations | Reported input tokens | Reported output tokens | Reported cache-read tokens |',
        '|:--|:--|:--|--:|--:|--:|--:|']
    for run,m,rows,u in records:
        for model in m['models']:
            counts={k:sum(s['usage'].get(k,0) for r in rows if r['model']==model for s in r['steps']) for k in ('cliInvocations','inputTokens','outputTokens','cacheReadTokens')}
            lines+=['| '+' | '.join([f'[{model}](../{run.name}/report.md)',m['harness'],m['effort'],*[f'{counts[k]:,}' for k in ('cliInvocations','inputTokens','outputTokens','cacheReadTokens')]])+' |']
    lines+=['','Usage totals are summed from each configuration’s recorded response steps. Usage fields come from different CLIs and are not verified account charges. Input includes harness overhead; the missing low case and different contexts prevent direct cost-efficiency inference. Raw CLI events remain private.','',
        '## Per-task evidence','']
    for run,m,rows,u in records:lines+=['- ['+m['harness']+' '+m['effort']+': '+', '.join(m['models'])+'](../'+run.name+'/report.md)']
    lines+=['','## Interpretation limits','',
        'These are eight small, freshly authored cases. Familiar concepts may occur in training. One sample cannot establish reliability, significance, causal effort gains or a universal ranking. The code checker uses six fixed inputs and does not exhaust the contract. Per-field checks are correlated debugging evidence, not additional independent tasks. The simulators do not measure visual perception or real navigation/recovery.','',
        'Frozen task/checker SHA256: `'+hashlib.sha256(frozen).hexdigest()+'`.']
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',nargs='+',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();build(args.runs,args.out)
