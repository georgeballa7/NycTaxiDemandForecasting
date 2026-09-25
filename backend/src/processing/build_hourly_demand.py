from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def build_hourly_demand(trips: DataFrame) -> DataFrame:
    """Aggregate cleaned taxi trips into hourly pickup demand by zone.

    Parameters
    ----------
    trips : DataFrame
        Cleaned trip-level data with pickup timestamps and PULocationID.

    Returns
    -------
    DataFrame
        DataFrame with LocationID, hour-truncated pickup_hour, and the pickup
        count for that zone-hour as demand.
    """

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