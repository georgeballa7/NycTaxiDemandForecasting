from airflow.sdk import dag, task
from datetime import datetime


@dag(
    dag_id="test_airflow_setup",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test"],
)
def test_airflow_setup():
    """Define a manual smoke-test DAG that verifies basic Airflow task execution."""

    @task
    def say_hello():
    """Print a confirmation message to verify task execution."""
        print("Airflow is running correctly for the NYC Taxi project.")

    say_hello()


test_airflow_setup()