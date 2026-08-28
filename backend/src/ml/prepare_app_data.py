from pathlib import Path
from shutil import copy2

from pyspark.sql import functions as F

from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ingestion.load_zone_lookup import load_zone_lookup
from backend.src.persistence.load_parquet import load_parquet
from backend.src.persistence.save_parquet import save_parquet


def prepare_app_data():
    spark = create_spark_session("NYC Taxi Demand - App Data")

    project_root = Path(__file__).resolve().parents[2]
    raw_path = project_root / "data" / "raw"
    processed_path = project_root / "data" / "processed"
    app_path = project_root / "data" / "app"

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
            zones.select(
                "LocationID",
                "Borough",
                "Zone",
                "service_zone",
            ),
            on="LocationID",
            how="left",
        )
        .select(
            "LocationID",
            "Borough",
            "Zone",
            "service_zone",
            "pickup_hour",
            F.col("demand").alias("actual_demand"),
            F.round("prediction", 2).alias("predicted_demand"),
        )
    )


    app_zones = (
    zones
    .select(
        "LocationID",
        "Borough",
        "Zone",
        "service_zone",
    )
    .orderBy("Borough", "Zone")
    )

    print("App prediction data prepared successfully.")

    app_path = project_root / "data" / "app"

    app_path.mkdir(parents=True, exist_ok=True)


    predictions_pd = app_predictions.toPandas()
    zones_pd = app_zones.toPandas()

    predictions_pd.to_parquet(
        app_path / "predictions.parquet",
        index=False,
    )

    zones_pd.to_parquet(
        app_path / "zones.parquet",
        index=False,
    )


    copy2(
        processed_path / "feature_importance.csv",
        app_path / "feature_importance.csv",
    )

    copy2(
        processed_path / "model_metrics.csv",
        app_path / "model_metrics.csv",
    )

    spark.stop()


if __name__ == "__main__":
    prepare_app_data()