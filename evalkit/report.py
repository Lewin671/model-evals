"""Publish model/effort results, a scorecard, and optionally reviewed answers."""
import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re

USAGE_FIELDS=("inputTokens","outputTokens","cacheReadTokens","cacheWriteTokens","reasoningTokens")
ROW_FIELDS=("model","harness","effort","variant","task","dimension","status","score","passed","total",
            "exit_code","prompt_sha256","observed_models","observed_efforts","identity_source")
MANIFEST_FIELDS=("seed","suite","suite_fingerprint","variants","models","tasks","cli_versions","cli_version",
                 "git_commit","zdr_enforced","max_turns","timeout_seconds","reasoning_effort","tools")
START="<!-- RESULTS:START -->"
END="<!-- RESULTS:END -->"


def identity(row):
    return row.get("variant",f"{row.get('harness','command-code')}:{row['model']}@{row.get('effort','unspecified')}")


def prepare(directories):
    manifests=[]
    safe=[]
    seen=set()
    artifacts=[]
    for directory in directories:
        manifest=json.loads((directory/"manifest.json").read_text())
        if manifests:
            for key in ("seed","suite","suite_fingerprint","tasks"):
                if manifest.get(key)!=manifests[0].get(key):
                    raise ValueError("cannot combine runs with different "+key)
        manifests.append({k:manifest[k] for k in MANIFEST_FIELDS if k in manifest})
        for row in json.loads((directory/"results.json").read_text()):
            key=(identity(row),row["task"])
            if key in seen: raise ValueError("duplicate model/effort/task; do not cherry-pick attempts")
            seen.add(key)
            item={k:row[k] for k in ROW_FIELDS if k in row}
            item["variant"]=identity(row)
            item.setdefault("harness","command-code")
            item.setdefault("effort","unspecified")
            item["usage"]={k:v for k,v in (row.get("usage") or {}).items()
                           if k in USAGE_FIELDS and type(v) in (int,float)}
            safe.append(item)
            artifacts.append((directory,row))
    hashes={}
    for row in safe:
        if row.get("prompt_sha256"):
            previous=hashes.setdefault(row["task"],row["prompt_sha256"])
            if previous!=row["prompt_sha256"]: raise ValueError("different prompts for same task")
    variants=[]
    for m in manifests:
        variants.extend(m.get("variants",[{"harness":"command-code","model":model,"effort":"unspecified"}
                                           for model in m["models"]]))
    variant_map={identity(v):v for v in variants}
    aggregates=[]
    for key,v in variant_map.items():
        subset=[r for r in safe if r["variant"]==key]
        graded=[r for r in subset if r.get("score") is not None]
        task_ids=[r["task"] for r in graded]
        complete=len(task_ids)==len(manifests[0]["tasks"]) and set(task_ids)==set(manifests[0]["tasks"])
        usage={k:sum(r["usage"].get(k,0) for r in subset) for k in USAGE_FIELDS if any(k in r["usage"] for r in subset)}
        aggregates.append({"variant":key,"model":v["model"],"harness":v["harness"],"effort":v["effort"],
            "score":sum(r["score"] for r in graded)/len(graded) if complete else None,
            "graded":len(graded),"tasks":len(manifests[0]["tasks"]),"usage":usage,
            "format_failures":sum(r["status"]=="format_error" for r in subset),
            "full_passes":sum(r.get("score")==1 for r in graded)})
    return {"runs":manifests,"results":safe,"aggregates":aggregates},artifacts


def percent(value):
    return "—" if value is None else f"{100*value:.1f}%"


def leaderboard(data):
    lines=["| Model | Reasoning effort | Source | Score | Full passes | Input / output tokens |",
           "|:--|:--|:--|--:|--:|--:|"]
    ordered=sorted(data["aggregates"],key=lambda r:-(r["score"] if r["score"] is not None else -1))
    for a in ordered:
        u=a["usage"]
        tokens=f"{u['inputTokens']:,} / {u['outputTokens']:,}" if {"inputTokens","outputTokens"}<=u.keys() else "—"
        coverage=f"{a['full_passes']}/{a['tasks']}" if a["score"] is not None else f"incomplete ({a['graded']}/{a['tasks']})"
        lines.append(f"| `{a['model']}` | `{a['effort']}` | {a['harness']} | **{percent(a['score'])}** | {coverage} | {tokens} |")
    return "\n".join(lines)


def markdown(data):
    first=data["runs"][0]
    lines=["# Model evaluation results", "",f"**Suite:** `{first.get('suite','micro-v1')}` · **Seed:** `{first['seed']}` · **Attempts:** 1 per task/configuration", "",
           leaderboard(data), "", "Equal task weights. A missing or failed infrastructure run receives no aggregate score.",
           "Token accounting is CLI-reported; cache and reasoning counters differ between providers. No dollar costs are inferred.",
           "", "## Task breakdown", "", "| Model | Effort | Source | Task | Score | Checks | Status |", "|:--|:--|:--|:--|--:|--:|:--|"]
    for r in data["results"]:
        checks=f"{r['passed']}/{r['total']}" if "passed" in r else "—"
        lines.append(f"| `{r['model']}` | {r['effort']} | {r['harness']} | {r['task']} | {percent(r.get('score'))} | {checks} | {r['status']} |")
    lines += ["", "## Reproducibility", "", "| Run | Commit | CLI versions |", "|:--|:--|:--|"]
    for i,m in enumerate(data["runs"],1):
        versions=m.get("cli_versions",{"cmd":m.get("cli_version","unknown")})
        lines.append(f"| {i} | `{m['git_commit']}` | {escape(json.dumps(versions,sort_keys=True))} |")
    lines += ["",f"Suite fingerprint: `{first.get('suite_fingerprint','not recorded')}`.",
              "", "Command Code model/effort identity is checked against request events. Codex JSONL does not expose those fields;",
              "Codex entries report the explicitly configured model/effort, not an independently verified upstream identity.",
              "Command Code ZDR enforcement is disabled only in evaluation child processes; this setting does not control Codex retention.",
              "", "Six tasks are a screening sample, not a statistically established general ranking. A tied score is a tie on this suite.",
              "Code cases within one task are correlated. Different harnesses remain a confound even with identical prompts and effort labels.", ""]
    return "\n".join(lines)


def scorecard(data):
    tasks=data["runs"][0]["tasks"]
    aggregates=data["aggregates"]
    width=1080
    height=155+len(aggregates)*74
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
         '<title id="title">Model evaluation scorecard</title>',
         '<desc id="desc">Scores by model, reasoning effort and task. Missing results are shown as dashes.</desc>',
         f'<rect width="{width}" height="{height}" rx="16" fill="#10151d"/>',
         '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" fill="#e8edf5">',
         '<text x="28" y="38" font-size="20" font-weight="600">MODEL EVALS</text>',
         '<text x="28" y="64" fill="#9ba8ba" font-size="13">micro-v1 · one attempt · equal task weights · higher is better</text>']
    labels={"config-merge":"Merge","reservation-ledger":"State","snapshot-pagination":"Repair",
            "security-triage":"Security","evidence-reconciliation":"Evidence","release-selection":"Planning"}
    for j,t in enumerate(tasks):
        svg.append(f'<text x="{421+j*92}" y="104" font-size="12" text-anchor="middle" fill="#aab8c9">{escape(labels.get(t,t))}</text>')
    svg.append('<text x="1008" y="104" font-size="12" text-anchor="middle" fill="#aab8c9">Overall</text>')
    for i,a in enumerate(aggregates):
        y=122+i*74
        svg += [f'<text x="28" y="{y+21}" font-size="14" font-weight="600">{escape(a["model"])}</text>',
                f'<text x="28" y="{y+43}" font-size="12" fill="#9ba8ba">{escape(a["effort"])} effort · {escape(a["harness"])}</text>']
        for j,t in enumerate(tasks):
            row=next((r for r in data["results"] if r["variant"]==a["variant"] and r["task"]==t),{})
            val=row.get("score")
            color="#243040" if val is None else ("#155b4d" if val==1 else "#704b23" if val>0 else "#713742")
            x=381+j*92
            svg += [f'<rect x="{x}" y="{y}" width="80" height="49" rx="7" fill="{color}"/>',
                    f'<text x="{x+40}" y="{y+30}" text-anchor="middle" font-size="14">{percent(val)}</text>']
        svg.append(f'<text x="1008" y="{y+31}" text-anchor="middle" font-size="18" font-weight="600">{percent(a["score"])}</text>')
    return "\n".join(svg+["</g></svg>"])


def render(directory):
    data,_=prepare([directory])
    return markdown(data),data


def reviewed_answers(artifacts):
    lines=["# Model responses", "", "Synthetic task prompts and final responses. Raw CLI transcripts are excluded.", ""]
    for directory,row in artifacts:
        stem=row.get("artifact_stem")
        if not stem: raise ValueError("run has no answer artifact mapping")
        prompt=(directory/f"{stem}.prompt.txt").read_text()
        answer=(directory/f"{stem}.answer.txt").read_text()
        if hashlib.sha256(prompt.encode()).hexdigest()!=row["prompt_sha256"]: raise ValueError("prompt hash mismatch")
        if re.search(r"/Users/|sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}",prompt+answer):
            raise ValueError("possible private data in answer export; inspect locally")
        fence="`"*max(4,max((len(m.group())+1 for m in re.finditer(r"`+",prompt+answer)),default=4))
        lines += [f"## {row['model']} · {row.get('effort','unspecified')} · {row['task']}", "",
                  f"Source: {row.get('harness','command-code')} · Score: {percent(row.get('score'))}", "",
                  "<details><summary>Prompt</summary>", "",fence+"text",prompt,fence,"","</details>","",
                  "Response:","",fence+"json",answer,fence,""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs",nargs="+",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--readme",type=Path,help="update marked README results section")
    parser.add_argument("--include-answers",action="store_true",help="export final answers; manually review before git add")
    args=parser.parse_args()
    data,artifacts=prepare(args.runs)
    answer_text=reviewed_answers(artifacts) if args.include_answers else None
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/"report.md").write_text(markdown(data))
    (args.output/"summary.json").write_text(json.dumps(data,indent=2))
    (args.output/"scorecard.svg").write_text(scorecard(data))
    if answer_text is not None: (args.output/"responses.md").write_text(answer_text)
    if args.readme:
        original=args.readme.read_text()
        if original.count(START)!=1 or original.count(END)!=1: raise ValueError("README results markers missing or duplicated")
        relative=Path(os.path.relpath(args.output,args.readme.parent)).as_posix()
        section=f"{START}\n\n{leaderboard(data)}\n\n![Per-task scorecard]({relative}/scorecard.svg)\n\n"
        section+=f"[Full results]({relative}/report.md) · [Machine-readable data]({relative}/summary.json)"
        if answer_text is not None: section+=f" · [Model responses]({relative}/responses.md)"
        section+="\n\nOne attempt per task; screening results, not a general model ranking.\n\n"+END
        args.readme.write_text(original[:original.index(START)]+section+original[original.index(END)+len(END):])
    print(args.output/"report.md")


if __name__=="__main__": main()
