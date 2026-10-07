"""Call the central agent API via verified HTTPS or the local SSH tunnel."""
import argparse
import json
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('No se permiten redirecciones con una credencial de agente.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='private/infra.local.json')
    parser.add_argument('--credential',required=True)
    parser.add_argument('--request',required=True,help='Archivo JSON privado, sin token')
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    url=config['central_url'].rstrip('/')
    parsed=urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
        raise ValueError('URL inválida')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname=='127.0.0.1' and config.get('transport')=='ssh-loopback'):
        raise ValueError('Se requiere HTTPS o túnel SSH local.')
    credential=json.loads(Path(args.credential).read_text(encoding='utf-8-sig'))
    payload=json.loads(Path(args.request).read_text(encoding='utf-8-sig'))
    payload['instance_id']=config['instance_id']
    request=urllib.request.Request(url+'/agent/v1/action',data=json.dumps(payload).encode(),headers={
        'Authorization':'Bearer '+credential['token'],'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(request,timeout=30) as response:
        print(response.read(1024*1024).decode())


if __name__=='__main__': main()
