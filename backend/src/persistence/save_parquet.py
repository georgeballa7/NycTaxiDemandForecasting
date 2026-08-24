from pathlib import Path

from pyspark.sql import DataFrame


def save_parquet(
    df: DataFrame,
    output_path: Path,
) -> None:
    (
        df.write
        .mode("overwrite")
        .parquet(str(output_path))
    )