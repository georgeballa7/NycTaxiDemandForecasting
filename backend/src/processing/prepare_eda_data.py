from pathlib import Path

from pyspark.sql import functions as F

from backend.src.ingestion.spark_session import create_spark_session


def _monthly_path(
    root: Path,
    year: int,
    month: int,
) -> Path:
    if not 1 <= month <= 12:
        raise ValueError(
            f"month must be between 1 and 12. Received: {month}"
        )

    return root / f"year={year}" / f"month={month:02d}"


def prepare_eda_data(
    year: int | None = None,
    month: int | None = None,
):
    """
    Prepare the daily zone-hour demand dataset used to populate PostgreSQL.

    A monthly run reads and writes only the requested dataset month. Calling
    the function without year/month preserves the existing full-refresh path.
    """
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[3]

    features_root = (
        project_root
        / "data"
        / "processed"
        / "features"
    )

    zones_path = (
        project_root
        / "data"
        / "app"
        / "zones.parquet"
    )

    output_root = (
        project_root
        / "data"
        / "app"
        / "eda"
    )

    if (year is None) != (month is None):
        raise ValueError(
            "year and month must either both be provided or both be omitted."
        )

    if year is not None and month is not None:
        features_path = _monthly_path(
            features_root,
            year,
            month,
        )
        output_path = _monthly_path(
            output_root,
            year,
            month,
        )
    else:
        features_path = features_root
        output_path = output_root

    output_path.mkdir(parents=True, exist_ok=True)

    complete_demand = (
        spark.read.parquet(str(features_path))
        .select(
            "LocationID",
            "pickup_hour",
            "demand",
        )
    )

    zones = spark.read.parquet(str(zones_path))

    zone_demand = (
        complete_demand
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
    )

    zone_hour_daily = (
        zone_demand
        .withColumn(
            "date",
            F.to_date("pickup_hour"),
        )
        .withColumn(
            "hour",
            F.hour("pickup_hour"),
        )
        .withColumn(
            "spark_day_of_week",
            F.dayofweek("pickup_hour"),
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
        .withColumn(
            "weekday",
            F.when(F.col("weekday_number") == 1, "Monday")
            .when(F.col("weekday_number") == 2, "Tuesday")
            .when(F.col("weekday_number") == 3, "Wednesday")
            .when(F.col("weekday_number") == 4, "Thursday")
            .when(F.col("weekday_number") == 5, "Friday")
            .when(F.col("weekday_number") == 6, "Saturday")
            .otherwise("Sunday"),
        )
        .select(
            "LocationID",
            "Borough",
            "Zone",
            "service_zone",
            "date",
            "hour",
            "weekday_number",
            "weekday",
            "demand",
        )
        .orderBy(
            "LocationID",
            "date",
            "hour",
        )
    )

    zone_hour_daily_pd = zone_hour_daily.toPandas()

    zone_hour_daily_pd.to_parquet(
        output_path / "zone_hour_daily.parquet",
        index=False,
    )

    print(
        "PostgreSQL demand source data prepared successfully."
    )
    print(f"Rows: {len(zone_hour_daily_pd):,}")
    print(f"Output path: {output_path}")

    spark.stop()


if __name__ == "__main__":
    prepare_eda_data()
