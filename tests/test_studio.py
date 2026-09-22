import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import openpyxl

from milenio.studio import build_studio, verify_studio


class StudioTests(unittest.TestCase):
    def test_imported_snapshot_does_not_invent_history(self):
        from milenio.fixtures import make_fixture
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'snapshot.json'
            source.write_text(json.dumps(make_fixture()),encoding='utf8')
            result=build_studio(root/'delivery',input_path=source)
            self.assertEqual(result['worksheets'],36)
            data=json.loads((root/'delivery/analysis.json').read_text(encoding='utf8'))
            self.assertEqual(data['summary']['history_coverage']['numerator'],0)
            self.assertEqual(data['marts']['mart_process_waits'],[])
            self.assertEqual(data['summary']['explicit_journey_links'],0)
            self.assertEqual(verify_studio(root/'delivery')['status'],'pass')

    def test_integrated_delivery_reconciles_sources_workbook_and_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'delivery'
            result = build_studio(output)
            self.assertEqual((result['physical_source_tables'],result['marts'],result['processes'],result['worksheets']),(27,6,6,36))
            self.assertEqual(verify_studio(output)['status'],'pass')
            analysis = json.loads((output/'analysis.json').read_text(encoding='utf8'))['summary']
            connection = sqlite3.connect(output/'warehouse.sqlite')
            try:
                billed = connection.execute("SELECT SUM(amount_cents) FROM invoices WHERE status='issued'").fetchone()[0]
                paid = connection.execute('SELECT SUM(amount_cents) FROM payments').fetchone()[0]
                self.assertEqual(analysis['invoiced_cents'],billed)
                self.assertEqual(analysis['paid_cents'],paid)
                self.assertEqual(analysis['receivable_cents'],billed-paid)
                self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(),[])
            finally: connection.close()
            book = openpyxl.load_workbook(output/'Milenio_Analisis.xlsx',data_only=True)
            try:
                cover=book['INICIO']
                self.assertEqual([cover[c].value for c in ('C8','C9','C10','C11','C13','C14')],
                    [billed/100,paid/100,(billed-paid)/100,0,analysis['delivered'],analysis['open_orders']])
                self.assertFalse([(sheet.title,cell.coordinate) for sheet in book for row in sheet for cell in row if cell.data_type=='e'])
            finally: book.close()
            self.assertEqual(len(list((output/'processes').glob('*.svg'))),6)
            for agent in (output/'agent_runs').iterdir():
                payload=json.loads((agent/'result.json').read_text(encoding='utf8'))
                self.assertFalse(payload['model_invoked'])
                self.assertFalse(payload['external_execution'])
            before=(output/'receipt.json').read_bytes()
            with self.assertRaises(ValueError): build_studio(output)
            self.assertEqual((output/'receipt.json').read_bytes(),before)
            (output/'analysis.json').write_text('{}',encoding='utf8')
            with self.assertRaises(ValueError): verify_studio(output)


if __name__=='__main__': unittest.main()
