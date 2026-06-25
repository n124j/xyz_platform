from django.urls import path
from . import views

app_name = "etl_monitor"

urlpatterns = [
    path("", views.ETLDashboardView.as_view(), name="dashboard"),
    path("runs/", views.DAGRunListView.as_view(), name="dag_run_list"),
    path("trigger/<str:dag_id>/", views.TriggerDAGView.as_view(), name="trigger_dag"),
    path("api/alerts/", views.PipelineAlertsAPIView.as_view(), name="alerts_api"),
    path("tasks/", views.AdHocTaskListView.as_view(), name="adhoc_tasks"),
    path("tasks/<int:pk>/status/", views.adhoc_task_status, name="adhoc_task_status"),
]
