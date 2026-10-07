"""Repeatable server lifecycle. No campaign is enabled by installation or recovery."""
import argparse
import getpass
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from milenio_web.deployment import config_path, read_config, guard_server, apply_environment, write_json


def release_id():
    # Works for a downloaded ZIP without .git. Hash the deployable source set.
    from scripts.package_web import _collect
    digest = hashlib.sha256()
    for name, path in sorted(_collect().items()):
        digest.update(name.encode() + b'\0' + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def command(*args):
    subprocess.run([sys.executable, str(ROOT / 'manage.py'), *args], cwd=ROOT, check=True)


def initialize(data_dir, backup_dir, port):
    path = config_path()
    if path.exists():
        config = guard_server()
        if Path(config['data_dir']).resolve() != Path(data_dir).resolve() or config['port'] != port:
            raise RuntimeError('Instalación existente distinta: no se reemplaza configuración ni base.')
        return config
    data, backup = Path(data_dir).resolve(), Path(backup_dir).resolve()
    if data.exists() and any(data.iterdir()):
        raise RuntimeError('La carpeta contiene datos. Usa un procedimiento de migración/restauración explícito.')
    if backup == data or backup.is_relative_to(data) or data.is_relative_to(backup):
        raise RuntimeError('Respaldo y datos deben estar en carpetas separadas.')
    if not 1024 <= port <= 65535:
        raise ValueError('Puerto fuera de rango.')
    config = dict(schema_version=2, role='server', instance_id=str(uuid.uuid4()),
                  expected_hostname=socket.gethostname(), windows_user=getpass.getuser(),
                  data_dir=str(data), backup_dir=str(backup), port=port,
                  central_url=f'http://127.0.0.1:{port}', transport='ssh-loopback',
                  mail_worker_allowed=False, release_id=release_id())
    guard_server(config)
    data.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)
    write_json(path, config)
    return config


def setup_django(config):
    apply_environment(config)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'milenio_web.settings'
    import django
    django.setup()


def backup_locked(config):
    from django.core.management import call_command
    destination = Path(config['backup_dir']) / (time.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8])
    call_command('backup_workshop', output=str(destination))
    write_json(Path(config['data_dir']) / 'last-backup.json', {'at':time.time(), 'path':str(destination)})
    return destination


def maintain(config, operation):
    setup_django(config)
    from django.core.management import call_command
    from workshop.management.commands.backup_workshop import instance_lock
    with instance_lock(Path(config['data_dir'])):
        if operation == 'backup':
            return backup_locked(config)
        if (Path(config['data_dir']) / 'workshop.sqlite3').is_file():
            backup_locked(config)
        call_command('migrate', interactive=False)
        call_command('check')
        config['release_id'] = release_id()
        write_json(config_path(), config)


def serve(config):
    """Parent holds singleton lock. Each child is restarted with bounded backoff."""
    setup_django(config)
    from django.core.management import call_command
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connection
    from workshop.management.commands.backup_workshop import instance_lock
    from scripts.run_web import stop_automation_worker
    data = Path(config['data_dir'])
    stop = data / '.stop-managed'
    if stop.exists():
        raise RuntimeError('Instalación detenida intencionalmente. Usa deploy.py resume para habilitar arranque.')
    if config['release_id'] != release_id():
        raise RuntimeError('El código cambió. Detén el servidor y ejecuta migrate para verificar la versión.')
    children = {}
    with instance_lock(data):
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise RuntimeError('Migraciones pendientes: ejecutar deploy.py migrate antes de iniciar.')
        call_command('check')
        connection.close()
        commands = {'web':['scripts/managed_web.py', '--port',str(config['port'])],
                    'analytics':['manage.py','run_automations','--watch-parent'],
                    'documents':['manage.py','run_document_captures','--watch-parent'],
                    'mail':['manage.py','run_mail','--watch-parent']}
        state = {name:{'restarts':0,'retry_at':0} for name in commands}
        try:
            while not stop.exists():
                for name, args in commands.items():
                    entry = children.get(name)
                    if entry and entry[0].poll() is not None:
                        stop_automation_worker(*entry)
                        del children[name]
                        state[name]['restarts'] += 1
                        state[name]['retry_at'] = time.time() + min(60, 2 ** min(state[name]['restarts'], 6))
                    if name not in children and time.time() >= state[name]['retry_at']:
                        log_path = data / (name + '-managed.log')
                        if log_path.exists() and log_path.stat().st_size > 5_000_000:
                            log_path.replace(log_path.with_suffix('.previous.log'))
                        log = log_path.open('ab')
                        options = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                        try:
                            process = subprocess.Popen([sys.executable, *args], cwd=ROOT, stdin=subprocess.PIPE,
                                stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ,'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8'}, **options)
                        except Exception:
                            log.close()
                            raise
                        children[name] = process, log
                    state[name]['running'] = name in children and children[name][0].poll() is None
                    state[name]['pid'] = children[name][0].pid if name in children else None
                write_json(data / 'supervisor.json', {'at':time.time(),'instance_id':config['instance_id'],
                    'release_id':config['release_id'],'workers':state})
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            for child in children.values():
                stop_automation_worker(*child)
            write_json(data / 'supervisor.json', {'at':time.time(),'stopped':True,'workers':{}})


def main():
    if len(sys.argv)>1 and sys.argv[1]=='manage':
        allowed={'connect_gmail','agent_access','import_commercial_catalog','deployment_mail','remote_ready','mail_status','createsuperuser','check'}
        if len(sys.argv)<3 or sys.argv[2] not in allowed:
            raise ValueError('Comando de administración no permitido por este wrapper; usa las acciones de mantenimiento documentadas.')
        apply_environment(guard_server())
        command(*sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init','migrate','serve','stop','resume','backup','status','restore','manage'])
    parser.add_argument('--data-dir')
    parser.add_argument('--backup-dir')
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--input')
    parser.add_argument('--confirm-restore', action='store_true')
    args, extra = parser.parse_known_args()
    if extra and args.action != 'manage': parser.error('Argumentos desconocidos')
    if args.action == 'init':
        if not args.data_dir or not args.backup_dir: parser.error('init requiere data-dir y backup-dir')
        config = initialize(args.data_dir,args.backup_dir,args.port)
        maintain(config,'migrate')
    else:
        config = guard_server()
        if args.action == 'status':
            print(json.dumps({'role':config['role'],'instance_id':config['instance_id'],
                             'release_id':config['release_id'],'port':config['port']},indent=2))
        elif args.action == 'stop':
            (Path(config['data_dir']) / '.stop-managed').touch()
            # Wait for the actual exclusive lock, not for a stale heartbeat.
            setup_django(config)
            from workshop.management.commands.backup_workshop import instance_lock
            from django.core.management.base import CommandError
            for _ in range(60):
                try:
                    with instance_lock(Path(config['data_dir'])): return
                except CommandError: time.sleep(1)
            raise RuntimeError('No se detuvo en 60 s; no continúes con mantenimiento.')
        elif args.action == 'resume':
            (Path(config['data_dir']) / '.stop-managed').unlink(missing_ok=True)
        elif args.action == 'serve': serve(config)
        elif args.action in ('backup','migrate'): maintain(config,args.action)
        elif args.action == 'manage':
            apply_environment(config)
            command(*extra)
        elif args.action == 'restore':
            if not args.input or not args.confirm_restore: parser.error('restore requiere input y confirm-restore')
            setup_django(config)
            # Latch before replacing data: even an interrupted restore cannot resume Gmail.
            (Path(config['data_dir']) / '.mail-recovery-hold').touch()
            config['mail_worker_allowed'] = False
            write_json(config_path(),config)
            from django.core.management import call_command
            call_command('restore_workshop', input=args.input, confirm_restore=True)
            from commercial.models import Mailbox
            Mailbox.objects.update(enabled=False,connected=False)
            print('Restaurado con correo bloqueado. Conciliar Gmail y reautorizar antes de reactivar.')


if __name__ == '__main__':
    try: main()
    except Exception as error:
        if os.environ.get('MILENIO_DEPLOYMENT_DEBUG') == '1':
            import traceback
            traceback.print_exc()
        print(f'Despliegue detenido: {error}',file=sys.stderr)
        raise SystemExit(1)
