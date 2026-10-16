"""Native Command Code file-tool calibration with bounded model turns."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from ..adapters import frames
from ..run import environment,parse_result,version_line
from .calibrate import MODELS,VARIANTS,preflight,setup_usage
from .checker import evaluate
from .importer import CHANGE,CONTRACT,materialize

NATIVE_PROTOCOL='''## Evaluation tools
Use the native repo_read, repo_write and repo_test tools to inspect, edit and verify the
repository. These are the only repository tools. Do not use shell, web, subagents or the
ordinary filesystem tools. Your final response can be ordinary Markdown; no JSON answer
envelope is required. Runnable source files are graded, not your explanation.
'''


def fingerprint():
    base=Path(__file__).parent
    names=('importer.py','checker.py','tools.py','bridge.py','native_tools.mjs','native_calibrate.py')
    return hashlib.sha256(b''.join((base/name).read_bytes() for name in names)).hexdigest()


def usage_from_events(events):
    usage={'cliInvocations':1,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
    ends=[]
    for f in events:
        e=f.get('event',{})
        if not isinstance(e,dict):continue
        if e.get('type')=='model_request_start':usage['observedModelRequests']+=1
        if e.get('type')=='model_request_end':ends.append(e.get('usage',{}))
    for count in ends:
        for k in ('inputTokens','outputTokens','cacheReadTokens'):usage[k]+=count.get(k,0)
    return usage


def episode(folder,model,variant,seed,turn_cap,output_budget,effort='low'):
    base=Path(__file__).parent.resolve()
    # The CLI's cwd has no ancestor workspace instructions or hidden graders.
    with tempfile.TemporaryDirectory(prefix='model-eval-native-',dir='/private/tmp') as d:
        root=Path(d);materialize(root,variant)
        task=CONTRACT.split('## Available file tools')[0]+NATIVE_PROTOCOL+f'\nModel-request budget: {turn_cap}. Batch source reads, source replacements and tests when useful. Final prose is optional; completed files are the goal.\n'
        (root/'README.md').write_text(task)
        config=root/'.commandcode';config.mkdir()
        (config/'settings.json').write_text(json.dumps({'tasteLearning':False,'reasoningEffort':{model:effort},
            'mods':{'disabled':['titling','learning']},'permissions':{
             'allow':['repo_read','repo_write','repo_test','search_tools'],
             'deny':['shell_command','read_file','write_file','edit_file','web_search','web_fetch','agent','mcp__*']}}))
        control=folder/'control.json';tool_log=folder/'tools.ndjson'
        env=environment()
        env.update({'MODEL_EVAL_WORKSPACE':str(root),'MODEL_EVAL_BRIDGE':str(base/'bridge.py'),
            'MODEL_EVAL_PYTHON':sys.executable,'MODEL_EVAL_SEED':str(seed),'MODEL_EVAL_VARIANT':variant,
            'MODEL_EVAL_CONTROL':str(control.resolve()),'MODEL_EVAL_TOOL_LOG':str(tool_log.resolve()),
            'MODEL_EVAL_CHANGE':json.dumps(CHANGE),'MODEL_EVAL_OUTPUT_BUDGET':str(output_budget)})
        argv=['cmd','-p','--model',model,'--output-format','json','--max-turns',str(turn_cap),
              '--no-session','--no-skills','--skip-onboarding','--no-auto-update','--permission-mode','dont-ask',
              '--mod',str(base/'native_tools.mjs')]
        (folder/'task.md').write_text(task)
        timed_out=False
        with (folder/'cli.ndjson').open('w') as stdout,(folder/'stderr.txt').open('w') as stderr:
            process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True,
                cwd=root,env=env,start_new_session=True)
            try:process.communicate('Complete the repository task in README.md.\n'+task,timeout=180*turn_cap)
            except subprocess.TimeoutExpired:
                timed_out=True
                os.killpg(process.pid,signal.SIGTERM)
                try:process.communicate(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.communicate()
            except BaseException:
                os.killpg(process.pid,signal.SIGKILL);process.communicate();raise
        raw=(folder/'cli.ndjson').read_text();events=frames(raw)
        usage=usage_from_events(events)
        state=json.loads(control.read_text()) if control.exists() else {}
        result={'model':model,'effort':effort,'harness':'Command Code / native repository tools',
            'variant':variant,'turn_cap':turn_cap,'exit_code':process.returncode,'usage':usage,
            'change_delivered':state.get('change_delivered',False),'control':state}
        try:
            final,_=parse_result(raw)
            result['models_observed']=final['observed_models'];result['efforts_observed']=final['observed_efforts']
            (folder/'answer.md').write_text(final.get('finalText',''))
            valid=not timed_out and not state.get('fatal_tool_error') and final['observed_models']==[model] and final['observed_efforts']==[effort] and process.returncode in (0,8) and final.get('subtype') in ('success','max_turns')
            result['stop']=final.get('stopReason') or final.get('subtype')
        except ValueError:valid=False;result['stop']='invalid_cli_output'
        result['tool_calls']=[e['event'].get('toolName') for e in events if isinstance(e.get('event'),dict) and e['event'].get('type')=='tool_running']
        result['tool_denials']=[e['event'].get('toolName') for e in events if isinstance(e.get('event'),dict) and e['event'].get('type')=='tool_denied']
        result['mod_errors']=[e['event'].get('hook') for e in events if isinstance(e.get('event'),dict) and e['event'].get('type')=='mod_error']
        artifact=folder/'workspace';artifact.mkdir()
        for name in ('README.md','ledger/__init__.py','ledger/parser.py','ledger/store.py','ledger/api.py'):
            dst=artifact/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text((root/name).read_text())
        result['grade']=evaluate(artifact,seed,variant) if valid and result['change_delivered'] and not result['mod_errors'] else None
        (folder/'result.json').write_text(json.dumps(result,indent=2))
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--setup-attempts',type=Path,nargs='*',default=[])
    parser.add_argument('--invalid-adapter-runs',type=Path,nargs='*',default=[])
    parser.add_argument('--effort',choices=['low','high'],default='low')
    parser.add_argument('--turn-cap',type=int,choices=[3,4,5],default=3)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    prior={'cliInvocations':0,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
    for path in args.setup_attempts:
        old=json.loads((path/'manifest.json').read_text())
        if old['seed']!=args.seed:parser.error('setup and calibration task seeds must match')
        counts=setup_usage(path)
        for k,v in counts.items():prior[k]+=v
    unknown_usage=0
    for path in args.invalid_adapter_runs:
        combined=[]
        for log in path.glob('*/cli.ndjson'):combined.extend(frames(log.read_text()))
        errors=[f['event'] for f in combined if isinstance(f.get('event'),dict) and f['event'].get('type')=='tool_errored']
        if not any(e.get('toolName')=='repo_test' and 'flatMap' in str(e.get('error')) for e in errors):
            parser.error('invalidated run must contain evidence of the test-tool schema crash')
        for log in path.glob('*/cli.ndjson'):
            events=frames(log.read_text());counts=usage_from_events(events)
            for k,v in counts.items():prior[k]+=v
            ends=sum(isinstance(f.get('event'),dict) and f['event'].get('type')=='model_request_end' for f in events)
            unknown_usage+=max(0,counts['observedModelRequests']-ends)
    gates=preflight(args.seed)
    plan={'workflow':'incremental-importer-native-v1','seed':args.seed,'models':MODELS,'variants':VARIANTS,
        'effort':args.effort,'turn_cap_per_episode':args.turn_cap,'max_observed_requests_including_setup':24,
        'output_token_guard_including_setup':32000,'setup_usage':prior,'fingerprint':fingerprint(),
        'preflight':'passed','zdr_enforced':False,'prior_requests_with_unreported_usage':unknown_usage}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    args.output.mkdir(parents=True,exist_ok=False)
    plan['cli_version']=version_line(subprocess.run(['cmd','--no-auto-update','--version'],capture_output=True,text=True,check=True,env=environment()).stdout)
    plan['commit']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
    (args.output/'manifest.json').write_text(json.dumps(plan,indent=2));(args.output/'preflight.json').write_text(json.dumps(gates,indent=2))
    usage=dict(prior);results=[]
    (args.output/'results.json').write_text('[]');(args.output/'usage.json').write_text(json.dumps(usage,indent=2))
    for i,(model,variant) in enumerate([(MODELS[0],'stream'),(MODELS[1],'stream'),(MODELS[1],'state'),(MODELS[0],'state')],1):
        if usage['observedModelRequests']+args.turn_cap>24 or usage['outputTokens']>=32000:break
        folder=args.output/f'{i:02}-{model.split("/")[-1]}-{variant}';folder.mkdir()
        print(f'[{i}/4] {model} / {variant}',flush=True)
        result=episode(folder,model,variant,args.seed,args.turn_cap,32000-usage['outputTokens'],args.effort)
        for k,v in result['usage'].items():usage[k]+=v
        results.append(result)
        (args.output/'results.json').write_text(json.dumps(results,indent=2));(args.output/'usage.json').write_text(json.dumps(usage,indent=2))
        print('  '+result['stop']+': '+str(result['grade'] and (result['grade']['passed'],result['grade']['total'])),flush=True)
        if result['grade'] is None:break


if __name__=='__main__':main()
