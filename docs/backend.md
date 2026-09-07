# Backend

The backend turns raw NYC Yellow Taxi records into analytical data, model outputs and API responses. It is responsible for data processing, persistence, modelling and serving; scheduling belongs to Airflow and presentation belongs to Streamlit.

## Data Processing

Monthly TLC Parquet files are validated and processed with PySpark. The processing layer cleans the trip records, derives time-based fields and produces aggregated datasets used by analytics and machine learning.

The database layer persists analytical tables in PostgreSQL. Local PostgreSQL supports development, while the production-facing copy is stored in Supabase PostgreSQL. Database access is isolated in repository modules rather than embedded in the API or frontend.

## Historical Model Evaluation

Historical demand evaluation uses features that are available when predicting the next observed hour, including calendar features, lagged demand and rolling demand statistics. A persistence baseline and Random Forest are evaluated on a time-based holdout rather than a random split.

The resulting metrics, feature importance and historical predictions are published to PostgreSQL so the frontend does not need to load training artifacts directly.

## Future Forecasting

True future prediction cannot depend on unknown future demand. The future pipeline therefore uses only forecast-safe information:

- calendar features such as hour, weekday, month and cyclical encodings;
- historical demand profiles derived only from previously observed data.

Candidate models include a zone-weekday-hour profile baseline, Linear Regression, Random Forest and Gradient-Boosted Trees. They are compared with rolling temporal backtests. The production model is selected automatically by lowest average MAE, with RMSE as the tie-breaker.

The selected model produces a month-aware demand profile by zone, month, weekday and hour. Only the production predictions are published for serving; evaluation metrics retain the comparison between candidates.

## FastAPI

FastAPI is the service boundary between the stored analytical results and Streamlit. It exposes health, analytics, historical-model and future-prediction functionality without retraining models during a request.

For a future request, the API converts the requested timestamp to the same calendar representation used during training and reads the corresponding stored prediction. Fallback profiles are used when an exact combination is unavailable.

This keeps inference lightweight: expensive PySpark processing and model training happen before serving, not when a user interacts with the application.

## Testing

The pytest suite focuses on logic where regressions would materially affect the application:

- forecast-safe calendar features;
- completeness of the future scoring grid;
- exclusion of unavailable future-demand features;
- automatic production-model selection;
- FastAPI health response.

Spark tests use small synthetic DataFrames rather than the full dataset, keeping tests reproducible and independent of live TLC or Supabase data.
