from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.sql import functions as F

from backend.src.features.build_future_features import (
    FUTURE_FEATURE_COLUMNS,
    add_historical_profile_features,
)
from backend.src.ingestion.spark_session import create_spark_session


def train_future_model():
    spark = create_spark_session()

    project_root = Path(__file__).resolve().parents[3]
    hourly_path = (
        project_root
        / "data"
        / "processed"
        / "hourly_demand"
    )

    hourly_demand = spark.read.parquet(
        str(hourly_path)
    )

    future_data = add_historical_profile_features(
        hourly_demand
    )

    latest_timestamp = (
        future_data
        .agg(
            F.max("pickup_hour").alias("latest")
        )
        .first()["latest"]
    )

    if latest_timestamp is None:
        raise RuntimeError(
            "No hourly demand data available."
        )

    test_start = latest_timestamp.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    model_data = future_data.dropna(
        subset=FUTURE_FEATURE_COLUMNS
    )

    train_data = model_data.filter(
        F.col("pickup_hour") < F.lit(test_start)
    )

    test_data = model_data.filter(
        F.col("pickup_hour") >= F.lit(test_start)
    )

    train_count = train_data.count()
    test_count = test_data.count()

    if train_count == 0 or test_count == 0:
        raise RuntimeError(
            "Future-model train/test split is empty."
        )

    print(
        f"Latest data timestamp: {latest_timestamp}"
    )
    print(
        f"Future-model test starts: {test_start}"
    )
    print(
        f"Training rows: {train_count:,}"
    )
    print(
        f"Test rows: {test_count:,}"
    )

    mae_evaluator = RegressionEvaluator(
        labelCol="demand",
        predictionCol="prediction",
        metricName="mae",
    )

    rmse_evaluator = RegressionEvaluator(
        labelCol="demand",
        predictionCol="prediction",
        metricName="rmse",
    )

    baseline_predictions = test_data.withColumn(
        "prediction",
        F.col("zone_dow_hour_mean"),
    )

    baseline_mae = mae_evaluator.evaluate(
        baseline_predictions
    )
    baseline_rmse = rmse_evaluator.evaluate(
        baseline_predictions
    )

    print(
        f"Future baseline MAE:  {baseline_mae:.2f}"
    )
    print(
        f"Future baseline RMSE: {baseline_rmse:.2f}"
    )

    assembler = VectorAssembler(
        inputCols=FUTURE_FEATURE_COLUMNS,
        outputCol="features",
    )

    rf = RandomForestRegressor(
        featuresCol="features",
        labelCol="demand",
        numTrees=100,
        maxDepth=10,
        seed=42,
    )

    pipeline = Pipeline(
        stages=[
            assembler,
            rf,
        ]
    )

    model = pipeline.fit(train_data)
    predictions = model.transform(test_data)

    rf_mae = mae_evaluator.evaluate(predictions)
    rf_rmse = rmse_evaluator.evaluate(predictions)

    print(
        f"Future Random Forest MAE:  {rf_mae:.2f}"
    )
    print(
        f"Future Random Forest RMSE: {rf_rmse:.2f}"
    )

    return {
        "spark": spark,
        "model": model,
        "predictions": predictions,
        "test_start": test_start,
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
        "rf_mae": rf_mae,
        "rf_rmse": rf_rmse,
    }


if __name__ == "__main__":
    result = train_future_model()
    result["spark"].stop()
