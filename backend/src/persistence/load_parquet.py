from pathlib import Path

from pyspark.sql import DataFrame, SparkSession


def load_parquet(
    spark: SparkSession,
    input_path: Path,
) -> DataFrame:
    """Load a Parquet dataset with an existing Spark session.

    Parameters
    ----------
    spark : SparkSession
        Spark session used for the read operation.
    input_path : Path
        File or directory containing the Parquet dataset.

    Returns
    -------
    DataFrame
        Spark DataFrame representing the persisted dataset.
    """
    return spark.read.parquet(str(input_path))