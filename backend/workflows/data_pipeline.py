from sqlalchemy import text

from backend.src.database.connection import engine, supabase_engine
from backend.src.database.load_businessdata_to_postgres import (
    main as load_businessdata_to_postgres,
)
from backend.src.database.load_demanddata_to_postgres import (
    load_demanddata_to_postgres,
)
from backend.src.processing.build_business_trips import build_business_trips
from backend.src.processing.build_dataset import build_dataset
from backend.src.processing.prepare_eda_data import prepare_eda_data


def reset_analytics_schema():
    """Legacy full-refresh helper. Never used by the monthly pipeline."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    taxi_analytics.fact_demand,
                    taxi_analytics.fact_trips,
                    taxi_analytics.dim_payment,
                    taxi_analytics.dim_hour,
                    taxi_analytics.dim_date,
                    taxi_analytics.dim_zone;
                """
            )
        )


def run_data_pipeline():
    """Preserve the established full-refresh workflow."""
    spark = build_dataset()
    spark.stop()
    build_business_trips()
    prepare_eda_data()

    reset_analytics_schema()

    load_demanddata_to_postgres()
    load_businessdata_to_postgres()


def _load_month_into_database(year: int, month: int, db_engine) -> None:
    load_demanddata_to_postgres(
        year=year,
        month=month,
        db_engine=db_engine,
    )
    load_businessdata_to_postgres(
        year=year,
        month=month,
        db_engine=db_engine,
    )


def run_monthly_data_pipeline(year: int, month: int) -> None:
    """Process and upsert one month without truncating existing analytics."""

    print(f"Starting monthly data pipeline for {year}-{month:02d}...")

    spark = build_dataset(year=year, month=month)
    spark.stop()

    build_business_trips(year=year, month=month)
    prepare_eda_data(year=year, month=month)

    print("Loading monthly data into local/default PostgreSQL...")
    _load_month_into_database(year, month, engine)

    if supabase_engine is not None:
        print("Loading monthly data into Supabase PostgreSQL...")
        _load_month_into_database(year, month, supabase_engine)
    else:
        print(
            "SUPABASE_DATABASE_URL is not configured; "
            "Supabase load skipped."
        )

    print(f"Monthly data pipeline completed for {year}-{month:02d}.")


if __name__ == "__main__":
    run_data_pipeline()
