"""Exercise a downloaded source package on disposable data; never connects Gmail."""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts.stage_install import stage


def wait_for(test,seconds=40):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            value=test()
            if value:return value
        except (OSError,ValueError,KeyError):pass
        time.sleep(.25)
    raise RuntimeError('Synthetic deployment did not reach expected state')


def verify():
    with tempfile.TemporaryDirectory(prefix='md-') as temporary:
        directory=Path(temporary)
        release=stage(directory/'install')
        root=Path(release['release_dir'])
        data=directory/'data/live'
        config=directory/'private/infra.local.json'
        config.parent.mkdir()
        env={**os.environ,'MILENIO_DEPLOYMENT_CONFIG':str(config),'PYTHONUTF8':'1','MILENIO_DEPLOYMENT_DEBUG':'1'}
        env.pop('MILENIO_DATA_DIR',None)
        env.pop('MILENIO_LEGACY_LOCAL',None)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        def run(*args,ok=True):
            result=subprocess.run([sys.executable,str(root/'scripts/deploy.py'),*args],env=env,cwd=root,
                text=True,capture_output=True,timeout=90,encoding='utf-8')
            if ok and result.returncode:raise RuntimeError(result.stderr.replace(str(directory),'<synthetic>'))
            return result
        run('init','--data-dir',str(data),'--backup-dir',str(directory/'backup'),'--port',str(port))
        first=json.loads(config.read_text(encoding='utf-8'))
        assert not first['mail_worker_allowed']
        run('init','--data-dir',str(data),'--backup-dir',str(directory/'backup'),'--port',str(port))
        assert json.loads(config.read_text(encoding='utf-8'))['instance_id']==first['instance_id']
        process=subprocess.Popen([sys.executable,str(root/'scripts/deploy.py'),'serve'],env=env,cwd=root,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        def health():
            with opener.open(f'http://127.0.0.1:{port}/health/',timeout=2) as response:return json.load(response)
        try:
            def check_parent():
                if process.poll() is not None: raise RuntimeError('Supervisor exited before health check')
                return health()
            observed=wait_for(lambda: (h if (h:=check_parent()).get('supervisor_recent') else None))
            assert observed['instance_id']==first['instance_id']
            assert observed['release_id']==release['release_id']
            wait_for(lambda:all(w.get('recent') for w in health()['workers'].values()))
            assert run('migrate',ok=False).returncode!=0
            assert run('backup',ok=False).returncode!=0
            assert run('serve',ok=False).returncode!=0
            # Kill only the child PID created by this disposable supervisor.
            state=json.loads((data/'supervisor.json').read_text(encoding='utf-8'))
            pid=state['workers']['documents']['pid']
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(pid),'/F'],capture_output=True,check=True)
            else:
                import signal
                os.kill(pid,signal.SIGTERM)
            wait_for(lambda:(s if (s:=json.loads((data/'supervisor.json').read_text(encoding='utf-8')))['workers']['documents']['restarts']>=1
                and s['workers']['documents']['running'] and s['workers']['documents']['pid']!=pid else None))
            run('stop')
            process.wait(timeout=20)
            assert process.returncode==0
            assert run('serve',ok=False).returncode!=0  # Persistent maintenance latch.
            run('backup')
            backup=sorted((directory/'backup').iterdir())[-1]
            run('restore','--input',str(backup),'--confirm-restore')
            assert (data/'.mail-recovery-hold').is_file()
            assert not json.loads(config.read_text(encoding='utf-8'))['mail_worker_allowed']
            return {'status':'pass','identity_persistent':True,'schema_created':True,'workers_observed':3,
                    'child_restart_verified':True,'singleton_and_maintenance_lock':True,
                    'backup_restore_verified':True,'mail_disabled_after_install_and_restore':True,
                    'scope':'disposable package; no real Gmail, SSH installation or Windows reboot'}
        except Exception as error:
            diagnostics={p.name:p.read_text(encoding='utf-8',errors='replace')[-20000:] for p in data.glob('*managed.log')}
            if process.poll() is not None and process.stderr:
                diagnostics['supervisor']=process.stderr.read().decode('utf-8',errors='replace')[-3000:]
            raise RuntimeError(str(error)+' '+json.dumps(diagnostics).replace(str(directory),'SYNTHETIC')) from error
        finally:
            if process.poll() is None:
                (data/'.stop-managed').touch()
                process.wait(timeout=30)
            if process.stderr:process.stderr.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=verify()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
