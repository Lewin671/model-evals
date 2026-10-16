"""Execute candidate repositories in a macOS sandbox; keep the oracle outside it."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .importer import scenarios

DRIVER=r'''
import contextlib,io,json,resource,sys
resource.setrlimit(resource.RLIMIT_CPU,(3,3))
resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
request=json.load(sys.stdin)
sys.path.insert(0,request["root"])
class Sink:
    def write(self,s): return len(s)
    def flush(self): pass
with contextlib.redirect_stdout(Sink()):
    from ledger import Ingestor,import_csv
    obj=Ingestor(request["db"])
out=[]
for operation in request["ops"]:
    try:
        with contextlib.redirect_stdout(Sink()):
            kind=operation["op"]
            if kind=="feed":
                value=obj.feed(operation["stream"],operation["delivery"],operation["text"],operation["final"])
            elif kind=="restart":
                obj=Ingestor(request["db"]);value=None
            elif kind=="legacy":
                value=import_csv(request["db"],operation["text"])
                obj=Ingestor(request["db"])
            else: value=None
            state={"records":obj.records(),"summary":obj.summary()}
        out.append({"result":value,"state":state})
    except Exception as exc:
        out.append({"error":type(exc).__name__})
with contextlib.redirect_stdout(Sink()):
    final={"records":obj.records(),"summary":obj.summary()}
print(json.dumps({"events":out,"state":final},allow_nan=False))
'''


def execute(root,ops):
    if sys.platform!="darwin" or not shutil.which("sandbox-exec"):
        raise RuntimeError("Workflow grading requires macOS sandbox-exec; no unsafe fallback")
    with tempfile.TemporaryDirectory(prefix="importer-state-") as scratch:
        allowed=["/System","/usr","/Library","/opt/homebrew","/private/var/db","/dev",
                 str(Path(sys.base_prefix).resolve()),str(root.resolve()),str(Path(scratch).resolve())]
        profile='(version 1)(deny default)(allow sysctl-read)(allow process-exec)(allow file-read-metadata)'
        profile+='(allow file-read* (literal "/") '+" ".join('(subpath '+json.dumps(p)+')' for p in allowed)+')'
        profile+='(allow file-write* (subpath '+json.dumps(str(Path(scratch).resolve()))+'))'
        proc=subprocess.run(["sandbox-exec","-p",profile,str(Path(sys.executable).resolve()),"-I","-S","-B","-c",DRIVER],
            input=json.dumps({"root":str(root.resolve()),"db":str(Path(scratch)/"state.json"),"ops":ops}),
            text=True,capture_output=True,timeout=8,cwd="/",env={"PATH":"/usr/bin:/bin"})
        if proc.returncode: raise ValueError("candidate process failed (exit "+str(proc.returncode)+")")
        return json.loads(proc.stdout)


def same(a,b): return json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True)


def check_case(root,case,reveal=False):
    try: actual=execute(root,case["ops"])
    except RuntimeError: raise
    except (ValueError,subprocess.TimeoutExpired):
        return {"passed":False,"reason":"candidate execution failed"}
    if not isinstance(actual,dict) or len(actual.get("events",[]))!=len(case["ops"]):
        return {"passed":False,"reason":"invalid candidate results"}
    def verdict(passed,reason):
        result={"passed":passed,"reason":reason}
        if reveal:result["observed"]=actual
        return result
    for i,event in enumerate(actual["events"]):
        if i in case["error_indices"]:
            if event.get("error")!="ValueError":return verdict(False,f"operation {i}: expected ValueError")
        elif "error" in event:
            return verdict(False,f"operation {i}: unexpected {event['error']}")
        if i in case["accepted"] and not same(event.get("result"),case["accepted"][i]):
            return verdict(False,f"operation {i}: wrong accepted revision count")
        if i in case["snapshots"] and not same(event.get("state"),case["snapshots"][i]):
            return verdict(False,f"operation {i}: incorrect intermediate records/report")
    if not same(actual.get("state"),case["expected"]):return verdict(False,"incorrect final records/report")
    return verdict(True,"verified API outputs")


def evaluate(root,seed,variant,public=False,change=True):
    results=[]
    for case in scenarios(seed,variant,public=public,change=change):
        result=dict(check_case(root,case,reveal=public),name=case["name"],tier=case["tier"])
        if public:result["test_fixture"]={k:v for k,v in case.items() if k not in ("name","tier")}
        results.append(result)
    tiers={}
    for tier in (1,2,3):
        subset=[r for r in results if r["tier"]==tier]
        if subset:tiers[f"L{tier}"]={"passed":sum(r["passed"] for r in subset),"total":len(subset)}
    passed=sum(r["passed"] for r in results)
    return {"passed":passed,"total":len(results),"fraction":passed/len(results),"tiers":tiers,"cases":results}
