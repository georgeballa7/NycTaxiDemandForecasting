from pathlib import Path

from pyspark.sql import DataFrame, SparkSession



def load_zone_lookup(
    spark: SparkSession,
    raw_data_path: Path,
) -> DataFrame:
    """Load the NYC TLC taxi-zone lookup CSV into Spark.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session used to read the CSV file.
    raw_data_path : Path
        Directory containing taxi_zone_lookup.csv.

    Returns
    -------
    DataFrame
        Taxi-zone lookup with header names and Spark-inferred column types.
    """

    lookup_path = raw_data_path / "taxi_zone_lookup.csv"

    return (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(str(lookup_path))
    )