from calendar import monthrange
from datetime import datetime
from pathlib import Path

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


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    if not 1 <= month <= 12:
        raise ValueError(
            f"month must be between 1 and 12. Received: {month}"
        )

    start_date = datetime(year, month, 1)

    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    return start_date, end_date


def build_dataset(
    year: int | None = None,
    month: int | None = None,
):
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[3]
    raw_data_path = project_root / "data" / "raw"
    processed_data_path = project_root / "data" / "processed"

    if (year is None) != (month is None):
        raise ValueError(
            "year and month must either both be provided or both be omitted."
        )

    trips = load_trip_data(
        spark=spark,
        raw_data_path=raw_data_path,
        year=year,
        month=month,
    )

    zones = load_zone_lookup(
        spark=spark,
        raw_data_path=raw_data_path,
    )

    if year is not None and month is not None:
        start_date, end_date = _month_bounds(year, month)
        last_day = monthrange(year, month)[1]
        grid_start = f"{year}-{month:02d}-01 00:00:00"
        grid_end = f"{year}-{month:02d}-{last_day:02d} 23:00:00"
    else:
        # Preserve the established Jan-Jun 2025 full-refresh behaviour.
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 7, 1)
        grid_start = "2025-01-01 00:00:00"
        grid_end = "2025-06-30 23:00:00"

    cleaned_trips = clean_trip_data(
        trips,
        start_date=start_date,
        end_date=end_date,
    )

    hourly_demand = build_hourly_demand(cleaned_trips)

    save_parquet(
        hourly_demand,
        processed_data_path / "hourly_demand",
    )

    complete_demand = complete_zone_hour_grid(
        hourly_demand,
        zones,
        start_date=grid_start,
        end_date=grid_end,
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
