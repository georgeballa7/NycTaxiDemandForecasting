import math

from pyspark.sql import DataFrame
from pyspark.sql import Window
from pyspark.sql import functions as F


CALENDAR_FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
]

PROFILE_FEATURE_COLUMNS = [
    "zone_mean_demand",
    "zone_hour_mean",
    "zone_dow_hour_mean",
]

FUTURE_FEATURE_COLUMNS = CALENDAR_FEATURE_COLUMNS + PROFILE_FEATURE_COLUMNS


def _add_calendar_columns(df: DataFrame) -> DataFrame:
    """Ergänzt zyklische Kalendermerkmale auf Basis vorhandener Zeitspalten."""
    return (
        df
        .withColumn(
            "is_weekend",
            F.when(F.col("day_of_week").isin(1, 7), 1).otherwise(0),
        )
        .withColumn(
            "hour_sin",
            F.sin(2 * math.pi * F.col("hour") / 24),
        )
        .withColumn(
            "hour_cos",
            F.cos(2 * math.pi * F.col("hour") / 24),
        )
        .withColumn(
            "dow_sin",
            F.sin(2 * math.pi * F.col("day_of_week") / 7),
        )
        .withColumn(
            "dow_cos",
            F.cos(2 * math.pi * F.col("day_of_week") / 7),
        )
        .withColumn(
            "month_sin",
            F.sin(2 * math.pi * F.col("month") / 12),
        )
        .withColumn(
            "month_cos",
            F.cos(2 * math.pi * F.col("month") / 12),
        )
    )


def add_future_calendar_features(df: DataFrame) -> DataFrame:
    """Ergänzt Kalendermerkmale, die für zukünftige Zeitpunkte bereits bekannt sind."""
    return _add_calendar_columns(
        df
        .withColumn("hour", F.hour("pickup_hour"))
        .withColumn("day_of_week", F.dayofweek("pickup_hour"))
        .withColumn("month", F.month("pickup_hour"))
    )


def add_historical_profile_features(df: DataFrame) -> DataFrame:
    """Erzeugt leakage-sichere historische Nachfrageprofile für das Backtesting."""
    data = (
        add_future_calendar_features(df)
        .withColumn("calendar_month", F.trunc(F.col("pickup_hour"), "month"))
    )

    month_zone = (
        data
        .groupBy("calendar_month", "LocationID")
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )
    zone_window = (
        Window
        .partitionBy("LocationID")
        .orderBy("calendar_month")
        .rowsBetween(Window.unboundedPreceding, -1)
    )
    month_zone = (
        month_zone
        .withColumn(
            "zone_mean_demand",
            F.sum("_sum").over(zone_window) / F.sum("_count").over(zone_window),
        )
        .select("calendar_month", "LocationID", "zone_mean_demand")
    )

    month_zone_hour = (
        data
        .groupBy("calendar_month", "LocationID", "hour")
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )
    zone_hour_window = (
        Window
        .partitionBy("LocationID", "hour")
        .orderBy("calendar_month")
        .rowsBetween(Window.unboundedPreceding, -1)
    )
    month_zone_hour = (
        month_zone_hour
        .withColumn(
            "zone_hour_mean",
            F.sum("_sum").over(zone_hour_window)
            / F.sum("_count").over(zone_hour_window),
        )
        .select("calendar_month", "LocationID", "hour", "zone_hour_mean")
    )

    month_zone_dow_hour = (
        data
        .groupBy("calendar_month", "LocationID", "day_of_week", "hour")
        .agg(
            F.sum("demand").alias("_sum"),
            F.count("demand").alias("_count"),
        )
    )
    zone_dow_hour_window = (
        Window
        .partitionBy("LocationID", "day_of_week", "hour")
        .orderBy("calendar_month")
        .rowsBetween(Window.unboundedPreceding, -1)
    )
    month_zone_dow_hour = (
        month_zone_dow_hour
        .withColumn(
            "zone_dow_hour_mean",
            F.sum("_sum").over(zone_dow_hour_window)
            / F.sum("_count").over(zone_dow_hour_window),
        )
        .select(
            "calendar_month",
            "LocationID",
            "day_of_week",
            "hour",
            "zone_dow_hour_mean",
        )
    )

    return (
        data
        .join(month_zone, ["calendar_month", "LocationID"], "left")
        .join(
            month_zone_hour,
            ["calendar_month", "LocationID", "hour"],
            "left",
        )
        .join(
            month_zone_dow_hour,
            ["calendar_month", "LocationID", "day_of_week", "hour"],
            "left",
        )
    )


def build_future_scoring_grid(df: DataFrame) -> DataFrame:
    """Erstellt aus der Historie ein wiederverwendbares Raster für zukünftige Prognosen."""
    data = add_future_calendar_features(df)
    spark = df.sparkSession

    zone_mean = (
        data
        .groupBy("LocationID")
        .agg(F.avg("demand").alias("zone_mean_demand"))
    )
    zone_hour = (
        data
        .groupBy("LocationID", "hour")
        .agg(F.avg("demand").alias("zone_hour_mean"))
    )
    zone_dow_hour = (
        data
        .groupBy("LocationID", "day_of_week", "hour")
        .agg(F.avg("demand").alias("zone_dow_hour_mean"))
    )

    zones = data.select("LocationID").distinct()
    months = spark.range(1, 13).select(F.col("id").cast("int").alias("month"))
    weekdays = spark.range(1, 8).select(
        F.col("id").cast("int").alias("day_of_week")
    )
    hours = spark.range(0, 24).select(F.col("id").cast("int").alias("hour"))

    grid = _add_calendar_columns(
        zones.crossJoin(months).crossJoin(weekdays).crossJoin(hours)
    )

    return (
        grid
        .join(zone_mean, "LocationID", "left")
        .join(zone_hour, ["LocationID", "hour"], "left")
        .join(
            zone_dow_hour,
            ["LocationID", "day_of_week", "hour"],
            "left",
        )
    )
