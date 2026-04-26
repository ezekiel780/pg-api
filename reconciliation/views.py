import os
import uuid
import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers as drf_serializers

from drf_spectacular.utils import extend_schema, inline_serializer

from .models import ReconciliationJob
from .serializers import ReconcileSerializer
from .tasks import run_reconciliation

logger = logging.getLogger(__name__)


# =========================
# PAGINATION
# =========================
class JobListPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


# =========================
# SCHEMAS
# =========================
_job_accepted_schema = inline_serializer(
    name="JobAccepted",
    fields={
        "task_id": drf_serializers.CharField(),
        "status": drf_serializers.CharField(),
    },
)


# =========================
# HELPERS
# =========================
def _unique_upload_path(filename: str) -> str:
    prefix = uuid.uuid4().hex[:12]
    safe_name = os.path.basename(filename)
    return f"recon/{prefix}_{safe_name}"


def _absolute_media_path(relative_path: str) -> str:
    return os.path.join(settings.MEDIA_ROOT, relative_path)


# =========================
# RECONCILE VIEW
# =========================
class ReconcileView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file_a": {
                        "type": "string",
                        "format": "binary"
                    },
                    "file_b": {
                        "type": "string",
                        "format": "binary"
                    },
                },
                "required": ["file_a", "file_b"],
            }
        },
        responses={202: _job_accepted_schema},
        summary="Upload two CSV files for reconciliation",
    )
    def post(self, request):
        serializer = ReconcileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_a = serializer.validated_data["file_a"]
        file_b = serializer.validated_data["file_b"]

        rel_a = default_storage.save(_unique_upload_path(file_a.name), file_a)
        rel_b = default_storage.save(_unique_upload_path(file_b.name), file_b)

        abs_a = _absolute_media_path(rel_a)
        abs_b = _absolute_media_path(rel_b)

        job = ReconciliationJob.objects.create(
            task_id=str(uuid.uuid4()),
            file_a_name=file_a.name,
            file_b_name=file_b.name,
            file_a_path=abs_a,
            file_b_path=abs_b,
            status=ReconciliationJob.Status.PENDING,
        )

        run_reconciliation.delay(job.task_id, abs_a, abs_b)

        return Response(
            {"task_id": job.task_id, "status": job.status},
            status=status.HTTP_202_ACCEPTED,
        )


# =========================
# STATUS VIEW
# =========================
class ReconciliationStatusView(APIView):

    def get(self, request, task_id):
        job = get_object_or_404(ReconciliationJob, task_id=task_id)

        return Response({
            "task_id": job.task_id,
            "status": job.status,
            "created_at": job.created_at,
            "result": job.result.get("summary") if job.result else None,
        })


# =========================
# LIST VIEW
# =========================
class ReconciliationListView(APIView):

    def get(self, request):
        queryset = ReconciliationJob.objects.order_by("-created_at")

        paginator = JobListPagination()
        page = paginator.paginate_queryset(queryset, request)

        return paginator.get_paginated_response([
            {
                "task_id": j.task_id,
                "status": j.status,
                "file_a": j.file_a_name,
                "file_b": j.file_b_name,
                "created_at": j.created_at,
            }
            for j in page
        ])


# =========================
# CANCEL VIEW
# =========================
class ReconciliationCancelView(APIView):

    def post(self, request, task_id):
        job = get_object_or_404(ReconciliationJob, task_id=task_id)

        if job.status in [
            ReconciliationJob.Status.SUCCESS,
            ReconciliationJob.Status.FAILED,
            ReconciliationJob.Status.CANCELLED,
        ]:
            return Response(
                {"message": "Job already completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from celery import current_app
            current_app.control.revoke(task_id, terminate=True)
        except Exception as e:
            logger.warning("Celery revoke failed: %s", e)

        job.status = ReconciliationJob.Status.CANCELLED
        job.save(update_fields=["status"])

        return Response({
            "task_id": job.task_id,
            "status": job.status
        })
    