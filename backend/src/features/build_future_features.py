import math

from pyspark.sql import DataFrame
from pyspark.sql import Window
from pyspark.sql import functions as F


CALENDAR_FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "day_of_month",
    "month",
    "week_of_year",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
]


PROFILE_FEATURE_COLUMNS = [
    "zone_hour_mean",
    "zone_dow_hour_mean",
    "zone_month_mean",
    "zone_month_hour_mean",
]


FUTURE_FEATURE_COLUMNS = (
    CALENDAR_FEATURE_COLUMNS
    + PROFILE_FEATURE_COLUMNS
)


def add_future_calendar_features(
    df: DataFrame,
) -> DataFrame:
    """
    Add features that are known for any future timestamp.

    These features do not depend on future observed taxi demand.
    """

    return (
        df
        .withColumn(
            "hour",
            F.hour("pickup_hour"),
        )
        .withColumn(
            "day_of_week",
            F.dayofweek("pickup_hour"),
        )
        .withColumn(
            "day_of_month",
            F.dayofmonth("pickup_hour"),
        )
        .withColumn(
            "month",
            F.month("pickup_hour"),
        )
        .withColumn(
            "week_of_year",
            F.weekofyear("pickup_hour"),
        )
        .withColumn(
            "is_weekend",
            F.when(
                F.col("day_of_week").isin(1, 7),
                1,
            ).otherwise(0),
        )
        .withColumn(
            "hour_sin",
            F.sin(
                2
                * math.pi
                * F.col("hour")
                / 24
            ),
        )
        .withColumn(
            "hour_cos",
            F.cos(
                2
                * math.pi
                * F.col("hour")
                / 24
            ),
        )
        .withColumn(
            "dow_sin",
            F.sin(
                2
                * math.pi
                * F.col("day_of_week")
                / 7
            ),
        )
        .withColumn(
            "dow_cos",
            F.cos(
                2
                * math.pi
                * F.col("day_of_week")
                / 7
            ),
        )
        .withColumn(
            "month_sin",
            F.sin(
                2
                * math.pi
                * F.col("month")
                / 12
            ),
        )
        .withColumn(
            "month_cos",
            F.cos(
                2
                * math.pi
                * F.col("month")
                / 12
            ),
        )
    )


def add_historical_profile_features(
    df: DataFrame,
) -> DataFrame:
    """
    Build demand-profile features using only earlier months.

    For every target month, profile values are calculated from
    observations belonging to strictly earlier calendar months.
    This prevents target leakage and mirrors future inference.
    """

    data = (
        add_future_calendar_features(df)
        .withColumn(
            "calendar_month",
            F.trunc(
                F.col("pickup_hour"),
                "month",
            ),
        )
    )

    month_zone_hour = (
        data
        .groupBy(
            "calendar_month",
            "LocationID",
            "hour",
        )
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )

    zone_hour_window = (
        Window
        .partitionBy(
            "LocationID",
            "hour",
        )
        .orderBy("calendar_month")
        .rowsBetween(
            Window.unboundedPreceding,
            -1,
        )
    )

    month_zone_hour = (
        month_zone_hour
        .withColumn(
            "zone_hour_mean",
            F.sum("_sum").over(
                zone_hour_window
            )
            / F.sum("_count").over(
                zone_hour_window
            ),
        )
        .select(
            "calendar_month",
            "LocationID",
            "hour",
            "zone_hour_mean",
        )
    )

    month_zone_dow_hour = (
        data
        .groupBy(
            "calendar_month",
            "LocationID",
            "day_of_week",
            "hour",
        )
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )

    zone_dow_hour_window = (
        Window
        .partitionBy(
            "LocationID",
            "day_of_week",
            "hour",
        )
        .orderBy("calendar_month")
        .rowsBetween(
            Window.unboundedPreceding,
            -1,
        )
    )

    month_zone_dow_hour = (
        month_zone_dow_hour
        .withColumn(
            "zone_dow_hour_mean",
            F.sum("_sum").over(
                zone_dow_hour_window
            )
            / F.sum("_count").over(
                zone_dow_hour_window
            ),
        )
        .select(
            "calendar_month",
            "LocationID",
            "day_of_week",
            "hour",
            "zone_dow_hour_mean",
        )
    )

    month_zone = (
        data
        .groupBy(
            "calendar_month",
            "LocationID",
        )
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
        .withColumn(
            "month_number",
            F.month("calendar_month"),
        )
    )

    zone_month_window = (
        Window
        .partitionBy(
            "LocationID",
            "month_number",
        )
        .orderBy("calendar_month")
        .rowsBetween(
            Window.unboundedPreceding,
            -1,
        )
    )

    month_zone = (
        month_zone
        .withColumn(
            "zone_month_mean",
            F.sum("_sum").over(
                zone_month_window
            )
            / F.sum("_count").over(
                zone_month_window
            ),
        )
        .select(
            "calendar_month",
            "LocationID",
            "zone_month_mean",
        )
    )

    month_zone_month_hour = (
        data
        .groupBy(
            "calendar_month",
            "LocationID",
            "month",
            "hour",
        )
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )

    zone_month_hour_window = (
        Window
        .partitionBy(
            "LocationID",
            "month",
            "hour",
        )
        .orderBy("calendar_month")
        .rowsBetween(
            Window.unboundedPreceding,
            -1,
        )
    )

    month_zone_month_hour = (
        month_zone_month_hour
        .withColumn(
            "zone_month_hour_mean",
            F.sum("_sum").over(
                zone_month_hour_window
            )
            / F.sum("_count").over(
                zone_month_hour_window
            ),
        )
        .select(
            "calendar_month",
            "LocationID",
            "month",
            "hour",
            "zone_month_hour_mean",
        )
    )

    return (
        data
        .join(
            month_zone_hour,
            [
                "calendar_month",
                "LocationID",
                "hour",
            ],
            "left",
        )
        .join(
            month_zone_dow_hour,
            [
                "calendar_month",
                "LocationID",
                "day_of_week",
                "hour",
            ],
            "left",
        )
        .join(
            month_zone,
            [
                "calendar_month",
                "LocationID",
            ],
            "left",
        )
        .join(
            month_zone_month_hour,
            [
                "calendar_month",
                "LocationID",
                "month",
                "hour",
            ],
            "left",
        )
    )
