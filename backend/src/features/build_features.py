import math


from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


def add_time_features(df: DataFrame) -> DataFrame:
    """
    Ergänzt Zeit- und Zyklusmerkmale für die Nachfrageprognose.

    Aus ``pickup_hour`` werden Stunde, Wochentag und Kalendertag abgeleitet.
    Zusätzlich wird markiert, ob der Zeitpunkt auf ein Wochenende fällt. Stunde
    und Wochentag werden außerdem mit Sinus- und Kosinuswerten zyklisch kodiert,
    damit z. B. 23 Uhr und 0 Uhr im Modell als zeitlich benachbart behandelt werden.

    Args:
        df: PySpark-DataFrame mit der Spalte ``pickup_hour``.

    Returns:
        DataFrame mit den zusätzlichen Spalten ``hour``, ``day_of_week``,
        ``day_of_month``, ``is_weekend``, ``hour_sin``, ``hour_cos``,
        ``dow_sin`` und ``dow_cos``.
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
    """
    Ergänzt verzögerte Nachfragewerte je Taxi-Zone.

    Die Daten werden pro ``LocationID`` chronologisch nach ``pickup_hour``
    betrachtet. Für jede Zeile werden die Nachfragewerte von einer Stunde,
    24 Stunden und 168 Stunden zuvor als zusätzliche Merkmale übernommen.

    Args:
        df: PySpark-DataFrame mit ``LocationID``, ``pickup_hour`` und ``demand``.

    Returns:
        DataFrame mit den zusätzlichen Spalten ``lag_1h``, ``lag_24h`` und
        ``lag_168h``. Fehlt für einen Zeitpunkt ausreichend Historie, bleibt der
        jeweilige Lag-Wert null.
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
    """
    Berechnet rollierende Nachfragekennzahlen je Taxi-Zone.

    Für jede ``LocationID`` werden ausschließlich vorherige Beobachtungen
    verwendet: die letzten 24 bzw. 168 Zeilen vor dem aktuellen Zeitpunkt.
    Neben dem Mittelwert wird jeweils gezählt, wie viele historische
    Nachfragewerte tatsächlich im Fenster vorhanden sind.

    Args:
        df: PySpark-DataFrame mit ``LocationID``, ``pickup_hour`` und ``demand``.

    Returns:
        DataFrame mit ``rolling_mean_24h``, ``history_count_24h``,
        ``rolling_mean_168h`` und ``history_count_168h``. Der aktuelle
        Nachfragewert selbst wird nicht in die rollierenden Fenster einbezogen.
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