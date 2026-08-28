# Demand forecasting

## Forecasting task

The model estimates the number of cleaned Yellow Taxi pickups in a taxi zone
during an hour. The supervised target is `demand` at the
`LocationID × pickup_hour` grain.

The implementation is a batch evaluation workflow. The deployed API serves
precomputed June 2025 results rather than performing online Spark inference.

## Modeling dataset

The hourly panel covers all 265 zones across the January–June 2025 project
period. Missing observed pickups are represented as zero demand.

Rows are retained for modeling only when `history_count_168h == 168`, ensuring
a complete seven-day trailing history.

## Features

The Spark model uses 13 predictors:

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

Rolling windows exclude the current target observation.

## Chronological validation

The training workflow uses:

- **training:** observations before `2025-06-01 00:00:00`;
- **test:** observations from `2025-06-01 00:00:00` through the end of June.

Validated row counts:

- training rows: **915,840**
- test rows: **190,800**

## Baseline

The baseline uses `lag_24h`.

Validated metrics:

- MAE: **7.1601**
- RMSE: **23.4332**

## Random Forest

The Spark ML `RandomForestRegressor` uses:

- 100 trees
- maximum depth 10
- random seed 42

Validated metrics:

- MAE: **5.0092**
- RMSE: **16.7101**

## Feature importance

| Feature | Importance |
|---|---:|
| `lag_168h` | 0.405756 |
| `lag_1h` | 0.258064 |
| `lag_24h` | 0.213218 |
| `rolling_mean_24h` | 0.054306 |
| `rolling_mean_168h` | 0.038072 |

Feature importance describes model reliance, not causality.

## Training outputs

`backend/src/ml/train_model.py` writes:

- `data/processed/predictions/`
- `data/processed/models/random_forest/`
- `data/processed/feature_importance.csv`
- `data/processed/model_metrics.csv`

## App-artifact publication

`backend/src/ml/prepare_app_data.py` publishes:

- `data/app/predictions.parquet`
- `data/app/zones.parquet`
- `data/app/feature_importance.csv`
- `data/app/model_metrics.csv`

The metrics and feature-importance CSV files are copied from the processed
directory as part of the current checked-in workflow.

## ML orchestration

`backend/workflows/ml_pipeline.py` runs:

```text
train_model()
prepare_app_data()
```

The top-level `backend/workflows/run_pipeline.py` runs the data pipeline first,
then the ML pipeline.

## Prediction serving

FastAPI loads the published predictions, metrics, and feature importance from
`data/app/`.

The Forecast page therefore presents historical held-out prediction results,
not live future inference.

## Current modeling scope

- January–June 2025 source period
- June 2025 chronological holdout
- batch rather than online inference
- no weather, event, holiday, traffic, or economic variables
- no hyperparameter search
- no rolling-origin backtesting
- persisted Spark model is not required by the runtime API

For upstream feature construction see [Data pipeline](data_pipeline.md).
