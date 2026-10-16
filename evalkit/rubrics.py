"""Deterministic acceptance of equivalent schedules, actions and click points."""
import json
import math

from .general import schedule_valid


def canonical(value): return json.dumps(value,sort_keys=True,allow_nan=False)


def result(checks):
    return {"status":"graded","score":sum(checks)/len(checks),"passed":sum(checks),"total":len(checks),"checks":checks}


def structured(task,answer):
    kind=task.rubric["kind"]
    if kind=="fields":
        if set(answer)!=set(task.expected): return {"score":0.0,"status":"format_error","detail":"incorrect fields"}
        fields={k:canonical(answer[k])==canonical(v) for k,v in task.expected.items()}
        return dict(result(list(fields.values())),field_results=fields)
    if kind=="schedule":
        data=task.rubric["data"]
        if set(answer)!={"schedule","unscheduled"} or not schedule_valid(data,answer["schedule"]):
            return {"score":0.0,"status":"graded","passed":0,"total":1,"detail":"infeasible or malformed schedule"}
        selected={e["id"] for e in answer["schedule"]}
        all_ids={j["id"] for j in data["jobs"]}
        if answer["unscheduled"]!=sorted(all_ids-selected):
            return {"score":0.0,"status":"graded","passed":0,"total":1,"detail":"incorrect omitted-task accounting"}
        value=sum(j["priority"] for j in data["jobs"] if j["id"] in selected)
        best=task.rubric["best"]
        return {"status":"graded","score":value/best if best else 1.0,"selected_priority":value,
                "optimal_priority":best,"feasible":True}
    if set(answer)!={"actions"} or not isinstance(answer["actions"],list):
        return {"score":0.0,"status":"format_error","detail":"expected actions list"}
    actions={};duplicate=set()
    for action in answer["actions"]:
        if not isinstance(action,dict) or not isinstance(action.get("case_id"),str): continue
        cid=action["case_id"]
        if cid in actions: duplicate.add(cid)
        actions[cid]={k:v for k,v in action.items() if k!="case_id"}
    valid_ids={r["case_id"] for r in task.rubric["checks"]}
    if set(actions)-valid_ids: return {"score":0.0,"status":"format_error","detail":"invented checkpoint ID"}
    checks=[]
    for rule in task.rubric["checks"]:
        action=actions.get(rule["case_id"])
        ok=action is not None and rule["case_id"] not in duplicate
        if ok and "allowed" in rule:
            ok=any(canonical(action)==canonical(a) for a in rule["allowed"])
        elif ok:
            box=rule["box"]
            ok=set(action)=={"op","x","y"} and action["op"]=="click"
            if ok:
                x,y=action["x"],action["y"]
                ok=type(x) in (int,float) and type(y) in (int,float) and math.isfinite(x) and math.isfinite(y)
                if ok: ok=box[0]+3<=x<=box[2]-3 and box[1]+3<=y<=box[3]-3
        checks.append(bool(ok))
    return dict(result(checks),case_results={r["case_id"]:ok for r,ok in zip(task.rubric["checks"],checks)})
