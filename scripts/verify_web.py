"""Run the operational suite on disposable data and write a reproducible receipt."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='artifacts/v5-verification.json')
    args=parser.parse_args()
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='milenio-v5-verification-') as temporary:
        os.environ['MILENIO_MODE']='test'
        os.environ['MILENIO_DATA_DIR']=str(Path(temporary)/'test')
        os.environ['DJANGO_SETTINGS_MODULE']='milenio_web.settings'
        import django
        django.setup()
        from django.core.management import call_command
        from django.test.runner import DiscoverRunner
        import unittest
        class RecordResult(unittest.TextTestResult):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)
                self.names=[]
            def startTest(self,test):
                self.names.append(test.id())
                super().startTest(test)
        class TextRunner(unittest.TextTestRunner):
            resultclass=RecordResult
        class EvidenceRunner(DiscoverRunner):
            test_runner=TextRunner
            def run_suite(self,suite,**kwargs):
                self.record=super().run_suite(suite,**kwargs)
                return self.record
        runner=EvidenceRunner(verbosity=1,interactive=False)
        errors=runner.run_tests(['workshop.tests'])
        result=runner.record
        stream=io.StringIO()
        checks=True
        try:
            call_command('check',stdout=stream,stderr=stream)
            call_command('makemigrations',check=True,dry_run=True,stdout=stream,stderr=stream)
        except (Exception,SystemExit) as exc:
            checks=False
            stream.write(str(exc))
        dependencies={}
        for line in (ROOT/'requirements-web.txt').read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.startswith('#'): continue
            name,expected=line.split('==')
            actual=importlib.metadata.version(name)
            dependencies[name]={'required':expected,'installed':actual,'ok':actual==expected}
        files=[]
        for folder in ['workshop','milenio_web']:
            files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.html','.css','.js'})
        files.extend(ROOT/p for p in ['manage.py','requirements-web.txt','scripts/run_web.py','scripts/package_web.py','scripts/verify_web.py','scripts/export_web_contracts.py','Setup-Web.ps1','Iniciar-Milenio.cmd','Iniciar-Demo.cmd'])
        source={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}
        receipt={'version':'5.0','status':'pass' if not errors and checks and all(d['ok'] for d in dependencies.values()) else 'fail','tested_at_utc':datetime.now(timezone.utc).isoformat(),'tests':{'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)},'checks_and_migrations':stream.getvalue().replace(str(ROOT),'<project>'),'dependencies':dependencies,'source_sha256':source,'native_inference':'not_exercised_by_this_suite','data_scope':'disposable synthetic fixtures; no client data','limitations':['Browser/manual checks are recorded separately','No client acceptance or production deployment is asserted','Mocked native runs do not prove real model inference']}
        output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        junit=ET.Element('testsuite',name='milenio-v5',tests=str(result.testsRun),failures=str(len(result.failures)),errors=str(len(result.errors)),skipped=str(len(result.skipped)))
        failures={test.id():info for test,info in result.failures}
        error_map={test.id():info for test,info in result.errors}
        skipped={test.id():reason for test,reason in result.skipped}
        for name in result.names:
            case=ET.SubElement(junit,'testcase',name=name)
            if name in failures or name in error_map:
                ET.SubElement(case,'failure' if name in failures else 'error').text=(failures.get(name) or error_map[name]).replace(str(ROOT),'<project>')
            if name in skipped: ET.SubElement(case,'skipped').text=skipped[name]
        ET.ElementTree(junit).write(output.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
        print(json.dumps({'status':receipt['status'],'tests':receipt['tests'],'receipt':str(output)},ensure_ascii=False))
        return 0 if receipt['status']=='pass' else 1

if __name__=='__main__': raise SystemExit(main())
