from django.contrib import admin
from django.utils.html import format_html
from .models import DAGRun, TaskInstance, PipelineAlert, AdHocTaskExecution


class TaskInstanceInline(admin.TabularInline):
    model = TaskInstance
    fields = ("task_id", "state", "start_date", "duration_seconds", "try_number")
    readonly_fields = fields
    extra = 0


@admin.register(DAGRun)
class DAGRunAdmin(admin.ModelAdmin):
    list_display = ("dag_id", "dag_run_id", "state_badge", "execution_date", "duration_display", "run_type")
    list_filter = ("dag_id", "state", "run_type")
    search_fields = ("dag_id", "dag_run_id")
    date_hierarchy = "execution_date"
    readonly_fields = ("synced_at",)
    inlines = [TaskInstanceInline]

    @admin.display(description="State")
    def state_badge(self, obj):
        colors = {
            "success": "green", "failed": "red",
            "running": "blue", "queued": "orange",
        }
        color = colors.get(obj.state, "grey")
        return format_html('<span style="color:{};font-weight:bold">{}</span>', color, obj.state.upper())


@admin.register(PipelineAlert)
class PipelineAlertAdmin(admin.ModelAdmin):
    list_display = ("dag_id", "severity", "acknowledged", "acknowledged_by", "created_at", "message_short")
    list_filter = ("severity", "acknowledged")
    search_fields = ("dag_id", "message")
    readonly_fields = ("created_at",)

    @admin.display(description="Message")
    def message_short(self, obj):
        return obj.message[:80] + "…" if len(obj.message) > 80 else obj.message


@admin.register(AdHocTaskExecution)
class AdHocTaskExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "status_badge", "triggered_by",
        "created_at", "duration_display_col", "parameters_short",
    )
    list_filter = ("status", "task_name")
    search_fields = ("task_name", "display_name", "celery_task_id")
    readonly_fields = (
        "task_name", "display_name", "celery_task_id", "parameters",
        "status", "result", "error_message", "triggered_by",
        "created_at", "started_at", "completed_at",
    )
    date_hierarchy = "created_at"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "SUCCESS": "green", "FAILURE": "red",
            "STARTED": "blue", "PENDING": "orange", "REVOKED": "grey",
        }
        color = colors.get(obj.status, "grey")
        return format_html('<span style="color:{};font-weight:bold">{}</span>', color, obj.status)

    @admin.display(description="Duration")
    def duration_display_col(self, obj):
        return obj.duration_display

    @admin.display(description="Parameters")
    def parameters_short(self, obj):
        s = str(obj.parameters)
        return s[:60] + "…" if len(s) > 60 else s
