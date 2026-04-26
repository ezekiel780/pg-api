from django.urls import path
from .views import (
    ReconcileView,
    ReconciliationStatusView,
    ReconciliationListView,
    ReconciliationCancelView,
)

urlpatterns = [
    path("reconcile/", ReconcileView.as_view(), name="reconcile-create"),

    path(
        "status/<str:task_id>/",
        ReconciliationStatusView.as_view(),
        name="reconcile-status"
    ),
    path(
        "reconcile/history/",
        ReconciliationListView.as_view(),
        name="reconcile-history"
    ),
    path(
        "reconcile/<str:task_id>/cancel/",
        ReconciliationCancelView.as_view(),
        name="reconcile-cancel"
    ),
]
