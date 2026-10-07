"""The durable image queue runs independently of analytics and commercial mail."""
import sys
import threading
import logging

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from workshop.document_capture import process_one
from milenio_web.worker_health import heartbeat


class Command(BaseCommand):
    help = "Read at most one queued image at a time without blocking other workshop workers."

    def add_arguments(self, parser):
        parser.add_argument("--once",action="store_true")
        parser.add_argument("--watch-parent",action="store_true")

    def handle(self,*args,**options):
        if options["once"]:
            self.stdout.write(str(process_one()))
            return
        stop = threading.Event()
        if options["watch_parent"]:
            def watch():
                sys.stdin.read()
                stop.set()
            threading.Thread(target=watch,daemon=True).start()
        while not stop.is_set():
            close_old_connections()
            try:
                heartbeat('documents','working')
                worked = process_one(cancel_event=stop)
                heartbeat('documents','completed' if worked else 'idle')
            except Exception as error:
                logging.getLogger(__name__).warning("Document worker tick failed: %s",type(error).__name__)
                worked = False
            stop.wait(0.2 if worked else 2)
