"""Sanitized evidence export for the frozen short diagnostic."""
import argparse
import json
from pathlib import Path
from .tasks import decode
import shutil


def export(run,out):
    manifest=json.loads((run/'manifest.json').read_text())
    rows=json.loads((run/'results.json').read_text())
    usage=json.loads((run/'usage.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if (run/'continuation.json').exists():shutil.copyfile(run/'continuation.json',out/'continuation.json')
    (out/'usage.json').write_text(json.dumps(usage,indent=2)+'\n')
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    evidence=[]
    for row in rows:
        name=row['task']+'-'+row['model'].split('/')[-1]
        src=run/name;dest=out/name;dest.mkdir()
        text=['# '+row['task']+' — '+row['model'],'',manifest['harness']+' · **'+manifest['effort']+' reasoning effort**','']
        for step in row['steps']:
            i=step['request'];prompt=(src/f'step-{i}.prompt.txt').read_text()
            text += ['## Request '+str(i),'','```text',prompt,'```','','## Response '+str(i),'','```text',step.get('answer',''),'```','']
            if 'observation' in step:
                text+=['## Simulator observation','','```json',json.dumps(step['observation'],indent=2),'```','']
        text+=['## Outcome','','```json',json.dumps({'status':row['status'],'grade':row['grade']},indent=2),'```','']
        (dest/'evidence.md').write_text('\n'.join(text))
        if row['domain']=='coding' and row['steps']:
            try:
                code=decode(row['steps'][-1].get('answer','')).get('source')
                if isinstance(code,str):(dest/'solution.py').write_text(code)
            except ValueError:pass
        for file in ('export.csv','comparison.json'):
            if (src/file).exists():shutil.copyfile(src/file,dest/file)
        evidence.append((row,name))
    lines=['# Paired short diagnostic v1','',
        'Configurations use **'+manifest['effort']+' reasoning effort**, '+manifest['harness']+' CLI. '+('Model/effort are configured through the invocation; Codex JSONL does not independently expose them.' if manifest['harness']=='Codex' else 'Model and effort are observed in CLI request events.'),
        'Eight independently presented cases across four domains; browser/desktop use two-step text-state simulators.',
        'This is a diagnostic screen, not an overall capability leaderboard.','',
        '| Model | Coding A / B | Everyday A / B | Browser simulation A / B | Desktop simulation A / B | Tasks complete | Pairs complete |',
        '|:--|:--|:--|:--|:--|:--|:--|']
    by={(r['model'],r['task']):r for r in rows}
    for model in manifest['models']:
        cells=[];total=0;pairs=0;graded=0;graded_pairs=0
        for domain in ('coding','everyday','browser','desktop'):
            marks=[];both=True;pair_graded=True
            for v in ('A','B'):
                r=by.get((model,domain+'-'+v))
                ok=bool(r and r['grade'] and r['grade']['complete'])
                marks.append('✓' if ok else '✗' if r and r['grade'] is not None else '—')
                total+=ok;both=both and ok
                available=bool(r and r['grade'] is not None)
                graded+=available;pair_graded=pair_graded and available
            pairs+=both;graded_pairs+=pair_graded;cells.append(' / '.join(marks))
        lines+=['| '+' | '.join([model,*cells,f'{total}/{graded} graded'+(f'; {8-graded} excluded/missing' if graded<8 else ''),f'{pairs}/{graded_pairs} graded'])+' |']
    complete=len(rows)==manifest['episodes'] and all(r['status']=='graded' for r in rows)
    ceiling=complete and all(r['grade']['complete'] for r in rows)
    lines +=['','## What this established','',
        'Ceiling: all evaluated configurations complete every task. This screen does **not** separate these configurations.' if ceiling else
        'The four-domain screen is incomplete. Missing or invalid responses are excluded, not scored zero. Any explicit continuation skips recorded episodes, including failures. Compare common graded cases descriptively; no full balanced aggregate is justified.' if not complete else
        'The table shows observed task differences in this small run. Treat them as hypotheses for follow-up, not a general ranking or statistical significance.','',
        'The paired cases change delivery-ID scope, approval of a meeting update, a live checkout quote, and workbook approval status. A pair counts only if both variants complete. All four domains have equal task weight. Partial field/check scores remain debugging evidence.','',
        '## Actual usage','',
        ("**"+str(usage['cliInvocations'])+" Codex exec invocations** (underlying model requests/retries not exposed)" if manifest['harness']=='Codex' else "**"+str(usage['observedModelRequests'])+" observed model requests**")+f", {usage['outputTokens']:,} reported output tokens; {usage['inputTokens']:,} reported input tokens and {usage['cacheReadTokens']:,} reported cache-read tokens (CLI usage fields).",
        'These are CLI-reported counts, not verified dollar charges. Earlier importer experiments are separate. ZDR was unset only in child processes.','',
        '## Per-task evidence','',
        '| Case | Model | Outcome | Evidence |','|:--|:--|:--|:--|']
    for row,name in evidence:
        g=row['grade'];mark='complete' if g and g['complete'] else 'incomplete' if g else row['status']
        lines+=['| '+' | '.join([row['task'],row['model'],mark,f'[Prompt, response & observations]({name}/evidence.md)'])+' |']
    lines+=['','## Limits','',
        'The tasks are small and explicitly specified. The simulator can open multiple IDs at once, has no real navigation cost, and exposes structured data. It does not establish visual perception, real browser/computer use, realistic recovery, or source-file preservation in an actual application. A simulated export creates a real CSV artifact but never opens a spreadsheet application.','',
        'Coding coverage is six fixed inputs, not exhaustive: the empty batch shares its account with a later valid batch, so it does not isolate zero-account creation. Cases are newly authored, but familiar underlying patterns may occur in training. One run per model/case cannot measure reliability. No checker or task was tuned after seeing responses. JSON fences are normalized; response-contract failures are separate from semantic grades and stop execution.','',
        '[Frozen task design and reproduction](../../docs/paired-short-screen.md)']
    (out/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('out',type=Path)
    args=parser.parse_args();export(args.run,args.out)
