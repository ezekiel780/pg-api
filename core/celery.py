import os
from celery import Celery
from celery.signals import setup_logging


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

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
