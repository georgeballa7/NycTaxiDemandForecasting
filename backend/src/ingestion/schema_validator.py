import logging

from pyspark.sql import DataFrame
from pyspark.sql.types import (
    ByteType,
    ShortType,
    IntegerType,
    LongType,
    FloatType,
    DoubleType,
    DecimalType,
    TimestampType,
    TimestampNTZType,
)


logger = logging.getLogger(__name__)


# --------------------------------------------------
# Columns required by the current project pipeline
# --------------------------------------------------

REQUIRED_COLUMNS = {
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "trip_distance",
    "fare_amount",
    "total_amount",
    "tip_amount",
    "tolls_amount",
    "congestion_surcharge",
    "Airport_fee",
    "cbd_congestion_fee",
}


# --------------------------------------------------
# Other columns currently known from TLC Yellow Taxi
# --------------------------------------------------

KNOWN_OPTIONAL_COLUMNS = {
    "passenger_count",
    "RatecodeID",
    "store_and_fwd_flag",
    "extra",
    "mta_tax",
    "improvement_surcharge",
}


KNOWN_COLUMNS = (
    REQUIRED_COLUMNS
    | KNOWN_OPTIONAL_COLUMNS
)


# --------------------------------------------------
# Compatible Spark data type groups
# --------------------------------------------------

INTEGER_TYPES = (
    ByteType,
    ShortType,
    IntegerType,
    LongType,
)

NUMERIC_TYPES = (
    ByteType,
    ShortType,
    IntegerType,
    LongType,
    FloatType,
    DoubleType,
    DecimalType,
)

TIMESTAMP_TYPES = (
    TimestampType,
    TimestampNTZType,
)


# --------------------------------------------------
# Expected types for columns used by the pipeline
# --------------------------------------------------

EXPECTED_TYPE_GROUPS = {
    "VendorID": INTEGER_TYPES,
    "PULocationID": INTEGER_TYPES,
    "DOLocationID": INTEGER_TYPES,
    "payment_type": INTEGER_TYPES,

    "tpep_pickup_datetime": TIMESTAMP_TYPES,
    "tpep_dropoff_datetime": TIMESTAMP_TYPES,

    "trip_distance": NUMERIC_TYPES,
    "fare_amount": NUMERIC_TYPES,
    "total_amount": NUMERIC_TYPES,
    "tip_amount": NUMERIC_TYPES,
    "tolls_amount": NUMERIC_TYPES,
    "congestion_surcharge": NUMERIC_TYPES,
    "Airport_fee": NUMERIC_TYPES,
    "cbd_congestion_fee": NUMERIC_TYPES,
}


def validate_trip_schema(
    trips: DataFrame,
) -> dict:
    """
    Validate the raw NYC Yellow Taxi schema.

    Rules:
    - Missing required columns stop the pipeline.
    - Incompatible types on critical columns stop the pipeline.
    - New additional TLC columns are reported but do not stop processing.
    - Missing known optional columns are reported but do not stop processing.
    """

    actual_columns = set(trips.columns)

    missing_required = (
        REQUIRED_COLUMNS - actual_columns
    )

    new_columns = (
        actual_columns - KNOWN_COLUMNS
    )

    missing_optional = (
        KNOWN_OPTIONAL_COLUMNS - actual_columns
    )

    # --------------------------------------------------
    # Required columns
    # --------------------------------------------------

    if missing_required:
        missing = sorted(missing_required)

        raise ValueError(
            "Raw TLC schema validation failed. "
            f"Missing required columns: {missing}"
        )

    # --------------------------------------------------
    # Critical data types
    # --------------------------------------------------

    schema_by_name = {
        field.name: field.dataType
        for field in trips.schema.fields
    }

    incompatible_types = {}

    for column, allowed_types in EXPECTED_TYPE_GROUPS.items():

        if column not in schema_by_name:
            continue

        actual_type = schema_by_name[column]

        if not isinstance(
            actual_type,
            allowed_types,
        ):
            incompatible_types[column] = (
                actual_type.simpleString()
            )

    if incompatible_types:
        raise TypeError(
            "Raw TLC schema validation failed. "
            "Incompatible column types: "
            f"{incompatible_types}"
        )

    # --------------------------------------------------
    # New columns
    # --------------------------------------------------

    if new_columns:
        logger.info(
            "New TLC columns detected: %s. "
            "Processing will continue.",
            sorted(new_columns),
        )

    # --------------------------------------------------
    # Known optional columns
    # --------------------------------------------------

    if missing_optional:
        logger.info(
            "Known optional TLC columns not present: %s. "
            "Processing will continue.",
            sorted(missing_optional),
        )

    # --------------------------------------------------
    # Success
    # --------------------------------------------------

    logger.info(
        "TLC schema validation passed. "
        "Columns found: %d.",
        len(actual_columns),
    )

    return {
        "valid": True,
        "column_count": len(actual_columns),
        "missing_required": [],
        "new_columns": sorted(new_columns),
        "missing_optional": sorted(
            missing_optional
        ),
        "incompatible_types": {},
    }
