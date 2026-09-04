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

    @task
    def say_hello():
        print("Airflow is running correctly for the NYC Taxi project.")

    say_hello()


test_airflow_setup()