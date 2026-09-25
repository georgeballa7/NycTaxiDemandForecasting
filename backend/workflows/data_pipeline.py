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
    """Truncate analytics facts and dimensions for the legacy full refresh.

    Returns
    -------
    None
        Target analytics tables are truncated in one local transaction.

    Notes
    -----
    The incremental monthly pipeline does not call this helper.
    """
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
    """Run the established full-refresh data workflow.

    Returns
    -------
    None
        Processed datasets and local PostgreSQL analytics tables are rebuilt.

    Notes
    -----
    The workflow builds demand/features, business trips and EDA artifacts,
    truncates the local analytics schema, then reloads demand and business
    tables. It is separate from the incremental monthly path.
    """
    spark = build_dataset()
    spark.stop()
    build_business_trips()
    prepare_eda_data()

    reset_analytics_schema()

    load_demanddata_to_postgres()
    load_businessdata_to_postgres()


def _load_month_into_database(year: int, month: int, db_engine) -> None:
    """Load one prepared month of demand and business data into a database.

    Parameters
    ----------
    year : int
        Dataset year.
    month : int
        Dataset month.
    db_engine
        SQLAlchemy engine for the target PostgreSQL database.
    """
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
    """Process and upsert one month without truncating existing analytics.

    Parameters
    ----------
    year : int
        Dataset year.
    month : int
        Dataset month.

    Returns
    -------
    None
        Monthly demand/features, business and EDA artifacts are built and
        loaded into local PostgreSQL and Supabase when configured.

    Notes
    -----
    Existing months remain untouched because monthly Parquet partitions and
    database rows are updated idempotently rather than full-refreshed.
    """

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
