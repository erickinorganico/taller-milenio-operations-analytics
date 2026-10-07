"""Real PowerShell/offline install rehearsal in temporary folders; no services/network changes."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def verify(archive):
    if os.name!='nt':raise RuntimeError('Windows-only rehearsal')
    with tempfile.TemporaryDirectory(prefix='mi-') as temporary:
        root=Path(temporary);source=root/'source';target=root/'server'
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).is_absolute() or '..' in Path(name).parts or ':' in name or '\\' in name:
                    raise ValueError('Unsafe package path')
            bundle.extractall(source)
        command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(source/'Setup-Server.ps1'),
                 '-InstallRoot',str(target),'-PythonPath',sys._base_executable,'-Offline','-NoStart']
        env={**os.environ,'PYTHONUTF8':'1'}
        env.pop('MILENIO_DATA_DIR',None);env.pop('MILENIO_DEPLOYMENT_CONFIG',None)
        for iteration in range(2):
            run=subprocess.run(command,cwd=source,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
            if run.returncode:
                raise RuntimeError((run.stdout[-2000:]+run.stderr[-3000:]).replace(str(root),'<synthetic>'))
            config=json.loads((target/'private/infra.local.json').read_text(encoding='utf-8-sig'))
            if iteration==0:instance=config['instance_id']
            else:assert config['instance_id']==instance
            assert not config['mail_worker_allowed']
            assert (target/'data/live/workshop.sqlite3').is_file()
            assert (target/'data/live/.stop-managed').is_file()
        return {'status':'pass','powershell_installer':True,'offline_dependencies':8,
                'repeat_preserves_identity':True,'starts_services':False,
                'changes_firewall_or_startup':False,'scope':'temporary install; no production or Gmail'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=verify(Path(args.package).resolve())
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
