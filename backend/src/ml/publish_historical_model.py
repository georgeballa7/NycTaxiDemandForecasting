from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyspark.sql import functions as F

from backend.src.database.connection import engine
from backend.src.database.historical_model_repo import (
    replace_historical_model_data_bulk,
)
from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ingestion.load_zone_lookup import load_zone_lookup
from backend.src.persistence.load_parquet import load_parquet


def publish_historical_model_data():
    """Publish the historical-model serving snapshot to local PostgreSQL.

    Returns
    -------
    None
        Metrics, feature importance and historical predictions are replaced
        in the local serving database.

    Raises
    ------
    RuntimeError
        If no historical predictions are available.
    FileNotFoundError
        If model metrics or feature-importance artifacts are missing.

    Notes
    -----
    Predictions are joined to valid zones and materialized to Pandas together
    with CSV metrics and feature importance. Spark is stopped before database
    I/O. The local snapshot is replaced using PostgreSQL COPY.
    """
    spark = create_spark_session("NYC Taxi Historical Model Publisher")

    try:
        project_root = Path(__file__).resolve().parents[3]
        raw_path = project_root / "data" / "raw"
        processed_path = project_root / "data" / "processed"

        predictions = load_parquet(
            spark,
            processed_path / "predictions",
        )
        zones = load_zone_lookup(
            spark=spark,
            raw_data_path=raw_path,
        )

        app_predictions = (
            predictions
            .join(
                zones.select("LocationID"),
                on="LocationID",
                how="inner",
            )
            .select(
                "LocationID",
                "pickup_hour",
                F.col("demand").cast("double").alias("actual_demand"),
                F.col("prediction").cast("double").alias("predicted_demand"),
            )
            .orderBy("LocationID", "pickup_hour")
        )

        trained_through = (
            app_predictions
            .agg(F.max("pickup_hour").alias("trained_through"))
            .first()["trained_through"]
        )
        if trained_through is None:
            raise RuntimeError("No historical predictions available to publish.")

        metrics_path = processed_path / "model_metrics.csv"
        importance_path = processed_path / "feature_importance.csv"
        if not metrics_path.exists():
            raise FileNotFoundError(f"Historical model metrics not found: {metrics_path}")
        if not importance_path.exists():
            raise FileNotFoundError(
                f"Historical feature importance not found: {importance_path}"
            )

        metrics = pd.read_csv(metrics_path)
        feature_importance = pd.read_csv(importance_path)
        predictions_pd = app_predictions.toPandas()
        generated_at = datetime.now(timezone.utc)

        # Spark wird nach der Materialisierung nicht mehr benötigt. Die Session
        # wird vor den potenziell langsamen SQL-Uploads beendet, damit während
        # des Publishings keine unnötigen Spark-Ressourcen aktiv bleiben.
        spark.stop()
        spark = None

        print("Publishing historical model snapshot to local PostgreSQL...")
        replace_historical_model_data_bulk(
            metrics,
            feature_importance,
            predictions_pd,
            trained_through,
            generated_at,
            engine,
        )

        print("Historical model database snapshot published.")
        print(f"Trained through: {trained_through}")
        print(f"Prediction rows: {len(predictions_pd):,}")
    finally:
        if spark is not None:
            spark.stop()


if __name__ == "__main__":
    publish_historical_model_data()
