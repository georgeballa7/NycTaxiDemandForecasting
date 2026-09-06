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

This means the project no longer hard-codes `zone_dow_hour_mean` as the production model. If the simple baseline remains best, it stays in production. If Linear Regression, Random Forest or GBT beats it on the temporal backtest, that model is published instead.

## Production scoring

After model selection, the publisher builds a true-future scoring grid across:

```text
LocationID × month × day_of_week × hour
```

Historical aggregate features are calculated from all observations available through the current training cutoff. If an ML candidate wins, it is fitted on the available leakage-safe training data and scores this grid. If the profile baseline wins, its historical zone/day/hour mean is used directly.

Predictions are clipped at zero because taxi-trip demand cannot be negative.

## Future prediction serving

The selected forecast snapshot is published transactionally to local PostgreSQL and, when configured, Supabase. FastAPI exposes `GET /future-model-metrics` and `POST /predict`.

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

The response's `forecast_method` reports the selected production model for an exact profile match. A requested datetime at or before `trained_through` returns HTTP 400.

## Serving storage

Historical serving tables:

- `taxi_analytics.historical_model_metric`
- `taxi_analytics.historical_feature_importance`
- `taxi_analytics.historical_model_prediction`

Future serving tables:

- `taxi_analytics.future_demand_profile`
- `taxi_analytics.future_model_metric`
- `taxi_analytics.future_forecast_metadata`

`future_demand_profile` is month-aware. Existing installations are migrated automatically by the repository before the next snapshot replacement.

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

For upstream construction see [Data pipeline](data_pipeline.md), and for production configuration see [Deployment](deployment.md).
