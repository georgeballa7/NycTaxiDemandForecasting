from datetime import date

from backend.src.config.settings import RAW_DATA_DIR
from backend.src.database.connection import engine, supabase_engine
from backend.src.database.pipeline_state import (
    get_last_successful_month,
    mark_failed,
    mark_running,
    mark_success,
)
from backend.src.ingestion.download_tlc_data import download_yellow_taxi_month
from backend.src.ingestion.tlc_availability import (
    build_yellow_taxi_url,
    is_month_available,
    next_month,
)
from backend.workflows.data_pipeline import run_monthly_data_pipeline


def _month_date(year: int, month: int) -> date:
    return date(year, month, 1)


def _source_filename(year: int, month: int) -> str:
    return f"yellow_tripdata_{year}-{month:02d}.parquet"


def _state_engines():
    engines = [engine]
    if supabase_engine is not None:
        engines.append(supabase_engine)
    return engines


def _mark_all_running(dataset_month: date, source_file: str) -> None:
    for db_engine in _state_engines():
        mark_running(db_engine, dataset_month, source_file)


def _mark_all_success(dataset_month: date, source_file: str) -> None:
    for db_engine in _state_engines():
        mark_success(db_engine, dataset_month, source_file)


def _mark_all_failed(
    dataset_month: date,
    source_file: str,
    error_message: str,
) -> None:
    for db_engine in _state_engines():
        try:
            mark_failed(
                db_engine,
                dataset_month,
                source_file,
                error_message,
            )
        except Exception as state_error:
            print(
                "Could not persist FAILED pipeline state: "
                f"{state_error}"
            )


def process_month(year: int, month: int) -> bool:
    """Download, process and load exactly one available TLC month."""

    if not is_month_available(year, month):
        print(
            f"TLC Yellow Taxi {year}-{month:02d} is not available yet."
        )
        return False

    dataset_month = _month_date(year, month)
    source_file = _source_filename(year, month)

    _mark_all_running(dataset_month, source_file)

    try:
        download_yellow_taxi_month(
            year=year,
            month=month,
            raw_data_path=RAW_DATA_DIR,
        )

        run_monthly_data_pipeline(year, month)

        _mark_all_success(dataset_month, source_file)

    except Exception as exc:
        _mark_all_failed(
            dataset_month,
            source_file,
            str(exc),
        )
        raise

    print(f"Monthly ingestion succeeded: {year}-{month:02d}")
    return True


def run_next_available_month() -> dict:
    """Process at most one month after the last successful local month."""

    last_success = get_last_successful_month(engine)
    year, month = next_month(
        last_success.year,
        last_success.month,
    )

    print(
        f"Last successful month: {last_success:%Y-%m}; "
        f"checking {year}-{month:02d}."
    )

    processed = process_month(year, month)

    return {
        "year": year,
        "month": month,
        "processed": processed,
        "source_url": build_yellow_taxi_url(year, month),
    }


def run_backfill(
    start_year: int = 2025,
    start_month: int = 7,
    end_year: int | None = None,
    end_month: int | None = None,
) -> list[str]:
    """Sequentially process available months, stopping on failure/unavailable."""

    if (end_year is None) != (end_month is None):
        raise ValueError(
            "end_year and end_month must either both be provided or omitted."
        )

    year, month = start_year, start_month
    processed_months = []

    while True:
        if end_year is not None and end_month is not None:
            if (year, month) > (end_year, end_month):
                break

        if not is_month_available(year, month):
            print(
                f"Backfill stopped: {year}-{month:02d} "
                "is not available from TLC."
            )
            break

        process_month(year, month)
        processed_months.append(f"{year}-{month:02d}")
        year, month = next_month(year, month)

    return processed_months
