from datetime import datetime
import json
import os
from urllib import request

from airflow.sdk import dag, task

from backend.src.ml.publish_future_forecast import publish_future_forecast_data
from backend.src.ml.publish_historical_model import publish_historical_model_data
from backend.src.ml.train_future_model import train_future_model
from backend.src.ml.train_model import train_model
from backend.workflows.monthly_ingestion import run_next_available_month


def _post_slack_message(message: str) -> bool:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print(
            "SLACK_WEBHOOK_URL is not configured; "
            "Slack notification skipped."
        )
        return False

    payload = json.dumps({"text": message}).encode("utf-8")
    slack_request = request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(slack_request, timeout=15) as response:
            if response.status >= 300:
                raise RuntimeError(
                    "Slack webhook returned HTTP "
                    f"{response.status}."
                )
    except Exception as exc:
        print(f"Slack notification failed: {exc}")
        return False

    print("Slack notification sent successfully.")
    return True


def notify_slack_failure(context):
    task_instance = context.get("task_instance")
    exception = context.get("exception")

    dag_id = getattr(task_instance, "dag_id", "unknown")
    task_id = getattr(task_instance, "task_id", "unknown")
    run_id = context.get("run_id") or getattr(
        task_instance,
        "run_id",
        "unknown",
    )
    log_url = getattr(task_instance, "log_url", None)

    data_month = None
    if task_instance is not None:
        try:
            ingestion_result = task_instance.xcom_pull(
                task_ids="process_next_month"
            )
            if isinstance(ingestion_result, dict):
                year = ingestion_result.get("year")
                month = ingestion_result.get("month")
                if year is not None and month is not None:
                    data_month = f"{year}-{int(month):02d}"
        except Exception as exc:
            print(
                "Could not read ingestion result for Slack failure "
                f"notification: {exc}"
            )

    lines = [
        "❌ NYC Taxi Pipeline Failed",
        "",
        f"DAG: {dag_id}",
        f"Task: {task_id}",
        f"Run: {run_id}",
    ]

    if data_month:
        lines.append(f"Data month: {data_month}")

    if exception:
        error_text = str(exception)
        if len(error_text) > 500:
            error_text = error_text[:497] + "..."
        lines.extend(["", f"Error: {error_text}"])

    if log_url:
        lines.extend(["", f"Airflow log: {log_url}"])

    _post_slack_message("\n".join(lines))


@dag(
    dag_id="nyc_taxi_monthly_ingestion",
    start_date=datetime(2026, 1, 1),
    schedule="0 19 * * 5",
    catchup=False,
    max_active_runs=1,
    default_args={
        "on_failure_callback": notify_slack_failure,
    },
    tags=["nyc-taxi", "ingestion"],
)
def nyc_taxi_monthly_ingestion():

    @task
    def process_next_month():
        return run_next_available_month()

    @task(pool="spark_ml_pool")
    def train_historical_model(ingestion_result: dict):
        if not ingestion_result["processed"]:
            print("No new TLC month was processed. Skipping historical training.")
            return {**ingestion_result, "trained": False}

        print("New TLC month processed. Starting historical model training.")
        spark = train_model()
        spark.stop()
        return {**ingestion_result, "trained": True}

    @task(pool="spark_ml_pool")
    def publish_historical_model(training_result: dict):
        if not training_result["trained"]:
            print("Historical training was skipped. Skipping historical publish.")
            return {**training_result, "published": False}

        publish_historical_model_data()
        return {**training_result, "published": True}

    @task(pool="spark_ml_pool")
    def train_future_forecast(ingestion_result: dict):
        if not ingestion_result["processed"]:
            print("No new TLC month was processed. Skipping future forecast training.")
            return {**ingestion_result, "trained": False}

        print("New TLC month processed. Starting future forecast training.")
        future_result = train_future_model()
        future_result["spark"].stop()
        return {**ingestion_result, "trained": True}

    @task(pool="spark_ml_pool")
    def publish_future_forecast(training_result: dict):
        if not training_result["trained"]:
            print("Future forecast training was skipped. Skipping future publish.")
            return {**training_result, "published": False}

        publish_future_forecast_data()
        return {**training_result, "published": True}

    @task
    def notify_slack_success(
        historical_result: dict,
        future_result: dict,
    ):
        if not historical_result["published"] and not future_result["published"]:
            print(
                "No new TLC month was processed. "
                "Slack success notification skipped."
            )
            return

        year = historical_result["year"]
        month = int(historical_result["month"])

        message = "\n".join(
            [
                "✅ NYC Taxi ML Retraining Completed",
                "",
                f"New data month: {year}-{month:02d}",
                "Historical model retrained and published successfully.",
                "Future forecast retrained and published successfully.",
            ]
        )

        _post_slack_message(message)

    ingestion_result = process_next_month()

    historical_training = train_historical_model(ingestion_result)
    historical_publish = publish_historical_model(historical_training)

    future_training = train_future_forecast(ingestion_result)
    future_publish = publish_future_forecast(future_training)

    notify_slack_success(historical_publish, future_publish)


nyc_taxi_monthly_ingestion()
