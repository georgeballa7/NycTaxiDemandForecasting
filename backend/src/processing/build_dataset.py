from pathlib import Path
from datetime import datetime

from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ingestion.load_trip_data import load_trip_data
from backend.src.ingestion.load_zone_lookup import load_zone_lookup
from backend.src.processing.clean_trip_data import clean_trip_data
from backend.src.processing.build_hourly_demand import build_hourly_demand
from backend.src.processing.complete_zone_hour_grid import complete_zone_hour_grid
from backend.src.features.build_features import (
    add_time_features,
    add_lag_features,
    add_rolling_features,
)
from backend.src.persistence.save_parquet import save_parquet


def build_dataset():
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[2]
    raw_data_path = project_root / "data" / "raw"
    processed_data_path = project_root / "data" / "processed"

    trips = load_trip_data(
        spark=spark,
        raw_data_path=raw_data_path,
    )

    zones = load_zone_lookup(
        spark=spark,
        raw_data_path=raw_data_path,
    )

    cleaned_trips = clean_trip_data(
        trips,
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 7, 1),
    )

    hourly_demand = build_hourly_demand(cleaned_trips)

    save_parquet(
        hourly_demand,
        processed_data_path / "hourly_demand",
    )

    complete_demand = complete_zone_hour_grid(
        hourly_demand,
        zones,
        start_date="2025-01-01 00:00:00",
        end_date="2025-06-30 23:00:00",
    )

    features = add_time_features(complete_demand)
    features = add_lag_features(features)
    features = add_rolling_features(features)

    save_parquet(
        features,
        processed_data_path / "features",
    )

    return spark


if __name__ == "__main__":
    spark = build_dataset()
    spark.stop()