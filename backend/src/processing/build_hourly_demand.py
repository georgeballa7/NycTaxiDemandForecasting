from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def build_hourly_demand(trips: DataFrame) -> DataFrame:

    return (
        trips
        .withColumn(
        "pickup_hour",
        F.date_trunc(
            "hour",
            F.col("tpep_pickup_datetime")
        ).cast("timestamp_ntz")
    )
        .groupBy(
            F.col("PULocationID").alias("LocationID"),
            "pickup_hour"
        )
        .agg(
            F.count("*").alias("demand")
        )
    )