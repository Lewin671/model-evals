"""Compare published low/high diagnostic records without inventing missing grades."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def compare(low,high,out):
    manifests=[json.loads((p/'manifest.json').read_text()) for p in (low,high)]
    rows=[json.loads((p/'results.json').read_text()) for p in (low,high)]
    usage=[json.loads((p/'usage.json').read_text()) for p in (low,high)]
    maps=[{(r['model'],r['task']):r for r in records} for records in rows]
    task_sources=[subprocess.check_output(['git','show',m['commit']+':evalkit/shortscreen/tasks.py']) for m in manifests]
    if task_sources[0]!=task_sources[1]:raise ValueError('Task/checker changed between runs')
    for key in ('suite','models','harness','max_model_requests','output_token_soft_guard','per_request_timeout_seconds','max_turns_per_request','cli_version'):
        if manifests[0][key]!=manifests[1][key]:raise ValueError('Comparison settings differ: '+key)
    if [m['effort'] for m in manifests]!=['low','high']:raise ValueError('Expected low/high')
    lines=['# Low versus high reasoning effort','',
        'Same eight cases, model IDs, task order, CLI version, checker, 120-second request timeout, one-turn response cap, 24-request budget and 16,000-output soft guard. Only effort is deliberately changed. Each episode starts fresh and receives no previous-run answer.',
        'Reasoning effort and identity are observed in CLI request events. ZDR is unset only in child processes.','',
        '| Model | Effort | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Strict completion |',
        '|:--|:--|:--|:--|:--|:--|:--|']
    def symbol(row):
        if not row or row['grade'] is None:return '—'
        return '✓' if row['grade']['complete'] else '✗'
    for model in manifests[0]['models']:
        for i,effort in enumerate(('low','high')):
            cells=[]
            for domain in ('coding','everyday','browser','desktop'):
                cells.append(' / '.join(symbol(maps[i].get((model,domain+'-'+v))) for v in ('A','B')))
            available=[r for r in rows[i] if r['model']==model and r['grade'] is not None]
            passed=sum(r['grade']['complete'] for r in available)
            lines+=['| '+' | '.join([model,effort,*cells,f'{passed}/{len(available)} graded'])+' |']
    lines+=['','✓ strict artifact completion · ✗ incomplete artifact · — excluded/missing, never a semantic zero.','',
        'The low DeepSeek/desktop-B failure is specifically an extra header with otherwise correct data. Strict completion is not a pure reasoning score. The low DeepSeek/browser-B case is a denied native shell call; it is excluded. See the [low-run failure analysis](../paired-short-01/failure-analysis.md).','',
        '## Within-model transitions','',
        '| Model | Case | Low → high |','|:--|:--|:--|']
    for model in manifests[0]['models']:
        for domain in ('coding','everyday','browser','desktop'):
            for v in ('A','B'):
                key=(model,domain+'-'+v)
                a,b=(symbol(m.get(key)) for m in maps)
                if a!=b:lines+=['| '+' | '.join([model,key[1],a+' → '+b])+' |']
    lines+=['','## Measured usage','',
        '| Effort | Model requests | Reported input tokens | Reported output tokens | Reported cache-read tokens |',
        '|:--|--:|--:|--:|--:|']
    for effort,u in zip(('low','high'),usage):
        lines+=['| '+' | '.join([effort,*[f'{u[k]:,}' for k in ('observedModelRequests','inputTokens','outputTokens','cacheReadTokens')]])+' |']
    lines+=['','Counts are CLI usage fields, not verified billing. Input context includes native CLI overhead. A soft guard can overshoot during an in-flight request. Missing/failed cases make total-usage ratios imperfect comparisons.','',
        '## Evidence and limits','',
        '[Low run](../paired-short-01/report.md) · [High run](../paired-short-high-01/report.md)','',
        'This is one sample per configuration/case. Changes can reflect sampling variation as well as effort; do not claim a causal effort gain, statistical significance, or a universal model ranking. The structured browser/desktop tasks do not measure real application control. No task or grader was tuned after either run.','',
        'Frozen task/checker SHA256: `'+hashlib.sha256(task_sources[0]).hexdigest()+'`.']
    out.write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('low',type=Path);parser.add_argument('high',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();compare(args.low,args.high,args.out)
