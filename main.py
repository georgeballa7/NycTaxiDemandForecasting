from pathlib import Path

from src.ingestion.spark_session import create_spark_session
from src.ingestion.load_trip_data import load_trip_data

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

    spark.stop()


if __name__ == "__main__":
    main()