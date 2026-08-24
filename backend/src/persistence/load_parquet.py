from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


def load_parquet(
    spark: SparkSession,
    input_path: Path,
) -> DataFrame:
    return spark.read.parquet(str(input_path))