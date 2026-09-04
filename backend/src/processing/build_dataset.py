from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path

from pyspark.sql import functions as F

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
from backend.src.persistence.save_parquet import (
    save_monthly_parquet,
    save_parquet,
)


HISTORY_HOURS = 168


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


def _monthly_path(
    root: Path,
    year: int,
    month: int,
) -> Path:
    return root / f"year={year}" / f"month={month:02d}"


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


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

    if year is None or month is None:
        # Preserve the established Jan-Jun 2025 full-refresh behaviour.
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 7, 1)

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

    start_date, end_date = _month_bounds(year, month)
    last_day = monthrange(year, month)[1]

    cleaned_trips = clean_trip_data(
        trips,
        start_date=start_date,
        end_date=end_date,
    )

    hourly_demand = build_hourly_demand(cleaned_trips)

    hourly_root = processed_data_path / "hourly_demand"
    features_root = processed_data_path / "features"

    hourly_output = save_monthly_parquet(
        hourly_demand,
        hourly_root,
        year,
        month,
    )

    current_complete = complete_zone_hour_grid(
        hourly_demand,
        zones,
        start_date=f"{year}-{month:02d}-01 00:00:00",
        end_date=f"{year}-{month:02d}-{last_day:02d} 23:00:00",
    )

    previous_year, previous_month = _previous_month(year, month)
    previous_hourly_path = _monthly_path(
        hourly_root,
        previous_year,
        previous_month,
    )

    feature_input = current_complete

    if previous_hourly_path.exists():
        history_start = start_date - timedelta(hours=HISTORY_HOURS)
        history_end = start_date - timedelta(hours=1)

        previous_hourly = spark.read.parquet(
            str(previous_hourly_path)
        )

        previous_complete = complete_zone_hour_grid(
            previous_hourly,
            zones,
            start_date=history_start.strftime("%Y-%m-%d %H:%M:%S"),
            end_date=history_end.strftime("%Y-%m-%d %H:%M:%S"),
        )

        feature_input = previous_complete.unionByName(
            current_complete
        )
    else:
        print(
            "No previous monthly hourly-demand dataset found at "
            f"{previous_hourly_path}. "
            "Current-month features will be created without prior-month "
            "history."
        )

    features = add_time_features(feature_input)
    features = add_lag_features(features)
    features = add_rolling_features(features)

    monthly_features = features.filter(
        (F.col("pickup_hour") >= F.lit(start_date))
        & (F.col("pickup_hour") < F.lit(end_date))
    )

    features_output = save_monthly_parquet(
        monthly_features,
        features_root,
        year,
        month,
    )

    print(f"Hourly demand saved: {hourly_output}")
    print(f"Monthly features saved: {features_output}")

    return spark


if __name__ == "__main__":
    spark = build_dataset()
    spark.stop()
