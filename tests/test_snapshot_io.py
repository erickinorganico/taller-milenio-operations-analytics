import json, subprocess, sys, tempfile, unittest
from pathlib import Path
from milenio.fixtures import make_fixture
from milenio.importers import export_csv
from milenio.snapshot_io import load_snapshot
from milenio.contracts import FIELDS

class SnapshotTests(unittest.TestCase):
 def write(self,d):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);p=Path(td.name)
  for k in FIELDS:(p/(k+'.csv')).write_text(export_csv(k,d[k]),encoding='utf8')
  return p
 def test_roundtrip(self):
  d=make_fixture();self.assertEqual(load_snapshot(self.write(d)),d)
 def test_missing_and_bad_later_row(self):
  p=self.write(make_fixture());(p/'parts.csv').unlink()
  with self.assertRaises(ValueError):load_snapshot(p)
  p=self.write(make_fixture());(p/'customers.csv').write_text((p/'customers.csv').read_text()+'BAD,Name,particular,true,x\n',encoding='utf8')
  with self.assertRaises(ValueError):load_snapshot(p)
 def test_invalid_join_formula_and_metadata(self):
  p=self.write(make_fixture());s=(p/'vehicles.csv').read_text();(p/'vehicles.csv').write_text(s.replace('C-001','NOPE',1),encoding='utf8')
  with self.assertRaises(ValueError):load_snapshot(p)
  p=self.write(make_fixture());lines=(p/'customers.csv').read_text().splitlines();cells=lines[1].split(',');cells[1]='=formula';lines[1]=','.join(cells);(p/'customers.csv').write_text('\n'.join(lines)+'\n',encoding='utf8')
  with self.assertRaises(ValueError):load_snapshot(p)
  p=self.write(make_fixture());s=(p/'customers.csv').read_text();(p/'customers.csv').write_text(s.replace('id,name,segment,consent,contact,synthetic','id,name,segment,consent,contact,synthetic,version').replace('C-001,','C-001,',1).replace(',true\n',',true,zero\n',1),encoding='utf8')
  with self.assertRaises(ValueError):load_snapshot(p)
 def test_cli_csv_snapshot_receipt(self):
  p=self.write(make_fixture());td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);out=Path(td.name)/'reports'
  run=subprocess.run([sys.executable,'-m','milenio','analyze','--input',str(p),'--output',str(out)],capture_output=True,text=True,encoding='utf8')
  self.assertEqual(run.returncode,0,run.stderr); receipt=json.loads((out/'receipt.json').read_text(encoding='utf8'))
  self.assertEqual(len(receipt['input_sha256']),25);self.assertEqual(receipt['checks']['history'],'unknown')
  verify=subprocess.run([sys.executable,'-m','milenio','verify-receipt','--input',str(out)],capture_output=True,text=True,encoding='utf8');self.assertEqual(verify.returncode,0,verify.stderr)
if __name__=='__main__':unittest.main()
