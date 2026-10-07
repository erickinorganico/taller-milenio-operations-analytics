"""Per-worker heartbeat; started cycles are distinguished from completed work."""
import time
from django.conf import settings
from .deployment import write_json


def heartbeat(name, state):
    write_json(settings.DATA_DIR / ('heartbeat-' + name + '.json'), {'at':time.time(),'state':state})


def status():
    import json
    import os
    result={'instance_id':os.environ.get('MILENIO_INSTANCE_ID',''),
            'release_id':os.environ.get('MILENIO_RELEASE',''),'workers':{}}
    try:
        supervisor=json.loads((settings.DATA_DIR/'supervisor.json').read_text(encoding='utf-8'))
        result['supervisor_recent']=time.time()-supervisor['at']<15 and not supervisor.get('stopped',False)
    except (OSError,ValueError,KeyError):
        result['supervisor_recent']=False
    for name in ('analytics','documents','mail'):
        try:
            record=json.loads((settings.DATA_DIR/('heartbeat-'+name+'.json')).read_text(encoding='utf-8'))
            record['age_seconds']=round(max(0,time.time()-record.pop('at')))
            record['recent']=record['age_seconds']<180
        except (OSError,ValueError,KeyError): record={'recent':False,'state':'unknown'}
        result['workers'][name]=record
    return result
