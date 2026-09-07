# Orchestration

Apache Airflow automates the recurring data update. Its job is orchestration: it decides when ingestion and retraining should run, while the actual processing and modelling remain in backend modules.

## Update Workflow

The DAG follows this sequence:

```text
Read latest successfully processed month
                ↓
Check the next TLC month
                ↓
        Is data available?
          ↙           ↘
        No             Yes
        ↓               ↓
      No-op        Ingest + process
                        ↓
                  Retrain models
                        ↓
                  Publish outputs
```

The workflow is state-driven rather than tied to a hard-coded month. Each run checks the month after the latest successfully processed one. This allows the project to continue updating as TLC publishes new files.

Only one new month is processed per run. With Airflow `catchup=False`, missed scheduler runs do not create a backlog of historical DAG runs; the next active run continues from the persisted data state.

## Retraining Behaviour

Retraining occurs only after a new month has been successfully ingested. The shared ML workflow refreshes both:

1. historical model evaluation and its database outputs;
2. future-model backtesting, production-model selection and the serving forecast profile.

If the next TLC month is not available, the DAG finishes successfully without retraining.

## Notifications

Slack is used for operational feedback:

- successful ingestion followed by successful retraining and publication → success notification;
- task or pipeline failure → failure notification;
- successful no-op because no new TLC month exists → no notification.

The webhook is supplied through environment configuration and is never stored in the repository.

## Local Airflow

Airflow runs through Docker Compose with the API server, scheduler, DAG processor and PostgreSQL metadata database. The project uses LocalExecutor, so a separate Celery worker is not required.

Airflow should call the same backend workflows used for manual execution. This avoids maintaining separate implementations for automated and local runs.
