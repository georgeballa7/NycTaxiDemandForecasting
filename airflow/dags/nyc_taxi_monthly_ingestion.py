from datetime import datetime
import json
import os
from urllib import request

from airflow.sdk import dag, task

from backend.workflows.monthly_ingestion import run_next_available_month
from backend.workflows.ml_pipeline import run_ml_pipeline


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
    schedule="@daily",
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

    @task
    def notify_slack_success(retraining_result: dict):
        if not retraining_result["retrained"]:
            print(
                "No retraining occurred. "
                "Slack success notification skipped."
            )
            return

        year = retraining_result["year"]
        month = int(retraining_result["month"])

        message = "\n".join(
            [
                "✅ NYC Taxi ML Retraining Completed",
                "",
                f"New data month: {year}-{month:02d}",
                "Historical model retrained successfully.",
                "Future forecast pipeline refreshed.",
                "",
                "Action required:",
                "Review and commit refreshed data/app artifacts.",
            ]
        )

        _post_slack_message(message)

    ingestion_result = process_next_month()
    retraining_result = retrain_model(ingestion_result)
    notify_slack_success(retraining_result)


nyc_taxi_monthly_ingestion()
