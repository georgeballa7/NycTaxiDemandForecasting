from datetime import datetime
from pathlib import Path

from pyspark.sql import functions as F

from backend.src.ingestion.spark_session import create_spark_session
from backend.src.ingestion.load_trip_data import load_trip_data
from backend.src.processing.clean_trip_data import clean_trip_data


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


def build_business_trips(
    year: int | None = None,
    month: int | None = None,
):
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[3]

    raw_data_path = (
        project_root
        / "data"
        / "raw"
    )

    output_path = (
        project_root
        / "data"
        / "processed"
        / "business_trips"
    )

    if (year is None) != (month is None):
        raise ValueError(
            "year and month must either both be provided or both be omitted."
        )

    # --------------------------------------------------
    # 1. Load raw trip data
    # --------------------------------------------------

    trips = load_trip_data(
        spark=spark,
        raw_data_path=raw_data_path,
        year=year,
        month=month,
    )

    # --------------------------------------------------
    # 2. Apply existing general cleaning
    # --------------------------------------------------

    if year is not None and month is not None:
        start_date, end_date = _month_bounds(year, month)
    else:
        # Preserve the established Jan-Jun 2025 full-refresh behaviour.
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 7, 1)

    cleaned_trips = clean_trip_data(
        trips,
        start_date=start_date,
        end_date=end_date,
    )

    # --------------------------------------------------
    # 3. Standard business-fare dataset
    # --------------------------------------------------

    business_trips = (
        cleaned_trips
        .filter(
            F.col("payment_type").isin(
                1,
                2,
                3,
                4,
                5,
            )
        )
        .filter(
            F.col("fare_amount") >= 0
        )
        .filter(
            F.col("total_amount") >= 0
        )
    )

    # --------------------------------------------------
    # 4. Business validation features
    # --------------------------------------------------

    business_trips = (
        business_trips
        .withColumn(
            "duration_minutes",
            (
                F.unix_timestamp(
                    "tpep_dropoff_datetime"
                )
                - F.unix_timestamp(
                    "tpep_pickup_datetime"
                )
            ) / 60,
        )
        .withColumn(
            "fare_per_mile",
            F.when(
                F.col("trip_distance") > 0,
                F.col("fare_amount")
                / F.col("trip_distance"),
            ),
        )
        .withColumn(
            "speed_mph",
            F.when(
                F.col("duration_minutes") > 0,
                F.col("trip_distance")
                / (
                    F.col("duration_minutes")
                    / 60
                ),
            ),
        )
    )

    # --------------------------------------------------
    # 5. Remove clearly implausible outliers
    # --------------------------------------------------

    business_trips = (
        business_trips
        .filter(
            F.col("speed_mph").isNull()
            | (F.col("speed_mph") <= 100)
        )
        .filter(
            F.col("fare_per_mile").isNull()
            | (F.col("fare_per_mile") <= 100)
        )
    )

    # --------------------------------------------------
    # 6. Add useful analytical time columns
    # --------------------------------------------------

    business_trips = (
        business_trips
        .withColumn(
            "pickup_date",
            F.to_date(
                "tpep_pickup_datetime"
            ),
        )
        .withColumn(
            "pickup_month",
            F.month(
                "tpep_pickup_datetime"
            ),
        )
        .withColumn(
            "pickup_hour",
            F.hour(
                "tpep_pickup_datetime"
            ),
        )
        .withColumn(
            "spark_day_of_week",
            F.dayofweek(
                "tpep_pickup_datetime"
            ),
        )
        .withColumn(
            "weekday_number",
            F.when(
                F.col("spark_day_of_week") == 1,
                7,
            ).otherwise(
                F.col("spark_day_of_week") - 1
            ),
        )
        .drop(
            "spark_day_of_week"
        )
    )

    # --------------------------------------------------
    # 7. Persist business trip dataset
    # --------------------------------------------------

    (
        business_trips
        .write
        .mode("overwrite")
        .partitionBy("pickup_month")
        .parquet(
            str(output_path)
        )
    )

    final_count = business_trips.count()

    print(
        f"Business trips saved successfully: "
        f"{final_count:,}"
    )

    print(
        f"Output path: {output_path}"
    )

    spark.stop()


if __name__ == "__main__":
    build_business_trips()
