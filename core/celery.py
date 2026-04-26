"""
Celery app initialization for Ledger Reconciliation API.

Worker startup (from project root):
  celery -A ledger worker -Q reconciliation,celery -l info --concurrency=4

Beat scheduler (runs periodic tasks):
  celery -A ledger beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

Combined (development only — not recommended in production):
  celery -A ledger worker --beat -l info
"""

import os
from celery import Celery
from celery.signals import setup_logging


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger.settings")

app = Celery("ledger_reconciliation")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@setup_logging.connect
def configure_logging(loglevel, logfile, format, colorize, **kwargs):
    """Hand full log control to Django's LOGGING configuration."""
    import logging.config
    from django.conf import settings
    logging.config.dictConfig(settings.LOGGING)

@app.task(bind=True, name="ledger.debug_task")
def debug_task(self):
    """Smoke-test task — confirms Celery worker and broker are alive."""
    print(f"[debug_task] Request: {self.request!r}")
    return {"status": "ok", "worker": self.request.hostname}
