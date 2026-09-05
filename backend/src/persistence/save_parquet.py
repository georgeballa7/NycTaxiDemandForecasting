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


def save_monthly_parquet(
    df: DataFrame,
    output_root: Path,
    year: int,
    month: int,
) -> Path:
    """
    Persist one dataset month idempotently.

    Only the target month directory is overwritten, so rerunning a month
    replaces that month without touching previously processed months.
    """

    if not 1 <= month <= 12:
        raise ValueError(
            f"month must be between 1 and 12. Received: {month}"
        )

    output_path = (
        output_root
        / f"year={year}"
        / f"month={month:02d}"
    )

    (
        df.write
        .mode("overwrite")
        .parquet(str(output_path))
    )

    return output_path
