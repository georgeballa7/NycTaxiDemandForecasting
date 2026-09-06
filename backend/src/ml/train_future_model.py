from pathlib import Path

import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import OneHotEncoder, StringIndexer, VectorAssembler
from pyspark.ml.regression import (
    GBTRegressor,
    LinearRegression,
    RandomForestRegressor,
)
from pyspark.sql import functions as F

from backend.src.features.build_future_features import FUTURE_FEATURE_COLUMNS, add_historical_profile_features
from backend.src.ingestion.spark_session import create_spark_session


MODEL_NAMES = [
    "zone_dow_hour_mean",
    "linear_regression",
    "random_forest",
    "gradient_boosted_trees",
]


def _build_pipeline(regressor):
    location_indexer = StringIndexer(
        inputCol="LocationID",
        outputCol="location_index",
        handleInvalid="keep",
    )
    location_encoder = OneHotEncoder(
        inputCol="location_index",
        outputCol="location_ohe",
        handleInvalid="keep",
    )
    assembler = VectorAssembler(
        inputCols=FUTURE_FEATURE_COLUMNS + ["location_ohe"],
        outputCol="features",
    )
    return Pipeline(stages=[location_indexer, location_encoder, assembler, regressor])


def _candidate_pipelines():
    return {
        "linear_regression": _build_pipeline(
            LinearRegression(
                featuresCol="features",
                labelCol="demand",
                predictionCol="prediction",
                regParam=0.1,
                elasticNetParam=0.0,
                maxIter=50,
            )
        ),
        "random_forest": _build_pipeline(
            RandomForestRegressor(
                featuresCol="features",
                labelCol="demand",
                predictionCol="prediction",
                numTrees=100,
                maxDepth=10,
                seed=42,
            )
        ),
        "gradient_boosted_trees": _build_pipeline(
            GBTRegressor(
                featuresCol="features",
                labelCol="demand",
                predictionCol="prediction",
                maxIter=50,
                maxDepth=6,
                stepSize=0.1,
                seed=42,
            )
        ),
    }


def train_future_model():
    spark = create_spark_session("NYC Taxi Future Model Selection")
    project_root = Path(__file__).resolve().parents[3]
    hourly_path = project_root / "data" / "processed" / "hourly_demand"

    hourly_demand = spark.read.parquet(str(hourly_path))
    future_data = add_historical_profile_features(hourly_demand)

    latest_timestamp = future_data.agg(F.max("pickup_hour").alias("latest")).first()["latest"]
    if latest_timestamp is None:
        raise RuntimeError("No hourly demand data available.")

    model_data = future_data.dropna(subset=FUTURE_FEATURE_COLUMNS).cache()
    test_months = [
        row["calendar_month"]
        for row in (
            model_data.select("calendar_month")
            .distinct()
            .orderBy(F.col("calendar_month").desc())
            .limit(4)
            .collect()
        )
    ]
    test_months.sort()
    if not test_months:
        raise RuntimeError("No test months available for rolling backtest.")

    mae_evaluator = RegressionEvaluator(
        labelCol="demand", predictionCol="prediction", metricName="mae"
    )
    rmse_evaluator = RegressionEvaluator(
        labelCol="demand", predictionCol="prediction", metricName="rmse"
    )

    print(f"Latest data timestamp: {latest_timestamp}")
    print("Rolling backtest months: " + ", ".join(str(month) for month in test_months))

    results = []
    pipelines = _candidate_pipelines()

    for test_month in test_months:
        train_data = model_data.filter(F.col("calendar_month") < F.lit(test_month)).cache()
        test_data = model_data.filter(F.col("calendar_month") == F.lit(test_month)).cache()
        train_count = train_data.count()
        test_count = test_data.count()
        if train_count == 0 or test_count == 0:
            raise RuntimeError(f"Empty rolling split for {test_month}.")

        row = {
            "test_month": str(test_month),
            "train_rows": train_count,
            "test_rows": test_count,
        }

        baseline_predictions = test_data.withColumn(
            "prediction", F.greatest(F.col("zone_dow_hour_mean"), F.lit(0.0))
        )
        row["zone_dow_hour_mean_mae"] = mae_evaluator.evaluate(baseline_predictions)
        row["zone_dow_hour_mean_rmse"] = rmse_evaluator.evaluate(baseline_predictions)

        for model_name, pipeline in pipelines.items():
            fitted = pipeline.fit(train_data)
            predictions = fitted.transform(test_data).withColumn(
                "prediction", F.greatest(F.col("prediction"), F.lit(0.0))
            )
            row[f"{model_name}_mae"] = mae_evaluator.evaluate(predictions)
            row[f"{model_name}_rmse"] = rmse_evaluator.evaluate(predictions)

        results.append(row)
        print(f"\nTest month: {test_month}")
        print(f"Training rows: {train_count:,}")
        print(f"Test rows: {test_count:,}")
        for model_name in MODEL_NAMES:
            print(
                f"{model_name}: MAE={row[f'{model_name}_mae']:.2f}, "
                f"RMSE={row[f'{model_name}_rmse']:.2f}"
            )

        train_data.unpersist()
        test_data.unpersist()

    summary = []
    for model_name in MODEL_NAMES:
        summary.append(
            {
                "model": model_name,
                "mae": sum(row[f"{model_name}_mae"] for row in results) / len(results),
                "rmse": sum(row[f"{model_name}_rmse"] for row in results) / len(results),
                "backtest_months": len(results),
            }
        )

    # MAE is the primary selection metric because it remains directly
    # interpretable as average hourly trip-demand error. RMSE breaks ties.
    winner = min(summary, key=lambda item: (item["mae"], item["rmse"]))
    production_model = winner["model"]

    print("\nRolling backtest summary")
    for item in summary:
        print(f"{item['model']}: MAE={item['mae']:.2f}, RMSE={item['rmse']:.2f}")
    print(f"Selected production model: {production_model}")

    metrics_path = project_root / "data" / "processed" / "future_model_backtest.csv"
    summary_path = project_root / "data" / "processed" / "future_model_summary.csv"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(metrics_path, index=False)
    pd.DataFrame(summary).to_csv(summary_path, index=False)

    model_data.unpersist()

    return {
        "spark": spark,
        "results": results,
        "summary": summary,
        "production_model": production_model,
        "latest_timestamp": latest_timestamp,
    }


if __name__ == "__main__":
    result = train_future_model()
    result["spark"].stop()
