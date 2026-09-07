# NYC Yellow Taxi Demand Forecasting

An end-to-end analytics project for NYC Yellow Taxi demand: automated TLC ingestion, PySpark processing, PostgreSQL, machine learning, FastAPI, Streamlit and Airflow.

**Live app:** https://george-nyc-taxi-analytics.streamlit.app/

## Project Flow

```text
TLC monthly data → PySpark → PostgreSQL / Supabase → ML → FastAPI → Streamlit
                         ↑
                    Airflow orchestration
```

The pipeline is state-driven: newly published TLC data can be ingested and model outputs refreshed without changing the documentation.

## Local Execution

Run from the repository root and configure the required environment variables in `.env`.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Build/process the analytical data
python -m backend.workflows.run_pipeline

# 3. Train, evaluate and publish ML outputs
python -m backend.workflows.ml_pipeline

# 4. Start FastAPI
uvicorn backend.serving.fast_api:app --reload

# 5. In a second terminal, start Streamlit
streamlit run frontend/Home.py

# 6. Run tests
pytest -q
```

GitHub Actions runs the focused pytest suite automatically on pushes and pull requests to `main`.

## Documentation

- [Backend](docs/backend.md) — data model, processing, ML and API
- [Orchestration](docs/orchestration.md) — Airflow update workflow
- [Frontend](docs/frontend.md) — Streamlit UI and mockup
- [Deployment](docs/deployment.md) — hosted architecture and CI

## Tech Stack

Python · PySpark · PostgreSQL · Supabase · Spark ML · FastAPI · Streamlit · Airflow · Docker · pytest · GitHub Actions
