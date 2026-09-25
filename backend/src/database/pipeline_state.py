from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.src.config.settings import DATABASE_SCHEMA


BASELINE_MONTH = date(2025, 6, 1)


def ensure_pipeline_runs_table(db_engine: Engine) -> None:
    """Create the pipeline-run state table when it does not already exist.

    Parameters
    ----------
    db_engine : Engine
        SQLAlchemy engine for the target PostgreSQL database.

    Returns
    -------
    None
        Schema creation is committed as a side effect.
    """
    with db_engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {DATABASE_SCHEMA}.pipeline_runs (
                    dataset_month DATE PRIMARY KEY,
                    source_file VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    error_message TEXT,
                    CONSTRAINT chk_pipeline_status
                        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED'))
                );
                """
            )
        )


def get_last_successful_month(db_engine: Engine) -> date:
    """Return the latest successfully processed dataset month.

    Parameters
    ----------
    db_engine : Engine
        SQLAlchemy engine containing pipeline state.

    Returns
    -------
    date
        Maximum SUCCESS dataset_month, or the June 2025 baseline when no
        successful state has yet been recorded.
    """
    ensure_pipeline_runs_table(db_engine)

    with db_engine.connect() as connection:
        result = connection.execute(
            text(
                f"""
                SELECT MAX(dataset_month)
                FROM {DATABASE_SCHEMA}.pipeline_runs
                WHERE status = 'SUCCESS';
                """
            )
        ).scalar()

    return result or BASELINE_MONTH


def mark_running(
    db_engine: Engine,
    dataset_month: date,
    source_file: str,
) -> None:
    """Mark a dataset month as currently running.

    Parameters
    ----------
    db_engine : Engine
        Target database engine.
    dataset_month : date
        First day identifying the processed dataset month.
    source_file : str
        TLC source filename associated with the run.

    Returns
    -------
    None
        State is inserted or reset to RUNNING atomically.
    """
    ensure_pipeline_runs_table(db_engine)
    now = datetime.now(timezone.utc)

    with db_engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {DATABASE_SCHEMA}.pipeline_runs (
                    dataset_month,
                    source_file,
                    status,
                    started_at,
                    completed_at,
                    error_message
                )
                VALUES (
                    :dataset_month,
                    :source_file,
                    'RUNNING',
                    :started_at,
                    NULL,
                    NULL
                )
                ON CONFLICT (dataset_month)
                DO UPDATE SET
                    source_file = EXCLUDED.source_file,
                    status = 'RUNNING',
                    started_at = EXCLUDED.started_at,
                    completed_at = NULL,
                    error_message = NULL;
                """
            ),
            {
                "dataset_month": dataset_month,
                "source_file": source_file,
                "started_at": now,
            },
        )


def mark_success(
    db_engine: Engine,
    dataset_month: date,
    source_file: str,
) -> None:
    """Persist SUCCESS state for a completed dataset month.

    Parameters
    ----------
    db_engine : Engine
        Target database engine.
    dataset_month : date
        Dataset month being completed.
    source_file : str
        TLC source filename associated with the run.
    """
    _mark_finished(
        db_engine,
        dataset_month,
        source_file,
        "SUCCESS",
        None,
    )


def mark_failed(
    db_engine: Engine,
    dataset_month: date,
    source_file: str,
    error_message: str,
) -> None:
    """Persist FAILED state and a bounded error message for a dataset month.

    Parameters
    ----------
    db_engine : Engine
        Target database engine.
    dataset_month : date
        Dataset month that failed.
    source_file : str
        TLC source filename associated with the run.
    error_message : str
        Failure description; at most 4,000 characters are persisted.
    """
    _mark_finished(
        db_engine,
        dataset_month,
        source_file,
        "FAILED",
        error_message[:4000],
    )


def _mark_finished(
    db_engine: Engine,
    dataset_month: date,
    source_file: str,
    status: str,
    error_message: str | None,
) -> None:
    """Insert or update the terminal state of a pipeline run.

    Parameters
    ----------
    db_engine : Engine
        Target database engine.
    dataset_month : date
        Dataset month being finalized.
    source_file : str
        TLC source filename.
    status : str
        Terminal pipeline status, expected to be SUCCESS or FAILED.
    error_message : str or None
        Optional persisted failure description.

    Returns
    -------
    None
        State and UTC completion timestamp are written transactionally.
    """
    ensure_pipeline_runs_table(db_engine)
    now = datetime.now(timezone.utc)

    with db_engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {DATABASE_SCHEMA}.pipeline_runs (
                    dataset_month,
                    source_file,
                    status,
                    started_at,
                    completed_at,
                    error_message
                )
                VALUES (
                    :dataset_month,
                    :source_file,
                    :status,
                    :completed_at,
                    :completed_at,
                    :error_message
                )
                ON CONFLICT (dataset_month)
                DO UPDATE SET
                    source_file = EXCLUDED.source_file,
                    status = EXCLUDED.status,
                    completed_at = EXCLUDED.completed_at,
                    error_message = EXCLUDED.error_message;
                """
            ),
            {
                "dataset_month": dataset_month,
                "source_file": source_file,
                "status": status,
                "completed_at": now,
                "error_message": error_message,
            },
        )
