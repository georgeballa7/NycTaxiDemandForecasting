from backend.src.ml.prepare_app_data import prepare_app_data
from backend.src.ml.train_model import train_model


def run_ml_pipeline():
    print("Starting ML pipeline...")

    spark = train_model()
    spark.stop()

    prepare_app_data()

    print("ML pipeline completed successfully.")


if __name__ == "__main__":
    run_ml_pipeline()
