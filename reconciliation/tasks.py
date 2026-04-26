import os
import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from django.utils import timezone

from .models import ReconciliationJob
from .services import reconcile

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  
    name="reconciliation.tasks.run_reconciliation",
)
def run_reconciliation(self, job_id: str, file_a_path: str, file_b_path: str):
    """
    Core reconciliation task — runs inside a Celery worker process.

    Flow:
      1. Guard: skip immediately if the job was cancelled while queued.
      2. Mark job PROCESSING.
      3. Open both CSV files and run the reconciliation algorithm.
      4. Persist the result and mark SUCCESS.
      5. Delete the uploaded CSV files from disk.
      6. On any exception: mark FAILED, write the error field, retry up to
         max_retries times.  Handle MaxRetriesExceeded cleanly so the job
         status stays FAILED rather than being left in an ambiguous state.

    Args:
        job_id:      The ReconciliationJob.task_id (UUID string).
        file_a_path: Absolute filesystem path to the source-A CSV file.
        file_b_path: Absolute filesystem path to the source-B CSV file.
    """
    logger.info("Starting reconciliation task: job_id=%s attempt=%d",
                job_id, self.request.retries + 1)

    try:
        job = ReconciliationJob.objects.get(task_id=job_id)
        if job.status == ReconciliationJob.Status.CANCELLED:
            logger.info(
                "Skipping cancelled job: job_id=%s", job_id
            )
            return {"skipped": True, "reason": "cancelled"}
        job.status = ReconciliationJob.Status.PROCESSING
        job.save(update_fields=["status", "updated_at"])
        with open(file_a_path, "rb") as file_a, open(file_b_path, "rb") as file_b:
            result = reconcile(file_a, file_b)
        job.status = ReconciliationJob.Status.SUCCESS
        job.result = result
        job.error = None 
        job.save(update_fields=["status", "result", "error", "updated_at"])

        logger.info(
            "Reconciliation complete: job_id=%s summary=%s",
            job_id, result.get("summary"),
        )
        _delete_file(file_a_path)
        _delete_file(file_b_path)

        return result

    except Exception as exc:
        logger.error(
            "Reconciliation failed: job_id=%s attempt=%d error=%s",
            job_id, self.request.retries + 1, exc,
            exc_info=True,
        )
        try:
            ReconciliationJob.objects.filter(task_id=job_id).update(
                status=ReconciliationJob.Status.FAILED,
                error=str(exc),
            )
        except Exception as db_exc:
            logger.error(
                "Could not persist FAILED status for job_id=%s: %s",
                job_id, db_exc,
            )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceeded:
            logger.error(
                "Max retries (%d) exceeded for job_id=%s — job is permanently FAILED",
                self.max_retries, job_id,
            )
            return {"error": str(exc), "retries_exhausted": True}
@shared_task(name="reconciliation.tasks.cleanup_old_uploads")
def cleanup_old_uploads():
    """
    Remove uploaded CSV files for jobs that finished more than 24 hours ago.

    Referenced by the beat schedule added in settings.py:
        CELERY_BEAT_SCHEDULE = {
            "cleanup-old-csv-files": {
                "task": "reconciliation.tasks.cleanup_old_uploads",
                "schedule": crontab(hour=3, minute=0),
            }
        }

    Only terminal jobs (SUCCESS, FAILED, CANCELLED) are eligible — we never
    delete files for a job that is still PENDING or PROCESSING.
    """
    cutoff = timezone.now() - timedelta(hours=24)

    terminal_statuses = [
        ReconciliationJob.Status.SUCCESS,
        ReconciliationJob.Status.FAILED,
        ReconciliationJob.Status.CANCELLED,
    ]

    old_jobs = ReconciliationJob.objects.filter(
        status__in=terminal_statuses,
        updated_at__lt=cutoff,
    ).exclude(
        file_a_path=None,
        file_b_path=None,
    ).only("id", "task_id", "file_a_path", "file_b_path")

    deleted_count = 0
    error_count = 0

    for job in old_jobs:
        if job.file_a_path:
            _delete_file(job.file_a_path)
        if job.file_b_path:
            _delete_file(job.file_b_path)
        job.file_a_path = None
        job.file_b_path = None
        job.save(update_fields=["file_a_path", "file_b_path"])

        deleted_count += 1

    logger.info(
        "cleanup_old_uploads complete: cleaned=%d errors=%d",
        deleted_count, error_count,
    )
    return {"cleaned": deleted_count, "errors": error_count}
def _delete_file(path: str) -> None:
    try:
        if os.path.isfile(path):
            os.remove(path)
            logger.debug("Deleted upload file: %s", path)
        else:
            logger.debug("Cleanup skipped — file not found: %s", path)
    except OSError as exc:
        logger.warning("Could not delete file %s: %s", path, exc)
