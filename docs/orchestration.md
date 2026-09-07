# Orchestration

Airflow controls when the backend workflows run; processing and modelling logic remain in backend modules.

## Monthly Update

```mermaid
flowchart TD
    A[Scheduled DAG run] --> B[Read latest successful dataset month]
    B --> C[Check next TLC month]
    C --> D{Available?}
    D -- No --> E[Successful no-op]
    D -- Yes --> F[Ingest & process]
    F --> G[Retrain & evaluate models]
    G --> H[Publish database outputs]
    H --> I[Slack success]
    F -. failure .-> J[Slack failure]
    G -. failure .-> J
    H -. failure .-> J
```

The workflow is state-driven, not hard-coded to a calendar month. It processes at most one new month per run. With `catchup=False`, missed scheduler runs do not create a backlog; a later run continues from the persisted pipeline state.

Retraining happens only after successful new-data ingestion. If TLC has not published the next month, the DAG succeeds without retraining or a Slack success message.

## Runtime

Local orchestration uses Docker Compose with the Airflow API server, scheduler, DAG processor and Airflow metadata PostgreSQL database. LocalExecutor is used, so no Celery worker is required.

The DAG calls the same backend workflows available for manual execution, avoiding a second implementation of the pipeline.
