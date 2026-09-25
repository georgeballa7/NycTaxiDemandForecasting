from backend.src.ml.publish_future_forecast import publish_future_forecast_data
from backend.src.ml.publish_historical_model import publish_historical_model_data
from backend.src.ml.train_future_model import train_future_model
from backend.src.ml.train_model import train_model


def run_ml_pipeline():
    """Run the complete historical and future ML workflow sequentially.

    Returns
    -------
    None
        Model artifacts and both serving snapshots are produced as side
        effects.

    Notes
    -----
    Historical training and publishing run first, followed by future-model
    backtesting and future-profile publishing. Spark sessions returned by
    each training function are stopped before the next stage.
    """
    print("Starting ML pipeline...")

    spark = train_model()
    spark.stop()

    publish_historical_model_data()

    future_result = train_future_model()
    future_result["spark"].stop()

    publish_future_forecast_data()

    print("ML pipeline completed successfully.")


if __name__ == "__main__":
    run_ml_pipeline()
