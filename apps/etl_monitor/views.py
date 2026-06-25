"""XYZ Platform — ETL Pipeline Monitor Views."""

import logging
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.views.generic import ListView, TemplateView

from . import services
from .models import AdHocTaskExecution, DAGRun, PipelineAlert

logger = logging.getLogger(__name__)


class ETLDashboardView(LoginRequiredMixin, TemplateView):
    """
    ETL pipeline monitoring dashboard — shows DAG run history,
    health statuses, and allows manual trigger of approved DAGs.
    """

    template_name = "etl_monitor/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        latest_per_dag = (
            DAGRun.objects.filter(
                dag_id=OuterRef("dag_id"),
            )
            .order_by("-execution_date")
            .values("pk")[:1]
        )
        ctx["dag_runs"] = DAGRun.objects.filter(
            pk__in=Subquery(
                DAGRun.objects.values("dag_id").annotate(latest_pk=Subquery(latest_per_dag)).values("latest_pk")
            )
        ).order_by("dag_id")
        ctx["alerts"] = PipelineAlert.objects.filter(acknowledged=False).order_by("-created_at")[:20]
        ctx["page_title"] = "ETL Pipeline Monitor"
        return ctx


class DAGRunListView(LoginRequiredMixin, ListView):
    model = DAGRun
    template_name = "etl_monitor/dag_run_list.html"
    context_object_name = "dag_runs"
    paginate_by = 50

    def get_queryset(self):
        qs = DAGRun.objects.all()
        dag_id = self.request.GET.get("dag_id", "")
        state = self.request.GET.get("state", "")
        if dag_id:
            qs = qs.filter(dag_id=dag_id)
        if state:
            qs = qs.filter(state=state)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dag_ids"] = DAGRun.objects.values_list("dag_id", flat=True).distinct()
        ctx["states"] = DAGRun.State.choices
        return ctx


class TriggerDAGView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Trigger a DAG run via Airflow REST API (requires etl_monitor.trigger_dag permission)."""

    permission_required = "etl_monitor.trigger_dag"

    def post(self, request, dag_id):
        try:
            result = services.trigger_dag(dag_id)
            messages.success(
                request,
                f"DAG {dag_id} triggered successfully (run_id: {result.get('dag_run_id')})",
            )
        except Exception as exc:
            logger.error("Failed to trigger DAG %s: %s", dag_id, exc)
            messages.error(request, f"Failed to trigger DAG {dag_id}: {exc}")
        return redirect("etl_monitor:dashboard")


class PipelineAlertsAPIView(LoginRequiredMixin, TemplateView):
    def get(self, request):
        alerts = list(
            PipelineAlert.objects.filter(acknowledged=False).values("id", "dag_id", "severity", "message", "created_at")
        )
        for a in alerts:
            a["created_at"] = str(a["created_at"])
        return JsonResponse({"alerts": alerts, "count": len(alerts)})


# ---------------------------------------------------------------------------
# Ad-Hoc Task Views
# ---------------------------------------------------------------------------
class AdHocTaskListView(LoginRequiredMixin, TemplateView):
    """Page listing all available ad-hoc tasks and recent execution history."""

    template_name = "etl_monitor/adhoc_tasks.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .tasks import ADHOC_TASK_REGISTRY

        categories = {}
        for key, meta in ADHOC_TASK_REGISTRY.items():
            cat = meta.get("category", "Other")
            categories.setdefault(cat, []).append({"key": key, **meta})
        ctx["categories"] = categories
        ctx["recent_executions"] = AdHocTaskExecution.objects.select_related("triggered_by")[:25]
        ctx["page_title"] = "Ad-Hoc Task Runner"
        return ctx

    def post(self, request):
        from .tasks import ADHOC_TASK_REGISTRY, run_adhoc_task

        task_key = request.POST.get("task_key", "")
        if task_key not in ADHOC_TASK_REGISTRY:
            messages.error(request, f"Unknown task: {task_key}")
            return redirect("etl_monitor:adhoc_tasks")

        meta = ADHOC_TASK_REGISTRY[task_key]
        parameters = {}
        for param_name, param_def in meta.get("parameters", {}).items():
            value = request.POST.get(f"param_{param_name}", "").strip()
            if param_def.get("required") and not value:
                messages.error(request, f"Parameter '{param_def['label']}' is required.")
                return redirect("etl_monitor:adhoc_tasks")
            if value:
                if param_def.get("type") == "number":
                    try:
                        value = int(value)
                    except ValueError:
                        messages.error(request, f"'{param_def['label']}' must be a number.")
                        return redirect("etl_monitor:adhoc_tasks")
                parameters[param_name] = value
            elif "default" in param_def:
                parameters[param_name] = param_def["default"]

        celery_task_id = f"adhoc-{uuid.uuid4()}"
        execution = AdHocTaskExecution.objects.create(
            task_name=task_key,
            display_name=meta["display_name"],
            celery_task_id=celery_task_id,
            parameters=parameters,
            triggered_by=request.user,
        )

        run_adhoc_task.apply_async(
            args=[execution.pk, task_key, parameters],
            task_id=celery_task_id,
        )

        messages.success(
            request,
            f"Task '{meta['display_name']}' dispatched successfully. " f"Tracking ID: {celery_task_id[:12]}...",
        )
        return redirect("etl_monitor:adhoc_tasks")


@login_required
@require_GET
def adhoc_task_status(request, pk):
    """JSON endpoint to poll the status of a running ad-hoc task."""
    execution = get_object_or_404(AdHocTaskExecution, pk=pk)
    return JsonResponse(
        {
            "id": execution.pk,
            "task_name": execution.task_name,
            "display_name": execution.display_name,
            "status": execution.status,
            "result": execution.result,
            "error_message": execution.error_message,
            "parameters": execution.parameters,
            "triggered_by": (str(execution.triggered_by) if execution.triggered_by else None),
            "created_at": str(execution.created_at),
            "started_at": str(execution.started_at) if execution.started_at else None,
            "completed_at": (str(execution.completed_at) if execution.completed_at else None),
            "duration": execution.duration_display,
        }
    )
