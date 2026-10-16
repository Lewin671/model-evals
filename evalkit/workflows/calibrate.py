"""Bounded, stateful importer calibration: two models, two repository variants."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
from types import SimpleNamespace

from ..run import environment,invoke,parse_result,version_line
from ..adapters import frames
from .checker import evaluate
from .importer import API_REFERENCE,CHANGE,CONTRACT,materialize,sources
from .tools import decode,perform

MODELS=["deepseek/deepseek-v4.1-flash","z-ai/glm-5.3-flash"]
VARIANTS=["stream","state"]


def fingerprint():
    base=Path(__file__).parent
    return hashlib.sha256(b"".join((base/f).read_bytes() for f in ("importer.py","checker.py","tools.py","calibrate.py","no_native_tools.mjs"))+(base.parent/'run.py').read_bytes()).hexdigest()


def preflight(seed):
    """Reference completion + deliberately wrong strategies; zero model calls."""
    results={"reference":{},"starter":{},"mutants":{},"reference_trace":[]}
    for variant in VARIANTS:
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);materialize(root,variant,reference=True)
            result=evaluate(root,seed,variant)
            if result["passed"]!=result["total"]:raise RuntimeError("reference failed: "+json.dumps(result))
            results["reference"][variant]=result
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);materialize(root,variant)
            result=evaluate(root,seed,variant)
            if result["passed"]==result["total"]:raise RuntimeError("starter unexpectedly passes every check")
            results["starter"][variant]=result
    expected={"line-splitter":"quoted-boundaries","last-arrival":"revisions-and-delete",
              "non-atomic":"atomic-corrected-retry","text-only-replay":"conflicting-replay","no-replay":"partition-replay"}
    for mutant,case in expected.items():
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);materialize(root,"stream",reference=True,mutant=mutant)
            result=evaluate(root,seed,"stream")
            if next(r for r in result["cases"] if r["name"]==case)["passed"]:
                raise RuntimeError("baseline failed to expose its intended error: "+mutant)
            results["mutants"][mutant]=result
    # Reference controller uses the same file tools as the models. It implements
    # the extra replay requirement only after the injected change request.
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);materialize(root,"stream")
        initial=sources("stream",reference=True)
        initial["ledger/api.py"]=API_REFERENCE.replace("if stream['deliveries'][delivery_id] != fingerprint:","if False:")
        trace=[[{"tool":"read","paths":["ledger/parser.py","ledger/store.py","ledger/api.py"]}],
               [{"tool":"write","files":{k:v for k,v in initial.items() if k.endswith('.py') and k!='ledger/__init__.py'}},{"tool":"test"}],
               [{"tool":"write","files":{"ledger/api.py":API_REFERENCE}},{"tool":"test"}],
               [{"tool":"finish"}]]
        for i,actions in enumerate(trace):
            observations,finished=perform(root,actions,seed,"stream",change=i>=2)
            for o in observations:
                if "error" in o:raise RuntimeError("reference tool error")
                if o.get("tool")=="test" and o["public_checks"]["fraction"]!=1:raise RuntimeError("reference public tests failed")
            results["reference_trace"].append({"turn":i+1,"tools":[a["tool"] for a in actions],"change_active":i>=2,"finished":finished})
        if evaluate(root,seed,"stream")["fraction"]!=1:raise RuntimeError("reference trace artifact failed")
    return results


def setup_usage(directory):
    results=json.loads((directory/'results.json').read_text())
    if any(r.get('grade') is not None or r.get('change_delivered') or any(t.get('actions') for t in r.get('trace',[])) for r in results):
        raise ValueError('a scored or progressed episode cannot be excluded as an adapter setup attempt')
    counts={"cliInvocations":0,"observedModelRequests":0,"inputTokens":0,"outputTokens":0,"cacheReadTokens":0}
    for path in directory.glob('*/turn-*.ndjson'):
        events=frames(path.read_text())
        if not any(f.get('event',{}).get('type')=='tool_denied' for f in events if isinstance(f.get('event'),dict)):
            raise ValueError('setup exclusion requires evidence of a denied native tool')
        counts['cliInvocations']+=1
        counts['observedModelRequests']+=sum(f.get('event',{}).get('type')=='model_request_start' for f in events if isinstance(f.get('event'),dict))
        for frame in events:
            if frame.get('type')=='result':
                for key in ('inputTokens','outputTokens','cacheReadTokens'):counts[key]+=frame.get('usage',{}).get(key,0)
    return counts


def episode(directory,model,variant,seed,max_turns,timeout,usage,output_limit,max_requests=24):
    workspace=directory/"workspace";workspace.mkdir();materialize(workspace,variant)
    conversation=[{"role":"task","text":CONTRACT,
                   "repository_files":list(sources(variant)),"budget":"At most "+str(max_turns)+" model responses; batch file actions when useful."}]
    trace=[];change_active=False;stop="response_budget";protocol_errors=0
    for turn in range(1,max_turns+1):
        if usage['cliInvocations']>=max_requests:stop='aggregate_request_guard';break
        if usage["outputTokens"]>=output_limit:stop="aggregate_output_token_guard";break
        message="You are repairing a repository through the controlled file tools described below.\n"+json.dumps(conversation,ensure_ascii=False)
        (directory/f"turn-{turn}.prompt.txt").write_text(message)
        usage["cliInvocations"]+=1
        rc,out,err=invoke(model,SimpleNamespace(prompt=message),1,timeout,effort="high",harness="command-code")
        (directory/f"turn-{turn}.ndjson").write_text(out);(directory/f"turn-{turn}.stderr.txt").write_text(err)
        event_frames=frames(out)
        usage["observedModelRequests"]+=sum(1 for f in event_frames if isinstance(f.get('event'),dict) and f['event'].get('type')=='model_request_start')
        counts=next((f.get('usage',{}) for f in event_frames if f.get('type')=='result'),{})
        for key in ("inputTokens","outputTokens","cacheReadTokens"):
            if isinstance(counts.get(key),(int,float)):usage[key]+=counts[key]
        if rc!=0:
            stop="cli_failure";trace.append({"turn":turn,"exit_code":rc,"usage":counts});break
        try:result,real_tools=parse_result(out)
        except ValueError:
            stop='cli_failure';trace.append({'turn':turn,'exit_code':rc,'usage':counts,'reason':'invalid CLI event stream'});break
        if result.get("subtype")!="success" or result["observed_models"]!=[model] or result["observed_efforts"]!=["high"] or real_tools:
            stop="identity_or_cli_protocol_failure";break
        text=result.get("finalText","")
        (directory/f"turn-{turn}.answer.txt").write_text(text)
        conversation.append({"role":"model","response":text})
        try:
            actions,normalizations=decode(text)
            observations,finished=perform(workspace,actions,seed,variant,change_active)
            protocol_error=None
        except (ValueError,TypeError,KeyError) as exc:
            protocol_errors+=1;actions=[];normalizations=[];finished=False
            protocol_error=str(exc);observations=[{"protocol_error":str(exc),"instruction":"Return file-tool actions; this does not change the repository."}]
        injected=False
        if not change_active and (turn>=2 or finished):
            change_active=True;injected=True;finished=False
            observations.append({"user_change_request":CHANGE})
        trace.append({"turn":turn,"actions":actions,"normalizations":normalizations,"protocol_error":protocol_error,
                      "observations":observations,"change_injected":injected,"usage":counts})
        (directory/"trace.json").write_text(json.dumps(trace,indent=2,ensure_ascii=False))
        conversation.append({"role":"tool_results","observations":observations})
        if finished:stop="finished";break
    # Files are graded even if the model omits finish or violates the response
    # envelope. Output compliance is not substituted for semantic correctness.
    grade=evaluate(workspace,seed,variant,change=True) if change_active and stop not in ("cli_failure","identity_or_cli_protocol_failure") else None
    return {"model":model,"effort":"high","harness":"Command Code / controlled file tools","variant":variant,
            "stop":stop,"turns":len(trace),"change_delivered":change_active,"protocol_errors":protocol_errors,
            "grade":grade,"trace":trace}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed",type=int)
    parser.add_argument("--output",type=Path,default=Path('.runs/importer-calibration-01'))
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--max-turns",type=int,default=6)
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--output-token-guard",type=int,default=32000)
    parser.add_argument("--max-requests",type=int,default=24,help='total CLI request ceiling including an excluded setup attempt')
    parser.add_argument("--setup-attempt",type=Path,help='retain and account for a verified adapter-only failure')
    args=parser.parse_args()
    if args.execute:parser.error('The controlled-response adapter is retired. Use evalkit.workflows.native_calibrate for the native-tool pilot.')
    if not 3<=args.max_turns<=6:parser.error("calibration allows 3–6 responses per episode")
    if args.timeout<1 or args.output_token_guard<1:parser.error("limits must be positive")
    if not 1<=args.max_requests<=24:parser.error('pilot total request ceiling must be 1–24')
    prior=setup_usage(args.setup_attempt) if args.setup_attempt else {"cliInvocations":0,"observedModelRequests":0,"inputTokens":0,"outputTokens":0,"cacheReadTokens":0}
    old_manifest=json.loads((args.setup_attempt/'manifest.json').read_text()) if args.setup_attempt else None
    seed=args.seed if args.seed is not None else old_manifest['seed'] if old_manifest else secrets.randbits(64)
    if old_manifest and seed!=old_manifest['seed']:parser.error('do not change the task seed after an adapter-only failure')
    print("Checking reference artifacts, counterexamples and a four-turn reference trace.",flush=True)
    gates=preflight(seed)
    plan={"workflow":"incremental-importer-v1","seed":seed,"models":MODELS,"effort":"high",
          "variants":VARIANTS,"max_cli_invocations":min(args.max_requests,prior['cliInvocations']+4*args.max_turns),"responses_per_episode":args.max_turns,
          "output_token_guard":args.output_token_guard,"timeout_seconds_per_response":args.timeout,
          "zdr_enforced":False,"fingerprint":fingerprint(),"preflight":"passed","setup_usage":prior,
          "native_tool_filter":"active tool schemas removed; empty-tool proof checked on every invocation"}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    args.output.mkdir(parents=True,exist_ok=False)
    version=version_line(subprocess.run(["cmd","--no-auto-update","--version"],text=True,capture_output=True,check=True,env=environment()).stdout)
    plan.update({"cli_version":version,"commit":subprocess.run(["git","rev-parse","HEAD"],text=True,capture_output=True,check=True).stdout.strip()})
    (args.output/"manifest.json").write_text(json.dumps(plan,indent=2));(args.output/"preflight.json").write_text(json.dumps(gates,indent=2))
    usage=dict(prior)
    results=[]
    order=[(MODELS[0],"stream"),(MODELS[1],"stream"),(MODELS[1],"state"),(MODELS[0],"state")]
    for index,(model,variant) in enumerate(order,1):
        if usage["outputTokens"]>=args.output_token_guard or usage['cliInvocations']>=args.max_requests:break
        folder=args.output/f"{index:02}-{model.split('/')[-1]}-{variant}";folder.mkdir()
        print(f"[{index}/4] {model} / {variant}",flush=True)
        result=episode(folder,model,variant,seed,args.max_turns,args.timeout,usage,args.output_token_guard,args.max_requests)
        results.append(result)
        (args.output/"results.json").write_text(json.dumps(results,indent=2,ensure_ascii=False))
        (args.output/"usage.json").write_text(json.dumps(usage,indent=2))
        print("  "+result["stop"]+": "+str(result["grade"] and (result["grade"]["passed"],result["grade"]["total"])),flush=True)
        if result["stop"] in ("cli_failure","identity_or_cli_protocol_failure"):break
    print("Private artifacts: "+str(args.output))


if __name__=="__main__":main()
