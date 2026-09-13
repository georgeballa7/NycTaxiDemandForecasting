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
    """
    Ergänzt aus vorhandenen Kalenderwerten zyklische Zeitmerkmale.

    Die Funktion markiert Wochenenden und kodiert Stunde, Wochentag und Monat
    jeweils mit Sinus und Kosinus. Dadurch bleibt ihre zyklische Struktur für
    das Machine-Learning-Modell erhalten.

    Args:
        df: PySpark-DataFrame mit den Spalten ``hour``, ``day_of_week`` und
            ``month``.

    Returns:
        DataFrame mit ``is_weekend`` sowie den Sinus-/Kosinusmerkmalen für
        Stunde, Wochentag und Monat.
    """
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
    """
    Erzeugt Kalendermerkmale, die auch für zukünftige Zeitpunkte bekannt sind.

    Aus ``pickup_hour`` werden Stunde, Wochentag und Monat abgeleitet. Danach
    ergänzt ``_add_calendar_columns`` Wochenend- und zyklische Merkmale. Die
    Funktion benötigt keine zukünftigen Nachfragewerte und kann deshalb auch
    beim echten Forecasting verwendet werden.

    Args:
        df: PySpark-DataFrame mit der Zeitstempelspalte ``pickup_hour``.

    Returns:
        DataFrame mit Stunde, Wochentag, Monat, Wochenendindikator und den
        zugehörigen zyklischen Sinus-/Kosinusmerkmalen.
    """
    return _add_calendar_columns(
        df
        .withColumn("hour", F.hour("pickup_hour"))
        .withColumn("day_of_week", F.dayofweek("pickup_hour"))
        .withColumn("month", F.month("pickup_hour"))
    )


def add_historical_profile_features(df: DataFrame) -> DataFrame:
    """
    Erzeugt leakage-sichere historische Nachfrageprofile für das Backtesting.

    Zunächst werden Kalendermerkmale und der jeweilige Kalendermonat ergänzt.
    Anschließend entstehen drei historische Durchschnittsprofile: pro Zone,
    pro Zone und Stunde sowie pro Zone, Wochentag und Stunde. Für einen
    Zielmonat werden dabei ausschließlich frühere Kalendermonate verwendet.
    Die berechneten Profile werden anschließend an die ursprünglichen Daten
    zurückgejoint. So fließt keine Nachfrage aus dem zu prognostizierenden
    Monat in dessen Features ein.

    Args:
        df: PySpark-DataFrame mit mindestens ``pickup_hour``, ``LocationID``
            und ``demand``.

    Returns:
        DataFrame mit Kalendermerkmalen, ``calendar_month`` und den historischen
        Profilmerkmalen ``zone_mean_demand``, ``zone_hour_mean`` und
        ``zone_dow_hour_mean``. Für frühe Monate ohne vorherige Historie können
        die Profilwerte null sein.
    """
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
    """
    Erstellt ein wiederverwendbares Merkmalsraster für zukünftige Prognosen.

    Aus der gesamten beobachteten Historie werden durchschnittliche
    Nachfrageprofile pro Zone, pro Zone/Stunde und pro Zone/Wochentag/Stunde
    berechnet. Danach entsteht per Kreuzprodukt ein Raster aus allen beobachteten
    Zonen, zwölf Monaten, sieben Wochentagen und 24 Stunden. Das Raster erhält
    die zyklischen Kalendermerkmale und wird mit den historischen Profilen
    verbunden. Es kann anschließend zur Bewertung zukünftiger Zeitpunkte durch
    das trainierte Modell verwendet werden.

    Args:
        df: Historischer PySpark-DataFrame mit ``LocationID``, ``pickup_hour``
            und ``demand``.

    Returns:
        DataFrame mit allen Zone-Monat-Wochentag-Stunde-Kombinationen,
        Kalendermerkmalen sowie ``zone_mean_demand``, ``zone_hour_mean`` und
        ``zone_dow_hour_mean`` als historische Profilmerkmale.
    """
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
