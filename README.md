# 🚕 NYC Taxi Demand Forecasting & Business Analytics

An end-to-end data engineering and analytics project built on NYC Yellow Taxi data. It combines automated data processing, business analytics, machine learning, demand forecasting, API serving and an interactive dashboard.

🌐 **Live application:** https://george-nyc-taxi-analytics.streamlit.app/

## What the Project Does

The project turns monthly NYC TLC Yellow Taxi data into analysis and demand forecasts through an automated workflow:

```text
NYC TLC monthly data
        ↓
PySpark processing
        ↓
PostgreSQL / Supabase
        ↓
Historical ML + Future Forecast
        ↓
FastAPI
        ↓
Streamlit Analytics App
```

Apache Airflow checks for newly available TLC data each day. When a new month appears, the pipeline processes it, updates the databases, retrains the models and republishes the serving data. If no new month is available, the run finishes without unnecessary retraining.

The currently validated data range is **January 2025 through May 2026**.

## Main Capabilities

- incremental monthly data ingestion and processing
- automated orchestration with Airflow
- PostgreSQL/Supabase analytical data model
- demand and business analytics by time, zone and borough
- historical demand-model evaluation
- leakage-safe future forecasting with automatic model selection
- FastAPI-backed analytics and prediction serving
- interactive Streamlit reporting
- Slack notifications for pipeline failures and successful retraining

## Forecasting

The project separates historical model evaluation from true future forecasting.

The historical Random Forest improves on the persistence baseline:

| Model | MAE | RMSE |
|---|---:|---:|
| Persistence baseline | 6.51 | 21.84 |
| **Random Forest** | **4.63** | **15.97** |

For future forecasting, four candidates are evaluated with rolling time-series backtesting. The production model is selected automatically using MAE, with RMSE as tie-breaker.

| Future model | MAE | RMSE |
|---|---:|---:|
| **Zone-weekday-hour baseline** | **6.40** | **16.04** |
| Linear Regression | 7.03 | 16.43 |
| Random Forest | 7.15 | 18.93 |
| Gradient-Boosted Trees | 7.30 | 19.37 |

The simpler baseline currently wins the future forecasting task and is therefore used in production. A different candidate will be promoted automatically if it performs better after a later retraining.

## Tech Stack

**Python · Pandas · PySpark · PostgreSQL · Supabase · Apache Airflow · Docker · Spark ML · FastAPI · SQLAlchemy · Streamlit · Plotly · Render · GitHub**

## Code Guide

```text
airflow/dags/       Airflow orchestration
backend/src/        ingestion, processing, database and ML logic
backend/workflows/  reusable end-to-end workflows
backend/serving/    FastAPI serving layer
backend/sql/        database schema
frontend/           Streamlit application
docs/               detailed technical documentation
```

The main workflow entry points are:

```bash
python -m backend.workflows.run_pipeline
python -m backend.workflows.ml_pipeline
```

For normal operation, the scheduled Airflow DAG handles incremental ingestion and triggers model retraining only when new data has been processed.

## Documentation

Implementation details are intentionally kept out of this README. The technical documentation is available under `docs/`:

- **Architecture** — system components and responsibilities
- **Data Pipeline** — ingestion, transformation and orchestration
- **Data Model** — PostgreSQL/Supabase analytical and serving tables
- **Forecasting** — feature engineering, backtesting and model selection
- **Deployment & Operations** — Airflow, Supabase, Render and Streamlit operation

## Live Demo

**NYC Taxi Analytics:** https://george-nyc-taxi-analytics.streamlit.app/

> The FastAPI backend uses Render's free tier, so the first request after inactivity may take a short time while the service starts.
