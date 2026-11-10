from datetime import datetime

from airflow.sdk import dag, task
from sqlalchemy import text

from backend.src.database.connection import engine


@dag(
    dag_id="test_database_connections",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test", "database"],
)
def test_database_connections():
    """Define a manual DAG to verify local analytics PostgreSQL connectivity."""

    @task
    def check_local_database():
        """Connect to local PostgreSQL and print the database name."""
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar()

        print("Local PostgreSQL connection successful.")
        print(f"Database: {database_name}")

    check_local_database()


test_database_connections()
