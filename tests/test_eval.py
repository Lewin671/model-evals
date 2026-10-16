import json
import os
from pathlib import Path
import subprocess
import tempfile
import sqlite3
import hashlib
import unittest
from unittest.mock import patch

from evalkit.grading import execute, grade
from evalkit.run import command, environment, invoke, parse_result, version_line
from evalkit.tasks import LEDGER_REF, PAGE_REF, merge, oracle, ref, legacy_suite as suite
from evalkit.tasks import suite as general_suite
from evalkit.report import render, prepare, scorecard
from evalkit.adapters import Variant, codex_command, parse_codex
from evalkit.regrade import apply as adjudicate
import xml.etree.ElementTree as ET


class Contracts(unittest.TestCase):
    def test_deterministic_and_fresh(self):
        self.assertEqual(suite(12), suite(12))
        self.assertNotEqual(suite(12), suite(13))

    def test_six_distinct_dimensions(self):
        tasks=suite(3)
        self.assertEqual(len(tasks),6)
        self.assertEqual(len({t.dimension for t in tasks}),6)

    def test_config_known(self):
        data=[{"x":{"a":1,"b":2},"list":[1]},
              {"x":{"a":{"$delete":True},"b":None},"list":[],"z":{"$delete":True}}]
        self.assertEqual(merge(data),{"x":{"b":None},"list":[]})
        self.assertEqual(merge([{"x":3},{"x":{"$delete":False}}]),{"x":{"$delete":False}})
        self.assertEqual(merge([{"x":3},{"x":{"$delete":1}}]),{"x":{"$delete":1}})

    def test_ledger_expiration_on_duplicate(self):
        data=[{"t":0,"id":"c","op":"credit","amount":10},
              {"t":1,"id":"h","op":"hold","key":"x","amount":7,"until":2},
              {"t":2,"id":"h","op":"hold","key":"x","amount":7,"until":2}]
        self.assertEqual(ref(LEDGER_REF,data),{"available":10,"holds":{}})

    def test_ledger_capture_and_rejection_idempotence(self):
        data=[{"t":0,"id":"a","op":"hold","amount":3,"key":"x","until":9},
              {"t":1,"id":"c","op":"credit","amount":10},
              {"t":2,"id":"a","op":"hold","amount":3,"key":"x","until":9},
              {"t":3,"id":"b","op":"hold","amount":4,"key":"y","until":9},
              {"t":4,"id":"d","op":"capture","key":"y"},
              {"t":5,"id":"e","op":"release","key":"y"}]
        self.assertEqual(ref(LEDGER_REF,data),{"available":6,"holds":{}})

    def test_page_filter_before_slice_and_tie(self):
        q={"rows":[{"tenant":"b","created":0,"id":"z"},
                  {"tenant":"a","created":1,"id":"b"},{"tenant":"a","created":1,"id":"a"}],
           "tenant":"a","snapshot":1,"limit":1,"after":None}
        self.assertEqual(ref(PAGE_REF,q),{"ids":["a"],"next":[1,"a"]})
        q["after"]=[1,"a"]
        self.assertEqual(ref(PAGE_REF,q),{"ids":["b"],"next":None})

    def test_json_is_strict(self):
        t=suite(1)[3]
        self.assertEqual(grade(t,"```json\n{}\n```else")["status"],"format_error")
        self.assertEqual(grade(t,json.dumps(t.expected))["score"],1)
        self.assertEqual(grade(t,json.dumps(dict(t.expected,extra=1)))["score"],0)

    def test_reference_answers_and_wrong_programs(self):
        for t in suite(17)[:3]:
            with self.subTest(t=t.id):
                self.assertEqual(grade(t,json.dumps({"source":t.reference}))["score"],1)
                self.assertLess(grade(t,json.dumps({"source":"def solve(x): return {}"}))["score"],1)

    def test_independent_oracles(self):
        for seed in range(8):
            for task in suite(seed)[:3]:
                for case in task.cases:
                    self.assertEqual(oracle(task.id,case),ref(task.reference,case))

    def test_mutation_is_failure(self):
        t=suite(1)[0]
        result=grade(t,json.dumps({"source":"def solve(x):\n x.append({})\n return {}"}))
        self.assertEqual(result["score"],0)

    def test_sandbox_blocks_home_network_write_and_fork(self):
        source='''def solve(x):
    import os, socket
    checks=[]
    for f in [lambda: open(x).read(), lambda: open('/tmp/cc-eval-forbidden','w'),
              lambda: socket.create_connection(('127.0.0.1',9)), lambda: os.fork()]:
        try: f(); checks.append(False)
        except OSError: checks.append(True)
    return checks
'''
        with tempfile.NamedTemporaryFile(dir=Path.home()) as f:
            f.write(b"synthetic sandbox test"); f.flush()
            self.assertEqual(execute(source,[f.name])[0]["value"],[True]*4)

    def test_zdr_unset_only_in_child(self):
        with patch.dict(os.environ,{"CMD_ZDR":"1"}):
            self.assertNotIn("CMD_ZDR",environment())
            self.assertEqual(os.environ["CMD_ZDR"],"1")

    def test_cli_has_explicit_model_and_limits(self):
        args=command("model/one",1)
        self.assertEqual(args[args.index("--model")+1],"model/one")
        self.assertEqual(args[args.index("--max-turns")+1],"1")
        self.assertNotIn("--yolo",args)

    def test_ndjson_and_tool_detection(self):
        raw='startup noise\n'+json.dumps({"type":"event","event":{"type":"tool_running"}})+'\n'+json.dumps({"type":"result","subtype":"success","finalText":"{}"})
        self.assertEqual(parse_result(raw)[1],1)
        with self.assertRaises(ValueError): parse_result('{}')
        with self.assertRaises(ValueError): parse_result(raw+'\n'+json.dumps({"type":"result"}))

    def test_fake_cli_end_to_end_child_environment(self):
        # No model calls: substitute a local executable, inspect flags and CWD.
        with tempfile.TemporaryDirectory() as directory:
            fake=Path(directory)/"cmd"
            fake.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
assert 'CMD_ZDR' not in os.environ
assert not pathlib.Path('evalkit').exists()
assert json.loads(pathlib.Path('.commandcode/settings.json').read_text())['permissions']['deny']==['*']
assert '--no-skills' in sys.argv and '--no-session' in sys.argv
print(json.dumps({'type':'result','subtype':'success','finalText':sys.stdin.read()}))
''')
            fake.chmod(0o700)
            with patch.dict(os.environ,{"PATH":directory+os.pathsep+os.environ["PATH"],"CMD_ZDR":"1"}):
                rc,out,err=invoke("test/fake",suite(1)[3],1,10)
            self.assertEqual(rc,0,err)
            self.assertEqual(parse_result(out)[0]["finalText"],suite(1)[3].prompt)

    def test_call_budget_dry_run(self):
        proc=subprocess.run([os.sys.executable,"-m","evalkit.run","--max-calls","1"],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("call count exceeds",proc.stderr)

    def test_report_does_not_publish_raw_metadata_or_incomplete_mean(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            manifest={"seed":1,"models":["a"],"tasks":["x","y"],"cli_version":"test","git_commit":"abc",
                      "zdr_enforced":False,"max_turns":1,"timeout_seconds":1,"reasoning_effort":"default","tools":"denied"}
            (p/"manifest.json").write_text(json.dumps(manifest))
            (p/"results.json").write_text(json.dumps([{"model":"a","task":"x","status":"graded","score":1,
                "sessionId":"SECRET_SESSION","detail":"/Users/private","usage":{"inputTokens":100,"secret":"SECRET"}}]))
            md,data=render(p)
            self.assertIn("incomplete (",md)
            self.assertNotIn("SECRET",json.dumps(data))
            self.assertNotIn("/Users",json.dumps(data))

    def test_codex_effort_flags_and_disabled_tools(self):
        variant=Variant("codex","gpt-6.1-sol","high")
        argv=codex_command(variant)
        self.assertIn('model_reasoning_effort="high"',argv)
        self.assertIn("features.shell_tool=false",argv)
        self.assertIn("--ignore-user-config",argv)
        self.assertNotIn("--output-schema",argv)
        self.assertNotEqual(variant.id,Variant("codex","gpt-6.1-sol","medium").id)
        with self.assertRaises(ValueError): Variant("wrong","x","high")
        with self.assertRaises(ValueError): Variant("codex","x","default")

    def test_codex_protocol_and_usage_normalization(self):
        events=[{"type":"item.completed","item":{"id":"a","type":"agent_message","text":"{}"}},
                {"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":60,"output_tokens":12}}]
        result,tools=parse_codex("\n".join(map(json.dumps,events)))
        self.assertEqual(result["usage"],{"inputTokens":100,"cacheReadTokens":60,"outputTokens":12})
        self.assertEqual(tools,0)
        self.assertEqual(result["observed_models"],[])
        events.insert(0,{"type":"item.completed","item":{"id":"warning","type":"error","message":"startup warning"}})
        self.assertEqual(parse_codex("\n".join(map(json.dumps,events)))[1],0)
        events.insert(0,{"type":"item.started","item":{"id":"t","type":"command_execution"}})
        events.insert(1,{"type":"item.completed","item":{"id":"t","type":"command_execution"}})
        self.assertEqual(parse_codex("\n".join(map(json.dumps,events)))[1],1)
        with self.assertRaises(ValueError): parse_codex(json.dumps({"type":"turn.failed"}))

    def test_command_code_effort_observed(self):
        raw="\n".join(map(json.dumps,[{"type":"event","event":{"type":"model_request_end","model":"m","effort":"high"}},
                                    {"type":"result","subtype":"success","finalText":"{}"}]))
        result,_=parse_result(raw)
        self.assertEqual(result["observed_models"],["m"])
        self.assertEqual(result["observed_efforts"],["high"])

    def test_same_model_different_efforts_remain_separate_and_svg_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            variants=[Variant("codex","m",e).record() for e in ("medium","high")]
            (p/"manifest.json").write_text(json.dumps({"seed":1,"models":["m"],"variants":variants,
                "tasks":["config-merge"],"git_commit":"abc"}))
            (p/"results.json").write_text(json.dumps([{"variant":v["id"],"model":"m","harness":"codex",
                "effort":v["effort"],"task":"config-merge","status":"graded","score":float(i)} for i,v in enumerate(variants)]))
            md,data=render(p)
            self.assertEqual(len(data["aggregates"]),2)
            self.assertEqual([r["score"] for r in data["aggregates"]],[0,1])
            self.assertIn("medium",md)
            ET.fromstring(scorecard(data))
            with self.assertRaises(ValueError): prepare([p,p])

    def test_mismatched_seeds_cannot_be_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for seed in (1,2):
                p=Path(directory)/str(seed);p.mkdir();paths.append(p)
                (p/"manifest.json").write_text(json.dumps({"seed":seed,"models":[],"tasks":[]}))
                (p/"results.json").write_text("[]")
            with self.assertRaisesRegex(ValueError,"seed"): prepare(paths)

    def test_campaign_requires_explicit_call_budget(self):
        proc=subprocess.run([os.sys.executable,"-m","evalkit.run","--campaign","configs/screening.json"],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("call count exceeds",proc.stderr)

    def test_version_update_notice_does_not_change_identity(self):
        self.assertEqual(version_line("Updated 1.82.3 → 1.82.5\n1.82.5\n"),"1.82.5")

    def test_security_oracle_matches_concrete_tenant_leak(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE docs (tenant TEXT, title TEXT)")
        db.executemany("INSERT INTO docs VALUES (?,?)",[("a","shared"),("b","shared")])
        self.assertEqual(len(db.execute("SELECT * FROM docs WHERE title = ?",("shared",)).fetchall()),2)
        task=suite(1)[3]
        snippets=json.loads(task.prompt.split("Snippets:\n",1)[1])
        parameterized=next(s["id"] for s in snippets if "WHERE title = ?" in s["code"])
        self.assertIn(parameterized,task.expected["vulnerable_ids"])
        db.close()

    def test_adjudication_preserves_prior_scores_and_is_not_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);task=suite(1)[3]
            variant=Variant("codex","fake-model","high")
            (p/"manifest.json").write_text(json.dumps({"seed":1,"variants":[variant.record()]}))
            row={"task":task.id,"score":0,"status":"graded","artifact_stem":"saved",
                 "prompt_sha256":hashlib.sha256(task.prompt.encode()).hexdigest()}
            (p/"results.json").write_text(json.dumps([row]))
            (p/"saved.prompt.txt").write_text(task.prompt)
            (p/"saved.answer.txt").write_text(json.dumps(task.expected))
            adjudicate(p)
            updated=json.loads((p/"results.json").read_text())[0]
            self.assertEqual(updated["score_before_adjudication"],0)
            self.assertEqual(updated["score"],1)
            self.assertEqual(json.loads((p/"results.before-adjudication-001.json").read_text())[0]["score"],0)
            with self.assertRaises(ValueError): adjudicate(p)

    def test_resume_never_repeats_a_recorded_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            answers={t.prompt:json.dumps(t.expected) for t in general_suite(1)[3:5]}
            (p/"answers.json").write_text(json.dumps(answers))
            fake=p/"codex"
            fake.write_text('''#!/usr/bin/env python3
import json,os,pathlib,sys
if '--version' in sys.argv:
    print('codex-cli fake-1');sys.exit()
p=pathlib.Path(os.environ['FAKE_ROOT'])
with (p/'calls').open('a') as f: f.write('call\\n')
answer=json.loads((p/'answers.json').read_text())[sys.stdin.read()]
print(json.dumps({'type':'item.completed','item':{'id':'w','type':'error','message':'warning'}}))
print(json.dumps({'type':'item.completed','item':{'id':'a','type':'agent_message','text':answer}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}))
''')
            fake.chmod(0o700)
            env=dict(os.environ,PATH=str(p)+os.pathsep+os.environ['PATH'],FAKE_ROOT=str(p))
            base=[os.sys.executable,'-m','evalkit.run','--harness','codex','--models','fake-model',
                  '--tasks','expense-reconciliation','browser-snapshots','--seed','1','--execute','--allow-prototype']
            output=p/'run'
            first=subprocess.run(base+['--output',str(output)],capture_output=True,text=True,env=env)
            self.assertEqual(first.returncode,0,first.stderr)
            second=subprocess.run(base+['--resume-run',str(output)],capture_output=True,text=True,env=env)
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual((p/'calls').read_text().splitlines(),['call','call'])
            self.assertTrue(all(r['score']==1 for r in json.loads((output/'results.json').read_text())))


if __name__=="__main__": unittest.main()
