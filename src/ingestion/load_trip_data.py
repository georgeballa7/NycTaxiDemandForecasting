from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


def load_trip_data(
    spark: SparkSession,
    raw_data_path: Path,
) -> DataFrame:

    parquet_pattern = str(
        raw_data_path / "yellow_tripdata_2025-*.parquet"
    )

    return spark.read.parquet(parquet_pattern)

