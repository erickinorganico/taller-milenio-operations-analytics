"""Package the fictional client walkthrough for reading without a Python runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from milenio.client_delivery import verify_client
from milenio.studio import verify_studio


def build(output):
    output = Path(output)
    if output.exists():
        raise ValueError('La salida ya existe')
    for name in ('semana_01','semana_02'):
        if verify_client(ROOT / 'examples/client_delivery' / name)['synthetic'] is not True:
            raise ValueError('El kit público sólo admite ejemplos sintéticos')
    verify_studio(ROOT / 'artifacts/workbench-v2')
    files = [ROOT / name for name in ('CLIENTE.html','README.md','LICENSE')]
    for folder in ('examples/client_data','examples/client_delivery','docs','artifacts/workbench-v2','specs'):
        files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file())
    for file in files:
        if file.is_symlink() or not file.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Ruta no permitida')
    manifest = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(files): archive.write(file,file.relative_to(ROOT).as_posix())
        archive.writestr('KIT-MANIFEST.json',json.dumps({'synthetic':True,'entries_sha256':manifest},indent=2,sort_keys=True))
        archive.writestr('ABRIR-PRIMERO.txt','Extraiga todo el ZIP. Abra CLIENTE.html. La muestra es ficticia. Para generar nuevos análisis descargue el paquete completo de la misma versión.\n')
    return {'files':len(files),'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    print(json.dumps(build(parser.parse_args().output)))
