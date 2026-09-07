# NYC Yellow Taxi Demand Forecasting

An end-to-end analytics project for NYC Yellow Taxi demand. It combines automated TLC data ingestion, PySpark processing, PostgreSQL, demand modelling, FastAPI, Streamlit, Airflow and automated tests.

The system is designed to grow with newly published monthly TLC data without requiring documentation changes.

## Project Flow

```text
TLC monthly data
      ↓
Ingestion + PySpark processing
      ↓
PostgreSQL / Supabase
      ↓
Historical model evaluation + future forecasting
      ↓
FastAPI
      ↓
Streamlit
```

Airflow orchestrates the recurring update workflow. When a new TLC month is available, the data is processed and the model outputs are refreshed. If no new month is available, the workflow exits without unnecessary retraining.

## Local Execution

Run commands from the repository root. Configure the required environment variables in `.env` before starting components that use the database or external services.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the data pipeline

```bash
python -m backend.workflows.run_pipeline
```

This performs the ingestion and processing workflow used to prepare the analytical data.

### 3. Run the ML pipeline

```bash
python -m backend.workflows.ml_pipeline
```

This evaluates the historical demand model, compares forecast-safe future models, selects the best candidate and publishes the serving data.

### 4. Start FastAPI

```bash
uvicorn backend.serving.fast_api:app --reload
```

### 5. Start Streamlit

In a second terminal:

```bash
streamlit run frontend/Home.py
```

### 6. Run tests

```bash
pytest -q
```

The focused test suite covers critical API, forecasting-feature and model-selection behaviour. GitHub Actions runs the same tests automatically on pushes and pull requests to `main`.

## Documentation

Detailed documentation is intentionally split by responsibility:

- [Backend](docs/backend.md) — data processing, database, modelling and API
- [Orchestration](docs/orchestration.md) — Airflow and automated monthly updates
- [Frontend](docs/frontend.md) — Streamlit application
- [Deployment](docs/deployment.md) — production services, configuration and CI

## Tech Stack

Python · PySpark · PostgreSQL · Supabase · scikit-learn / Spark ML · FastAPI · Streamlit · Airflow · Docker · pytest · GitHub Actions
