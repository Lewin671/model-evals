"""Export only whitelisted workflow evidence, keeping CLI transcripts private."""
import argparse
import json
from pathlib import Path
import shutil


def export(run, destination):
    manifest=json.loads((run/'manifest.json').read_text())
    rows=json.loads((run/'results.json').read_text())
    destination.mkdir(parents=True,exist_ok=False)
    public={key:manifest[key] for key in ('workflow','seed','models','variants','effort',
        'turn_cap_per_episode','max_observed_requests_including_setup','output_token_guard_including_setup',
        'setup_usage','fingerprint','preflight','zdr_enforced','prior_requests_with_unreported_usage','cli_version','commit')}
    public['usage_including_invalid_attempts']=json.loads((run/'usage.json').read_text())
    (destination/'manifest.json').write_text(json.dumps(public,indent=2)+'\n')
    (destination/'qualification.json').write_text((run/'preflight.json').read_text())
    lines=['# Incremental importer: bounded calibration','',
        'Coding only. Each episode is a fresh repository with actual native read/write/test tools.',
        'The planned paired pilot uses **'+manifest['effort']+' reasoning effort**, with a **'+str(manifest['turn_cap_per_episode'])+' model-request cap**.',
        'This measures performance within this tight budget; it is not an overall model ranking.','',
        '| Model | Starter | L1 | L2 | L3 | Total | Stop | Evidence |',
        '|:--|:--|:--|:--|:--|:--|:--|:--|']
    summaries=[]
    for i,row in enumerate(rows,1):
        original=next(p for p in run.glob(f'{i:02}-*') if p.is_dir())
        name=f'{i:02}-{row["model"].split("/")[-1]}-{row["variant"]}'
        target=destination/name;target.mkdir()
        clean={k:row[k] for k in ('model','effort','harness','variant','turn_cap','exit_code','usage',
            'change_delivered','models_observed','efforts_observed','stop','tool_calls','tool_denials','mod_errors','grade') if k in row}
        summaries.append(clean)
        (target/'result.json').write_text(json.dumps(clean,indent=2)+'\n')
        shutil.copytree(original/'workspace',target/'workspace')
        shutil.copyfile(original/'task.md',target/'task.md')
        trace=[]
        if (original/'tools.ndjson').exists():
            for raw in (original/'tools.ndjson').read_text().splitlines():
                event=json.loads(raw)
                trace.append({k:event[k] for k in ('round','action','result')})
        (target/'tools.json').write_text(json.dumps(trace,indent=2)+'\n')
        grade=row['grade']
        def fraction(part):return f'{part["passed"]}/{part["total"]}'
        cells=[fraction(grade['tiers'][tier]) if grade else 'invalid' for tier in ('L1','L2','L3')]
        lines.append('| '+ ' | '.join([row['model'],row['variant'],*cells,fraction(grade) if grade else 'excluded',row['stop'],f'[Source & trace]({name}/result.json)'])+' |')
    (destination/'results.json').write_text(json.dumps(summaries,indent=2)+'\n')
    lines+=['','## Interpretation','']
    if len(rows)!=4 or any(r['grade'] is None for r in rows):
        verdict='Incomplete pilot. No paired model conclusion is justified.'
    else:
        scores=[r['grade']['passed'] for r in rows]
        if all(r['grade']['fraction']==1 for r in rows):verdict='Ceiling: all four artifacts pass. This task does not separate these configurations.'
        elif all(x==0 for x in scores):verdict='Floor: no artifact passes. This budget/task combination does not establish useful model separation.'
        elif (scores[0]-scores[1])*(scores[3]-scores[2])>0:verdict='The same model scores higher on both starters. This is a small coding-only calibration signal, not statistical significance.'
        else:verdict='Mixed results or ties across starters. There is no consistent paired winner.'
    lines +=[verdict,'','The L1/L2/L3 checks cover baseline API/fragmentation, quoted streaming/replay, and coupled revision/atomicity/change behavior. Each scenario has equal weight; scenarios are correlated.','',
        '## Limits and accounting','',
        'Task/checker frozen before these calls. Final source is independently executed against eleven acceptance scenarios; prose is not scored. Identity and effort are verified from CLI events. ZDR was unset only in child processes.','',
        'Earlier adapter experiments are excluded from scores but included in usage. One interrupted prior request has unreported tokens, so reported totals are a lower bound. See [adapter incidents](../../docs/native-importer-pilot.md). Raw CLI streams and personal paths remain private.','',
        'Two independent source variants and one episode per model/variant were planned. The table lists the episodes actually completed. This does not establish reliability across seeds, maximum coding capability, browser use, desktop use, or everyday-task performance. Codex has not been run on this replacement task.']
    (destination/'report.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();export(args.run,args.destination)
