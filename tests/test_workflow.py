import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
import subprocess
import shutil
from unittest.mock import patch

from evalkit.workflows.importer import API_REFERENCE,csv_text,materialize,oracle_rows,row,sources
from evalkit.workflows.checker import evaluate
from evalkit.workflows.calibrate import episode,preflight,setup_usage
from evalkit.workflows.tools import decode,perform


class ImporterWorkflow(unittest.TestCase):
    def test_native_tools_bridge_and_midpoint_change_without_model_calls(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node required for the Command Code mod')
        base=Path(__file__).resolve().parents[1]/'evalkit/workflows'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'repo';root.mkdir();materialize(root,'stream')
            env=dict(os.environ,MODEL_EVAL_WORKSPACE=str(root),MODEL_EVAL_PYTHON=sys.executable,
                MODEL_EVAL_BRIDGE=str(base/'bridge.py'),MODEL_EVAL_SEED='481',MODEL_EVAL_VARIANT='stream',
                MODEL_EVAL_CHANGE=json.dumps('ADDED REQUIREMENT'),MODEL_EVAL_CONTROL=str(Path(d)/'control.json'))
            script='''import make from '''+json.dumps((base/'native_tools.mjs').as_uri())+''';
const tools={};let hooks;let active=[];
make({addTool:t=>{tools[t.schema.name]=t},setActiveTools:a=>{active=a},getActiveTools:()=>active,
      hooks:h=>{hooks=h},on:()=>{}});
const state={messages:[]};hooks.onTurnStart({state,turnNumber:1});
if(active.length!==3 || hooks.appendSystemPrompt().includes('ADDED REQUIREMENT'))throw Error('wrong initial surface');
const read=await tools.repo_read.run({input:{paths:['ledger/api.py']}});
if(!read.ok)throw Error('read failed');
const files=JSON.parse(process.env.TEST_REFERENCE_FILES);
const [,before]=await Promise.all([tools.repo_write.run({input:{files}}),tools.repo_test.run({input:{}})]);
const initialChecks=JSON.parse(before.content[0].text).public_checks;
if(initialChecks.total!==3 || initialChecks.passed!==3)throw Error('write/test ordering failed');
hooks.onTurnStart({state,turnNumber:3});
if(!hooks.appendSystemPrompt().includes('ADDED REQUIREMENT'))throw Error('change missing');
const after=await tools.repo_test.run({input:{}});
const checks=JSON.parse(after.content[0].text).public_checks;
if(checks.total!==4 || checks.passed!==4)throw Error('changed tests failed');
'''
            env['TEST_REFERENCE_FILES']=json.dumps({k:v for k,v in sources('stream',reference=True).items() if k in ('ledger/api.py','ledger/parser.py','ledger/store.py')})
            result=subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,0,result.stderr)
    def test_native_tool_filter_mod_removes_schemas_without_inference(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node needed only for Command Code mod check')
        mod=Path(__file__).resolve().parents[1]/'evalkit/workflows/no_native_tools.mjs'
        script='''import make from '''+json.dumps(mod.as_uri())+''';
let active=['read_file','shell_command'];let hooks;
make({setActiveTools:(a)=>{active=a},getActiveTools:()=>active,hooks:(h)=>{hooks=h}});
const state={messages:[]};
if(hooks.onTurnStart({state})!==state || active.length!==0)throw Error('tools still active');
if(!hooks.appendSystemPrompt().includes('no native tools'))throw Error('missing protocol instruction');
'''
        result=subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_reference_artifacts_and_wrong_strategy_gates(self):
        gates=preflight(481)
        self.assertTrue(all(r['fraction']==1 for r in gates['reference'].values()))
        self.assertTrue(all(r['fraction']<1 for r in gates['starter'].values()))
        self.assertEqual(len(gates['mutants']),5)
        self.assertEqual([r['change_active'] for r in gates['reference_trace']],[False,False,True,True])

    def test_reference_on_a_second_generated_variant_pair(self):
        for variant in ('stream','state'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);materialize(root,variant,reference=True)
                self.assertEqual(evaluate(root,92173,variant)['fraction'],1)

    def test_whole_document_oracle_hand_checked(self):
        original=csv_text([row('a',1,700),row('b',1,50)])
        revised=csv_text([row('a',3,-125,'travel'),row('b',2,'','','',op='delete')])
        stale=csv_text([row('a',2,999,'wrong'),row('b',1,888)])
        self.assertEqual(oracle_rows([original,revised,stale]),{
            'records':[{'id':'a','revision':3,'category':'travel','amount_cents':-125,'note':''}],
            'summary':{'total_cents':-125,'by_category':{'travel':-125}}})

    def test_format_normalizations_and_tools_cannot_escape_allowlist(self):
        actions,normalizations=decode('```json\n[{"actions":[{"tool":"finish"}]}]\n```')
        self.assertEqual(len(normalizations),2)
        for text in ('I will read the code. {"actions":[{"tool":"read","paths":["ledger/api.py"]}]}',
                     '[{"tool":"finish"}]','{"tool":"finish"}'):
            self.assertTrue(decode(text)[0])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);materialize(root,'stream')
            before=(root/'ledger/api.py').read_text()
            observations,_=perform(root,[{'tool':'write','files':{'../bad':'x','ledger/api.py':'broken'}}],1,'stream',False)
            self.assertIn('error',observations[0])
            self.assertEqual((root/'ledger/api.py').read_text(),before)
            observations,_=perform(root,[{'tool':'read','paths':['../../checker.py']}],1,'stream',False)
            self.assertIn('error',observations[0])

    def fake(self,replies,counts=None,prompts=None):
        iterator=iter(replies)
        def invoke(model,task,*args,**kwargs):
            if prompts is not None:prompts.append(task.prompt)
            text=next(iterator)
            frames=[{'type':'event','event':{'type':'model_request_start','model':model}},
                    {'type':'event','event':{'type':'model_request_end','model':model,'effort':'high'}},
                    {'type':'result','subtype':'success','finalText':text,'usage':counts or {'inputTokens':10,'outputTokens':1,'cacheReadTokens':0}}]
            return 0,'\n'.join(map(json.dumps,frames)),''
        return invoke

    def test_feedback_loop_changes_artifact_without_format_zero(self):
        final={k:v for k,v in sources('stream',reference=True).items() if k in ('ledger/parser.py','ledger/store.py','ledger/api.py')}
        replies=['not JSON',json.dumps({'actions':[{'tool':'read','paths':list(final)}]}),
                 '```json\n'+json.dumps([{'actions':[{'tool':'write','files':final},{'tool':'test'}]}])+'\n```',
                 json.dumps({'actions':[{'tool':'finish'}]})]
        usage={'cliInvocations':0,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
        prompts=[]
        with tempfile.TemporaryDirectory() as d,patch('evalkit.workflows.calibrate.invoke',self.fake(replies,prompts=prompts)):
            result=episode(Path(d),'test/model','stream',481,6,5,usage,1000)
        self.assertEqual(result['grade']['fraction'],1)
        self.assertEqual(result['protocol_errors'],1)
        self.assertEqual(usage['cliInvocations'],4)
        self.assertEqual(usage['observedModelRequests'],4)
        self.assertNotIn('Change request from the downstream consumer',prompts[1])
        self.assertIn('Change request from the downstream consumer',prompts[2])

    def test_response_budget_stops_stalling(self):
        response=json.dumps({'actions':[{'tool':'read','paths':['README.md']}]})
        usage={'cliInvocations':0,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
        with tempfile.TemporaryDirectory() as d,patch('evalkit.workflows.calibrate.invoke',self.fake([response]*3)):
            result=episode(Path(d),'test/model','state',481,3,5,usage,1000)
        self.assertEqual(usage['cliInvocations'],3)
        self.assertEqual(result['stop'],'response_budget')
        self.assertLess(result['grade']['fraction'],1)

    def test_aggregate_output_guard_prevents_further_calls(self):
        response=json.dumps({'actions':[{'tool':'read','paths':['README.md']}]})
        usage={'cliInvocations':0,'observedModelRequests':0,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
        with tempfile.TemporaryDirectory() as d,patch('evalkit.workflows.calibrate.invoke',self.fake([response],counts={'outputTokens':100})):
            result=episode(Path(d),'test/model','state',481,6,5,usage,1)
        self.assertEqual(usage['cliInvocations'],1)
        self.assertEqual(result['stop'],'aggregate_output_token_guard')
        self.assertIsNone(result['grade'])

    def test_total_request_budget_includes_adapter_setup_cost(self):
        usage={'cliInvocations':24,'observedModelRequests':24,'inputTokens':0,'outputTokens':0,'cacheReadTokens':0}
        with tempfile.TemporaryDirectory() as d,patch('evalkit.workflows.calibrate.invoke') as invoke:
            result=episode(Path(d),'test/model','state',481,6,5,usage,1000)
            invoke.assert_not_called()
        self.assertEqual(result['stop'],'aggregate_request_guard')

    def test_setup_exclusion_accounts_usage_and_rejects_scored_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);folder=p/'01-setup';folder.mkdir()
            (p/'results.json').write_text(json.dumps([{'grade':None,'change_delivered':False,'trace':[]}]))
            data=[{'type':'event','event':{'type':'model_request_start'}},
                  {'type':'event','event':{'type':'tool_denied'}},
                  {'type':'result','usage':{'inputTokens':100,'outputTokens':10,'cacheReadTokens':40}}]
            (folder/'turn-1.ndjson').write_text('\n'.join(map(json.dumps,data)))
            self.assertEqual(setup_usage(p)['outputTokens'],10)
            self.assertEqual(setup_usage(p)['cliInvocations'],1)
            (p/'results.json').write_text(json.dumps([{'grade':{'passed':0},'change_delivered':False}]))
            with self.assertRaises(ValueError):setup_usage(p)


if __name__=='__main__':unittest.main()
