# Backend

The backend transforms raw taxi records into analytical tables, model outputs and API responses.

## Data Processing & Storage

```mermaid
flowchart LR
    TLC[TLC Parquet] --> Spark[PySpark]
    Spark --> DB[(PostgreSQL)]
    Spark --> ML[Spark ML]
    ML --> DB
    DB --> API[FastAPI]
```

**PySpark** handles cleaning, feature preparation and aggregation because the trip data is large enough to benefit from distributed DataFrame processing. **PostgreSQL** stores structured analytics and serving tables; the same relational model is published to **Supabase PostgreSQL** for the hosted application. Repository modules isolate SQL access from the API and frontend.

## Data Model

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

Supporting tables store pipeline state, model metrics, feature importance and forecast metadata.

## Machine Learning

The project separates two prediction problems.

**Historical evaluation** asks how well demand can be predicted when prior observed demand is available. It can therefore use calendar features, lagged demand and rolling statistics. A persistence baseline and Random Forest are evaluated on a chronological holdout.

**Future forecasting** must work for dates where demand has not yet been observed. Its features are restricted to calendar information and historical demand profiles to prevent leakage.

### Future Model Selection

```mermaid
flowchart LR
    F[Forecast-safe features] --> B[Rolling temporal backtests]
    B --> P[Profile baseline]
    B --> LR[Linear Regression]
    B --> RF[Random Forest]
    B --> GBT[Gradient-Boosted Trees]
    P --> M[Average MAE & RMSE]
    LR --> M
    RF --> M
    GBT --> M
    M --> S[Lowest MAE wins]
    S --> T[RMSE tie-breaker]
    T --> PUB[Publish production forecast profile]
```

The latest time periods are used as rolling holdouts. Every candidate is trained only on earlier observations and evaluated on the following holdout period. Metrics are averaged across the backtests. The candidate with the lowest average **MAE** becomes the production model; **RMSE** breaks a tie. Selection is therefore based on out-of-time performance rather than model complexity.

**Spark ML** is used for the trainable models so feature engineering and modelling stay in the same scalable processing ecosystem.

## FastAPI & Testing

**FastAPI** provides a lightweight service layer over published PostgreSQL results. Forecast requests read precomputed serving profiles instead of launching Spark or retraining a model, keeping interactive requests fast.

**pytest** validates forecast-safe feature logic, scoring-grid completeness, leakage protection, model selection and API health. Spark tests use small synthetic DataFrames so the suite remains practical for local execution and CI.
