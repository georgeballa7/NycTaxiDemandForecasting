from datetime import datetime, timezone
from pathlib import Path
import json

import pandas as pd
from pyspark.sql import functions as F

from backend.src.database.connection import engine, supabase_engine
from backend.src.database.future_forecast_repo import (
    replace_future_forecast_data,
)
from backend.src.ingestion.spark_session import (
    create_spark_session,
)


def publish_future_forecast_data():
    spark = create_spark_session(
        "NYC Taxi Future Forecast Publisher"
    )

    project_root = Path(__file__).resolve().parents[3]

    hourly_path = (
        project_root
        / "data"
        / "processed"
        / "hourly_demand"
    )

    backtest_path = (
        project_root
        / "data"
        / "processed"
        / "future_model_backtest.csv"
    )

    app_dir = (
        project_root
        / "data"
        / "app"
        / "future_forecast"
    )
    app_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    hourly_demand = spark.read.parquet(
        str(hourly_path)
    )

    latest_timestamp = (
        hourly_demand
        .agg(
            F.max("pickup_hour").alias(
                "trained_through"
            )
        )
        .first()["trained_through"]
    )

    if latest_timestamp is None:
        raise RuntimeError(
            "No hourly demand data available."
        )

    profiles = (
        hourly_demand
        .withColumn(
            "day_of_week",
            F.dayofweek("pickup_hour"),
        )
        .withColumn(
            "hour",
            F.hour("pickup_hour"),
        )
        .groupBy(
            "LocationID",
            "day_of_week",
            "hour",
        )
        .agg(
            F.avg("demand").alias(
                "predicted_demand"
            )
        )
        .orderBy(
            "LocationID",
            "day_of_week",
            "hour",
        )
    )

    profiles_pandas = profiles.toPandas()

    profiles_path = (
        app_dir
        / "future_demand_profiles.parquet"
    )

    profiles_pandas.to_parquet(
        profiles_path,
        index=False,
    )

    if not backtest_path.exists():
        raise FileNotFoundError(
            "Future-model backtest results not found: "
            f"{backtest_path}"
        )

    backtest = pd.read_csv(backtest_path)

    metrics = pd.DataFrame(
        [
            {
                "model": "zone_dow_hour_mean",
                "mae": backtest[
                    "baseline_mae"
                ].mean(),
                "rmse": backtest[
                    "baseline_rmse"
                ].mean(),
                "backtest_months": len(
                    backtest
                ),
            },
            {
                "model": "random_forest",
                "mae": backtest[
                    "rf_mae"
                ].mean(),
                "rmse": backtest[
                    "rf_rmse"
                ].mean(),
                "backtest_months": len(
                    backtest
                ),
            },
        ]
    )

    metrics.to_csv(
        app_dir
        / "future_model_metrics.csv",
        index=False,
    )

    metadata = {
        "production_model": "zone_dow_hour_mean",
        "trained_through": latest_timestamp.isoformat(),
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "profile_dimensions": [
            "LocationID",
            "day_of_week",
            "hour",
        ],
        "profile_rows": len(profiles_pandas),
    }

    with open(
        app_dir / "metadata.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    print("Publishing future forecast snapshot to local PostgreSQL...")
    replace_future_forecast_data(
        profiles_pandas,
        metrics,
        metadata,
        engine,
    )

    if supabase_engine is not None:
        print("Publishing future forecast snapshot to Supabase PostgreSQL...")
        replace_future_forecast_data(
            profiles_pandas,
            metrics,
            metadata,
            supabase_engine,
        )
    else:
        print(
            "SUPABASE_DATABASE_URL is not configured; "
            "future forecast Supabase publish skipped."
        )

    spark.stop()

    print(
        "Future forecast artifacts published."
    )
    print(
        f"Profiles: {profiles_path}"
    )
    print(
        f"Trained through: {latest_timestamp}"
    )
    print(
        f"Profile rows: {len(profiles_pandas):,}"
    )


if __name__ == "__main__":
    publish_future_forecast_data()
