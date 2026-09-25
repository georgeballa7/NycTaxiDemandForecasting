from datetime import datetime

from airflow.sdk import dag, task
from sqlalchemy import create_engine, text

from backend.src.config.settings import (
    DATABASE_URL,
    SUPABASE_DATABASE_URL,
)


@dag(
    dag_id="test_database_connections",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test", "database"],
)
def test_database_connections():
    """Define a manual DAG that tests local and Supabase PostgreSQL connectivity."""

    @task
    def check_local_database():
    """Connect to local PostgreSQL and print the current database name."""
        engine = create_engine(DATABASE_URL)

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database()")
            ).scalar()

        print(f"Local PostgreSQL connection successful.")
        print(f"Database: {result}")

    @task
    def check_supabase_database():
    """Connect to Supabase PostgreSQL and print the current database name."""
        if not SUPABASE_DATABASE_URL:
            raise RuntimeError(
                "SUPABASE_DATABASE_URL is not set."
            )

        engine = create_engine(SUPABASE_DATABASE_URL)

        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT current_database()")
            ).scalar()

        print("Supabase PostgreSQL connection successful.")
        print(f"Database: {result}")

    check_local_database()
    check_supabase_database()


test_database_connections()