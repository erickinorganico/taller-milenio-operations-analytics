"""Web-only child of the singleton deployment supervisor; no migration or mail."""
import argparse
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from milenio_web.deployment import guard_server, apply_environment


def main():
    if os.environ.get('MILENIO_DEPLOYMENT_DEBUG') == '1':
        import faulthandler
        faulthandler.enable()
        faulthandler.dump_traceback_later(12, repeat=True)
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args()
    apply_environment(guard_server())
    os.environ['DJANGO_SETTINGS_MODULE']='milenio_web.settings'
    import django
    django.setup()
    # Resolve forms and URL modules in the main thread before concurrent requests.
    from django.core.management import call_command
    call_command('check', verbosity=0)
    from milenio_web.wsgi import application
    from scripts.run_web import WorkshopStatic
    from waitress import create_server
    server=create_server(WorkshopStatic(application),host='127.0.0.1',port=args.port,threads=4)
    stop=threading.Event()
    def parent():
        sys.stdin.read()
        stop.set()
    threading.Thread(target=parent,daemon=True).start()
    try:
        while not stop.is_set(): server.asyncore.loop(timeout=.25,count=1,map=server._map)
    finally:
        if os.environ.get('MILENIO_DEPLOYMENT_DEBUG') == '1':
            faulthandler.cancel_dump_traceback_later()
        server.task_dispatcher.shutdown()
        server.asyncore.close_all(server._map)


if __name__=='__main__': main()
