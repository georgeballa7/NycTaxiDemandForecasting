import math


from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


def add_time_features(df: DataFrame) -> DataFrame:
    """Add calendar and cyclical time features for demand modelling.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame containing pickup_hour.

    Returns
    -------
    DataFrame
        Input rows extended with hour, day_of_week, day_of_month, is_weekend,
        hour_sin, hour_cos, dow_sin and dow_cos.

    Notes
    -----
    Hour and weekday are encoded with sine/cosine pairs so their cyclical
    proximity is represented numerically; Spark day-of-week uses Sunday=1.
    """
    return (
        df
        .withColumn("hour", F.hour("pickup_hour"))
        .withColumn("day_of_week", F.dayofweek("pickup_hour"))
        .withColumn("day_of_month", F.dayofmonth("pickup_hour"))
        .withColumn(
            "is_weekend",
            F.when(F.col("day_of_week").isin(1, 7), 1).otherwise(0)
        )
        .withColumn(
            "hour_sin",
            F.sin(2 * math.pi * F.col("hour") / 24)
        )
        .withColumn(
            "hour_cos",
            F.cos(2 * math.pi * F.col("hour") / 24)
        )
        .withColumn(
            "dow_sin",
            F.sin(2 * math.pi * F.col("day_of_week") / 7)
        )
        .withColumn(
            "dow_cos",
            F.cos(2 * math.pi * F.col("day_of_week") / 7)
        )
    )


def add_lag_features(df: DataFrame) -> DataFrame:
    """Add zone-specific historical demand lag features.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame containing LocationID, pickup_hour and demand.

    Returns
    -------
    DataFrame
        Input rows extended with lag_1h, lag_24h and lag_168h. Lag values are
        null when insufficient history exists.

    Notes
    -----
    Rows are partitioned by LocationID and ordered chronologically, so each
    feature uses only earlier observations from the same taxi zone.
    """

    zone_window = (
        Window
        .partitionBy("LocationID")
        .orderBy("pickup_hour")
    )

    return (
        df
        .withColumn("lag_1h", F.lag("demand", 1).over(zone_window))
        .withColumn("lag_24h", F.lag("demand", 24).over(zone_window))
        .withColumn("lag_168h", F.lag("demand", 168).over(zone_window))
    )


def add_rolling_features(df: DataFrame) -> DataFrame:
    """Add leakage-safe rolling demand statistics for each taxi zone.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame containing LocationID, pickup_hour and demand.

    Returns
    -------
    DataFrame
        Rows extended with 24-hour and 168-hour rolling means plus the number
        of historical demand observations present in each window.

    Notes
    -----
    Windows cover only the preceding 24 or 168 rows and explicitly exclude
    the current demand value, preventing target leakage.
    """

    zone_window = (
        Window
        .partitionBy("LocationID")
        .orderBy("pickup_hour")
    )

    window_24h = zone_window.rowsBetween(-24, -1)
    window_168h = zone_window.rowsBetween(-168, -1)

    return (
        df
        .withColumn(
            "rolling_mean_24h",
            F.avg("demand").over(window_24h)
        )
        .withColumn(
            "history_count_24h",
            F.count("demand").over(window_24h)
        )
        .withColumn(
            "rolling_mean_168h",
            F.avg("demand").over(window_168h)
        )
        .withColumn(
            "history_count_168h",
            F.count("demand").over(window_168h)
        )
    )