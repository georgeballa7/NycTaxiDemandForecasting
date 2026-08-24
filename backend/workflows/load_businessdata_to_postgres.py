import os

from pyspark.sql import functions as F
from sqlalchemy import text

from backend.src.database.connection import engine
from backend.src.ingestion.spark_session import create_spark_session


# --------------------------------------------------
# Windows / local Spark configuration
# --------------------------------------------------

os.environ.setdefault(
    "SPARK_LOCAL_IP",
    "127.0.0.1",
)


# --------------------------------------------------
# Paths
# --------------------------------------------------

BUSINESS_TRIPS_PATH = (
    "data/processed/business_trips"
)


# --------------------------------------------------
# Build aggregated fact table
# --------------------------------------------------

def build_fact_trips(business_trips):
    fact_trips = (
        business_trips
        .groupBy(
            "PULocationID",
            "pickup_date",
            "pickup_hour",
            "payment_type",
        )
        .agg(
            F.count("*").alias(
                "trip_count"
            ),
            F.sum("fare_amount").alias(
                "fare_amount"
            ),
            F.sum("total_amount").alias(
                "total_amount"
            ),
            F.sum("tip_amount").alias(
                "tip_amount"
            ),
            F.sum("trip_distance").alias(
                "trip_distance"
            ),
            F.sum("tolls_amount").alias(
                "tolls_amount"
            ),
            F.sum(
                "congestion_surcharge"
            ).alias(
                "congestion_surcharge"
            ),
            F.sum("Airport_fee").alias(
                "airport_fee"
            ),
            F.sum(
                "cbd_congestion_fee"
            ).alias(
                "cbd_congestion_fee"
            ),
        )
        .withColumnRenamed(
            "PULocationID",
            "location_id",
        )
        .withColumnRenamed(
            "pickup_hour",
            "hour",
        )
    )

    # Match PostgreSQL data types
    fact_trips = (
        fact_trips
        .withColumn(
            "location_id",
            F.col("location_id")
            .cast("short"),
        )
        .withColumn(
            "hour",
            F.col("hour")
            .cast("short"),
        )
        .withColumn(
            "payment_type",
            F.col("payment_type")
            .cast("short"),
        )
        .withColumn(
            "trip_count",
            F.col("trip_count")
            .cast("int"),
        )
    )

    numeric_columns = [
        "fare_amount",
        "total_amount",
        "tip_amount",
        "trip_distance",
        "tolls_amount",
        "congestion_surcharge",
        "airport_fee",
        "cbd_congestion_fee",
    ]

    for column in numeric_columns:
        fact_trips = (
            fact_trips
            .withColumn(
                column,
                F.round(
                    F.col(column),
                    2,
                ).cast("decimal(14,2)"),
            )
        )

    return fact_trips.select(
        "location_id",
        "pickup_date",
        "hour",
        "payment_type",
        "trip_count",
        "fare_amount",
        "total_amount",
        "tip_amount",
        "trip_distance",
        "tolls_amount",
        "congestion_surcharge",
        "airport_fee",
        "cbd_congestion_fee",
    )


# --------------------------------------------------
# Load into PostgreSQL
# --------------------------------------------------

def load_fact_trips(
    fact_trips,
):
    print(
        "Converting aggregated fact data "
        "to Pandas..."
    )

    fact_trips_pd = (
        fact_trips.toPandas()
    )

    print(
        f"Aggregated rows: "
        f"{len(fact_trips_pd):,}"
    )

    # Clear old fact data before reload
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    taxi_business.fact_trips;
                """
            )
        )

    print(
        "Existing fact_trips data "
        "truncated."
    )

    # Batch insert
    fact_trips_pd.to_sql(
        name="fact_trips",
        con=engine,
        schema="taxi_business",
        if_exists="append",
        index=False,
        chunksize=5000,
        method="multi",
    )

    print(
        "Business fact data loaded "
        "successfully."
    )


# --------------------------------------------------
# Validate PostgreSQL load
# --------------------------------------------------

def validate_load():
    query = text(
        """
        SELECT
            COUNT(*) AS fact_rows,
            SUM(trip_count) AS total_trips,
            MIN(pickup_date) AS min_date,
            MAX(pickup_date) AS max_date,
            MIN(hour) AS min_hour,
            MAX(hour) AS max_hour
        FROM taxi_business.fact_trips;
        """
    )

    with engine.connect() as connection:
        result = (
            connection.execute(query)
            .mappings()
            .one()
        )

    print()
    print("PostgreSQL validation")
    print("---------------------")
    print(
        f"Fact rows:   "
        f"{result['fact_rows']:,}"
    )
    print(
        f"Total trips: "
        f"{result['total_trips']:,}"
    )
    print(
        f"Date range:  "
        f"{result['min_date']} "
        f"to {result['max_date']}"
    )
    print(
        f"Hour range:  "
        f"{result['min_hour']} "
        f"to {result['max_hour']}"
    )


# --------------------------------------------------
# Main workflow
# --------------------------------------------------

def main():
    spark = create_spark_session(
        "LoadBusinessDataToPostgres"
    )

    print(
        "Loading cleaned business trips..."
    )

    business_trips = (
        spark.read.parquet(
            BUSINESS_TRIPS_PATH
        )
    )

    print(
        "Building aggregated fact_trips..."
    )

    fact_trips = build_fact_trips(
        business_trips
    )

    fact_rows = fact_trips.count()

    print(
        f"Fact rows before database load: "
        f"{fact_rows:,}"
    )

    load_fact_trips(
        fact_trips
    )

    validate_load()

    spark.stop()


if __name__ == "__main__":
    main()