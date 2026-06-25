# XYZ Platform — Design Document

**XYZ Corp Internal Investment Banking Platform**

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Date | 2026-06-24 |
| Stack | Django 4.2 · PostgreSQL 16 · Redis 7 · Celery 5 · Apache Airflow 2.9 · Plotly Dash |
| Status | Active Development |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Django Applications](#3-django-applications)
4. [Data Model](#4-data-model)
5. [ETL Pipelines (Airflow)](#5-etl-pipelines-airflow)
6. [Interactive Dashboards (Plotly Dash)](#6-interactive-dashboards-plotly-dash)
7. [REST API](#7-rest-api)
8. [Infrastructure & Deployment](#8-infrastructure--deployment)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Security](#10-security)
11. [Observability](#11-observability)

---

## 1. Overview

### 1.1 Purpose

The XYZ Platform is an internal investment banking application that provides:

- **Client & Account Management** — Hierarchy of clients, accounts, holdings, and transactions
- **Portfolio Dashboard** — Aggregated AUM snapshots, asset allocation, and performance tracking
- **Risk Analytics** — VaR, Sharpe ratio, drawdown, correlation, and stress testing
- **ETL Pipeline Monitoring** — Real-time visibility into Airflow DAG execution, alerting on failures

### 1.2 Users

| Role | Access |
|------|--------|
| Superuser (admin) | Full Django admin, all views, DAG triggering |
| Staff (relationship managers) | Client views, portfolio dashboard, analytics |
| Read-only analysts | Dashboards and risk metric views |

Default development credentials are defined in `.env`:
- `admin / xyzplatform2024` (superuser)
- `jmorgan / xyzplatform2024` (staff)
- `swilliams / xyzplatform2024` (staff)

### 1.3 Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | Django 4.2.13 |
| API | Django REST Framework 3.15 |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Task Queue | Celery 5.4 + django-celery-beat |
| Orchestration | Apache Airflow 2.9.2 (LocalExecutor) |
| Dashboards | Plotly Dash 2.17 via django-plotly-dash |
| WebSockets | Django Channels 4.1 + channels-redis |
| Static Files | WhiteNoise 6.7 |
| Containerization | Docker Compose (dev + prod) |
| Reverse Proxy | Nginx (TLS, rate limiting) |
| CI/CD | GitHub Actions |
| Error Tracking | Sentry (production) |

---

## 2. Architecture

### 2.1 System Context

```
┌─────────────┐      HTTPS       ┌──────────┐
│   Browser    │◄────────────────►│  Nginx   │
│  (Staff UI)  │                  │ (TLS/RL) │
└─────────────┘                  └────┬─────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
               ┌────▼────┐    ┌──────▼──────┐    ┌─────▼──────┐
               │  Django  │    │ Plotly Dash │    │  DRF API   │
               │ (Views)  │    │ (Embedded)  │    │ (/api/v1/) │
               └────┬─────┘    └──────┬──────┘    └─────┬──────┘
                    │                 │                  │
                    └────────┬────────┘                  │
                             │                           │
                    ┌────────▼───────────────────────────▼┐
                    │           PostgreSQL 16              │
                    │  (accounts, portfolio, analytics,    │
                    │   etl_monitor, celery_results)       │
                    └────────────────┬────────────────────┘
                                    │
            ┌───────────────────────┼────────────────────┐
            │                       │                    │
     ┌──────▼──────┐        ┌──────▼──────┐     ┌──────▼──────┐
     │   Celery    │        │   Celery    │     │  Airflow    │
     │   Worker    │        │    Beat     │     │ Scheduler   │
     │ (tasks)     │        │ (periodic)  │     │  + DAGs     │
     └──────┬──────┘        └─────────────┘     └──────┬──────┘
            │                                          │
            └──────────────┬───────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │ (cache +    │
                    │  broker)    │
                    └─────────────┘
```

### 2.2 Layered Design

| Layer | Responsibility | Implementation |
|-------|---------------|----------------|
| Presentation | HTML templates, Dash iframes, KPI cards | Django Templates + Plotly Dash |
| API | RESTful JSON endpoints | DRF ViewSets + Serializers |
| Business Logic | Aggregations, risk math, DAG sync | Model methods, `services.py`, Celery tasks |
| Data Access | ORM queries, raw SQL in DAGs | Django ORM, Airflow PostgresHook |
| External Integration | Airflow REST API, market data feeds | `requests` + BasicAuth |

### 2.3 Request Flow

1. **Browser** → Nginx (TLS termination, rate limiting)
2. **Nginx** → Gunicorn (Django WSGI, 8 workers in prod)
3. **Django** → Session auth check → View → ORM → PostgreSQL
4. **Dash iframes** served via django-plotly-dash middleware
5. **WebSocket** connections upgrade through Nginx → Django Channels → Redis channel layer

---

## 3. Django Applications

### 3.1 Accounts (`apps/accounts/`)

Core entity hierarchy: **Client → Account → Holding / Transaction**

**Views:**

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/clients/` | `ClientListView` | List active clients, filter by name/tier |
| `/clients/<pk>/` | `ClientDetailView` | Client profile + accounts + recent transactions |
| `/clients/account/<account_number>/` | `AccountDetailView` | Holdings and transaction history |

**Admin Features:**
- `ClientAdmin` with inline `AccountInline`, formatted AUM display
- `AccountAdmin` with inline `HoldingInline`
- `TransactionAdmin` with date hierarchy, search by reference number

### 3.2 Portfolio (`apps/portfolio/`)

Aggregated portfolio metrics and daily snapshots.

**Views:**

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/` and `/dashboard/` | `PortfolioDashboardView` | KPI cards (AUM, P&L, YTD return, client count) + Plotly Dash iframe |
| `/api/snapshot/` | `PortfolioSnapshotAPIView` | JSON endpoint for D3.js AUM trend chart (default 90 days) |

### 3.3 Analytics (`apps/analytics/`)

Market data storage and risk metric computation.

**Views:**

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/analytics/` | `AnalyticsDashboardView` | Risk KPI cards (VaR, Sharpe, MaxDD, Volatility) + Plotly Dash iframe |
| `/analytics/risk/` | `RiskMetricListView` | Paginated risk metrics, filterable by scope |
| `/analytics/market-data/<ticker>/` | `MarketDataAPIView` | OHLCV JSON for a ticker (default 90 days) |

### 3.4 ETL Monitor (`apps/etl_monitor/`)

Airflow pipeline monitoring, DAG triggering, and failure alerting.

**Views:**

| URL Pattern | View | Purpose |
|-------------|------|---------|
| `/etl/` | `ETLDashboardView` | Latest DAG runs by dag_id, unacknowledged alerts, Plotly Dash iframe |
| `/etl/runs/` | `DAGRunListView` | Paginated DAG run history, filter by dag_id & state |
| `/etl/trigger/<dag_id>/` | `TriggerDAGView` | POST to trigger a DAG (requires `etl_monitor.trigger_dag` permission) |
| `/etl/api/alerts/` | `PipelineAlertsAPIView` | JSON endpoint returning unacknowledged alerts |

**Service Layer (`services.py`):**
- `sync_dag_runs(dag_id, limit)` — Poll Airflow API, upsert `DAGRun` records, auto-create `CRITICAL` alerts on failure
- `trigger_dag(dag_id, conf)` — POST to Airflow to trigger a new DAG run
- `list_dags()` — List all active DAGs from Airflow

**Celery Task:**
- `sync_all_dag_runs()` — Periodic (via django-celery-beat), syncs last 20 runs for each monitored DAG, retries up to 3 times

---

## 4. Data Model

### 4.1 Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    User      │       │     Client       │       │   Account    │
│ (auth_user)  │◄──────│                  │──────►│              │
│              │  RM   │ client_id (UK)   │  1:N  │ account_num  │
│              │       │ name, email      │       │ (UK)         │
│              │       │ tier (ENUM)      │       │ account_type │
│              │       │ risk_profile     │       │ market_value │
│              │       │ kyc_verified     │       │ ytd_return   │
└──────────────┘       └──────────────────┘       └──────┬───────┘
                                                         │
                                              ┌──────────┼──────────┐
                                              │ 1:N               1:N│
                                     ┌────────▼────────┐  ┌────────▼────────┐
                                     │    Holding      │  │  Transaction    │
                                     │                 │  │                 │
                                     │ ticker          │  │ type (ENUM)     │
                                     │ asset_class     │  │ ticker          │
                                     │ quantity        │  │ trade_date      │
                                     │ market_value    │  │ net_amount      │
                                     │ unrealized_pnl  │  │ reference_num   │
                                     │ weight          │  │                 │
                                     └─────────────────┘  └─────────────────┘
                                     UK: (account, ticker)

┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐
│ PortfolioSnapshot │  │ AssetAllocation   │  │     MarketData        │
│                   │  │ Target            │  │                       │
│ snapshot_date(UK) │  │                   │  │ ticker + price_date   │
│ total_aum         │  │ risk_profile (UK) │  │ (UK)                  │
│ equity_value      │  │ equity_target_%   │  │ OHLCV + volume        │
│ fi_value          │  │ fi_target_%       │  │ adjusted_close        │
│ alt_value         │  │ alt_target_%      │  │                       │
│ cash_value        │  │ cash_target_%     │  │                       │
│ daily_pnl         │  │ rebal_threshold   │  │                       │
│ daily/ytd_return  │  │                   │  │                       │
└───────────────────┘  └───────────────────┘  └───────────────────────┘

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│    RiskMetric      │  │  BenchmarkReturn   │  │  Performance       │
│                    │  │                    │  │  Attribution       │
│ scope (ENUM)       │  │ benchmark_code +   │  │                    │
│ reference_id       │  │ return_date (UK)   │  │ account_number     │
│ calculation_date   │  │                    │  │ period_start/end   │
│ var_95/99_1d       │  │ daily_return       │  │ asset_class        │
│ cvar_95_1d         │  │ cumulative_return  │  │ allocation_effect  │
│ sharpe / sortino   │  │ index_level        │  │ selection_effect   │
│ max_drawdown       │  │                    │  │ interaction_effect │
│ beta / alpha       │  │                    │  │ total_effect       │
└────────────────────┘  └────────────────────┘  └────────────────────┘
UK: (scope, ref_id, calc_date, lookback)

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│     DAGRun         │  │  TaskInstance      │  │  PipelineAlert     │
│                    │  │                    │  │                    │
│ dag_id             │  │ dag_run (FK)       │  │ dag_run (FK, null) │
│ dag_run_id (UK)    │  │ task_id            │  │ dag_id             │
│ state (ENUM)       │  │ state              │  │ severity (ENUM)    │
│ execution_date     │  │ start/end_date     │  │ message            │
│ start/end_date     │  │ duration_seconds   │  │ acknowledged       │
│ duration_seconds   │  │ try_number         │  │ acknowledged_by    │
│ conf (JSON)        │  │ log_url            │  │                    │
└────────────────────┘  └─────────┬──────────┘  └────────────────────┘
                        UK: (dag_run, task_id)
```

### 4.2 Key Enumerations

| Field | Values |
|-------|--------|
| Client.tier | `UHNW` (Ultra-High Net Worth), `HNW`, `MA` (Mass Affluent), `INST` (Institutional) |
| Client.risk_profile | `CONSERVATIVE`, `MODERATE`, `AGGRESSIVE`, `VERY_AGGRESSIVE` |
| Account.account_type | `DISC` (Discretionary), `ADV` (Advisory), `CUST` (Custody), `TRUST`, `RET` (Retirement) |
| Holding.asset_class | `EQ` (Equity), `FI` (Fixed Income), `ALT` (Alternatives), `CASH`, `RE` (Real Estate), `COMM` (Commodities) |
| Transaction.type | `BUY`, `SELL`, `DIV`, `INT`, `FEE`, `TFI` (Transfer In), `TFO` (Transfer Out), `DEP`, `WIT` |
| RiskMetric.scope | `ACCOUNT`, `PORTFOLIO`, `SECURITY` |
| DAGRun.state | `queued`, `running`, `success`, `failed`, `skipped` |
| PipelineAlert.severity | `CRITICAL`, `WARNING`, `INFO` |

### 4.3 Database Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| Client | `(tier, is_active)` | Filter clients by tier |
| Holding | `(account, ticker)` UNIQUE | Prevent duplicate positions |
| Transaction | `(account, trade_date)` | Query recent trades per account |
| Transaction | `(ticker, trade_date)` | Cross-account ticker lookup |
| MarketData | `(ticker, -price_date)` | Latest price fetch |
| RiskMetric | `(scope, reference_id, calculation_date, lookback_days)` UNIQUE | Prevent duplicate metrics |
| DAGRun | `(dag_id, -execution_date)` | Latest runs per DAG |

---

## 5. ETL Pipelines (Airflow)

Three DAGs orchestrate the data pipeline. All use PostgreSQL connections (`xyz_postgres`) and follow an **extract → validate → transform → load** pattern with idempotent upserts (`ON CONFLICT DO UPDATE`).

### 5.1 Portfolio ETL DAG

| Property | Value |
|----------|-------|
| Schedule | Mon–Fri 18:30 ET (`30 23 * * 1-5` UTC) |
| Timeout | 2 hours |
| Retries | 2 × 5 minutes |

```
start
  └─► extract_holdings
        └─► validate_holdings ──► [validation_failed]
              └─► transform_holdings
                    └─► load_holdings
                          └─► compute_portfolio_stats
                                └─► refresh_risk_metrics
                                      └─► notify_success
```

**Key Operations:**
- Extract position files from custody/OMS
- Validate data quality (ticker resolution, price freshness, balance checks)
- Apply FX rates, compute P&L, normalize schema
- Upsert into `Holding` and `Account` tables
- Aggregate into `PortfolioSnapshot`
- Calculate VaR (95%, 99%), volatility, Sharpe, max drawdown → `RiskMetric`

### 5.2 Market Data DAG

| Property | Value |
|----------|-------|
| Schedule | Every 15 min, market hours Mon–Fri (`*/15 14-21 * * 1-5` UTC) |
| Timeout | 10 minutes |
| Retries | 3 × 2 minutes |

```
start
  └─► check_market_open ──► [skip if closed]
        ├─► fetch_equity_prices (15 tickers)
        ├─► fetch_fx_rates (6 pairs)
        └─► fetch_benchmark_levels (SPX, MXWO, LBUSTRUU)
              └─► validate_prices (Z-score > 4.5σ → fail, >20% failure → circuit breaker)
                    └─► persist_market_data → update_holding_prices → update_account_values
```

**Tracked Securities:** AAPL, MSFT, GOOGL, AMZN, JPM, GS, BRK.B, TLT, GLD, and others.
**FX Pairs:** EUR/USD, GBP/USD, JPY/USD, CHF/USD, CAD/USD, AUD/USD.

### 5.3 Risk Report DAG

| Property | Value |
|----------|-------|
| Schedule | Tue–Sat 00:00 UTC (`0 0 * * 2-6`) |
| Timeout | 3 hours |
| Retries | 1 × 10 minutes |

```
start
  └─► wait_for_portfolio_etl (ExternalTaskSensor, 1hr timeout)
        ├─► compute_historical_var (252-day, 90/95/99% confidence)
        ├─► compute_parametric_var (Delta-Normal / variance-covariance)
        ├─► compute_stress_tests (4 scenarios)
        └─► compute_attribution (Brinson-Hood-Beebower)
              └─► build_risk_report → persist_risk_metrics → distribute_reports
```

**Stress Test Scenarios:**

| Scenario | Equity Shock | Credit Spread | Volatility |
|----------|-------------|---------------|------------|
| GFC 2008 | -42% | +5% | 2.5× |
| COVID 2020 | -34% | +2.5% | 4× |
| Taper Tantrum 2013 | -6% | +130 bps rates | — |
| Rate Rise 300bps | -18% | +300 bps rates | — |

### 5.4 Pipeline Dependency Chain

```
Market Data DAG (every 15 min, intraday)
        │
        ▼
Portfolio ETL DAG (18:30 ET daily)
        │
        ▼ (ExternalTaskSensor)
Risk Report DAG (19:00 ET daily)
```

---

## 6. Interactive Dashboards (Plotly Dash)

Three Dash apps are embedded into Django templates via `django-plotly-dash` iframes.

### 6.1 Portfolio Dashboard (`PortfolioDashApp`)

| Component | Type | Description |
|-----------|------|-------------|
| Period selector | Dropdown | YTD, 6M, 1Y, 3Y |
| Benchmark selector | Dropdown | S&P 500, MSCI World, 60/40 Blend |
| AUM trend | Line chart | Total AUM over selected period |
| Asset allocation | Sunburst | Equity (US Large/Small/Intl), FI (Treasuries/IG/HY), Alternatives, Cash |
| Attribution | Bar chart | Brinson-Hood-Beebower: allocation + selection + interaction |
| Rolling return | Line chart | Portfolio vs benchmark return |

### 6.2 Risk Analytics (`RiskAnalyticsApp`)

| Component | Type | Description |
|-----------|------|-------------|
| Account selector | Dropdown | Individual account or total portfolio |
| Lookback slider | Range | 63–504 trading days |
| VaR fan chart | Area chart | 90/95/99% confidence, 1–21 day horizons |
| Drawdown | Line chart | Cumulative loss from peak |
| Correlation heatmap | Heatmap | 8-asset correlation matrix |
| Efficient frontier | Scatter | Markowitz mean-variance frontier |

### 6.3 ETL Monitor (`ETLMonitorApp`)

| Component | Type | Description |
|-----------|------|-------------|
| Days slider | Range | 1–30 days of history |
| Gantt timeline | Gantt | DAG runs color-coded by state (green/red/blue) |
| Success rate | Bar chart | % successful runs per DAG |
| Duration | Box plot | Min/max/median run time per DAG |

---

## 7. REST API

Base URL: `/api/v1/`

### 7.1 Endpoints

| Endpoint | ViewSet | Methods | Features |
|----------|---------|---------|----------|
| `/api/v1/accounts/clients/` | `ClientViewSet` | CRUD | Search (name, client_id, email), order (name, onboarded_date) |
| `/api/v1/accounts/clients/{id}/aum_summary/` | Custom action | GET | Returns client_id + total_aum |
| `/api/v1/accounts/accounts-list/` | `AccountViewSet` | CRUD | Filter (account_type, currency, client), order (market_value, ytd_return) |
| `/api/v1/accounts/transactions/` | `TransactionViewSet` | Read-only | Filter (type, ticker, account), order (trade_date, net_amount) |
| `/api/v1/analytics/market-data/` | `MarketDataViewSet` | Read-only | Search (ticker, security_name), filter (ticker, currency) |
| `/api/v1/analytics/risk-metrics/` | `RiskMetricViewSet` | Read-only | Filter (scope, reference_id), order (calculation_date) |

### 7.2 Authentication & Authorization

- **Authentication:** Session + Basic (DRF default)
- **Permission:** `IsAuthenticated` on all endpoints
- **Pagination:** `PageNumberPagination`, page size 50

### 7.3 Serializers

| Serializer | Nesting | Computed Fields |
|------------|---------|-----------------|
| `ClientSerializer` | Nested `AccountSerializer` | `total_aum` |
| `AccountSerializer` | Nested `HoldingSerializer` | — |
| `HoldingSerializer` | — | `unrealized_pnl_pct` |
| `TransactionSerializer` | — | — |
| `MarketDataSerializer` | — | — |
| `RiskMetricSerializer` | — | — |

---

## 8. Infrastructure & Deployment

### 8.1 Docker Services

| Service | Image | Port (Dev) | Purpose |
|---------|-------|------------|---------|
| `db` | postgres:16-alpine | 3000 | Primary database |
| `redis` | redis:7-alpine | 3001 | Cache + Celery broker |
| `django` | Custom (Python 3.11) | 3002 | Web application |
| `celery-worker` | Same as django | — | Background task execution (4 workers) |
| `celery-beat` | Same as django | — | Periodic task scheduler |
| `airflow-webserver` | Custom (Airflow 2.9) | 3003 | Airflow UI |
| `airflow-scheduler` | Same as airflow | — | DAG execution |
| `airflow-init` | Same as airflow | — | One-time DB migration + admin user |
| `nginx` | Custom (nginx) | 80, 443 | Reverse proxy (production only) |

### 8.2 Production Configuration

| Component | Setting |
|-----------|---------|
| Gunicorn | 8 workers, gthread class, 4 threads/worker, 120s timeout |
| Celery | 8 concurrency |
| PostgreSQL | shared_buffers=512MB, effective_cache_size=2GB |
| Redis | Password-protected, persistence (save 60 1) |
| Nginx | TLS 1.2/1.3, rate limiting (login: 5 req/min, API: 60 req/min) |
| Django | Non-root user (`xyz:xyz`), static collected at build time |

### 8.3 Networking

```
Internet ──► Nginx (443/TLS) ──► Gunicorn (8000)
                    │
                    ├──► Static files (WhiteNoise, 30d cache)
                    ├──► Media files (7d cache)
                    └──► WebSocket upgrade (/ws/channel)
```

### 8.4 Volumes

| Volume | Contents |
|--------|----------|
| `postgres_data` | Database files (persistent) |
| `redis_data` | Redis AOF/RDB snapshots |
| `static_files` | Collected static assets |
| `media_files` | User-uploaded files |

---

## 9. CI/CD Pipeline

**Platform:** GitHub Actions (`.github/workflows/ci-cd.yml`)

```
┌────────┐     ┌────────┐     ┌────────┐     ┌──────────────┐
│  Lint  │────►│  Test  │────►│ Build  │────►│   Deploy     │
│        │     │        │     │(Docker)│     │(Staging/Prod)│
└────────┘     └────────┘     └────────┘     └──────────────┘
```

### 9.1 Stages

| Stage | Trigger | Actions |
|-------|---------|---------|
| **Lint** | All pushes/PRs | Black format check, Flake8 (max-line=120), isort |
| **Test** | After lint | pytest with coverage, PostgreSQL 16 + Redis 7 services, upload to Codecov |
| **Build** | Push only | Multi-arch Docker build (QEMU), push to GHCR with SHA/branch/semver tags |
| **Deploy Staging** | `develop` branch | SSH pull + `docker compose up -d` + migrate + collectstatic |
| **Deploy Production** | `main` branch | Blue-green: scale to 2 → migrate → health check → scale to 1; Slack notification |

---

## 10. Security

### 10.1 Application Security

| Control | Implementation |
|---------|----------------|
| Authentication | Django session auth, `@login_required` on all views |
| CSRF | `CsrfViewMiddleware` + `CSRF_TRUSTED_ORIGINS` |
| CORS | `django-cors-headers`, whitelist-only in production |
| Secrets | Environment variables via `.env`, never committed |
| Password Policy | 4 validators (similarity, min length, common, numeric) |

### 10.2 Production Hardening

| Control | Setting |
|---------|---------|
| HSTS | Enabled with preload |
| CSP | Configured in Nginx |
| Secure Cookies | `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` |
| SSL Redirect | `SECURE_SSL_REDIRECT=True` |
| X-Frame-Options | `DENY` (prod), `SAMEORIGIN` (dev, for Dash iframes) |
| Rate Limiting | Login: 5 req/min, API: 60 req/min (Nginx) |
| Container Security | Non-root user (`xyz:xyz`), minimal base image |

### 10.3 Airflow Security

- Basic auth for API access (credentials in `.env`)
- Separate database (`airflow_db`) from application database
- DAGs restricted to read-only in scheduler container

---

## 11. Observability

### 11.1 Logging

| Logger | Level | Handlers | Notes |
|--------|-------|----------|-------|
| Root | INFO | Console | Catch-all |
| `django` | WARNING | Console + File | Framework-level errors |
| `apps` | DEBUG | Console + File | Application-level detail |
| `dags` | INFO | Console + File | Airflow DAG execution |

Log files rotate at 10 MB with 5 backups (`logs/xyz_platform.log`).

### 11.2 Health Checks

| Component | Endpoint/Method |
|-----------|----------------|
| Django | `curl /admin/login/` (Docker healthcheck) |
| Nginx | `/health/` → 200 OK |
| PostgreSQL | `pg_isready` |
| Redis | `redis-cli ping` |
| Airflow | `curl /health` |

### 11.3 Error Tracking

- **Sentry** integration in production (if `SENTRY_DSN` is set)
- Celery task failures logged and retried (configurable per task)
- Airflow failures auto-create `CRITICAL` `PipelineAlert` records

### 11.4 Monitoring Points

| What | How |
|------|-----|
| DAG run failures | `PipelineAlert` model + unacknowledged alerts API |
| Celery task state | `django-celery-results` (stored in PostgreSQL) |
| Request latency | Nginx access logs |
| Application errors | Sentry (prod), rotating log files (all envs) |
| Database health | PostgreSQL `pg_isready`, connection timeout (10s) |

---

## Appendix A: URL Map

```
/                                          Portfolio Dashboard
/dashboard/                                Portfolio Dashboard (alias)
/admin/                                    Django Admin

/accounts/login/                           Login
/accounts/logout/                          Logout

/clients/                                  Client List
/clients/<pk>/                             Client Detail
/clients/account/<account_number>/         Account Detail

/analytics/                                Analytics Dashboard
/analytics/risk/                           Risk Metric List
/analytics/market-data/<ticker>/           Market Data JSON

/etl/                                      ETL Dashboard
/etl/runs/                                 DAG Run List
/etl/trigger/<dag_id>/                     Trigger DAG (POST)
/etl/api/alerts/                           Pipeline Alerts JSON

/api/v1/accounts/clients/                  Client API
/api/v1/accounts/accounts-list/            Account API
/api/v1/accounts/transactions/             Transaction API
/api/v1/analytics/market-data/             Market Data API
/api/v1/analytics/risk-metrics/            Risk Metric API

/django_plotly_dash/app/PortfolioDashApp/  Portfolio Dash App
/django_plotly_dash/app/RiskAnalyticsApp/  Risk Analytics Dash App
/django_plotly_dash/app/ETLMonitorApp/     ETL Monitor Dash App
```

## Appendix B: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DEBUG` | No | `False` | Debug mode |
| `ALLOWED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated host list |
| `DB_NAME` | No | `xyz_platform` | PostgreSQL database name |
| `DB_USER` | Yes | — | PostgreSQL user |
| `DB_PASSWORD` | Yes | — | PostgreSQL password |
| `DB_HOST` | No | `localhost` | PostgreSQL host |
| `DB_PORT` | No | `5432` | PostgreSQL port |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `AIRFLOW_API_URL` | No | `http://localhost:8080/api/v1` | Airflow REST API base URL |
| `AIRFLOW_API_USER` | Yes | — | Airflow API username |
| `AIRFLOW_API_PASSWORD` | Yes | — | Airflow API password |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |
| `USE_S3` | No | `False` | Enable S3 static/media storage |
| `CORS_ALLOWED_ORIGINS` | No | — | Allowed CORS origins (production) |

## Appendix C: Dependencies

**Runtime (base.txt):**
Django 4.2.13, djangorestframework 3.15.2, psycopg2-binary 2.9.9, redis 5.0.4, celery 5.4.0, django-celery-beat 2.6.0, django-celery-results 2.5.1, channels 4.1.0, channels-redis 4.2.0, django-plotly-dash 2.5.1, plotly 5.22.0, dash 2.17.1, pandas 2.2.2, numpy 1.26.4, scipy 1.13.1, apache-airflow 2.9.2, gunicorn 22.0.0, whitenoise 6.7.0, django-environ 0.11.2, django-cors-headers 4.4.0, django-filter 24.2, crispy-forms 2.2, crispy-bootstrap5 0.7, Pillow 10.3.0, openpyxl 3.1.4, requests 2.32.3

**Development (development.txt):**
django-debug-toolbar 4.4.2, factory-boy 3.3.0, faker 25.9.1, pytest 8.2.2, pytest-django 4.8.0, pytest-cov 5.0.0, coverage 7.5.4, black 24.4.2, flake8 7.1.0, isort 5.13.2, pre-commit 3.7.1, ipython 8.25.0, django-extensions 3.2.3

**Production (production.txt):**
sentry-sdk 2.5.1, django-storages 1.14.3, boto3 1.34.134, psutil 5.9.8
