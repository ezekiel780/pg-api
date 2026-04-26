from django.db import models

class ReconciliationJob(models.Model):

    class Status(models.TextChoices):
        PENDING    = "PENDING",    "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS    = "SUCCESS",    "Success"
        FAILED     = "FAILED",     "Failed"
        CANCELLED  = "CANCELLED",  "Cancelled"
    task_id = models.CharField(
        max_length=255,
        unique=True,
    )
    file_a_name = models.CharField(max_length=255)
    file_b_name = models.CharField(max_length=255)
    file_a_path = models.CharField(max_length=500, null=True, blank=True)
    file_b_path = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    result = models.JSONField(null=True, blank=True)

    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Reconciliation Job"
        verbose_name_plural = "Reconciliation Jobs"

    def __str__(self):
        return f"ReconciliationJob {self.task_id[:8]}… [{self.status}]"

    @property
    def is_terminal(self) -> bool:
        """True if the job has reached a final state and will not change."""
        return self.status in {
            self.Status.SUCCESS,
            self.Status.FAILED,
            self.Status.CANCELLED,
        }

    @property
    def is_cancellable(self) -> bool:
        """True if the job can still be cancelled."""
        return self.status in {self.Status.PENDING, self.Status.PROCESSING}
    
    