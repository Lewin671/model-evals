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
