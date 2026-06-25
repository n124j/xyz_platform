# XYZ Investment Platform

**XYZ Corp — Internal Investment Banking Platform**

A full-stack private banking web application built on Django, featuring real-time portfolio analytics powered by Plotly Dash and D3.js, interactive AG Grid data tables, Apache Airflow ETL pipelines, and a complete containerised deployment stack.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser / Client                          │
└────────────┬───────────────────────────────────┬────────────────┘
             │ HTTPS                              │ WebSocket (ws/)
┌────────────▼───────────────────────────────────▼────────────────┐
│                    Nginx (TLS termination)                        │
└────────────┬───────────────────────────────────────────────────-─┘
             │
┌────────────▼────────────────────────────────────────────────────┐
│        Django (Gunicorn / Daphne ASGI)  + Django Channels        │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Portfolio App  │  │  Accounts    │  │ Analytics (Risk)   │   │
│  │ Plotly Dash    │  │  AG Grid     │  │ D3.js Charts       │   │
│  └────────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                ETL Pipeline Monitor                        │  │
│  │  Airflow REST API ←→ Django ←→ Celery (sync tasks)        │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────┬──────────────────────────┬────────────────────────────-─┘
         │                          │
┌────────▼────────┐   ┌─────────────▼──────────┐
│   PostgreSQL 16  │   │      Redis 7            │
│   (ORM + ETL     │   │   (Cache + Celery       │
│    staging)      │   │    broker + Channels)   │
└─────────────────┘   └────────────────────────┘
         │
┌────────▼─────────────────────────────────────┐
│              Apache Airflow 2.9               │
│  ┌──────────────────┐  ┌───────────────────┐  │
│  │ portfolio_etl_dag│  │ market_data_dag   │  │
│  └──────────────────┘  └───────────────────┘  │
│  ┌──────────────────┐                         │
│  │ risk_report_dag  │                         │
│  └──────────────────┘                         │
└──────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Web Framework | Django 4.2 |
| API | Django REST Framework |
| Visualisation | Plotly Dash 2.17, D3.js v7 |
| Data Grid | AG Grid Community 31 |
| ETL Orchestration | Apache Airflow 2.9 |
| Task Queue | Celery 5.4 + django-celery-beat |
| Real-time | Django Channels + Redis |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Reverse Proxy | Nginx 1.27 |
| Application Server | Gunicorn (HTTP) / Daphne (ASGI/WS) |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Application Modules

### Portfolio Dashboard
Interactive AUM trend chart (D3.js), asset allocation sunburst, rolling return vs benchmark, and performance attribution — all powered by Plotly Dash components mounted inside Django templates.

### Client & Account Management
Full CRUD for clients, accounts, holdings, and transactions. AG Grid tables with instant filter/sort/export. KYC status tracking and relationship manager assignment.

### Market Data & Risk Analytics
Real-time price history charts (D3.js), return distribution histograms, VaR fan chart, correlation heatmap, and efficient frontier scatter — all computed on live data and rendered in Plotly Dash.

### ETL Pipeline Monitor
Gantt timeline of Airflow DAG runs, success rate bar chart, and run duration box plots. Allows authorised users to trigger DAGs directly from the Django UI. Celery syncs Airflow state every 5 minutes.

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Docker Desktop 4.x+ (with Docker Compose v2)
- Git

### Option A — Docker Compose (Recommended)

This starts all services (Django, PostgreSQL, Redis, Celery, Airflow) in one command.

```bash
# 1. Clone the repository
git clone https://github.com/xyz-internal/xyz-platform.git
cd xyz-platform/xyz_platform

# 2. Create your environment file
cp .env.example .env
# Edit .env — set SECRET_KEY to a long random string

# 3. Build and start all services
docker compose up --build

# 4. In a separate terminal, create a Django superuser
docker compose exec django python manage.py createsuperuser

# 5. (Optional) Load sample data
docker compose exec django python manage.py loaddata fixtures/sample_data.json
```

Services available after startup:

| Service | URL |
|---------|-----|
| PostgreSQL | `localhost:3000` |
| Redis | `localhost:3001` |
| Django Application | <http://localhost:3002> |
| Django Admin | <http://localhost:3002/admin> |
| Airflow UI | <http://localhost:3003> (credentials configured in `.env`) |

### Option B — Native Python (without Docker)

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 2. Install development dependencies
pip install -r requirements/development.txt

# 3. Configure environment
cp .env.example .env
# Edit .env to point DB_HOST=localhost and set your local PostgreSQL credentials

# 4. Set up the database
#    (Assumes PostgreSQL is running locally with the credentials in .env)
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# 5. Run Django development server
python manage.py runserver

# 6. In separate terminals, start Celery worker and beat scheduler
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# 7. (Separate terminal) Start Airflow
export AIRFLOW_HOME=$(pwd)/.airflow
airflow db migrate
airflow users create --role Admin --username "$AIRFLOW_API_USER" --password "$AIRFLOW_API_PASSWORD" \
    --firstname XYZ --lastname Admin --email admin@xyz.local
airflow webserver --port 8080 &
airflow scheduler &
```

---

## Production Deployment

### Server Requirements

- Ubuntu 22.04 LTS (recommended)
- 8 vCPU / 32 GB RAM minimum
- 500 GB SSD (PostgreSQL data + Airflow logs)
- Inbound ports: 80 (HTTP redirect), 443 (HTTPS)

### Step 1 — Server Preparation

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y docker.io docker-compose-plugin git curl

sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Step 2 — TLS Certificate

```bash
# Option A: Let's Encrypt (public domain)
sudo apt-get install certbot
sudo certbot certonly --standalone -d xyz.internal.com
sudo cp /etc/letsencrypt/live/xyz.internal.com/fullchain.pem docker/nginx/certs/
sudo cp /etc/letsencrypt/live/xyz.internal.com/privkey.pem docker/nginx/certs/

# Option B: Internal CA certificate (for corporate intranet)
cp /path/to/your/fullchain.pem docker/nginx/certs/
cp /path/to/your/privkey.pem docker/nginx/certs/
```

### Step 3 — Deploy Application

```bash
# Clone repository on the server
git clone https://github.com/xyz-internal/xyz-platform.git /opt/xyz_platform
cd /opt/xyz_platform/xyz_platform

# Create production .env
cp .env.example .env
nano .env
# Required changes for production:
#   SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
#   DEBUG=False
#   ALLOWED_HOSTS=xyz.internal.com
#   DB_USER=<database username>
#   DB_PASSWORD=<strong random password>
#   REDIS_PASSWORD=<strong random password>
#   AIRFLOW_API_USER=<airflow admin username>
#   AIRFLOW_API_PASSWORD=<strong random password>
#   AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=<update with actual DB_USER and DB_PASSWORD>

# Build and start with production overrides
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Run database migrations
docker compose exec django python manage.py migrate --noinput

# Collect static files
docker compose exec django python manage.py collectstatic --noinput

# Create admin superuser
docker compose exec django python manage.py createsuperuser
```

### Step 4 — Configure Airflow Connections

Log in to Airflow at `https://xyz.internal.com:8080` and create the following connections in Admin → Connections:

| Conn ID | Type | Host | Schema | Login | Password |
| ------- | ---- | ---- | ------ | ----- | -------- |
| `xyz_postgres` | Postgres | `db` | `xyz_platform` | your `DB_USER` value | your `DB_PASSWORD` value |
| `xyz_custody_api` | HTTP | your-custody-host | — | api-key | api-secret |

### Step 5 — Verify Deployment

```bash
# Check all containers are healthy
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Test the health endpoint
curl https://xyz.internal.com/health/

# Check Django logs
docker compose logs django --tail=50

# Trigger the portfolio ETL DAG manually to verify end-to-end
docker compose exec airflow-webserver airflow dags trigger portfolio_etl_dag
```

---

## GitHub Actions CI/CD

The pipeline (`.github/workflows/ci-cd.yml`) runs on every push and PR:

```
push/PR → Lint (black, flake8, isort)
        → Test (pytest + coverage, Postgres + Redis services)
        → Build (Docker image → GitHub Container Registry)
        → Deploy Staging  (on push to develop)
        → Deploy Production (on push to main, with manual approval gate)
```

### Required GitHub Secrets & Variables

Navigate to **Settings → Secrets and Variables → Actions** and add:

**Secrets:**

| Secret | Description |
| ------ | ----------- |
| `CI_SECRET_KEY` | Django secret key for CI test runs |
| `CI_DB_USER` | PostgreSQL username for CI test database |
| `CI_DB_PASSWORD` | PostgreSQL password for CI test database |
| `CI_AIRFLOW_USER` | Airflow admin username for CI |
| `CI_AIRFLOW_PASSWORD` | Airflow admin password for CI |
| `STAGING_HOST` | IP / hostname of staging server |
| `STAGING_USER` | SSH username |
| `STAGING_SSH_KEY` | Private SSH key (RSA or Ed25519) |
| `PROD_HOST` | IP / hostname of production server |
| `PROD_USER` | SSH username |
| `PROD_SSH_KEY` | Private SSH key |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for deploy notifications |

**Variables:**

| Variable | Description |
| -------- | ----------- |
| `CI_DB_NAME` | PostgreSQL database name for CI test runs |

---

## Running Tests

The project includes comprehensive unit tests for all backend apps (models, views, serializers, API endpoints, services) and frontend components (templates, URL routing, admin pages).

### Test Structure

```
tests/
├── conftest.py                     # Shared fixtures (users, clients, accounts, etc.)
├── accounts/
│   ├── test_models.py              # Client, Account, Holding, Transaction models
│   ├── test_views.py               # ClientListView, ClientDetailView, AccountDetailView
│   ├── test_serializers.py         # DRF serializers (nested, computed fields)
│   └── test_api.py                 # REST API ViewSets (CRUD, search, filters)
├── portfolio/
│   ├── test_models.py              # PortfolioSnapshot, AssetAllocationTarget
│   └── test_views.py               # Dashboard view, Snapshot API (JSON)
├── analytics/
│   ├── test_models.py              # MarketData, RiskMetric, BenchmarkReturn, Attribution
│   ├── test_views.py               # Dashboard, RiskMetricList, MarketDataAPI
│   └── test_serializers.py         # All analytics serializers
├── etl_monitor/
│   ├── test_models.py              # DAGRun, TaskInstance, PipelineAlert
│   ├── test_views.py               # ETLDashboard, DAGRunList, TriggerDAG, AlertsAPI
│   ├── test_services.py            # Airflow API sync, trigger (mocked)
│   └── test_tasks.py               # Celery task (sync_all_dag_runs)
└── frontend/
    ├── test_templates.py           # Template existence, login page, page rendering
    ├── test_urls.py                # URL resolution and reverse for all routes
    └── test_admin.py               # Admin access control, changelist pages
```

### Running Tests

```bash
# Run the full test suite with coverage
pytest --cov=apps --cov-report=term-missing

# Run only unit tests (no database required)
pytest -m unit

# Run a specific app's tests
pytest tests/accounts/ -v

# Run only model tests
pytest tests/ -k "test_model" -v

# Run only API tests
pytest tests/ -k "test_api" -v

# Run only frontend tests (templates, URLs, admin)
pytest tests/frontend/ -v

# Generate HTML coverage report
pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

### Running Tests in Docker

```bash
# Run all tests inside the Django container
docker compose exec django pytest --cov=apps --cov-report=term-missing

# Run a specific test file
docker compose exec django pytest tests/accounts/test_models.py -v
```

---

## Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 . --max-line-length=120

# Run all pre-commit hooks
pre-commit run --all-files
```

---

## Airflow DAG Reference

| DAG ID | Schedule | Description |
|--------|----------|-------------|
| `portfolio_etl_dag` | Mon–Fri 18:30 ET | Extract → validate → transform → load positions; compute portfolio snapshot and risk metrics |
| `market_data_dag` | Every 15 min, market hours | Intraday equity prices, FX rates, benchmark levels; mark-to-market holdings |
| `risk_report_dag` | Mon–Fri 19:00 ET | VaR (historical + parametric), stress tests, BHB attribution, distribute PDF reports |

---

## REST API Reference

All endpoints require authentication (session or basic auth).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/accounts/clients/` | List all active clients |
| GET | `/api/v1/accounts/clients/{id}/aum_summary/` | Client AUM summary |
| GET | `/api/v1/accounts/accounts-list/` | List accounts |
| GET | `/api/v1/accounts/transactions/` | Transaction history |
| GET | `/api/v1/analytics/market-data/` | Market data records |
| GET | `/api/v1/analytics/risk-metrics/` | Risk metric records |
| GET | `/api/v1/portfolio/snapshots/` | Daily portfolio snapshots |
| GET | `/api/v1/etl/alerts/` | Active pipeline alerts |

---

## Performance Optimisation

- **Database**: All frequently-queried fields are indexed; `CONN_MAX_AGE=60` enables connection pooling.
- **Caching**: Redis cache backed by `django.core.cache.backends.redis.RedisCache`.
- **Static files**: WhiteNoise serves compressed, fingerprinted static assets with long-lived cache headers.
- **Dash**: `serve_locally=True` + `compress_all_assets=True` in PLOTLY_DASH settings.
- **Celery**: Concurrency set to match CPU cores; Celery Beat avoids cron duplication.
- **PostgreSQL** (production): `shared_buffers=512MB`, `effective_cache_size=2GB` tuned for 32 GB server.

---

## Security Notes

- **Authentication**: All views require `@login_required` / `LoginRequiredMixin`. Admin console uses Django's built-in 2FA-compatible auth.
- **CSRF**: Enabled on all state-changing endpoints.
- **TLS**: Enforced at Nginx with TLS 1.2/1.3 only, HSTS preload header.
- **Secrets**: Managed via `.env` file (never committed); production secrets injected via GitHub Secrets into the CI/CD pipeline.
- **Rate limiting**: Login endpoint rate-limited to 5 req/min per IP at the Nginx layer.
- **Docker**: Application runs as non-root user `xyz` inside the container.

---

## Design Document

A comprehensive design document is available as both Markdown and Microsoft Word:

- **Markdown**: [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md)
- **Word**: [`XYZ_Platform_Design_Document.docx`](XYZ_Platform_Design_Document.docx)

The Word document includes visual diagrams (system architecture, data flow, ER diagram, ETL flowcharts, request flow).

### Regenerating the Word Document

To regenerate the `.docx` file (e.g. after updating the design):

```bash
# Install dependencies (if not already installed)
pip install python-docx matplotlib

# Generate the document
python generate_design_doc.py
```

This produces:

- `XYZ_Platform_Design_Document.docx` — the Word file
- `doc_images/` — PNG diagrams embedded in the document

---

## Contributing

1. Branch from `develop`: `git checkout -b feature/your-feature`
2. Follow PEP 8 / Black formatting, write tests for new code
3. Open a pull request to `develop` — CI must pass before merge
4. Releases to `main` trigger production deployment after manual approval

---

*© XYZ Corp — Confidential & Proprietary. For internal use only.*
