# 🚕 NYC Taxi Demand Forecasting & Business Analytics

An end-to-end data engineering and analytics project that transforms NYC Yellow Taxi data into demand forecasts, business insights, and an interactive cloud-deployed application.

🌐 **[Live Application](https://george-nyc-taxi-analytics.streamlit.app/)**

## Overview

This project demonstrates a complete analytics workflow across **data engineering, analytical data modeling, machine learning, API serving, visualization, and cloud deployment**.

NYC TLC Yellow Taxi data is processed with PySpark, transformed into demand and business datasets, loaded into a unified PostgreSQL analytical model, and used to train a Random Forest demand model. FastAPI exposes the analytical and ML outputs to a multi-page Streamlit application.

<a href="https://george-nyc-taxi-analytics.streamlit.app/">
  <img src="docs/images/overview_1.jpeg" alt="NYC Taxi Demand Forecasting Overview">
</a>

*Interactive NYC Taxi analytics application — click the image to open the live app.*

## Architecture

```text
NYC TLC Yellow Taxi Parquet + Zone Lookup
                  ↓
              PySpark
                  ↓
       Data Pipeline / ML Pipeline
            ↙             ↘
PostgreSQL / Supabase    App & ML Artifacts
            ↘             ↙
             FastAPI on Render
                    ↓
        Streamlit Community Cloud
```

The project deliberately separates **offline processing** from **runtime serving**. PySpark performs large-scale transformations and model training offline; the deployed application consumes PostgreSQL tables and lightweight precomputed artifacts rather than starting Spark for user requests.

Pipeline orchestration is organized into three entry points:

- `backend/workflows/data_pipeline.py` — data preparation and PostgreSQL loading
- `backend/workflows/ml_pipeline.py` — model training and app-artifact publication
- `backend/workflows/run_pipeline.py` — complete Data Pipeline → ML Pipeline execution

## Analytical Data Model

PostgreSQL uses one unified schema, **`taxi_analytics`**, with shared dimensions and separate facts for demand and business analytics:

```text
taxi_analytics
├── dim_zone
├── dim_date
├── dim_hour
├── dim_payment
├── fact_demand
└── fact_trips
```

This supports demand analysis by zone/date/hour while also enabling revenue, payment, tip, distance, toll, surcharge, and trip-volume analysis.

## Key Features

- Large-scale ingestion and transformation with PySpark
- Complete zone-hour demand panel including zero-demand observations
- Temporal, cyclical, lag, and rolling-window feature engineering
- Unified PostgreSQL analytical model with dimensions and fact tables
- Random Forest demand forecasting with chronological validation
- Baseline-vs-model evaluation using MAE and RMSE
- Revenue, payment, tip, trip-value, and zone-level business analytics
- REST API serving with FastAPI and SQLAlchemy
- Interactive multi-page Streamlit application with Plotly visualizations
- PDF project-report generation
- Cloud deployment with Supabase, Render, and Streamlit Community Cloud

## 🔮 Demand Forecasting

The forecasting workflow uses historical hourly demand features including **1-hour, 24-hour, and 168-hour lags** plus rolling demand averages and cyclical time encodings.

The model is evaluated chronologically using June 2025 as the held-out period.

| Model | MAE | RMSE |
|---|---:|---:|
| 24-hour persistence baseline | 7.1601 | 23.4332 |
| Random Forest | **5.0092** | **16.7101** |

The strongest model signal is weekly demand recurrence (`lag_168h`), followed by recent hourly and daily demand history.

![Actual vs Predicted Taxi Demand](docs/images/forecast_2.jpeg)

## 💼 Business Analytics

The business analytics layer complements demand forecasting with commercial and operational measures including:

- trip volume
- fare and total revenue
- tips
- payment methods
- trip distance
- tolls and congestion-related charges
- borough and taxi-zone performance

![NYC Taxi Business Analytics](docs/images/business_1.jpeg)

## 🎯 From Analytics to Decisions

The Strategic Insights layer combines demand patterns, forecasting results, and commercial performance to support practical interpretation of when and where taxi activity is strongest.

![NYC Taxi Strategic Insights](docs/images/strategic_1.jpeg)

## Tech Stack

| Area | Technologies |
|---|---|
| Data Processing | Python, Pandas, PySpark |
| Data Engineering | Parquet, feature pipelines, workflow orchestration |
| Database | PostgreSQL, Supabase |
| Machine Learning | Spark ML Random Forest |
| Backend | FastAPI, SQLAlchemy |
| Frontend | Streamlit, Plotly |
| Deployment | Render, Streamlit Community Cloud, Supabase |
| Development | Git, GitHub |

## Project Structure

```text
backend/
├── serving/             # FastAPI application and schemas
├── sql/                 # PostgreSQL schema DDL
├── src/
│   ├── config/          # Central backend settings
│   ├── database/        # Connection, loaders and query repositories
│   ├── features/        # Forecast feature engineering
│   ├── ingestion/       # Spark session and source ingestion
│   ├── ml/              # Model training and app-artifact preparation
│   ├── persistence/     # Parquet helpers
│   └── processing/      # Data transformations and dataset construction
└── workflows/
    ├── data_pipeline.py
    ├── ml_pipeline.py
    └── run_pipeline.py

frontend/
├── config/              # Frontend API settings
├── pages/               # Streamlit application pages
├── utils/               # API, theme and report utilities
└── streamlit_app.py
```

## Documentation

Detailed technical documentation:

- [Architecture](docs/architecture.md)
- [Data Pipeline](docs/data_pipeline.md)
- [Data Model](docs/data_model.md)
- [Forecasting](docs/forecasting.md)
- [Deployment](docs/deployment.md)

## Live Demo

👉 **[Launch NYC Taxi Analytics](https://george-nyc-taxi-analytics.streamlit.app/)**

> The backend is hosted on Render's free tier. The first request after a period of inactivity may take approximately 50 seconds while the service starts.
