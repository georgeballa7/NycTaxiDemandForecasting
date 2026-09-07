# Backend

The backend owns data processing, persistence, modelling and API serving.

## Data Flow

```mermaid
flowchart LR
    TLC[TLC Parquet] --> Spark[PySpark processing]
    Spark --> DB[(PostgreSQL)]
    Spark --> ML[Model training & evaluation]
    ML --> DB
    DB --> API[FastAPI]
```

Monthly TLC files are cleaned and aggregated with PySpark. PostgreSQL stores analytics and published model outputs so neither FastAPI nor Streamlit needs to run Spark during user requests.

## Data Model

The analytical schema uses dimensions for zone, date, hour and payment method; facts hold aggregated demand and trip measures. Model-serving tables are linked to taxi zones where appropriate.

```mermaid
erDiagram
    DIM_ZONE ||--o{ FACT_DEMAND : location_id
    DIM_DATE ||--o{ FACT_DEMAND : pickup_date
    DIM_HOUR ||--o{ FACT_DEMAND : hour

    DIM_ZONE ||--o{ FACT_TRIPS : location_id
    DIM_DATE ||--o{ FACT_TRIPS : pickup_date
    DIM_HOUR ||--o{ FACT_TRIPS : hour
    DIM_PAYMENT ||--o{ FACT_TRIPS : payment_type

    DIM_ZONE ||--o{ HISTORICAL_MODEL_PREDICTION : location_id
    DIM_ZONE ||--o{ FUTURE_DEMAND_PROFILE : location_id

    DIM_ZONE {
        int location_id PK
        varchar borough
        varchar zone
        varchar service_zone
    }
    DIM_DATE {
        date full_date PK
        smallint year
        smallint month
        smallint weekday_number
        boolean is_weekend
    }
    DIM_HOUR {
        smallint hour PK
        varchar day_part
    }
    DIM_PAYMENT {
        smallint payment_type PK
        varchar payment_method
    }
    FACT_DEMAND {
        int location_id PK, FK
        date pickup_date PK, FK
        smallint hour PK, FK
        int demand
    }
    FACT_TRIPS {
        int location_id PK, FK
        date pickup_date PK, FK
        smallint hour PK, FK
        smallint payment_type PK, FK
        int trip_count
        numeric fare_amount
        numeric total_amount
        numeric trip_distance
    }
    HISTORICAL_MODEL_PREDICTION {
        int location_id PK, FK
        timestamp pickup_hour PK
        double actual_demand
        double predicted_demand
    }
    FUTURE_DEMAND_PROFILE {
        int location_id PK, FK
        smallint month PK
        smallint day_of_week PK
        smallint hour PK
        double predicted_demand
    }
```

Operational/model metadata tables (`pipeline_runs`, model metrics, feature importance and forecast metadata) are intentionally omitted from the ERD to keep the analytical relationships readable.

## Modelling

**Historical evaluation** may use calendar, lag and rolling-demand features because previous observed demand is available. A persistence baseline and Random Forest are evaluated with a time-based holdout.

**Future forecasting** cannot use unknown future demand. It uses calendar features and historical demand profiles only. A profile baseline, Linear Regression, Random Forest and Gradient-Boosted Trees are compared with rolling temporal backtests. Production selection is automatic: lowest average MAE, then RMSE as tie-breaker.

The winning forecast is published as a month-aware zone × weekday × hour profile.

## API & Tests

FastAPI reads published PostgreSQL results and exposes analytics, model evaluation and future prediction without retraining on request. Future prediction uses exact profile matching with progressively broader fallbacks when necessary.

Pytest covers forecast-safe features, scoring-grid completeness, leakage protection, model selection and the API health endpoint. Spark tests use small synthetic DataFrames rather than production data.
