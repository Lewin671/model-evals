"""Apply the documented security oracle correction to unchanged saved answers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .grading import grade
from .run import suite_fingerprint
from .tasks import legacy_suite as suite


def apply(directory):
    manifest=json.loads((directory/"manifest.json").read_text())
    rows=json.loads((directory/"results.json").read_text())
    if manifest.get("ground_truth_revision"): raise ValueError("adjudication already applied")
    task=next(t for t in suite(manifest["seed"]) if t.id=="security-triage")
    selected=[r for r in rows if r["task"]==task.id]
    if len(selected)!=len(manifest["variants"]): raise ValueError("need every configuration's saved security answer")
    expected_hash=hashlib.sha256(task.prompt.encode()).hexdigest()
    updated=[]
    for row in selected:
        if row["prompt_sha256"]!=expected_hash: raise ValueError("prompt changed; refusing regrade")
        stem=row["artifact_stem"]
        if (directory/f"{stem}.prompt.txt").read_text()!=task.prompt: raise ValueError("saved prompt changed")
        result=grade(task,(directory/f"{stem}.answer.txt").read_text())
        updated.append((row,result))
    for name in ("results","manifest"):
        destination=directory/f"{name}.before-adjudication-001.json"
        with destination.open("x") as f: f.write((directory/f"{name}.json").read_text())
    for row,result in updated:
        row["score_before_adjudication"]=row["score"]
        row["adjudication"]="001-security-triage"
        row.update(result)
    manifest.update({"ground_truth_revision":"001-security-triage","grading_fingerprint":suite_fingerprint(),
        "adjudication_commit":subprocess.run(["git","rev-parse","HEAD"],text=True,capture_output=True,check=True).stdout.strip()})
    (directory/"results.json").write_text(json.dumps(rows,indent=2))
    (directory/"manifest.json").write_text(json.dumps(manifest,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    args=parser.parse_args()
    apply(args.run)
    print("Applied adjudication 001 to saved responses. No model calls.")


if __name__=="__main__": main()
