"""
XYZ Platform — ETL Pipeline Monitor Models

Provides a Django-native view of Airflow DAG run history
and pipeline health, cached from the Airflow REST API.
"""
from django.db import models


class DAGRun(models.Model):
    """Cached Airflow DAG run record."""
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    dag_id = models.CharField(max_length=255, db_index=True)
    dag_run_id = models.CharField(max_length=255, unique=True)
    run_type = models.CharField(max_length=50, default="scheduled")
    state = models.CharField(max_length=20, choices=State.choices)
    execution_date = models.DateTimeField(db_index=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    conf = models.JSONField(default=dict, blank=True)
    note = models.TextField(blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-execution_date"]
        indexes = [models.Index(fields=["dag_id", "-execution_date"])]

    def __str__(self):
        return f"{self.dag_id} [{self.state}] {self.execution_date:%Y-%m-%d %H:%M}"

    @property
    def is_healthy(self):
        return self.state == self.State.SUCCESS

    @property
    def duration_display(self):
        if not self.duration_seconds:
            return "—"
        m, s = divmod(int(self.duration_seconds), 60)
        return f"{m}m {s}s"


class TaskInstance(models.Model):
    """Individual Airflow task within a DAG run."""
    dag_run = models.ForeignKey(DAGRun, on_delete=models.CASCADE, related_name="task_instances")
    task_id = models.CharField(max_length=255)
    state = models.CharField(max_length=20)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    try_number = models.IntegerField(default=1)
    log_url = models.URLField(blank=True)

    class Meta:
        unique_together = [("dag_run", "task_id")]
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.dag_run.dag_id}.{self.task_id} [{self.state}]"


class PipelineAlert(models.Model):
    """Alert raised when a DAG fails or exceeds SLA."""
    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        WARNING = "WARNING", "Warning"
        INFO = "INFO", "Info"

    dag_run = models.ForeignKey(DAGRun, on_delete=models.SET_NULL, null=True, blank=True)
    dag_id = models.CharField(max_length=255)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.WARNING)
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.dag_id} — {self.created_at:%Y-%m-%d %H:%M}"


class AdHocTaskExecution(models.Model):
    """Tracks an ad-hoc Celery task fired manually by a staff user."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        STARTED = "STARTED", "Started"
        SUCCESS = "SUCCESS", "Success"
        FAILURE = "FAILURE", "Failure"
        REVOKED = "REVOKED", "Revoked"

    task_name = models.CharField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    celery_task_id = models.CharField(max_length=255, unique=True, db_index=True)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    triggered_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="adhoc_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ad-Hoc Task Execution"
        verbose_name_plural = "Ad-Hoc Task Executions"

    def __str__(self):
        return f"{self.display_name} [{self.status}] — {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def duration_display(self):
        dur = self.duration_seconds
        if dur is None:
            return "—"
        m, s = divmod(int(dur), 60)
        return f"{m}m {s}s" if m else f"{s}s"
