from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyspark.sql import functions as F

from backend.src.database.connection import engine, supabase_engine
from backend.src.database.future_forecast_repo import replace_future_forecast_data
from backend.src.features.build_future_features import (
    FUTURE_FEATURE_COLUMNS,
    add_historical_profile_features,
    build_future_scoring_grid,
)
from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ml.train_future_model import _candidate_pipelines


def publish_future_forecast_data():
    spark = create_spark_session("NYC Taxi Future Forecast Publisher")
    project_root = Path(__file__).resolve().parents[3]
    hourly_path = project_root / "data" / "processed" / "hourly_demand"
    summary_path = project_root / "data" / "processed" / "future_model_summary.csv"

    try:
        hourly_demand = spark.read.parquet(str(hourly_path)).cache()
        latest_timestamp = hourly_demand.agg(
            F.max("pickup_hour").alias("trained_through")
        ).first()["trained_through"]
        if latest_timestamp is None:
            raise RuntimeError("No hourly demand data available.")
        if not summary_path.exists():
            raise FileNotFoundError(
                f"Future-model summary not found: {summary_path}"
            )

        metrics = pd.read_csv(summary_path)
        required_metric_columns = {"model", "mae", "rmse", "backtest_months"}
        if not required_metric_columns.issubset(metrics.columns):
            raise RuntimeError("Future-model summary has an invalid schema.")
        if metrics.empty:
            raise RuntimeError("Future-model summary is empty.")

        metrics = metrics.sort_values(["mae", "rmse", "model"]).reset_index(drop=True)
        production_model = str(metrics.iloc[0]["model"])

        scoring_grid = build_future_scoring_grid(hourly_demand).dropna(
            subset=FUTURE_FEATURE_COLUMNS
        )

        if production_model == "zone_dow_hour_mean":
            profiles = scoring_grid.select(
                "LocationID",
                "month",
                "day_of_week",
                "hour",
                F.greatest(F.col("zone_dow_hour_mean"), F.lit(0.0)).alias(
                    "predicted_demand"
                ),
            )
        else:
            pipelines = _candidate_pipelines()
            if production_model not in pipelines:
                raise RuntimeError(
                    f"Unsupported selected production model: {production_model}"
                )

            training_data = add_historical_profile_features(hourly_demand).dropna(
                subset=FUTURE_FEATURE_COLUMNS
            )
            fitted_model = pipelines[production_model].fit(training_data)
            profiles = (
                fitted_model.transform(scoring_grid)
                .select(
                    "LocationID",
                    "month",
                    "day_of_week",
                    "hour",
                    F.greatest(F.col("prediction"), F.lit(0.0)).alias(
                        "predicted_demand"
                    ),
                )
            )

        profiles_pandas = profiles.orderBy(
            "LocationID", "month", "day_of_week", "hour"
        ).toPandas()

        metadata = {
            "production_model": production_model,
            "trained_through": latest_timestamp.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile_dimensions": [
                "LocationID",
                "month",
                "day_of_week",
                "hour",
            ],
            "profile_rows": len(profiles_pandas),
        }

        # Spark is no longer needed after materialisation. Stop it before the
        # potentially slow SQL uploads so the executor does not emit heartbeat
        # warnings while PostgreSQL/Supabase publishing is in progress.
        hourly_demand.unpersist()
        spark.stop()
        spark = None

        print("Publishing future forecast snapshot to local PostgreSQL...")
        replace_future_forecast_data(profiles_pandas, metrics, metadata, engine)

        if supabase_engine is not None:
            print("Publishing future forecast snapshot to Supabase PostgreSQL...")
            replace_future_forecast_data(
                profiles_pandas, metrics, metadata, supabase_engine
            )
        else:
            print(
                "SUPABASE_DATABASE_URL is not configured; "
                "future forecast Supabase publish skipped."
            )

        print("Future forecast database snapshot published.")
        print(f"Production model: {production_model}")
        print(f"Trained through: {latest_timestamp}")
        print(f"Profile rows: {len(profiles_pandas):,}")
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    publish_future_forecast_data()
