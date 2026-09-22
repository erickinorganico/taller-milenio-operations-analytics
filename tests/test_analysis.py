import hashlib
import tempfile
import unittest
from pathlib import Path
from milenio.analysis import analyze
from milenio.contracts import DEMO_NOW
from milenio.fixtures import make_fixture
from milenio.presentation import render_reports

class AnalysisTests(unittest.TestCase):
    def test_money_unknown_and_evidence(self):
        r=analyze(make_fixture(),DEMO_NOW)
        self.assertEqual(r['administracion']['money']['invoiced_cents'],695000)
        self.assertEqual(r['administracion']['money']['paid_cents'],185000)
        self.assertEqual(r['administracion']['money']['receivable_cents'],510000)
        self.assertEqual(r['flotillas']['commercial']['pipeline_cents'],2030000)
        self.assertTrue(r['taller']['parts']['waiting_order_evidence'])
        d=make_fixture();d['leads']=[]
        self.assertIsNone(analyze(d)['particulares']['journey']['won']['rate'])
    def test_reports_readable_and_repeatable(self):
        r=analyze(make_fixture(),DEMO_NOW)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            pa=render_reports(r,a); render_reports(r,b)
            self.assertGreaterEqual(len(pa),13)
            for name in ('particulares.md','taller.md','flotillas.md','gruas.md','administracion.md','informe_ejecutivo.html','charts/particulares.svg','charts/taller.svg','charts/flotillas.svg','charts/gruas.svg','charts/finanzas.svg','charts/particulares.png','charts/taller.png','charts/flotillas.png','charts/gruas.png','charts/finanzas.png'):
                one,two=Path(a,name),Path(b,name);self.assertTrue(one.exists());self.assertGreater(one.stat().st_size,100);self.assertEqual(hashlib.sha256(one.read_bytes()).hexdigest(),hashlib.sha256(two.read_bytes()).hexdigest())
    def test_median_aging_and_sla_eligibility(self):
        r=analyze(make_fixture(),DEMO_NOW)
        self.assertEqual(r['taller']['wip']['median_open_hours'],74.0)
        self.assertEqual(sum(r['administracion']['aging']['buckets_cents'].values()),r['administracion']['money']['receivable_cents'])
        self.assertLessEqual(r['flotillas']['contracted']['sla_eligibility']['numerator'],r['flotillas']['contracted']['sla_eligibility']['denominator'])
        d=make_fixture();d['tows'][0]['closed_at']=None
        self.assertIsNotNone(analyze(d)['gruas']['timing']['closed_with_duration'])
if __name__=='__main__': unittest.main()
