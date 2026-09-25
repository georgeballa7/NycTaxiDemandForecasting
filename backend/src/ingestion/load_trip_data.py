from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from backend.src.ingestion.schema_validator import validate_trip_schema


def load_trip_data(
    spark: SparkSession,
    raw_data_path: Path,
    year: int | None = None,
    month: int | None = None,
) -> DataFrame:
    """Load raw NYC Yellow Taxi trip data into Spark.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session used to read the Parquet data.
    raw_data_path : Path
        Directory containing the downloaded TLC Parquet files.
    year : int or None
        Year of a single monthly dataset; supplied together with month.
    month : int or None
        Month of a single monthly dataset; supplied together with year.

    Returns
    -------
    DataFrame
        Spark DataFrame containing the validated raw trip records.

    Raises
    ------
    ValueError
        If only one date component is supplied or month is outside 1-12.
    FileNotFoundError
        If the requested monthly file, or any compatible full-refresh file,
        cannot be found.

    Notes
    -----
    With no year and month, all 2025 monthly files are loaded to preserve the
    established full-refresh workflow. TLC schema validation runs before the
    DataFrame is returned.
    """

    if (year is None) != (month is None):
        raise ValueError(
            "year and month must either both be provided or both be omitted."
        )

    if year is not None and month is not None:
        if not 1 <= month <= 12:
            raise ValueError(
                f"month must be between 1 and 12. Received: {month}"
            )

        parquet_file = (
            raw_data_path
            / f"yellow_tripdata_{year}-{month:02d}.parquet"
        )

        if not parquet_file.exists():
            raise FileNotFoundError(
                f"NYC taxi parquet file not found: {parquet_file}"
            )

        print(f"Loading monthly trip data: {parquet_file}")

        trips = spark.read.parquet(str(parquet_file))
        validate_trip_schema(trips)

        return trips

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

    trips = spark.read.parquet(*file_paths)
    validate_trip_schema(trips)

    return trips
