"""Run the durable local analytics automation worker."""
import logging
import sys
import threading
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError

from workshop import models
from workshop.automation import run_once


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run bounded local analytics automation jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Generate due work and execute at most one job.")
        parser.add_argument("--worker-id", default=None)
        parser.add_argument("--idle-sleep", type=float, default=2.0)
        parser.add_argument("--max-idle", type=int, default=0, help="Stop after this many idle ticks; zero waits indefinitely.")
        parser.add_argument("--watch-parent", action="store_true", help="Stop when the parent process closes stdin.")

    def handle(self, *args, **options):
        if options["idle_sleep"] <= 0 or options["max_idle"] < 0:
            raise CommandError("idle-sleep debe ser positivo y max-idle no puede ser negativo")
        stop_event = threading.Event()
        if options["watch_parent"]:
            threading.Thread(target=self._watch_stdin, args=(stop_event,), daemon=True).start()
        if options["once"]:
            self.stdout.write(str(run_once(worker_id=options["worker_id"])))
            return
        # A stable process ID retains the lease identity between polling ticks.
        worker_id = options["worker_id"] or str(uuid.uuid4())
        idle_count = 0
        while not stop_event.is_set():
            try:
                result = run_once(worker_id=worker_id)
            except OperationalError as error:
                message = f"{type(error).__name__}: {str(error)[:400]}"
                logger.warning("Automation tick hit a transient database error: %s", message)
                self.stderr.write(f"Automation worker database error; retrying: {message}")
                self._record_failure(message)
                stop_event.wait(max(options["idle_sleep"], 2.0))
                continue
            except Exception as error:
                message = f"{type(error).__name__}: {str(error)[:400]}"
                logger.exception("Automation tick failed unexpectedly: %s", message)
                self.stderr.write(f"Automation worker tick failed; retrying after backoff: {message}")
                self._record_failure(message)
                stop_event.wait(max(options["idle_sleep"], 5.0))
                continue
            if result["status"] in {"idle", "busy", "paused"}:
                idle_count += 1
                if options["max_idle"] and idle_count >= options["max_idle"]:
                    break
                stop_event.wait(options["idle_sleep"])
            else:
                idle_count = 0
                delay = min(options["idle_sleep"], 0.1) if result["status"] == "completed" else max(options["idle_sleep"], 1.0)
                stop_event.wait(delay)

    @staticmethod
    def _watch_stdin(stop_event):
        try:
            sys.stdin.read()
        finally:
            stop_event.set()

    @staticmethod
    def _record_failure(message):
        """Expose the error without refreshing the worker heartbeat."""
        try:
            models.AutomationWorkerState.objects.filter(pk=1).update(
                status="error", last_error=message[:1000])
        except Exception:
            logger.exception("Could not persist automation worker failure state")
