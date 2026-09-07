# Deployment

The production architecture separates data persistence, API serving, frontend hosting, orchestration and continuous integration.

## Services

| Component | Role |
|---|---|
| Supabase PostgreSQL | Production analytical and model-serving data |
| Render | FastAPI hosting |
| Streamlit Community Cloud | Streamlit frontend |
| Docker Compose | Local Airflow environment |
| GitHub Actions | Automated pytest execution |

The hosted FastAPI service reads prepared results from Supabase PostgreSQL. Streamlit communicates with FastAPI and therefore does not require direct access to the analytical database.

## Configuration

Secrets and environment-specific values are supplied through environment variables rather than committed files. Typical configuration includes the database connection, hosted API URL and optional Slack webhook.

Local development can use a local PostgreSQL connection while hosted services use their production configuration. The codebase keeps the same application logic across environments.

## Deployment Flow

```text
Code push
   ↓
GitHub Actions tests
   ↓
Application deployment
   ↓
FastAPI reads published PostgreSQL data
   ↓
Streamlit consumes FastAPI
```

GitHub Actions installs Python dependencies and Java for PySpark, then runs the focused pytest suite. Tests use isolated configuration and do not require production database credentials.

## Data Refresh vs. Code Deployment

A monthly TLC ingestion is a **data refresh**, not a code deployment. Airflow processes newly available data and republishes model outputs without requiring changes to README or documentation.

A deployment is needed only when application code, dependencies or infrastructure configuration changes. This distinction allows the live system to advance to new data months while the architecture documentation remains valid.

## Operational Checks

The main production checks are intentionally simple:

- Airflow DAG completes successfully;
- new data triggers model retraining and publication;
- a no-op run remains successful when TLC has not published the next month;
- FastAPI health endpoint responds successfully;
- Streamlit can retrieve API data;
- GitHub Actions tests pass for code changes.

No production credentials are required by the unit-test suite.
