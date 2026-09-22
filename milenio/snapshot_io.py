"""Strict all-table synthetic CSV snapshot loader (stdlib only)."""
import csv, json
from pathlib import Path
from datetime import datetime
from .contracts import FIELDS, DEMO_NOW
from .domain import validate_record, validate_dataset

MAX_BYTES=1_000_000; MAX_ROWS=5000
META=("version","created_at","updated_at")
def _parse(v,spec):
    v='' if v is None else v.strip()
    optional=spec.endswith('?'); base=spec.rstrip('?')
    if not v:
        if optional:return None
        raise ValueError('required value')
    if v.startswith("'") and len(v)>1 and v[1] in '=+-@':v=v[1:]
    if base in ('str','state') or base.startswith(('ref:','enum:')):
        if v.startswith(('=','+','-','@')): raise ValueError('formula-like value')
        return v
    if base=='date':
        if v.startswith(('=','+','-','@')): raise ValueError('formula-like value')
        if datetime.fromisoformat(v.replace('Z','+00:00')).tzinfo is None:raise ValueError('timezone required')
        return v
    if base=='bool':
        if v not in ('true','false'):raise ValueError('expected true or false')
        return v=='true'
    if base in ('int','money','positive','signed'):
        if not v.lstrip('-').isdigit():raise ValueError('integer required')
        n=int(v)
        if base=='positive' and n<=0:raise ValueError('positive required')
        return n
    if base=='list':
        x=json.loads(v)
        if not isinstance(x,list):raise ValueError('JSON list required')
        return x
    raise ValueError('unsupported type')

def load_snapshot(directory)->dict:
    root=Path(directory).resolve()
    if not root.is_dir():raise ValueError('snapshot directory required')
    data={}
    for kind,fields in FIELDS.items():
        path=(root/(kind+'.csv')).resolve()
        if path.parent!=root or not path.is_file():raise ValueError(f'missing required table: {kind}.csv')
        if path.stat().st_size>MAX_BYTES:raise ValueError(f'{kind}: exceeds 1MB')
        with path.open('r',encoding='utf-8-sig',newline='') as fh:
            reader=csv.DictReader(fh); headers=reader.fieldnames
            if not headers or len(headers)!=len(set(headers)):raise ValueError(f'{kind}: invalid headers')
            allowed={'id','synthetic',*fields,*META}
            if set(headers)-allowed:raise ValueError(f'{kind}: unknown column')
            required={'id','synthetic',*fields}
            if required-set(headers):raise ValueError(f'{kind}: missing required column')
            rows=[]; seen=set()
            for n,row in enumerate(reader,2):
                if n>MAX_ROWS+1:raise ValueError(f'{kind}: too many rows')
                if None in row:raise ValueError(f'{kind}:{n}: too many cells')
                ident=(row.get('id') or '').strip()
                if ident in seen or not ident:raise ValueError(f'{kind}:{n}: duplicate or blank id')
                seen.add(ident)
                if row.get('synthetic')!='true':raise ValueError(f'{kind}:{n}: synthetic must be true')
                try: values={f:_parse(row.get(f),s) for f,s in fields.items()}
                except Exception as exc:raise ValueError(f'{kind}:{n}: {exc}') from None
                rec={'id':ident,'synthetic':True,'version':int(row.get('version') or 1),'created_at':row.get('created_at') or DEMO_NOW,'updated_at':row.get('updated_at') or DEMO_NOW,**values}
                try:validate_record(kind,rec)
                except Exception as exc:raise ValueError(f'{kind}:{n}: {exc}') from None
                rows.append(rec)
            data[kind]=rows
    validate_dataset(data)
    return data
