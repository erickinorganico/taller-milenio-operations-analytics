"""Copy only the reviewed application allowlist into an immutable release directory."""
import argparse
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts.package_web import _collect
from scripts.deploy import release_id


def stage(install_root):
    root=Path(install_root).resolve()
    if any(p.casefold().startswith('onedrive') for p in root.parts):
        raise ValueError('Instala fuera de OneDrive.')
    if root.exists() and any(root.iterdir()) and not (root/'private/current.json').is_file() and not (root/'.install-in-progress').is_file():
        raise ValueError('Destino no vacío sin instalación Milenio; no se modifica.')
    root.mkdir(parents=True,exist_ok=True)
    (root/'.install-in-progress').touch()
    version=release_id()
    destination=root/'releases'/version[:16]
    entries=_collect()
    destination.mkdir(parents=True,exist_ok=True)
    for name,source in entries.items():
        target=destination/name
        if target.exists() and target.read_bytes()!=source.read_bytes():
            raise ValueError('Release existente modificada. No se sobrescribe.')
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with source.open("rb") as reader, target.open("wb") as writer:
                shutil.copyfileobj(reader,writer)
    return {'release_dir':str(destination),'release_id':version}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--install-root',required=True)
    print(json.dumps(stage(parser.parse_args().install_root)))
