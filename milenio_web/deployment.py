"""Private installation identity and guards, without importing Django."""
import getpass
import json
import os
import socket
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def config_path():
    return Path(os.environ.get('MILENIO_DEPLOYMENT_CONFIG') or ROOT / 'private/infra.local.json')


def read_config(required=False):
    path = config_path()
    if not path.is_file():
        if required:
            raise RuntimeError('Equipo sin asignar. Ejecuta Setup-Server.ps1 o Setup-Client.ps1.')
        return None
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if config.get('schema_version') != 2:
        raise RuntimeError('Configuración de infraestructura incompatible; usa el instalador v2.')
    return config


def guard_server(config=None):
    config = config or read_config(required=True)
    if config.get('role') != 'server':
        raise RuntimeError('Este equipo es cliente: no puede crear base ni ejecutar workers.')
    if config.get('expected_hostname', '').casefold() != socket.gethostname().casefold():
        raise RuntimeError('La configuración pertenece a otro equipo. No clones la identidad del servidor.')
    if config.get('windows_user', '').casefold() != getpass.getuser().casefold():
        raise RuntimeError('Usuario de ejecución distinto al instalado; protege la identidad DPAPI.')
    uuid.UUID(config['instance_id'])
    data = Path(config['data_dir']).resolve()
    if data.name != 'live' or any(p.casefold().startswith('onedrive') for p in data.parts):
        raise RuntimeError('Datos live deben estar en disco local, fuera de OneDrive.')
    if Path(os.environ.get('MILENIO_DATA_DIR', str(data))).resolve() != data:
        raise RuntimeError('La base solicitada no coincide con la instalación asignada.')
    return config


def apply_environment(config):
    guard_server(config)
    os.environ.update(MILENIO_MODE='live', MILENIO_DATA_DIR=config['data_dir'],
                      MILENIO_INSTANCE_ID=config['instance_id'],
                      MILENIO_RELEASE=config.get('release_id', 'unknown'),
                      MILENIO_DEPLOYMENT_CONFIG=str(config_path().resolve()))


def guard_configured_live():
    if os.environ.get('MILENIO_MODE', 'live') == 'live':
        config = read_config()
        if config:
            apply_environment(config)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
