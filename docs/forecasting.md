# Demand forecasting

## Forecasting tasks

The project deliberately separates two forecasting problems:

1. **Historical model evaluation** — a Spark Random Forest using observed lag and rolling-demand features.
2. **True future inference** — long-horizon forecasting using only information available before the requested future timestamp.

Both estimate hourly cleaned Yellow Taxi pickup demand at taxi-zone level, but their feature-availability constraints are different.

## Historical Random Forest

The historical model uses time, lag and rolling-demand predictors. This is appropriate for historical/near-term evaluation because recent observed demand exists. The validated May 2026 snapshot achieved MAE 4.63 and RMSE 15.97 versus baseline MAE 6.51 and RMSE 21.84.

Historical predictions, metrics and feature importance are published to PostgreSQL/Supabase after training and served by FastAPI.

## Why the future model is separate

Features such as `lag_1h`, `lag_24h`, `lag_168h` and rolling observed demand cannot be known for an arbitrary date months into the future. The future pipeline therefore excludes them and uses only forecast-safe predictors.

## Forecast-safe feature set

Calendar features known in advance:

- `hour`
- `day_of_week`
- `month`
- `is_weekend`
- cyclical hour, weekday and month sine/cosine encodings

Historical aggregate features:

- `zone_mean_demand`
- `zone_hour_mean`
- `zone_dow_hour_mean`

During rolling backtesting, each aggregate is calculated strictly from months earlier than the test month. This prevents target leakage. `LocationID` is treated as a categorical zone identifier through `StringIndexer` + `OneHotEncoder`, rather than as an ordinal number.

## Rolling model selection

The latest four available calendar months are used as temporal holdouts. Every candidate is evaluated on the same splits with MAE and RMSE:

- `zone_dow_hour_mean` — strong transparent baseline
- `linear_regression`
- `random_forest`
- `gradient_boosted_trees`

MAE is the primary production-selection metric because it is directly interpretable as average hourly demand error; RMSE is the tie-breaker. The winning model is selected automatically after every future-model retraining. The pipeline writes both per-month results and an aggregate model summary.

### Validated May 2026 snapshot

| Model | MAE | RMSE | Holdout months |
|---|---:|---:|---:|
| **`zone_dow_hour_mean`** | **6.4030** | **16.0399** | 4 |
| `linear_regression` | 7.0330 | 16.4268 | 4 |
| `random_forest` | 7.1507 | 18.9252 | 4 |
| `gradient_boosted_trees` | 7.2954 | 19.3715 | 4 |

The selected production model is `zone_dow_hour_mean`. This is an empirical model-selection result rather than a hard-coded serving decision: if Linear Regression, Random Forest or GBT wins after a later retraining, that candidate becomes the production scorer instead.

## Production scoring

After model selection, the publisher builds a true-future scoring grid across:

```text
LocationID × month × day_of_week × hour
```

Historical aggregate features are calculated from all observations available through the current training cutoff. If an ML candidate wins, it is fitted on the available leakage-safe training data and scores this grid. If the profile baseline wins, its historical zone/day/hour mean is used directly.

Predictions are clipped at zero because taxi-trip demand cannot be negative.

The validated May 2026 publication contains **499,248 profile rows** and is trained through **2026-05-31 23:00:00**. The row count, 12-month coverage, model metrics and metadata were verified in both local PostgreSQL and Supabase.

## Future prediction serving

The selected forecast snapshot is published to local PostgreSQL and, when configured, Supabase. FastAPI exposes `GET /future-model-metrics` and `POST /predict`.

`POST /predict` converts the requested datetime to New York local time when needed and looks up:

```text
zone + month + day-of-week + hour
        ↓
zone + month + hour fallback
        ↓
zone + hour fallback
        ↓
zone overall fallback
```

For an exact profile match, `forecast_method` reports the selected production model. For a fallback, it reports the fallback level. A requested datetime at or before `trained_through` returns HTTP 400.

The validated production path has been exercised end-to-end through Spark training, automatic model selection, local/Supabase publication, Render FastAPI and `POST /predict`.

## Streamlit presentation

The Forecast page reads all current future-model metrics from FastAPI, sorts them by the same MAE/RMSE selection rule and displays all four candidates. It does not assume that the current baseline will remain the production winner after later retraining.

## Serving storage

Historical serving tables:

- `taxi_analytics.historical_model_metric`
- `taxi_analytics.historical_feature_importance`
- `taxi_analytics.historical_model_prediction`

Future serving tables:

- `taxi_analytics.future_demand_profile`
- `taxi_analytics.future_model_metric`
- `taxi_analytics.future_forecast_metadata`

`future_demand_profile` is month-aware. Existing installations are migrated automatically by the repository before snapshot replacement.

Both historical and future serving are database-backed. There is no manual Git deployment step for monthly model-serving snapshots after retraining.

## ML orchestration

`backend/workflows/ml_pipeline.py` runs:

```text
Historical Random Forest
        ↓
Historical database publisher
        ↓
Future temporal model comparison
        ↓
Automatic production-model selection
        ↓
Month-aware future profile generation
        ↓
Future database publisher
        ↓
Local PostgreSQL + Supabase
```

## Limitations

The future model intentionally stays practical and reproducible. It does not currently depend on weather, live traffic, special-event feeds or unknown future observations. Those can be evaluated later only if they provide enough value to justify additional data dependencies and operational complexity.

The current month-aware serving profile is intentionally model-independent and therefore relatively large. Supabase publication performance can be optimized later without changing the model-selection or serving contract.

For upstream construction see [Data pipeline](data_pipeline.md), and for production configuration see [Deployment](deployment.md).
