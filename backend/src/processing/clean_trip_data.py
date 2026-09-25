from datetime import datetime

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def clean_trip_data(
    trips: DataFrame,
    start_date: datetime,
    end_date: datetime,
) -> DataFrame:
    """Filter raw trips to the requested period and remove correction pairs.

    Parameters
    ----------
    trips : DataFrame
        Raw TLC trip-level Spark DataFrame.
    start_date : datetime
        Inclusive lower bound for pickup time.
    end_date : datetime
        Exclusive upper bound for pickup time.

    Returns
    -------
    DataFrame
        Chronologically valid trips after correction groups are removed.

    Notes
    -----
    Trips with drop-off before pickup are removed. Duplicate groups sharing
    the project trip key are treated as corrections when they contain both
    negative and non-negative fares; those groups are removed completely.
    """

    cleaned = trips.filter(
        (F.col("tpep_pickup_datetime") >= F.lit(start_date)) &
        (F.col("tpep_pickup_datetime") < F.lit(end_date))
    )

    cleaned = cleaned.filter(
        F.col("tpep_dropoff_datetime") >=
        F.col("tpep_pickup_datetime")
    )

    trip_keys = [
        "VendorID",
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "PULocationID",
        "DOLocationID",
        "trip_distance",
    ]

    correction_groups = (
        cleaned
        .groupBy(*trip_keys)
        .agg(
            F.count("*").alias("records"),
            F.min("fare_amount").alias("min_fare"),
            F.max("fare_amount").alias("max_fare"),
        )
        .filter(
            (F.col("records") > 1) &
            (F.col("min_fare") < 0) &
            (F.col("max_fare") >= 0)
        )
    )

    correction_keys = correction_groups.select(*trip_keys)

    cleaned = cleaned.join(
        correction_keys,
        on=trip_keys,
        how="left_anti",
    )

    return cleaned