# ──────────────────────────────────────────────────────────────
# XYZ Platform — Apache Airflow Dockerfile
# Extends the official Airflow image with XYZ DAG dependencies
# ──────────────────────────────────────────────────────────────
FROM apache/airflow:2.9.2-python3.11

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install additional providers and XYZ-specific packages
COPY requirements/base.txt /tmp/requirements-base.txt
RUN pip install --no-cache-dir \
    apache-airflow-providers-postgres==5.11.0 \
    apache-airflow-providers-http==4.11.0 \
    apache-airflow-providers-celery==3.7.2 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    scipy==1.13.1 \
    requests==2.32.3

# Copy DAGs
COPY --chown=airflow:root dags/ /opt/airflow/dags/

ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor \
    AIRFLOW__CORE__LOAD_EXAMPLES=False \
    AIRFLOW__WEBSERVER__EXPOSE_CONFIG=False \
    AIRFLOW__WEBSERVER__AUTHENTICATE=True \
    AIRFLOW__CORE__PARALLELISM=4 \
    AIRFLOW__CORE__DAG_CONCURRENCY=2

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD airflow db check
