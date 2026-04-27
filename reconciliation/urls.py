from django.urls import path
from .views import (
    ReconcileView,
    ReconciliationStatusView,
    ReconciliationListView,
    ReconciliationCancelView,
)

urlpatterns = [
    # POST — submit two CSV files
    path(
        "reconcile/",
        ReconcileView.as_view(),
        name="reconcile-create",
    ),

    # GET — list all jobs (must be before <task_id> pattern)
    path(
        "reconcile/history/",
        ReconciliationListView.as_view(),
        name="reconcile-history",
    ),

    # GET — poll single job status
    path(
        "reconcile/<str:task_id>/",
        ReconciliationStatusView.as_view(),
        name="reconcile-status",
    ),

    # POST — cancel a job
    path(
        "reconcile/<str:task_id>/cancel/",
        ReconciliationCancelView.as_view(),
        name="reconcile-cancel",
    ),
]
