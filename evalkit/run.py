"""Archived prototype runner; paid reproduction requires explicit opt-in."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import tempfile
from datetime import datetime, timezone

from .grading import execute, grade
from .tasks import suite
from .adapters import Variant, codex_command, parse_codex


def suite_fingerprint():
    base=Path(__file__).parent
    return hashlib.sha256(b"".join((base/name).read_bytes() for name in ("tasks.py","general.py","grading.py","rubrics.py"))).hexdigest()


def version_line(text):
    # Older cmd versions can print an updater notice before the version line.
    return text.strip().splitlines()[-1]

MODELS = ["deepseek/deepseek-v4.1-flash", "z-ai/glm-5.3-flash"]


def command(model, turns):
    return ["cmd", "-p", "--model", model, "--output-format", "json",
            "--max-turns", str(turns), "--no-session", "--no-skills",
            "--skip-onboarding", "--no-auto-update", "--permission-mode", "dont-ask"]


def environment():
    env = dict(os.environ)
    env.pop("CMD_ZDR", None)
    env.update({"DO_NOT_TRACK":"1", "COMMANDCODE_SKIP_UPDATES":"1"})
    return env


def parse_result(raw):
    frames = []
    for line in raw.splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if isinstance(item, dict): frames.append(item)
    results = [f for f in frames if f.get("type")=="result"]
    if len(results)!=1: raise ValueError("expected exactly one CLI result frame")
    tools = [f["event"] for f in frames if f.get("type")=="event" and
             isinstance(f.get("event"),dict) and f["event"].get("type")=="tool_running"]
    result=dict(results[0])
    result["observed_models"]=sorted({f["event"]["model"] for f in frames if f.get("type")=="event"
        and isinstance(f.get("event"),dict) and f["event"].get("type") in ("model_request_start","model_request_end")
        and isinstance(f["event"].get("model"),str)})
    result["observed_efforts"]=sorted({f["event"]["effort"] for f in frames if f.get("type")=="event"
        and isinstance(f.get("event"),dict) and f["event"].get("type")=="model_request_end"
        and isinstance(f["event"].get("effort"),str)})
    result["identity_source"]="CLI request events"
    return result, len(tools)


def invoke(model, task, turns, timeout, effort="high", harness="command-code",mod_path=None):
    # Outside the benchmark checkout: generators/oracles are not auto-context.
    with tempfile.TemporaryDirectory(prefix="cc-eval-") as scratch:
        config = Path(scratch)/".commandcode"
        config.mkdir()
        (config/"settings.json").write_text(json.dumps({
            "tasteLearning":False, "reasoningEffort":{model:effort},"permissions":{"deny":["*"]}}))
        variant=Variant(harness,model,effort)
        argv=command(model,turns) if harness=="command-code" else codex_command(variant)
        env=environment()
        proof=Path(scratch)/"tool-visibility.json"
        if mod_path:
            if harness!="command-code":raise ValueError("native tool filter supports Command Code only")
            argv += ["--mod",str(Path(mod_path).resolve())]
            env["MODEL_EVAL_TOOL_PROOF"]=str(proof)
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, cwd=scratch, env=env, start_new_session=True)
        try:
            out,err=process.communicate(task.prompt,timeout=timeout)
            exit_code=process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try: out,err=process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                out,err=process.communicate()
            exit_code=124
        except BaseException:
            os.killpg(process.pid,signal.SIGKILL)
            process.communicate()
            raise
        if mod_path:
            try:verified=json.loads(proof.read_text())=={"active_tools":[]}
            except (OSError,ValueError):verified=False
            if not verified:
                exit_code=125;err+="\nNative-tool visibility proof missing or nonempty.\n"
            else:err+="\nMODEL_EVAL_NATIVE_TOOLS_VERIFIED_EMPTY\n"
    return exit_code,out,err


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="fresh random seed by default; reuse for paired reproduction")
    parser.add_argument("--suite",choices=["general-v2"],default="general-v2")
    parser.add_argument("--models", nargs="+")
    parser.add_argument("--harness",choices=["command-code","codex"],default="command-code")
    parser.add_argument("--effort",default="high",help="explicit reasoning effort, default high")
    parser.add_argument("--campaign",type=Path,help="JSON variants with harness, model, effort")
    parser.add_argument("--tasks", nargs="+", help="subset of task IDs")
    parser.add_argument("--max-turns",type=int,default=1)
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--max-calls",type=int,default=12)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--resume-run",type=Path,help="reuse every recorded response; invoke only never-attempted slots")
    parser.add_argument("--execute",action="store_true",help="actually spend credits; otherwise print plan")
    parser.add_argument("--allow-prototype",action="store_true",help="explicitly reproduce the uncalibrated prototype; not a capability ranking")
    args=parser.parse_args()
    if args.execute and not args.allow_prototype:
        parser.error("general-v2 is an uncalibrated prototype with a ceiling effect. Paid runs require --allow-prototype for archival reproduction only.")
    if args.resume_run and args.output: parser.error("--resume-run cannot combine with --output")
    previous=json.loads((args.resume_run/"manifest.json").read_text()) if args.resume_run else None
    if min(args.max_turns,args.timeout,args.max_calls)<1: parser.error("limits must be positive")
    try:
        if args.campaign:
            if args.models or args.harness!="command-code" or args.effort!="high":
                parser.error("--campaign cannot combine with model/harness/effort overrides")
            variants=[Variant(**v) for v in json.loads(args.campaign.read_text())["variants"]]
        else:
            if args.harness=="codex" and not args.models: parser.error("Codex requires explicit --models")
            variants=[Variant(args.harness,m,args.effort) for m in (args.models or MODELS)]
        if not variants or len({v.id for v in variants})!=len(variants): parser.error("empty or duplicate variants")
    except (ValueError,KeyError,TypeError) as e: parser.error(str(e))
    seed=args.seed if args.seed is not None else previous["seed"] if previous else secrets.randbits(64)
    tasks=suite(seed)
    if args.tasks:
        if set(args.tasks)-{t.id for t in tasks}: parser.error("unknown task")
        tasks=[t for t in tasks if t.id in args.tasks]
    # Rotate first position across tasks and reverse alternate rows.
    schedule=[]
    for i,t in enumerate(tasks):
        offset=i%len(variants)
        order=variants[offset:]+variants[:offset]
        schedule.extend((v,t) for v in (order if i%2==0 else order[::-1]))
    if len(schedule)>args.max_calls: parser.error("call count exceeds --max-calls; no partial run")
    domains=list(dict.fromkeys(t.domain for t in tasks))
    plan={"seed":seed,"suite":args.suite,"suite_fingerprint":suite_fingerprint(),
          "calls":len(schedule),"variants":[v.record() for v in variants],
          "models":[v.model for v in variants],"tasks":[t.id for t in tasks],
          "task_domains":{t.id:t.domain for t in tasks},"domain_weights":{d:1/len(domains) for d in domains},
          "scope":"subset" if args.tasks and len(tasks)!=6 else "full",
          "max_turns":args.max_turns,"timeout_seconds":args.timeout,"zdr_enforced":False,
          "tools":"no tool use permitted", "reasoning_effort":"explicit per variant"}
    if previous:
        for key in ("seed","suite","suite_fingerprint","variants","tasks","task_domains","domain_weights","max_turns","timeout_seconds"):
            if previous.get(key)!=plan.get(key): parser.error("resume plan differs in "+key)
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute: return
    binaries={"cmd" if v.harness=="command-code" else "codex" for v in variants}
    for binary in binaries:
        if not shutil.which(binary): parser.error(binary+" not found")
    # Check grading substrate before the first paid call.
    if execute("def solve(x): return x",[1]) != [{"value":1,"mutated":False}]:
        raise RuntimeError("sandbox preflight failed")
    output=args.resume_run or args.output or Path(".runs")/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not previous: output.mkdir(parents=True,exist_ok=False)
    versions={b:version_line(subprocess.run([b]+(["--no-auto-update"] if b=="cmd" else [])+["--version"],
        text=True,capture_output=True,check=True,env=environment()).stdout) for b in sorted(binaries)}
    plan.update({"cli_versions":versions,"created_utc":datetime.now(timezone.utc).isoformat(),
                 "git_commit":subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()})
    if previous:
        if {b:version_line(v) for b,v in previous["cli_versions"].items()}!=versions: parser.error("CLI versions changed during campaign")
        current_commit=plan["git_commit"]
        plan=previous
        plan["cli_versions"]=versions
        plan["adapter_commits"]=list(dict.fromkeys(plan.get("adapter_commits",[plan["git_commit"]])+[current_commit]))
        rows=json.loads((output/"results.json").read_text())
        (output/f"results.before-resume-{datetime.now(timezone.utc).strftime('%H%M%S')}.json").write_text(json.dumps(rows,indent=2))
    else: rows=[]
    (output/"manifest.json").write_text(json.dumps(plan,indent=2))
    recorded=len(rows)
    if recorded>len(schedule): parser.error("more recorded attempts than scheduled")
    for i,(variant,task) in enumerate(schedule):
        model=variant.model
        print(f"[{i+1}/{len(schedule)}] {variant.id} / {task.id}",flush=True)
        stem=f"{i+1:02}-{variant.harness}-{model.replace('/','_')}-{variant.effort}-{task.id}"
        if i<recorded:
            prior=rows[i]
            if (prior["variant"],prior["task"],prior["prompt_sha256"]) != (variant.id,task.id,hashlib.sha256(task.prompt.encode()).hexdigest()):
                raise ValueError("recorded attempt differs from schedule; refusing another call")
            rc=prior["exit_code"]
            out=(output/f"{stem}.ndjson").read_text()
            print("  Reusing recorded response; no model invocation.",flush=True)
        else:
            if (output/f"{stem}.ndjson").exists():
                raise ValueError("unrecorded raw attempt exists; refusing a possible duplicate call")
            (output/f"{stem}.prompt.txt").write_text(task.prompt)
            rc,out,err=invoke(model,task,args.max_turns,args.timeout,variant.effort,variant.harness)
            (output/f"{stem}.ndjson").write_text(out)
            (output/f"{stem}.stderr.txt").write_text(err)
        row={"model":model,"harness":variant.harness,"effort":variant.effort,"variant":variant.id,
             "task":task.id,"dimension":task.dimension,"domain":task.domain,"exit_code":rc,"artifact_stem":stem,
             "prompt_sha256":hashlib.sha256(task.prompt.encode()).hexdigest()}
        try:
            result,tool_count=parse_result(out) if variant.harness=="command-code" else parse_codex(out)
            row.update({"usage":result.get("usage"),"cli_subtype":result.get("subtype"),"tool_calls":tool_count,
                        "observed_models":result["observed_models"],"observed_efforts":result["observed_efforts"],
                        "identity_source":result["identity_source"]})
            (output/f"{stem}.answer.txt").write_text(result.get("finalText", ""))
            if variant.harness=="command-code" and result["observed_models"] != [model]:
                row.update({"status":"model_identity_unverified","score":None})
            elif variant.harness=="command-code" and result["observed_efforts"] != [variant.effort]:
                row.update({"status":"reasoning_effort_unverified","score":None})
            elif tool_count:
                row.update({"status":"protocol_failure","score":None})
            elif rc==0 and result.get("subtype")=="success":
                row.update(grade(task,result.get("finalText","")))
            else:
                row.update({"status":"infrastructure_or_cli_failure","score":None})
        except ValueError as e:
            row.update({"status":"invalid_cli_output","score":None,"detail":str(e)})
        if i<recorded: rows[i]=row
        else: rows.append(row)
        (output/"results.json").write_text(json.dumps(rows,indent=2))
        print(f"  {row['status']}: {row['score']}",flush=True)
        # Fail fast: no retries or silently substituted models.
        if rc!=0 or row["score"] is None:
            print("Stopped on CLI/infrastructure/protocol failure; no automatic retries.",flush=True)
            break
    print(f"Private artifacts: {output}")


if __name__=="__main__": main()
