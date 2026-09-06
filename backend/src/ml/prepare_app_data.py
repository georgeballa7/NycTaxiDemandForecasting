from pathlib import Path

from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ingestion.load_zone_lookup import load_zone_lookup


def prepare_app_data():
    """Refresh the lightweight taxi-zone artifact used by offline app/EDA tooling."""
    spark = create_spark_session("NYC Taxi Demand - App Data")

    try:
        project_root = Path(__file__).resolve().parents[3]
        raw_path = project_root / "data" / "raw"
        app_path = project_root / "data" / "app"

        zones = load_zone_lookup(
            spark=spark,
            raw_data_path=raw_path,
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

        app_path.mkdir(parents=True, exist_ok=True)
        app_zones.toPandas().to_parquet(
            app_path / "zones.parquet",
            index=False,
        )

        print("Taxi-zone app artifact prepared successfully.")
    finally:
        spark.stop()


if __name__ == "__main__":
    prepare_app_data()
