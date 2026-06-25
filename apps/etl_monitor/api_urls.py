from django.urls import path

from .views import PipelineAlertsAPIView

urlpatterns = [
    path("alerts/", PipelineAlertsAPIView.as_view(), name="etl-alerts"),
]
