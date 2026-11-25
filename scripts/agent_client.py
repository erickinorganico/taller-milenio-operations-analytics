"""Call the central agent API via verified HTTPS or the local SSH tunnel."""
import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('No se permiten redirecciones con una credencial de agente.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='private/infra.local.json')
    parser.add_argument('--workshop',action='store_true',help='Usar el acceso limitado del taller en su dominio HTTPS.')
    parser.add_argument('--credential',required=True)
    parser.add_argument('--request',required=True,help='Archivo JSON privado, sin token')
    args=parser.parse_args()
    credential=json.loads(Path(args.credential).read_text(encoding='utf-8-sig'))
    payload=json.loads(Path(args.request).read_text(encoding='utf-8-sig'))
    if args.workshop:
        if 'workshop_url' not in credential:
            parser.error('La operación requiere una credencial específica del taller.')
        url=credential['workshop_url']
        config={}
        endpoint='/api/taller/v1/accion'
    else:
        if 'workshop_url' in credential:
            parser.error('Esta credencial requiere --workshop.')
        config=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
        url=config['central_url'].rstrip('/')
        payload['instance_id']=config['instance_id']
        endpoint='/agent/v1/action'
    parsed=urlsplit(url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('URL inválida')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname=='127.0.0.1' and config.get('transport')=='ssh-loopback'):
        raise ValueError('Se requiere HTTPS o túnel SSH local.')
    request=urllib.request.Request(url.rstrip('/')+endpoint,data=json.dumps(payload).encode(),headers={
        'Authorization':'Bearer '+credential['token'],'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    try:
        with opener.open(request,timeout=30) as response:
            print(response.read(1024*1024).decode())
    except urllib.error.HTTPError as exc:
        try:
            code=json.loads(exc.read(8192)).get('error', 'request_failed')
        except (ValueError, AttributeError):
            code='request_failed'
        print(f'HTTP {exc.code}: {code}', file=sys.stderr)
        return 1


if __name__=='__main__': sys.exit(main())
