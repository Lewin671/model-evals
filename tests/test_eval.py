import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evalkit.grading import execute, grade
from evalkit.run import command, environment, invoke, parse_result
from evalkit.tasks import LEDGER_REF, PAGE_REF, merge, oracle, ref, suite
from evalkit.report import render


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
            self.assertIn("incomplete run",md)
            self.assertNotIn("SECRET",json.dumps(data))
            self.assertNotIn("/Users",json.dumps(data))


if __name__=="__main__": unittest.main()
