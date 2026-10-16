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
    return hashlib.sha256(b"".join((base/f).read_bytes() for f in ("importer.py","checker.py","tools.py","calibrate.py"))).hexdigest()


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


def episode(directory,model,variant,seed,max_turns,timeout,usage,output_limit):
    workspace=directory/"workspace";workspace.mkdir();materialize(workspace,variant)
    conversation=[{"role":"task","text":CONTRACT,
                   "repository_files":list(sources(variant)),"budget":"At most "+str(max_turns)+" model responses; batch file actions when useful."}]
    trace=[];change_active=False;stop="response_budget";protocol_errors=0
    for turn in range(1,max_turns+1):
        if usage["outputTokens"]>=output_limit:stop="aggregate_output_token_guard";break
        message="You are repairing a repository through the controlled file tools described below.\n"+json.dumps(conversation,ensure_ascii=False)
        (directory/f"turn-{turn}.prompt.txt").write_text(message)
        usage["cliInvocations"]+=1
        rc,out,err=invoke(model,SimpleNamespace(prompt=message),1,timeout,effort="high",harness="command-code")
        (directory/f"turn-{turn}.ndjson").write_text(out);(directory/f"turn-{turn}.stderr.txt").write_text(err)
        if rc!=0:
            stop="cli_failure";trace.append({"turn":turn,"exit_code":rc});break
        result,real_tools=parse_result(out)
        if result.get("subtype")!="success" or result["observed_models"]!=[model] or result["observed_efforts"]!=["high"] or real_tools:
            stop="identity_or_cli_protocol_failure";break
        counts=result.get("usage") or {}
        for key in ("inputTokens","outputTokens","cacheReadTokens"):
            if isinstance(counts.get(key),(int,float)):usage[key]+=counts[key]
        usage["observedModelRequests"]+=sum(1 for frame in frames(out) if frame.get("type")=="event"
            and isinstance(frame.get("event"),dict) and frame["event"].get("type")=="model_request_start")
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
    args=parser.parse_args()
    if not 3<=args.max_turns<=6:parser.error("calibration allows 3–6 responses per episode")
    if args.timeout<1 or args.output_token_guard<1:parser.error("limits must be positive")
    seed=args.seed if args.seed is not None else secrets.randbits(64)
    print("Checking reference artifacts, counterexamples and a four-turn reference trace.",flush=True)
    gates=preflight(seed)
    plan={"workflow":"incremental-importer-v1","seed":seed,"models":MODELS,"effort":"high",
          "variants":VARIANTS,"max_cli_invocations":4*args.max_turns,"responses_per_episode":args.max_turns,
          "output_token_guard":args.output_token_guard,"timeout_seconds_per_response":args.timeout,
          "zdr_enforced":False,"fingerprint":fingerprint(),"preflight":"passed"}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute:return
    args.output.mkdir(parents=True,exist_ok=False)
    version=version_line(subprocess.run(["cmd","--no-auto-update","--version"],text=True,capture_output=True,check=True,env=environment()).stdout)
    plan.update({"cli_version":version,"commit":subprocess.run(["git","rev-parse","HEAD"],text=True,capture_output=True,check=True).stdout.strip()})
    (args.output/"manifest.json").write_text(json.dumps(plan,indent=2));(args.output/"preflight.json").write_text(json.dumps(gates,indent=2))
    usage={"cliInvocations":0,"observedModelRequests":0,"inputTokens":0,"outputTokens":0,"cacheReadTokens":0}
    results=[]
    order=[(MODELS[0],"stream"),(MODELS[1],"stream"),(MODELS[1],"state"),(MODELS[0],"state")]
    for index,(model,variant) in enumerate(order,1):
        if usage["outputTokens"]>=args.output_token_guard:break
        folder=args.output/f"{index:02}-{model.split('/')[-1]}-{variant}";folder.mkdir()
        print(f"[{index}/4] {model} / {variant}",flush=True)
        result=episode(folder,model,variant,seed,args.max_turns,args.timeout,usage,args.output_token_guard)
        results.append(result)
        (args.output/"results.json").write_text(json.dumps(results,indent=2,ensure_ascii=False))
        (args.output/"usage.json").write_text(json.dumps(usage,indent=2))
        print("  "+result["stop"]+": "+str(result["grade"] and (result["grade"]["passed"],result["grade"]["total"])),flush=True)
        if result["stop"] in ("cli_failure","identity_or_cli_protocol_failure"):break
    print("Private artifacts: "+str(args.output))


if __name__=="__main__":main()
