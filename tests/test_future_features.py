import math
import os
import sys

import pytest
from pyspark.sql import SparkSession

from backend.src.features.build_future_features import (
    FUTURE_FEATURE_COLUMNS,
    add_future_calendar_features,
    build_future_scoring_grid,
)


@pytest.fixture(scope="module")
def spark():
    # Spark launches separate Python workers. Point them explicitly at the
    # interpreter running pytest so Conda, Windows and CI use the same Python.
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    session = (
        SparkSession.builder.master("local[1]")
        .appName("nyc-taxi-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .getOrCreate()
    )
    yield session
    session.stop()


def test_calendar_features_are_forecast_safe_and_correct(spark):
    df = spark.createDataFrame(
        [(1, "2026-09-06 18:00:00", 10.0)],
        ["LocationID", "pickup_hour", "demand"],
    ).selectExpr(
        "LocationID",
        "cast(pickup_hour as timestamp) as pickup_hour",
        "demand",
    )

    row = add_future_calendar_features(df).first()

    assert row.hour == 18
    assert row.day_of_week == 1  # Spark: Sunday=1
    assert row.month == 9
    assert row.is_weekend == 1
    assert row.hour_sin == pytest.approx(math.sin(2 * math.pi * 18 / 24))
    assert row.hour_cos == pytest.approx(math.cos(2 * math.pi * 18 / 24))


def test_future_feature_contract_contains_only_known_or_historical_features():
    forbidden = {"demand", "lag_1h", "lag_24h", "lag_168h", "rolling_mean_24h"}
    assert forbidden.isdisjoint(FUTURE_FEATURE_COLUMNS)


def test_scoring_grid_covers_all_calendar_combinations(spark):
    df = spark.createDataFrame(
        [
            (1, "2026-01-01 00:00:00", 2.0),
            (2, "2026-01-01 00:00:00", 3.0),
        ],
        ["LocationID", "pickup_hour", "demand"],
    ).selectExpr(
        "LocationID",
        "cast(pickup_hour as timestamp) as pickup_hour",
        "demand",
    )

    grid = build_future_scoring_grid(df)

    assert grid.count() == 2 * 12 * 7 * 24
    assert grid.select("month").distinct().count() == 12
    assert grid.select("day_of_week").distinct().count() == 7
    assert grid.select("hour").distinct().count() == 24
