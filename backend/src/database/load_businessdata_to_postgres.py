from pyspark.sql import functions as F
from sqlalchemy import text

from backend.src.config.settings import (
    DATABASE_SCHEMA,
    PROCESSED_DATA_DIR,
)
from backend.src.database.connection import engine
from backend.src.ingestion.spark_session import create_spark_session


# --------------------------------------------------
# Paths
# --------------------------------------------------

BUSINESS_TRIPS_PATH = PROCESSED_DATA_DIR / "business_trips"


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

def load_dim_payment():
    payment_rows = [
        {"payment_type": 1, "payment_method": "Credit card"},
        {"payment_type": 2, "payment_method": "Cash"},
        {"payment_type": 3, "payment_method": "No charge"},
        {"payment_type": 4, "payment_method": "Dispute"},
        {"payment_type": 5, "payment_method": "Unknown"},
        {"payment_type": 6, "payment_method": "Voided trip"},
    ]

    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {DATABASE_SCHEMA}.dim_payment
                    (payment_type, payment_method)
                VALUES
                    (:payment_type, :payment_method);
                """
            ),
            payment_rows,
        )

    print("Payment dimension loaded successfully.")


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

    # Batch insert
    fact_trips_pd.to_sql(
        name="fact_trips",
        con=engine,
        schema=DATABASE_SCHEMA,
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
        f"""
        SELECT
            COUNT(*) AS fact_rows,
            SUM(trip_count) AS total_trips,
            MIN(pickup_date) AS min_date,
            MAX(pickup_date) AS max_date,
            MIN(hour) AS min_hour,
            MAX(hour) AS max_hour
        FROM {DATABASE_SCHEMA}.fact_trips;
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

    load_dim_payment()

    load_fact_trips(
        fact_trips
    )

    validate_load()

    spark.stop()


if __name__ == "__main__":
    main()