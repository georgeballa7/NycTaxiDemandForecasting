from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


def load_trip_data(
    spark: SparkSession,
    raw_data_path: Path,
) -> DataFrame:

    parquet_files = sorted(
        raw_data_path.glob("yellow_tripdata_2025-*.parquet")
    )

    if not parquet_files:
        raise FileNotFoundError(
            f"No NYC taxi parquet files found in: {raw_data_path}"
        )

    file_paths = [str(path) for path in parquet_files]

    print(f"Found {len(file_paths)} parquet files:")
    for path in file_paths:
        print(f"  {path}")

    return spark.read.parquet(*file_paths)