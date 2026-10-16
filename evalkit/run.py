"""Bounded paired CLI runs. Private artifacts stay under .runs/ by default."""
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
    return result, len(tools)


def invoke(model, task, turns, timeout):
    # Outside the benchmark checkout: generators/oracles are not auto-context.
    with tempfile.TemporaryDirectory(prefix="cc-eval-") as scratch:
        config = Path(scratch)/".commandcode"
        config.mkdir()
        (config/"settings.json").write_text(json.dumps({
            "tasteLearning":False, "permissions":{"deny":["*"]}}))
        process = subprocess.Popen(command(model,turns), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, cwd=scratch, env=environment(), start_new_session=True)
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
    return exit_code,out,err


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="fresh random seed by default; reuse for paired reproduction")
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--tasks", nargs="+", help="subset of task IDs")
    parser.add_argument("--max-turns",type=int,default=1)
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--max-calls",type=int,default=12)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--execute",action="store_true",help="actually spend credits; otherwise print plan")
    args=parser.parse_args()
    if min(args.max_turns,args.timeout,args.max_calls)<1: parser.error("limits must be positive")
    if len(set(args.models))!=len(args.models): parser.error("duplicate model")
    seed=args.seed if args.seed is not None else secrets.randbits(64)
    tasks=suite(seed)
    if args.tasks:
        if set(args.tasks)-{t.id for t in tasks}: parser.error("unknown task")
        tasks=[t for t in tasks if t.id in args.tasks]
    # Alternate A/B then B/A; one fresh session per model/task. Same prompt bytes.
    schedule=[(m,t) for i,t in enumerate(tasks) for m in (args.models if i%2==0 else args.models[::-1])]
    if len(schedule)>args.max_calls: parser.error("call count exceeds --max-calls; no partial run")
    plan={"seed":seed,"calls":len(schedule),"models":args.models,"tasks":[t.id for t in tasks],
          "max_turns":args.max_turns,"timeout_seconds":args.timeout,"zdr_enforced":False,
          "tools":"denied", "reasoning_effort":"CLI/provider defaults (not forced)"}
    print(json.dumps(plan,indent=2),flush=True)
    if not args.execute: return
    if not shutil.which("cmd"): parser.error("cmd not found")
    # Check grading substrate before the first paid call.
    if execute("def solve(x): return x",[1]) != [{"value":1,"mutated":False}]:
        raise RuntimeError("sandbox preflight failed")
    output=args.output or Path(".runs")/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output.mkdir(parents=True,exist_ok=False)
    version=subprocess.run(["cmd","--version"],text=True,capture_output=True,check=True).stdout.strip()
    plan.update({"cli_version":version,"created_utc":datetime.now(timezone.utc).isoformat(),
                 "git_commit":subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()})
    (output/"manifest.json").write_text(json.dumps(plan,indent=2))
    rows=[]
    for i,(model,task) in enumerate(schedule):
        print(f"[{i+1}/{len(schedule)}] {model} / {task.id}",flush=True)
        stem=f"{i+1:02}-{model.replace('/','_')}-{task.id}"
        (output/f"{stem}.prompt.txt").write_text(task.prompt)
        rc,out,err=invoke(model,task,args.max_turns,args.timeout)
        (output/f"{stem}.ndjson").write_text(out)
        (output/f"{stem}.stderr.txt").write_text(err)
        row={"model":model,"task":task.id,"dimension":task.dimension,"exit_code":rc,
             "prompt_sha256":hashlib.sha256(task.prompt.encode()).hexdigest()}
        try:
            result,tool_count=parse_result(out)
            row.update({"usage":result.get("usage"),"cli_subtype":result.get("subtype"),"tool_calls":tool_count,
                        "observed_models":result["observed_models"]})
            (output/f"{stem}.answer.txt").write_text(result.get("finalText", ""))
            if result["observed_models"] != [model]:
                row.update({"status":"model_identity_unverified","score":None})
            elif tool_count:
                row.update({"status":"protocol_failure","score":None})
            elif rc==0 and result.get("subtype")=="success":
                row.update(grade(task,result.get("finalText","")))
            else:
                row.update({"status":"infrastructure_or_cli_failure","score":None})
        except ValueError as e:
            row.update({"status":"invalid_cli_output","score":None,"detail":str(e)})
        rows.append(row)
        (output/"results.json").write_text(json.dumps(rows,indent=2))
        print(f"  {row['status']}: {row['score']}",flush=True)
        # Fail fast: no retries or silently substituted models.
        if rc!=0 or row["score"] is None:
            print("Stopped on CLI/infrastructure/protocol failure; no automatic retries.",flush=True)
            break
    print(f"Private artifacts: {output}")


if __name__=="__main__": main()
