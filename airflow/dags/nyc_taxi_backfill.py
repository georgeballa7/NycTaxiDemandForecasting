from datetime import datetime

from airflow.sdk import dag, task

from backend.workflows.monthly_ingestion import run_backfill
from backend.workflows.ml_pipeline import run_ml_pipeline


@dag(
    dag_id="nyc_taxi_backfill",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    params={
        "start_year": 2025,
        "start_month": 7,
        "end_year": None,
        "end_month": None,
    },
    tags=["nyc-taxi", "backfill"],
)
def nyc_taxi_backfill():

    @task
    def process_backfill(**context):
        params = context["params"]
        return run_backfill(
            start_year=int(params["start_year"]),
            start_month=int(params["start_month"]),
            end_year=(
                int(params["end_year"])
                if params.get("end_year") is not None
                else None
            ),
            end_month=(
                int(params["end_month"])
                if params.get("end_month") is not None
                else None
            ),
        )

    @task
    def retrain_model(processed_months: list[str]):
        if not processed_months:
            print(
                "Backfill processed no new TLC months. "
                "Skipping ML retraining."
            )
            return {
                "retrained": False,
                "processed_months": [],
            }

        print(
            f"Backfill processed {len(processed_months)} month(s): "
            f"{', '.join(processed_months)}. "
            "Starting ML retraining."
        )

        run_ml_pipeline()

        return {
            "retrained": True,
            "processed_months": processed_months,
        }

    processed_months = process_backfill()
    retrain_model(processed_months)


nyc_taxi_backfill()
