"""General-v2: coding, everyday tasks and structured UI decision snapshots."""
from dataclasses import replace
import itertools
import json
import random

from .tasks import Task, legacy_suite

PREFIX="Do not use real tools, files, browser, or desktop. All task data is below. Return ONLY one JSON object, without Markdown. "


def schedule_valid(data, entries):
    jobs={j["id"]:j for j in data["jobs"]}
    if not isinstance(entries,list): return False
    used=set();intervals=[]
    for e in entries:
        if not isinstance(e,dict) or set(e)!={"id","start"}: return False
        if e["id"] not in jobs or e["id"] in used or type(e["start"]) is not int: return False
        j=jobs[e["id"]]
        if e["start"] not in j["allowed_starts"]: return False
        interval=(e["start"],e["start"]+j["duration"])
        if interval[0]<data["window"][0] or interval[1]>data["window"][1]: return False
        if any(interval[0]<end and start<interval[1] for start,end in data["busy"]): return False
        used.add(e["id"]);intervals.append(interval)
    # Recovery buffer is needed between scheduled jobs, but not next to busy slots.
    intervals.sort()
    return all(b[0]-a[1]>=data["buffer"] for a,b in zip(intervals,intervals[1:]))


def optimal_schedule(data):
    best=-1;answer=[]
    choices=[[None]+j["allowed_starts"] for j in data["jobs"]]
    for starts in itertools.product(*choices):
        entries=[{"id":j["id"],"start":s} for j,s in zip(data["jobs"],starts) if s is not None]
        if not schedule_valid(data,entries): continue
        value=sum(j["priority"] for j,s in zip(data["jobs"],starts) if s is not None)
        if value>best: best=value;answer=entries
    return best,answer


def expense_answer(records):
    latest={}
    for r in records:
        if r["id"] not in latest or r["revision"]>latest[r["id"]]["revision"]: latest[r["id"]]=r
    included=[];excluded=[];missing=[];total=0
    for key,r in sorted(latest.items()):
        if r["status"]!="approved": excluded.append(key)
        elif r["currency"]!="USD": excluded.append(key);missing.append(key)
        else: included.append(key);total+=r["amount_cents"]
    return {"total_cents":total,"included_ids":included,"excluded_ids":excluded,"needs_exchange_rate":missing}


def browser_task(rng):
    ids=iter(f"n{x}" for x in rng.sample(range(1000,9999),25))
    cases=[];rules=[];references=[]
    case_ids=iter(rng.sample(range(10000,99999),6))
    def add(goal,observation,allowed):
        cid=f"b{next(case_ids)}"
        cases.append({"case_id":cid,"goal":goal,"observation":observation})
        rules.append({"case_id":cid,"allowed":allowed})
        references.append(dict(allowed[0],case_id=cid))
    good,expensive,out_of_stock,wrong_size,shipping_trap=[next(ids) for _ in range(5)]
    budget=rng.randrange(70,100)
    add(f"Open the cheapest in-stock jacket in size M, including shipping, with a total at most ${budget}.",
        {"nodes":[{"id":expensive,"role":"link","product":"Wind jacket","size":"M","price":budget+9,"shipping":0,"in_stock":True},
                  {"id":out_of_stock,"role":"link","product":"Rain jacket","size":"M","price":budget-40,"shipping":0,"in_stock":False},
                  {"id":shipping_trap,"role":"link","product":"Shell jacket","size":"M","price":budget-25,"shipping":20,"in_stock":True},
                  {"id":wrong_size,"role":"link","product":"Light jacket","size":"S","price":budget-45,"shipping":0,"in_stock":True},
                  {"id":good,"role":"link","product":"Trail jacket","size":"M","price":budget-20,"shipping":5,"in_stock":True}]},
        [{"op":"click","target":good}])
    apply,old_result,select=next(ids),next(ids),next(ids)
    add("Set the category to Packs and view the matching results.",
        {"applied_category":"All","draft_category":"Packs","results_belong_to":"All",
         "nodes":[{"id":select,"role":"combobox","value":"Packs"},{"id":apply,"role":"button","name":"Apply filters","enabled":True},
                  {"id":old_result,"role":"link","name":"Popular pack"}]},[{"op":"click","target":apply}])
    close,later,behind=next(ids),next(ids),next(ids)
    add("Open order history.",
        {"modal":{"nodes":[{"id":close,"role":"button","name":"Close"},{"id":later,"role":"button","name":"Not now"}]},
         "background_nodes":[{"id":behind,"role":"link","name":"Order history","occluded":True}]},
        [{"op":"click","target":close},{"op":"click","target":later}])
    stale=next(ids)
    add("Change the delivery date to 20 October.",
        {"last_action_error":"stale element after navigation","current_dom_available":False,
         "previous_nodes":[{"id":stale,"role":"button","name":"Choose date","stale":True}]},[{"op":"observe"}])
    save,field=next(ids),next(ids)
    name=f"Workspace {rng.randrange(100,999)}"
    add(f"Save the display name '{name}'.",
        {"saved":False,"nodes":[{"id":field,"role":"textbox","value":name},
                                  {"id":save,"role":"button","name":"Save changes","enabled":True}]},
        [{"op":"click","target":save}])
    add(f"Save the display name '{name}'.",
        {"busy":False,"server_confirmation":"Changes saved","display_name":name,"dirty":False},[{"op":"finish"}])
    rng.shuffle(cases)
    prompt=PREFIX+'Return {"actions":[{"case_id":"...","op":"click","target":"visible node ID"}, ...]}. '
    prompt+='Each case is an INDEPENDENT browser checkpoint. Return exactly ONE next action for each case, in any order. '
    prompt+='Allowed actions: click(target), observe() to obtain fresh DOM, wait() while work is in progress, finish() only when completion is supported. '
    prompt+='For observe/wait/finish omit target. Use no real tools. Select a visible, current, unblocked node; do not invent IDs. '
    return Task("browser-snapshots","DOM grounding and workflow decisions",prompt+json.dumps(cases),
        expected={"actions":references},domain="browser",rubric={"kind":"actions","checks":rules})


def desktop_task(rng):
    ids=iter(f"w{x}" for x in rng.sample(range(1000,9999),25))
    cases=[];rules=[];references=[]
    case_ids=iter(rng.sample(range(10000,99999),6))
    def add(goal,observation,allowed=None,box=None):
        cid=f"d{next(case_ids)}"
        cases.append({"case_id":cid,"goal":goal,"observation":observation})
        rule={"case_id":cid}
        if box:
            rule["box"]=box
            reference={"op":"click","x":(box[0]+box[2])/2,"y":(box[1]+box[3])/2}
        else: rule["allowed"]=allowed;reference=allowed[0]
        rules.append(rule);references.append(dict(reference,case_id=cid))
    intended,other=next(ids),next(ids)
    add("Add 'Follow up next Monday' to the Notes document.",
        {"focused_window":other,"windows":[{"id":other,"app":"Spreadsheet","document":"Budget"},
         {"id":intended,"app":"Text editor","document":"Notes"}]},[{"op":"focus","target":intended}])
    filename=next(ids);wanted=f"meeting-{rng.randrange(100,999)}.txt"
    add(f"Save a new copy named '{wanted}'.",
        {"active_dialog":"Save as","focused_control":filename,"controls":[{"id":filename,"role":"textbox","name":"Filename","value":"Untitled.txt"}]},
        [{"op":"replace_text","target":filename,"value":wanted}])
    ox,oy=rng.randrange(80,180),rng.randrange(40,120)
    x,y,w,h=rng.randrange(380,580),rng.randrange(250,380),120,40
    box=[ox+x,oy+y,ox+x+w,oy+y+h]
    add("Click Export CSV, keeping the click at least 3 logical pixels inside its boundary.",
        {"coordinate_system":"global logical pixels","window_origin":[ox,oy],"device_pixel_ratio":2,
         "bounds_format":"window-local [x,y,width,height] in logical pixels",
         "controls":[{"name":"Export CSV","bounds":[x,y,w,h],"enabled":True},
                     {"name":"Export PDF","bounds":[x,y+55,w,h],"enabled":True}]},box=box)
    save,discard,cancel,background=next(ids),next(ids),next(ids),next(ids)
    add("Open the other document, preserving the current unsaved edits. Resolve the modal before proceeding.",
        {"modal":{"name":"Save changes?","controls":[{"id":save,"role":"button","name":"Save"},
         {"id":discard,"role":"button","name":"Don't save"},{"id":cancel,"role":"button","name":"Cancel"}]},
         "background_controls":[{"id":background,"name":"Open document","occluded":True}]},[{"op":"click","target":save}])
    add("Copy all four selected files to the destination folder.",
        {"files_copied":1,"files_total":4,"current_file_progress_percent":100,"overall_status":"Copying","done":False},
        [{"op":"observe"},{"op":"wait"}])
    add("Continue exporting the current document.",
        {"last_screenshot_version":17,"window_event_version":18,"last_event":"window resized; layout changed",
         "old_export_button_center":[720,500],"current_screenshot_available":False},[{"op":"observe"}])
    rng.shuffle(cases)
    prompt=PREFIX+'Return {"actions":[{"case_id":"...","op":"...", ...}, ...]}. '
    prompt+='These are INDEPENDENT structured desktop checkpoints, not images. Return exactly ONE next action per case, in any order. '
    prompt+='Actions: focus(target window ID), replace_text(target control ID,value) replacing its full contents, click(target control ID), '
    prompt+='click(x,y) for coordinate-only screens, observe() to get current state/screenshot, wait(), finish(). '
    prompt+='Omit unused fields. Coordinates are global LOGICAL pixels; do not multiply by device pixel ratio. Use the current focused/modal state. '
    return Task("desktop-snapshots","focus, dialogs and coordinate frames",prompt+json.dumps(cases),
        expected={"actions":references},domain="computer",rubric={"kind":"actions","checks":rules})


def build(seed):
    rng=random.Random(seed ^ 0xA93D)
    old=legacy_suite(seed)
    tasks=[replace(old[0],domain="coding"),replace(old[2],domain="coding")]
    job_ids=[f"task-{i}" for i in rng.sample(range(100,999),5)]
    jobs=[{"id":key,"duration":rng.choice([15,30]),"priority":rng.randrange(2,10),
           "allowed_starts":sorted(rng.sample(list(range(540,721,15)),3))} for key in job_ids]
    data={"jobs":jobs,"busy":[[600,630],[690,705]],"buffer":15,"window":[540,750]}
    best,chosen=optimal_schedule(data)
    answer={"schedule":chosen,"unscheduled":sorted(set(job_ids)-{e["id"] for e in chosen})}
    prompt=PREFIX+'Return {"schedule":[{"id":"task ID","start":integer minutes after midnight}],"unscheduled":[sorted IDs]}. '
    prompt+='Plan 09:00–12:30. Each job is optional, can be scheduled at most once, and MUST start at one of its allowed_starts. '
    prompt+='Jobs and fixed busy intervals may touch but must not overlap. Leave at least buffer minutes between scheduled jobs; '
    prompt+='that buffer is NOT required next to fixed busy intervals. Maximize SUM of priorities, not job count. Any optimal schedule is accepted. '
    prompt+='List every omitted job in unscheduled. Intervals are half-open [start,end); durations are minutes. Data: '
    tasks.append(Task("morning-planner","constraint following and useful planning",prompt+json.dumps(data),expected=answer,domain="everyday",
                      rubric={"kind":"schedule","data":data,"best":best}))
    names=[f"INV-{n}" for n in rng.sample(range(1000,9999),5)]
    amounts=[rng.randrange(900,9800) for _ in names]
    records=[{"id":key,"revision":1,"status":"approved","currency":"USD","amount_cents":value} for key,value in zip(names,amounts)]
    records[1]["status"]="pending"
    records[2]["currency"]="EUR"
    records[3]["amount_cents"]=-amounts[3]
    revised=dict(records[0],revision=2,amount_cents=amounts[0]+rng.randrange(100,600))
    records += [revised,dict(revised),dict(records[4],revision=2,status="rejected")]
    rng.shuffle(records)
    prompt=PREFIX+'Return {"total_cents":integer,"included_ids":[sorted IDs],"excluded_ids":[sorted IDs],"needs_exchange_rate":[sorted IDs]}. '
    prompt+='Reconcile reimbursement records. For each invoice ID use only its highest revision; repeated identical copies count once. '
    prompt+='Include only approved USD records. Negative amounts are credits and must be subtracted, not ignored. Amounts already include tax; add no tax. '
    prompt+='Exclude pending/rejected records. Exclude approved non-USD records and list them in needs_exchange_rate because no rate is provided. '
    prompt+='Every latest invoice belongs to exactly one of included_ids/excluded_ids; needs_exchange_rate is a subset of excluded_ids. Records: '
    tasks.append(Task("expense-reconciliation","deduplication, updates and arithmetic",prompt+json.dumps(records),
                      expected=expense_answer(records),domain="everyday",rubric={"kind":"fields"}))
    tasks += [browser_task(rng),desktop_task(rng)]
    return tasks
