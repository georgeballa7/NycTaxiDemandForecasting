from pathlib import Path

from pyspark.sql import DataFrame


def save_parquet(
    df: DataFrame,
    output_path: Path,
) -> None:
    """Overwrite a Parquet dataset at the specified path.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame to persist.
    output_path : Path
        Destination directory for the Parquet dataset.

    Returns
    -------
    None
        Data is written as a side effect.
    """
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
    """Persist one dataset month idempotently as Parquet.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame containing the monthly dataset.
    output_root : Path
        Root directory of the partitioned dataset.
    year : int
        Partition year.
    month : int
        Partition month from 1 through 12.

    Returns
    -------
    Path
        Directory written in year=YYYY/month=MM layout.

    Raises
    ------
    ValueError
        If month is outside 1-12.

    Notes
    -----
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
