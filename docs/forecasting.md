# Demand forecasting

## Forecasting tasks

The project distinguishes two related forecasting tasks:

1. **Historical model evaluation** — a Spark Random Forest using lag and rolling-demand features.
2. **Future demand inference** — a long-horizon forecasting model validated with future-month backtests and served from PostgreSQL/Supabase.

Both estimate hourly cleaned Yellow Taxi pickup demand at taxi-zone level, but they have different purposes and feature-availability constraints.

## Historical Random Forest

The historical Spark ML model uses 13 predictors:

- `hour`
- `day_of_week`
- `day_of_month`
- `is_weekend`
- `hour_sin`
- `hour_cos`
- `dow_sin`
- `dow_cos`
- `lag_1h`
- `lag_24h`
- `lag_168h`
- `rolling_mean_24h`
- `rolling_mean_168h`

Rolling windows exclude the current target observation. Rows are retained for modeling only after a complete seven-day trailing history is available.

The Spark `RandomForestRegressor` uses 100 trees, maximum depth 10 and random seed 42.

### Latest validated historical retraining

Using data through May 2026:

| Metric | Baseline | Random Forest |
|---|---:|---:|
| MAE | 6.51 | **4.63** |
| RMSE | 21.84 | **15.97** |

Training rows: **2,079,720**  
Test rows: **197,160**  
Latest data timestamp: **2026-05-31 23:00:00**  
Test period: **May 2026**

Historical predictions, model metrics and feature importance are published to PostgreSQL/Supabase after training. FastAPI reads them from the database rather than `data/app` files.

## Why a separate future model is needed

Lag-based features such as `lag_1h`, `lag_24h` and `lag_168h` require recent observed demand. They are appropriate for historical/near-term evaluation but are not naturally available for an arbitrary date months into the future.

For long-horizon user-facing forecasts, models must be validated using features available at prediction time.

## Rolling future-model validation

Four future months were evaluated:

| Test month | Profile MAE | Profile RMSE | RF MAE | RF RMSE |
|---|---:|---:|---:|---:|
| 2026-02 | 7.3255 | 19.1128 | 7.5178 | 19.4840 |
| 2026-03 | 6.0025 | 14.7159 | 7.2744 | 20.4239 |
| 2026-04 | 5.7818 | 14.0006 | 6.5784 | 17.5946 |
| 2026-05 | 6.5023 | 16.3303 | 7.9272 | 21.4538 |

Aggregate results:

| Model | MAE | RMSE | Backtest months |
|---|---:|---:|---:|
| `zone_dow_hour_mean` | **6.4030** | **16.0399** | 4 |
| `random_forest` | 7.3245 | 19.7391 | 4 |

The profile model currently wins the validated future comparison and is therefore the **production future forecasting model**.

## Production future model

`zone_dow_hour_mean` computes average historical demand for:

```text
LocationID × Spark day_of_week × hour
```

Validated snapshot through May 2026:

- production model: `zone_dow_hour_mean`
- trained through: `2026-05-31 23:00:00`
- profile rows: `41,604`

## Future prediction serving

FastAPI exposes `GET /future-model-metrics` and `POST /predict`. The prediction endpoint maps a future datetime to the published profile and uses this fallback order:

```text
exact zone + day-of-week + hour
        ↓
zone + hour average
        ↓
zone overall average
```

A forecast datetime at or before the model's `trained_through` timestamp returns HTTP 400.

## Serving storage

Historical serving tables:

- `taxi_analytics.historical_model_metric`
- `taxi_analytics.historical_feature_importance`
- `taxi_analytics.historical_model_prediction`

Future serving tables:

- `taxi_analytics.future_demand_profile`
- `taxi_analytics.future_model_metric`
- `taxi_analytics.future_forecast_metadata`

Both historical and future serving are database-backed. There is no manual Git deployment step for model-serving snapshots after retraining.

## ML orchestration

`backend/workflows/ml_pipeline.py` runs:

```text
Historical Random Forest
        ↓
Historical database publisher
        ↓
Future rolling backtest
        ↓
Future database publisher
        ↓
Local PostgreSQL + Supabase
```

## Modeling limitations and next evaluation direction

The current production future profile captures recurring zone/day/hour patterns but does not currently model weather, special events, holidays as a dedicated feature, traffic conditions or unexpected disruptions.

A practical next modeling iteration is to compare the existing profile baseline with additional models using only forecast-safe calendar and historical aggregate features. Candidate features include hour/day/month cyclical encodings, weekend/holiday indicators and zone-level historical demand profiles. This allows fair comparison without using unknown future observed lags.

For upstream construction see [Data pipeline](data_pipeline.md), and for production configuration see [Deployment](deployment.md).
