import json

from django.contrib import admin
from django.utils.html import format_html

from .models import ReconciliationJob


@admin.register(ReconciliationJob)
class ReconciliationJobAdmin(admin.ModelAdmin):
    list_display = (
        "short_task_id",   
        "file_a_name",
        "file_b_name",
        "status_badge",    
        "created_at",
        "updated_at",
    )

    list_filter = ("status",)
    search_fields = (
        "=task_id",       
        "^file_a_name",  
        "^file_b_name",
    )

    ordering = ("-created_at",)
    list_per_page = 25

    show_full_result_count = False

    date_hierarchy = "created_at"

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    readonly_fields = (
        "task_id",
        "file_a_name",
        "file_b_name",
        "file_a_path",    
        "file_b_path",
        "status",
        "pretty_result",   
        "error",         
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Identity", {
            "fields": ("task_id", "status"),
        }),
        ("Files", {
            "fields": (
                ("file_a_name", "file_a_path"),
                ("file_b_name", "file_b_path"),
            ),
        }),
        ("Outcome", {
            "fields": ("pretty_result", "error"),
            "description": (
                "result shows reconciliation counts and up to 10,000 "
                "discrepancy IDs. error is only populated for FAILED jobs."
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),  
        }),
    )

    actions = ["mark_cancelled"]

    @admin.action(description="Mark selected jobs as CANCELLED")
    def mark_cancelled(self, request, queryset):
        cancellable = queryset.filter(
            status__in=[
                ReconciliationJob.Status.PENDING,
                ReconciliationJob.Status.PROCESSING,
            ]
        )
        updated = cancellable.update(status=ReconciliationJob.Status.CANCELLED)
        skipped = queryset.count() - updated

        self.message_user(
            request,
            f"{updated} job(s) marked as CANCELLED. "
            f"{skipped} job(s) skipped (already in a terminal state).",
        )
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # List view only needs these columns — defer everything else
        if request.resolver_match.url_name == "reconciliation_reconciliationjob_changelist":
            return qs.only(
                "id",
                "task_id",
                "file_a_name",
                "file_b_name",
                "status",
                "created_at",
                "updated_at",
            )

        return qs

    @admin.display(description="Task ID")
    def short_task_id(self, obj):
        """Show first 8 characters of the UUID — enough to identify a job."""
        return f"{obj.task_id[:8]}…"

    @admin.display(description="Status")
    def status_badge(self, obj):
        """
        Render status as a coloured pill badge so FAILED jobs stand out
        immediately on the list page without scanning a plain-text column.
        """
        colours = {
            ReconciliationJob.Status.PENDING:    "#6b7280",  # grey
            ReconciliationJob.Status.PROCESSING: "#2563eb",  # blue
            ReconciliationJob.Status.SUCCESS:    "#16a34a",  # green
            ReconciliationJob.Status.FAILED:     "#dc2626",  # red
            ReconciliationJob.Status.CANCELLED:  "#d97706",  # amber
        }
        colour = colours.get(obj.status, "#6b7280")
        return format_html(
            '<span style="'
            "background:{colour};"
            "color:#fff;"
            "padding:2px 10px;"
            "border-radius:12px;"
            "font-size:11px;"
            "font-weight:600;"
            '">{label}</span>',
            colour=colour,
            label=obj.get_status_display(),
        )

    @admin.display(description="Result")
    def pretty_result(self, obj):
        if not obj.result:
            return "—"

        summary = obj.result.get("summary")
        if summary:
            formatted = json.dumps({"summary": summary}, indent=2)
            detail_note = (
                "<br><small style='color:#6b7280'>"
                "Full discrepancy ID lists are available via the API. "
                "(<code>GET /api/v1/reconcile/{task_id}/</code>)"
                "</small>"
            )
        else:
            formatted = json.dumps(obj.result, indent=2)
            detail_note = ""

        return format_html(
            "<pre style='"
            "background:#f3f4f6;"
            "padding:12px;"
            "border-radius:6px;"
            "font-size:12px;"
            "max-height:400px;"
            "overflow:auto;"
            "'>{}</pre>{}",
            formatted,
            format_html(detail_note),
        )
    
    