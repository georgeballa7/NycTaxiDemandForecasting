# Demand forecasting

## Forecasting tasks

The project now distinguishes two related forecasting tasks:

1. **Historical model evaluation** — a Spark Random Forest using lag and rolling-demand features.
2. **Future demand inference** — a long-horizon zone/day-of-week/hour demand profile served from PostgreSQL/Supabase.

Both estimate hourly cleaned Yellow Taxi pickup demand at taxi-zone level, but they have different purposes and serving requirements.

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

The Spark `RandomForestRegressor` uses:

- 100 trees
- maximum depth 10
- random seed 42

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

The Random Forest therefore remains useful for historical validation and short-horizon model evaluation.

## Why a separate future model is needed

Lag-based features such as `lag_1h`, `lag_24h` and `lag_168h` require recent observed demand. They are appropriate for historical/near-term evaluation but are not naturally available for an arbitrary date months into the future.

For long-horizon user-facing forecasts, the project therefore validates models using rolling future-month backtests and deploys a profile model that only requires:

- taxi zone
- day of week
- hour of day

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

The profile model wins the validated future comparison and is therefore the **production future forecasting model**.

## Production future model

`zone_dow_hour_mean` computes average historical demand for:

```text
LocationID × Spark day_of_week × hour
```

The publisher creates one serving snapshot and writes it to PostgreSQL/Supabase.

Validated snapshot through May 2026:

- production model: `zone_dow_hour_mean`
- trained through: `2026-05-31 23:00:00`
- profile rows: `41,604`

## Future prediction serving

FastAPI exposes:

- `GET /future-model-metrics`
- `POST /predict`

`POST /predict` accepts a taxi-zone ID and future datetime. Internally it maps the datetime to NYC time where needed and looks up the published profile.

Fallback order:

```text
exact zone + day-of-week + hour
        ↓
zone + hour average
        ↓
zone overall average
```

The response reports the method used as:

- `zone_dow_hour`
- `zone_hour_fallback`
- `zone_fallback`

A zone with no historical profile returns HTTP 404. A forecast datetime at or before the model's `trained_through` timestamp returns HTTP 400.

Example validated production request:

```text
LocationID: 161 (Midtown Center)
Forecast datetime: 2026-09-18 20:00
Predicted demand: 275.596...
Method: zone_dow_hour
Trained through: 2026-05-31 23:00
```

## Serving storage

Future forecast serving is fully database-backed. The following tables are used:

- `taxi_analytics.future_demand_profile`
- `taxi_analytics.future_model_metric`
- `taxi_analytics.future_forecast_metadata`

There is intentionally no `data/app/future_forecast/` directory in the production design.

Historical model outputs remain file-based under `data/app/` and are loaded by FastAPI for historical validation views.

## ML orchestration

`backend/workflows/ml_pipeline.py` runs:

```text
Historical Random Forest
        ↓
Historical app artifacts
        ↓
Future rolling backtest
        ↓
Future profile publisher
        ↓
Local PostgreSQL + Supabase
```

## Modeling limitations

The production future profile captures recurring zone/day/hour patterns but does not currently model:

- weather
- special events
- holidays as a dedicated feature
- traffic conditions
- economic shocks
- unexpected service disruptions

The forecast should therefore be interpreted as expected demand based on recurring historical temporal patterns, not as a real-time event-aware forecast.

For upstream construction see [Data pipeline](data_pipeline.md), and for production configuration see [Deployment](deployment.md).
