from pathlib import Path

from pyspark.sql import DataFrame, SparkSession



def load_zone_lookup(
    spark: SparkSession,
    raw_data_path: Path,
) -> DataFrame:

    lookup_path = raw_data_path / "taxi_zone_lookup.csv"

    return (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(str(lookup_path))
    )