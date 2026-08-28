from pathlib import Path

from pyspark.sql import functions as F

from backend.src.ingestion.spark_session import create_spark_session


def prepare_eda_data():
    """
    Prepare the daily zone-hour demand dataset used to populate PostgreSQL.

    NYC-wide and zone-specific EDA aggregates are no longer persisted here.
    They are calculated dynamically from PostgreSQL by the API repository layer.
    """
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[2]

    features_path = (
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

    output_path = (
        project_root
        / "data"
        / "app"
        / "eda"
    )

    output_path.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Load persisted datasets
    # --------------------------------------------------

    complete_demand = (
        spark.read.parquet(str(features_path))
        .select(
            "LocationID",
            "pickup_hour",
            "demand",
        )
    )

    zones = spark.read.parquet(
        str(zones_path)
    )

    # --------------------------------------------------
    # Enrich demand with taxi-zone information
    # --------------------------------------------------

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

    # --------------------------------------------------
    # Prepare daily zone-hour demand for PostgreSQL
    # --------------------------------------------------

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
            F.when(
                F.col("weekday_number") == 1,
                "Monday",
            )
            .when(
                F.col("weekday_number") == 2,
                "Tuesday",
            )
            .when(
                F.col("weekday_number") == 3,
                "Wednesday",
            )
            .when(
                F.col("weekday_number") == 4,
                "Thursday",
            )
            .when(
                F.col("weekday_number") == 5,
                "Friday",
            )
            .when(
                F.col("weekday_number") == 6,
                "Saturday",
            )
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

    # The dataset is small enough to persist as one app-ready Parquet file.
    zone_hour_daily_pd = zone_hour_daily.toPandas()

    zone_hour_daily_pd.to_parquet(
        output_path / "zone_hour_daily.parquet",
        index=False,
    )

    print(
        "PostgreSQL demand source data prepared successfully."
    )
    print(
        f"Rows: {len(zone_hour_daily_pd):,}"
    )

    spark.stop()


if __name__ == "__main__":
    prepare_eda_data()
