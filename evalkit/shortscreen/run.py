"""Bounded paired diagnostic runner. Raw CLI evidence stays private."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from datetime import datetime,timezone
from ..run import invoke,parse_result,environment,version_line
from ..workflows.native_calibrate import usage_from_events
from ..adapters import frames
from .tasks import suite,qualify,decode,observe,grade

MODELS=['deepseek/deepseek-v4.1-flash','z-ai/glm-5.3-flash']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--resume-unattempted',action='store_true',help='explicit continuation; never retry any recorded episode')
    args=p.parse_args()
    tasks=suite();qualification=qualify()
    fingerprint=hashlib.sha256((Path(__file__).read_bytes()+Path(__file__).with_name('tasks.py').read_bytes())).hexdigest()
    plan={'suite':'paired-short-v1','models':MODELS,'harness':'Command Code','effort':'low',
        'episodes':16,'max_model_requests':24,'output_token_soft_guard':16000,
        'per_request_timeout_seconds':120,'max_turns_per_request':1,'fingerprint':fingerprint,
        'qualification':qualification,'zdr_enforced':False,'created_utc':datetime.now(timezone.utc).isoformat(),
        'domain_weights':{d:0.25 for d in ('coding','everyday','browser','desktop')},
        'scope':'Diagnostic only; structured-state simulation, no real browser/desktop or overall ranking'}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    previous=None
    if args.resume_unattempted:
        previous=json.loads((args.output/'manifest.json').read_text())
        frozen=subprocess.check_output(['git','show',previous['commit']+':evalkit/shortscreen/tasks.py'])
        if frozen!=Path(__file__).with_name('tasks.py').read_bytes():raise RuntimeError('task/checker changed; refusing continuation')
        (args.output/'results.before-continuation.json').write_text((args.output/'results.json').read_text())
        (args.output/'continuation.json').write_text(json.dumps({'policy':'Skip every recorded episode including failures; invoke only unattempted slots','adapter_fingerprint':fingerprint},indent=2))
    else:args.output.mkdir(parents=True,exist_ok=False)
    plan['commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    plan['cli_version']=version_line(subprocess.check_output(['cmd','--no-auto-update','--version'],text=True,env=environment()))
    if not previous:(args.output/'manifest.json').write_text(json.dumps(plan,indent=2))
    usage={'cliInvocations':0,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
    rows=[]
    if previous:
        rows=json.loads((args.output/'results.json').read_text())
        usage=json.loads((args.output/'usage.json').read_text())
    recorded={(r['task'],r['model']) for r in rows}
    def checkpoint():
        (args.output/'results.json').write_text(json.dumps(rows,indent=2))
        (args.output/'usage.json').write_text(json.dumps(usage,indent=2))
    checkpoint()
    for index,t in enumerate(tasks):
        order=MODELS if index%2==0 else MODELS[::-1]
        for model in order:
            if (t['id'],model) in recorded:continue
            if usage['observedModelRequests']+t['calls']>24 or usage['outputTokens']>=16000:
                print('Stopped at predeclared budget guard',flush=True);return
            name=t['id']+'-'+model.split('/')[-1]
            folder=args.output/name;folder.mkdir()
            print(name,flush=True)
            row={'task':t['id'],'domain':t['domain'],'case':t['variant'],'model':model,'effort':'low',
                'harness':'Command Code','steps':[],'status':'running','grade':None}
            rows.append(row);checkpoint();prompt=t['prompt'];last=None
            for step in range(t['calls']):
                stem=folder/f'step-{step+1}'
                stem.with_suffix('.prompt.txt').write_text(prompt)
                rc,raw,err=invoke(model,SimpleNamespace(prompt=prompt),1,120,'low')
                stem.with_suffix('.cli.ndjson').write_text(raw);stem.with_suffix('.stderr.txt').write_text(err)
                counts=usage_from_events(frames(raw))
                for k,v in counts.items():usage[k]+=v
                info={'request':step+1,'exit_code':rc,'usage':counts}
                row['steps'].append(info)
                try:
                    result,tools=parse_result(raw)
                    info.update({'models_observed':result['observed_models'],'efforts_observed':result['observed_efforts'],
                        'tool_calls':tools,'subtype':result.get('subtype'),'answer':result.get('finalText','')})
                    if rc!=0 or tools or result['observed_models']!=[model] or result['observed_efforts']!=['low'] or result.get('subtype')!='success':
                        raise RuntimeError('CLI/tool/identity/effort failure')
                    last=decode(result.get('finalText',''))
                except (ValueError,RuntimeError) as exc:
                    row['status']='adapter_or_response_contract_failure';row['error']=str(exc);checkpoint()
                    print('Stopped; no retry or capability zero',flush=True);return
                if step==0 and t['calls']==2:
                    observation=observe(t,last)
                    info['observation']=observation
                    prompt=t['prompt']+'\nYour previous action:\n'+json.dumps(last)+'\nSimulator observation:\n'+json.dumps(observation)+'\nRespond with the final artifact JSON only, under 150 words.'
                checkpoint()
            row['grade']=grade(t,last);row['status']='graded';checkpoint()
            if t['domain']=='desktop' and last.get('action')=='export':
                import csv,io
                data=io.StringIO();writer=csv.writer(data);writer.writerow(['employee','amount_cents'])
                if isinstance(last.get('rows'),list):writer.writerows(last['rows'])
                (folder/'export.csv').write_text(data.getvalue())
            if t['domain']=='browser':(folder/'comparison.json').write_text(json.dumps(last,indent=2))
            print('complete='+str(row['grade']['complete'])+' output_total='+str(usage['outputTokens']),flush=True)


if __name__=='__main__':main()
