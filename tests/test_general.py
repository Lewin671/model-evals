import copy
import json
from pathlib import Path
import tempfile
import unittest

from evalkit.tasks import Task,suite
from evalkit.general import expense_answer,optimal_schedule
from evalkit.grading import grade
from evalkit.report import prepare,scorecard
import xml.etree.ElementTree as ET


class GeneralSuite(unittest.TestCase):
    def test_current_scope_has_no_security_and_four_domains(self):
        tasks=suite(5)
        self.assertEqual(len(tasks),6)
        self.assertEqual([t.domain for t in tasks],["coding","coding","everyday","everyday","browser","computer"])
        self.assertNotIn("security-triage",[t.id for t in tasks])
        self.assertEqual(tasks,suite(5))
        self.assertNotEqual(tasks,suite(6))

    def test_reference_answers_before_paid_calls(self):
        for seed in (0,17,112,902):
            for t in suite(seed):
                with self.subTest(seed=seed,task=t.id):
                    answer={"source":t.reference} if t.cases is not None else t.expected
                    self.assertEqual(grade(t,json.dumps(answer))["score"],1)

    def test_expenses_known_updates_duplicates_credit_and_missing_rate(self):
        records=[{"id":"a","revision":1,"status":"approved","currency":"USD","amount_cents":1000},
                 {"id":"a","revision":2,"status":"approved","currency":"USD","amount_cents":1200},
                 {"id":"a","revision":2,"status":"approved","currency":"USD","amount_cents":1200},
                 {"id":"b","revision":1,"status":"approved","currency":"USD","amount_cents":-300},
                 {"id":"c","revision":1,"status":"approved","currency":"EUR","amount_cents":900},
                 {"id":"d","revision":1,"status":"pending","currency":"USD","amount_cents":50}]
        self.assertEqual(expense_answer(records),{"total_cents":900,"included_ids":["a","b"],"excluded_ids":["c","d"],"needs_exchange_rate":["c"]})

    def test_planning_accepts_alternatives_but_rejects_overlap_and_missing_ids(self):
        data={"jobs":[{"id":"a","duration":30,"priority":2,"allowed_starts":[540,555]},
                      {"id":"b","duration":15,"priority":3,"allowed_starts":[600,615]}],
              "busy":[[580,590]],"buffer":15,"window":[540,660]}
        best,_=optimal_schedule(data);self.assertEqual(best,5)
        task=Task("custom","everyday","",rubric={"kind":"schedule","data":data,"best":best})
        for start in (600,615):
            answer={"schedule":[{"id":"a","start":540},{"id":"b","start":start}],"unscheduled":[]}
            self.assertEqual(grade(task,json.dumps(answer))["score"],1)
        answer={"schedule":[{"id":"a","start":555},{"id":"b","start":600}],"unscheduled":[]}
        self.assertEqual(grade(task,json.dumps(answer))["score"],0)
        answer={"schedule":[{"id":"a","start":540}],"unscheduled":["b"]}
        self.assertEqual(grade(task,json.dumps(answer))["score"],.4)
        answer["unscheduled"]=[]
        self.assertEqual(grade(task,json.dumps(answer))["score"],0)

    def test_equivalent_ui_actions_and_coordinate_hit_regions(self):
        for task in suite(12)[4:]:
            answer=copy.deepcopy(task.expected)
            for action in answer["actions"]:
                rule=next(r for r in task.rubric["checks"] if r["case_id"]==action["case_id"])
                if "allowed" in rule: action.update(rule["allowed"][-1])
                else: action.update(x=rule["box"][0]+4,y=rule["box"][1]+4)
            self.assertEqual(grade(task,json.dumps(answer))["score"],1)
        action=next(a for a in answer["actions"] if "x" in a)
        action["x"]*=2;action["y"]*=2
        self.assertEqual(grade(task,json.dumps(answer))["score"],5/6)

    def test_stale_click_and_duplicate_checkpoint_fail(self):
        task=suite(2)[4]
        answer=copy.deepcopy(task.expected)
        action=next(a for a in answer["actions"] if a["op"]=="observe")
        action.update(op="click",target="invented-stale-node")
        self.assertEqual(grade(task,json.dumps(answer))["score"],5/6)
        answer=copy.deepcopy(task.expected)
        answer["actions"].append(dict(answer["actions"][0]))
        self.assertEqual(grade(task,json.dumps(answer))["score"],5/6)

    def test_domain_macro_average_not_task_average(self):
        tasks=suite(5)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            manifest={"seed":5,"suite":"general-v2","models":["m"],"tasks":[t.id for t in tasks],
                "task_domains":{t.id:t.domain for t in tasks},"domain_weights":{d:.25 for d in ("coding","everyday","browser","computer")}}
            rows=[{"model":"m","task":t.id,"status":"graded","score":1 if t.domain in ("coding","everyday") else 0} for t in tasks]
            (p/"manifest.json").write_text(json.dumps(manifest));(p/"results.json").write_text(json.dumps(rows))
            data,_=prepare([p])
            self.assertEqual(data["aggregates"][0]["score"],.5)
            ET.fromstring(scorecard(data))


if __name__=="__main__": unittest.main()
