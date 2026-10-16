"""Bounded file tools and tolerant response decoding; no shell/network tool."""
import json
from pathlib import Path

from .checker import evaluate
from .importer import sources

WRITABLE={"ledger/parser.py","ledger/store.py","ledger/api.py"}


def decode(text):
    normalizations=[]
    value=text.strip()
    if value.startswith("```") and value.endswith("```"):
        value=value.split("\n",1)[1].rsplit("```",1)[0].strip();normalizations.append("markdown fence")
    answer=json.loads(value)
    if isinstance(answer,list) and len(answer)==1 and isinstance(answer[0],dict):
        answer=answer[0];normalizations.append("singleton array")
    if not isinstance(answer,dict) or not isinstance(answer.get("actions"),list):
        raise ValueError("Return an object containing actions list")
    if not 1<=len(answer["actions"])<=6:raise ValueError("Use between 1 and 6 actions per response")
    return answer["actions"],normalizations


def perform(root,actions,seed,variant,change):
    observations=[];finished=False
    readable=set(sources(variant))
    for action in actions:
        try:
            if not isinstance(action,dict):raise ValueError("action must be an object")
            tool=action.get("tool")
            if tool=="read":
                paths=action["paths"]
                if not isinstance(paths,list) or any(p not in readable for p in paths):raise ValueError("unknown readable path")
                observations.append({"tool":"read","files":{p:(root/p).read_text() for p in paths}})
            elif tool=="write":
                files=action["files"]
                if not isinstance(files,dict) or not files or not set(files)<=WRITABLE:raise ValueError("only the three source files are writable")
                if any(not isinstance(v,str) or len(v)>24000 for v in files.values()):raise ValueError("file contents must be strings of at most 24000 characters")
                for path,text in files.items():(root/path).write_text(text)
                observations.append({"tool":"write","saved":list(files)})
            elif tool=="test":
                observations.append({"tool":"test","public_checks":evaluate(root,seed,variant,public=True,change=change)})
            elif tool=="finish":
                observations.append({"tool":"finish","acknowledged":True});finished=True;break
            else:raise ValueError("Unknown tool; use read, write, test or finish")
        except (ValueError,KeyError,TypeError) as exc:
            observations.append({"tool":action.get("tool") if isinstance(action,dict) else None,"error":str(exc)})
    return observations,finished
