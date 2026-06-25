from django.apps import AppConfig


class EtlMonitorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.etl_monitor"
    verbose_name = "ETL Pipeline Monitor"
