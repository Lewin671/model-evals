import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evalkit.workflows.importer import API_REFERENCE,csv_text,materialize,oracle_rows,row,sources
from evalkit.workflows.checker import evaluate
from evalkit.workflows.calibrate import episode,preflight
from evalkit.workflows.tools import decode,perform


class ImporterWorkflow(unittest.TestCase):
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


if __name__=='__main__':unittest.main()
