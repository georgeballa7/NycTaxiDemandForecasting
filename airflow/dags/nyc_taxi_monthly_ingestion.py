from datetime import datetime

from airflow.sdk import dag, task

from backend.workflows.monthly_ingestion import run_next_available_month


@dag(
    dag_id="nyc_taxi_monthly_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["nyc-taxi", "ingestion"],
)
def nyc_taxi_monthly_ingestion():

    @task
    def process_next_month():
        return run_next_available_month()

    process_next_month()


nyc_taxi_monthly_ingestion()
