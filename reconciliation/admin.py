from django.contrib import admin
from .models import ReconciliationJob


@admin.register(ReconciliationJob)
class ReconciliationJobAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "file_a_name",
        "file_b_name",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")

    search_fields = ("task_id", "file_a_name", "file_b_name")

    readonly_fields = (
        "task_id",
        "file_a_name",
        "file_b_name",
        "result",
        "created_at",
    )

    ordering = ("-created_at",)
    