import math


from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


def add_time_features(df: DataFrame) -> DataFrame:
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