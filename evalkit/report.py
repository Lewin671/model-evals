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
            "exit_code","prompt_sha256","observed_models","observed_efforts","identity_source",
            "score_before_adjudication","adjudication","domain","case_results","field_results",
            "selected_priority","optimal_priority","feasible")
MANIFEST_FIELDS=("seed","suite","suite_fingerprint","variants","models","tasks","cli_versions","cli_version",
                 "git_commit","adapter_commits","acquisition_notes","grading_fingerprint","ground_truth_revision",
                 "adjudication_commit","zdr_enforced","max_turns","timeout_seconds","reasoning_effort","tools",
                 "task_domains","domain_weights","scope")
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
            for key in ("seed","suite","suite_fingerprint","grading_fingerprint","ground_truth_revision","tasks","task_domains","domain_weights"):
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
        domain_scores={}
        mapping=manifests[0].get("task_domains",{})
        if complete and mapping:
            for domain in manifests[0]["domain_weights"]:
                values=[r["score"] for r in graded if mapping[r["task"]]==domain]
                domain_scores[domain]=sum(values)/len(values)
            overall=sum(domain_scores[d]*w for d,w in manifests[0]["domain_weights"].items())
        else: overall=sum(r["score"] for r in graded)/len(graded) if complete else None
        aggregates.append({"variant":key,"model":v["model"],"harness":v["harness"],"effort":v["effort"],
            "score":overall,"domain_scores":domain_scores,
            "graded":len(graded),"tasks":len(manifests[0]["tasks"]),"usage":usage,
            "format_failures":sum(r["status"]=="format_error" for r in subset),
            "full_passes":sum(r.get("score")==1 for r in graded)})
    return {"runs":manifests,"results":safe,"aggregates":aggregates},artifacts


def percent(value):
    return "—" if value is None else f"{100*value:.1f}%"


def source_label(harness):
    return {"codex":"Codex","command-code":"Command Code"}.get(harness,harness)


DOMAIN_LABELS={"coding":"Coding","everyday":"Everyday","browser":"Browser (sim.)","computer":"Desktop (sim.)"}


def domain_table(data):
    domains=list(data["runs"][0].get("domain_weights",{}))
    if not domains: return ""
    lines=["| Model | Effort | "+" | ".join(DOMAIN_LABELS[d] for d in domains)+" |",
           "|:--|:--|"+"--:|"*len(domains)]
    for a in data["aggregates"]:
        values=[]
        for d in domains:
            failed=any(r["variant"]==a["variant"] and r.get("domain")==d and r["status"]=="format_error" for r in data["results"])
            values.append(percent(a["domain_scores"].get(d))+(" *" if failed else ""))
        lines.append(f"| `{a['model']}` | {a['effort']} | "+" | ".join(values)+" |")
    return "\n".join(lines)


def leaderboard(data):
    general=bool(data["runs"][0].get("domain_weights"))
    score_label="Strict outcome" if general else "Score"
    reliability_label="Format failures" if general else "Full passes"
    lines=[f"| Model | Reasoning effort | Source | {score_label} | {reliability_label} | Input / output tokens |",
           "|:--|:--|:--|--:|--:|--:|"]
    ordered=sorted(data["aggregates"],key=lambda r:-(r["score"] if r["score"] is not None else -1))
    for a in ordered:
        u=a["usage"]
        tokens=f"{u['inputTokens']:,} / {u['outputTokens']:,}" if {"inputTokens","outputTokens"}<=u.keys() else "—"
        coverage=f"{a['full_passes']}/{a['tasks']}" if a["score"] is not None else f"incomplete ({a['graded']}/{a['tasks']})"
        if general and a["score"] is not None: coverage=f"{a['format_failures']}/{a['tasks']}"
        lines.append(f"| `{a['model']}` | `{a['effort']}` | {source_label(a['harness'])} | **{percent(a['score'])}** | {coverage} | {tokens} |")
    return "\n".join(lines)


def markdown(data):
    first=data["runs"][0]
    weighting="Each domain has equal weight; tasks are averaged within a domain." if first.get("domain_weights") else "Equal task weights."
    lines=["# Model evaluation results", "",f"**Suite:** `{first.get('suite','micro-v1')}` · **Seed:** `{first['seed']}` · **Attempts:** 1 per task/configuration", "",
           leaderboard(data), "", weighting+" A missing or failed infrastructure run receives no aggregate score.",
           "Token accounting is CLI-reported; cache and reasoning counters differ between providers. No dollar costs are inferred.",
           "", "## Task breakdown", "", "| Model | Effort | Source | Task | Score | Checks | Status |", "|:--|:--|:--|:--|--:|--:|:--|"]
    if first.get("ground_truth_revision"):
        note="**Ground truth correction:** tenant-isolation classification in security triage was corrected for every saved answer, without new model calls. [Adjudication and original scores](../../docs/adjudications/001-security-triage.md)."
        lines[4:4]=[note, ""]
    if first.get("domain_weights"):
        index=lines.index("## Task breakdown")
        lines[index:index]=["## Domain breakdown", "",domain_table(data),"",
            "\\* Includes a response-contract failure scored as zero under the frozen rules. Inspect the response before interpreting it as a reasoning failure.","",
            "Browser/desktop results measure independent structured-state decisions, not real browsing, visual perception, or interactive tool execution.",""]
    for r in data["results"]:
        checks=f"{r['passed']}/{r['total']}" if "passed" in r else "—"
        lines.append(f"| `{r['model']}` | {r['effort']} | {source_label(r['harness'])} | {r['task']} | {percent(r.get('score'))} | {checks} | {r['status']} |")
    lines += ["", "## Reproducibility", "", "| Run | Commit | CLI versions |", "|:--|:--|:--|"]
    for i,m in enumerate(data["runs"],1):
        versions=m.get("cli_versions",{"cmd":m.get("cli_version","unknown")})
        lines.append(f"| {i} | `{m['git_commit']}` | {escape(json.dumps(versions,sort_keys=True))} |")
    for m in data["runs"]:
        if m.get("adapter_commits"):
            lines += ["", "Adapter revisions: " + ", ".join(f"`{c}`" for c in m["adapter_commits"]) + "."]
        if m.get("acquisition_notes"):
            lines += ["",m["acquisition_notes"]]
    lines += ["",f"Suite fingerprint: `{first.get('suite_fingerprint','not recorded')}`.",
              "", "Command Code model/effort identity is checked against request events. Codex JSONL does not expose those fields;",
              "Codex entries report the explicitly configured model/effort, not an independently verified upstream identity.",
              "Command Code ZDR enforcement is disabled only in evaluation child processes; this setting does not control Codex retention.",
              "", "Six tasks are a screening sample, not a statistically established general ranking. A tied score is a tie on this suite.",
              "Code cases within one task are correlated. Different harnesses remain a confound even with identical prompts and effort labels.", ""]
    if first.get("grading_fingerprint"):
        lines += [f"Corrected grading fingerprint: `{first['grading_fingerprint']}`.",
                  f"Adjudication commit: `{first.get('adjudication_commit','unknown')}`.",""]
    return "\n".join(lines)


def scorecard(data):
    domains=list(data["runs"][0].get("domain_weights",{}))
    tasks=domains or data["runs"][0]["tasks"]
    spacing=132 if domains else 92
    cell_width=120 if domains else 80
    aggregates=sorted(data["aggregates"],key=lambda r:-(r["score"] if r["score"] is not None else -1))
    width=1080
    height=155+len(aggregates)*74
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
         '<title id="title">Model evaluation scorecard</title>',
         '<desc id="desc">Scores by model, reasoning effort and task. Missing results are shown as dashes.</desc>',
         f'<rect width="{width}" height="{height}" rx="16" fill="#10151d"/>',
         '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" fill="#e8edf5">',
         '<text x="28" y="38" font-size="20" font-weight="600">MODEL EVALS</text>',
         f'<text x="28" y="64" fill="#9ba8ba" font-size="13">{escape(data["runs"][0].get("suite","micro-v1"))} · one attempt · {"equal domain weights" if domains else "equal task weights"} · higher is better</text>']
    labels={"config-merge":"Merge","reservation-ledger":"State","snapshot-pagination":"Repair",
            "security-triage":"Security","evidence-reconciliation":"Evidence","release-selection":"Planning"}
    for j,t in enumerate(tasks):
        label=DOMAIN_LABELS[t] if domains else labels.get(t,t)
        svg.append(f'<text x="{381+cell_width/2+j*spacing}" y="104" font-size="12" text-anchor="middle" fill="#aab8c9">{escape(label)}</text>')
    svg.append('<text x="1008" y="104" font-size="12" text-anchor="middle" fill="#aab8c9">Overall</text>')
    for i,a in enumerate(aggregates):
        y=122+i*74
        svg += [f'<text x="28" y="{y+21}" font-size="14" font-weight="600">{escape(a["model"])}</text>',
                f'<text x="28" y="{y+43}" font-size="12" fill="#9ba8ba">{escape(a["effort"])} effort · {escape(source_label(a["harness"]))}</text>']
        for j,t in enumerate(tasks):
            row=next((r for r in data["results"] if r["variant"]==a["variant"] and r["task"]==t),{})
            val=a["domain_scores"].get(t) if domains else row.get("score")
            format_failed=domains and any(r["variant"]==a["variant"] and r.get("domain")==t and r["status"]=="format_error" for r in data["results"])
            color="#243040" if val is None else ("#155b4d" if val==1 else "#704b23" if val>0 else "#713742")
            x=381+j*spacing
            svg += [f'<rect x="{x}" y="{y}" width="{cell_width}" height="49" rx="7" fill="{color}"/>',
                    f'<text x="{x+cell_width/2}" y="{y+30}" text-anchor="middle" font-size="14">{percent(val)}{" *" if format_failed else ""}</text>']
        svg.append(f'<text x="1008" y="{y+31}" text-anchor="middle" font-size="18" font-weight="600">{percent(a["score"])}</text>')
    if data["runs"][0].get("ground_truth_revision"):
        svg.append(f'<text x="28" y="{height-12}" fill="#9ba8ba" font-size="11">Security ground truth corrected uniformly; see Adjudication 001. Small sample; no general ranking.</text>')
    elif domains:
        svg.append(f'<text x="28" y="{height-27}" fill="#9ba8ba" font-size="11">* Includes a response-contract failure. Strict outcome is not a pure reasoning score; inspect the responses.</text>')
        svg.append(f'<text x="28" y="{height-12}" fill="#9ba8ba" font-size="11">Browser/desktop: structured snapshot reasoning only. No real tool use or visual perception measured.</text>')
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
