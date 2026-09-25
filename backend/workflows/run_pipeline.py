from backend.workflows.data_pipeline import run_data_pipeline
from backend.workflows.ml_pipeline import run_ml_pipeline


def run_pipeline():
    """Run the project's full data pipeline followed by the full ML pipeline.

    Returns
    -------
    None
        Processed data, database tables, model artifacts and serving
        snapshots are produced by the delegated workflows.
    """
    print("Starting full NYC Taxi pipeline...")

    run_data_pipeline()
    run_ml_pipeline()

    print("Full pipeline completed successfully.")


if __name__ == "__main__":
    run_pipeline()