from datetime import datetime

from airflow.sdk import dag, task

from backend.workflows.monthly_ingestion import run_next_available_month
from backend.workflows.ml_pipeline import run_ml_pipeline


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

    @task
    def retrain_model(ingestion_result: dict):
        if not ingestion_result["processed"]:
            print(
                "No new TLC month was processed. "
                "Skipping ML retraining."
            )
            return {
                "retrained": False,
                "year": ingestion_result["year"],
                "month": ingestion_result["month"],
            }

        print(
            "New TLC month processed successfully. "
            "Starting ML retraining."
        )

        run_ml_pipeline()

        return {
            "retrained": True,
            "year": ingestion_result["year"],
            "month": ingestion_result["month"],
        }

    ingestion_result = process_next_month()
    retrain_model(ingestion_result)


nyc_taxi_monthly_ingestion()
