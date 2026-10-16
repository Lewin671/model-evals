"""Export an allowlisted summary, never raw transcripts or session metadata."""
import argparse
import json
from pathlib import Path

USAGE_FIELDS=("inputTokens","outputTokens","cacheReadTokens","cacheWriteTokens")


def render(directory):
    manifest=json.loads((directory/"manifest.json").read_text())
    rows=json.loads((directory/"results.json").read_text())
    safe=[]
    for row in rows:
        item={k:row[k] for k in ("model","task","dimension","status","score","passed","total",
                                "exit_code","prompt_sha256","observed_models") if k in row}
        item["usage"]={k:v for k,v in (row.get("usage") or {}).items()
                       if k in USAGE_FIELDS and type(v) in (int,float)}
        safe.append(item)
    lines=["# Evaluation result", "", f"Seed: `{manifest['seed']}` · CLI: `{manifest['cli_version']}`",
           f"Commit: `{manifest['git_commit']}`", "",
           "ZDR enforcement: off for child processes. One attempt per task. No automatic retries.", "",
           "| Model | Task | Score | Status |", "|---|---|---:|---|"]
    for r in safe:
        score="—" if r.get("score") is None else f"{100*r['score']:.1f}%"
        lines.append(f"| {r['model']} | {r['task']} | {score} | {r['status']} |")
    lines += ["", "## Aggregate", "", "Each task has equal weight. Code test cases are correlated, not independent samples.", ""]
    for model in manifest["models"]:
        subset=[r for r in safe if r["model"]==model]
        graded=[r for r in subset if r.get("score") is not None]
        complete=len(graded)==len(manifest["tasks"])
        score=f"{100*sum(r['score'] for r in graded)/len(graded):.1f}%" if complete else "not reported (incomplete run)"
        lines.append(f"- {model}: {score}; graded {len(graded)}/{len(manifest['tasks'])} tasks.")
        usage={k:sum(r["usage"].get(k,0) for r in subset) for k in USAGE_FIELDS if any(k in r["usage"] for r in subset)}
        lines.append(f"  CLI-reported tokens: `{json.dumps(usage,sort_keys=True)}`. Dollar charges are not inferred.")
    lines += ["", "This is a small screening run, not a statistically established ranking. No hardware-speed conclusions.",
              "Prompts, responses and private logs must be inspected locally before publishing a conclusion.", ""]
    public_manifest={k:manifest[k] for k in ("seed","models","tasks","cli_version","git_commit","zdr_enforced",
                                              "max_turns","timeout_seconds","reasoning_effort","tools")}
    return "\n".join(lines), {"manifest":public_manifest,"results":safe}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    markdown,data=render(args.run)
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/"report.md").write_text(markdown)
    (args.output/"summary.json").write_text(json.dumps(data,indent=2))
    print(args.output/"report.md")


if __name__=="__main__": main()
