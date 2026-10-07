"""Independent bounded Gmail process. The deployment latch defaults to disabled."""
import sys
import threading
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import close_old_connections
from milenio_web.deployment import read_config, guard_server
from milenio_web.worker_health import heartbeat
from commercial.mail_flow import tick


class Command(BaseCommand):
    def add_arguments(self,parser):
        parser.add_argument('--once',action='store_true')
        parser.add_argument('--watch-parent',action='store_true')

    def handle(self,*args,**options):
        stop=threading.Event()
        if options['watch_parent']:
            def watch():
                sys.stdin.read()
                stop.set()
            threading.Thread(target=watch,daemon=True).start()
        while not stop.is_set():
            close_old_connections()
            config=read_config()
            if config: guard_server(config)
            allowed=bool(config and config.get('mail_worker_allowed'))
            if allowed and not (settings.DATA_DIR/'.mail-recovery-hold').exists():
                heartbeat('mail','working')
                result=tick()
            else: result='deployment_paused'
            heartbeat('mail',result)
            if options['once']:
                self.stdout.write(result)
                return
            stop.wait(5)
