"""Strict JSON protocol and macOS OS-sandboxed code execution (fail closed)."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from .tasks import oracle


CHILD = r'''
import contextlib, copy, json, resource, sys
resource.setrlimit(resource.RLIMIT_CPU, (3,3))
resource.setrlimit(resource.RLIMIT_FSIZE, (0,0))
class Sink:
    def write(self, s): return len(s)
    def flush(self): pass
request=json.load(sys.stdin)
scope={}
with contextlib.redirect_stdout(Sink()):
    exec(request["source"],scope)
results=[]
for original in request["cases"]:
    arg=copy.deepcopy(original)
    try:
        with contextlib.redirect_stdout(Sink()):
            value=scope["solve"](arg)
        # Force JSON serializability and prevent aliases from subsequent calls.
        value=json.loads(json.dumps(value, allow_nan=False))
        results.append({"value":value,"mutated":arg!=original})
    except Exception as e:
        results.append({"error":type(e).__name__})
print(json.dumps(results, allow_nan=False))
'''


def execute(source, cases):
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        raise RuntimeError("Code grading requires macOS sandbox-exec; no unsandboxed fallback")
    # Deny network, writes, home reads, and forking further processes. Python
    # and its standard libraries may live in Apple's or Homebrew's directories.
    python = str(Path(sys.executable).resolve())
    profile = '(version 1)(deny default)(allow sysctl-read)(allow process-exec)(allow file-read-metadata)'
    profile += '(allow file-read* (literal "/") (subpath "/System") (subpath "/usr") (subpath "/Library") (subpath "/opt/homebrew") (subpath "/private/var/db") (subpath "/dev"))'
    profile += '(allow file-read* (subpath ' + json.dumps(str(Path(sys.base_prefix).resolve())) + '))'
    proc = subprocess.run(["sandbox-exec", "-p", profile, python, "-I", "-S", "-c", CHILD],
        input=json.dumps({"source":source,"cases":cases}), text=True, capture_output=True,
        timeout=8, cwd="/", env={"PATH":"/usr/bin:/bin", "PYTHONHASHSEED":"0"})
    if proc.returncode:
        raise ValueError("candidate execution failed: " + proc.stderr[-600:])
    return json.loads(proc.stdout)


def grade(task, text):
    try:
        answer = json.loads(text)
        if not isinstance(answer, dict): raise ValueError("expected an object")
    except (ValueError, TypeError) as e:
        return {"score":0.0,"status":"format_error","detail":str(e)}
    if task.rubric:
        from .rubrics import structured
        try: return structured(task,answer)
        except (ValueError,TypeError,KeyError):
            return {"score":0.0,"status":"format_error","detail":"malformed structured answer"}
    if task.cases is None:
        # Lists are intentionally ordered in every response schema.
        ok = json.dumps(answer,sort_keys=True) == json.dumps(task.expected,sort_keys=True)
        return {"score":float(ok),"status":"graded","passed":int(ok),"total":1}
    if set(answer) != {"source"} or not isinstance(answer["source"], str):
        return {"score":0.0,"status":"format_error","detail":"expected source string only"}
    if len(answer["source"])>65536:
        return {"score":0.0,"status":"format_error","detail":"source exceeds 64 KiB"}
    try:
        actual = execute(answer["source"], task.cases)
    except RuntimeError:
        raise  # Platform/setup failure must never become a model zero.
    except (ValueError, subprocess.TimeoutExpired) as e:
        return {"score":0.0,"status":"execution_error","detail":str(e)}
    if not isinstance(actual,list):
        return {"score":0.0,"status":"execution_error","detail":"invalid execution output"}
    expected = [oracle(task.id, case) for case in task.cases]
    checks = [isinstance(a,dict) and not a.get("mutated",True) and
              json.dumps(a.get("value"),sort_keys=True)==json.dumps(e,sort_keys=True)
              for a,e in zip(actual,expected)]
    passed = sum(checks) if len(actual)==len(expected) else 0
    return {"score":passed/len(expected),"status":"graded","passed":passed,"total":len(expected)}
