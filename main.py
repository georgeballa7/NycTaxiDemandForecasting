from pathlib import Path
from datetime import datetime

from src.ingestion.spark_session import create_spark_session
from src.ingestion.load_trip_data import load_trip_data
from src.ingestion.load_zone_lookup import load_zone_lookup
from src.processing.clean_trip_data import clean_trip_data

def main():
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parent
    raw_data_path = project_root / "data" / "raw"

    trips = load_trip_data(
        spark=spark,
        raw_data_path=raw_data_path,
    )

    print(f"Records Jan-Jun: {trips.count():,}")
    trips.printSchema()

    zones = load_zone_lookup(spark, raw_data_path)

    print(f"Taxi Zones: {zones.count():,}")
    zones.printSchema()
    zones.show(10, truncate=False)

    cleaned_trips = clean_trip_data(
    trips,
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 7, 1),
    )

    print(f"Vor Cleaning:  {trips.count():,}")
    print(f"Nach Cleaning: {cleaned_trips.count():,}")

    spark.stop()


if __name__ == "__main__":
    main()