import unittest
from evalkit.shortscreen.tasks import task,suite,qualify,observe,grade

class ShortScreen(unittest.TestCase):
    def test_reference_and_counterfactual_gates(self):
        self.assertEqual(qualify()['reference'],'pass')
        self.assertEqual(len(suite()),8)
        self.assertEqual(sum(t['calls'] for t in suite())*2,24)

    def test_unopened_data_is_not_revealed(self):
        t=task('desktop','A')
        self.assertEqual(observe(t,{'action':'open','files':['r2.xlsx']})['workbooks'],{'r2.xlsx':t['files']['r2.xlsx']})
        self.assertEqual(observe(t,{'action':'open','files':['outside']})['workbooks'],{})
        t=task('browser','A')
        self.assertEqual(set(observe(t,{'action':'inspect','pages':['B']})['detail_pages']),{'B'})

    def test_wrong_default_strategies_fail(self):
        for variant in ('A','B'):
            t=task('desktop',variant)
            answer=dict(t['expected'],rows=[['ada',1030]])
            self.assertFalse(grade(t,answer)['complete'])
            t=task('browser',variant)
            self.assertFalse(grade(t,{'action':'save','plan':'C','annual_total':70})['complete'])

    def test_explicit_continuation_never_retries_recorded_failure(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from evalkit.shortscreen import run
        rows=[{'task':'coding-A','model':m,'status':'adapter_or_response_contract_failure','grade':None} for m in run.MODELS]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'manifest.json').write_text(json.dumps({'commit':'frozen'}))
            (root/'results.json').write_text(json.dumps(rows))
            (root/'usage.json').write_text(json.dumps({'cliInvocations':2,'observedModelRequests':2,'inputTokens':10,'outputTokens':3,'cacheReadTokens':0}))
            frozen=Path(run.__file__).with_name('tasks.py').read_bytes()
            def command(argv,**kwargs):
                if argv[:2]==['git','show']:return frozen
                return 'test-version\n'
            with patch('sys.argv',['run','--output',d,'--execute','--resume-unattempted']),patch.object(run,'qualify',return_value={}),patch.object(run,'suite',return_value=[task('coding','A')]),patch.object(run.subprocess,'check_output',side_effect=command),patch.object(run,'invoke') as invoke,contextlib.redirect_stdout(io.StringIO()):
                run.main()
            invoke.assert_not_called()
            self.assertEqual(json.loads((root/'results.json').read_text()),rows)

    def test_high_effort_is_passed_and_verified(self):
        import contextlib,io,json,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from evalkit.shortscreen import run
        t=task('everyday','A')
        def invoke(model,task,turns,timeout,effort):
            self.assertEqual(effort,'high')
            events=[{'type':'event','event':{'type':'model_request_start','model':model}},
                {'type':'event','event':{'type':'model_request_end','model':model,'effort':effort,'usage':{'outputTokens':2}}},
                {'type':'result','subtype':'success','finalText':json.dumps(t['expected'])}]
            return 0,'\n'.join(map(json.dumps,events)),''
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            with patch('sys.argv',['run','--output',str(root),'--effort','high','--execute']),patch.object(run,'qualify',return_value={}),patch.object(run,'suite',return_value=[t]),patch.object(run.subprocess,'check_output',return_value='test-version\n'),patch.object(run,'invoke',side_effect=invoke),contextlib.redirect_stdout(io.StringIO()):
                run.main()
            rows=json.loads((root/'results.json').read_text())
            self.assertTrue(all(r['grade']['complete'] and r['effort']=='high' for r in rows))
            self.assertEqual(json.loads((root/'manifest.json').read_text())['effort'],'high')
