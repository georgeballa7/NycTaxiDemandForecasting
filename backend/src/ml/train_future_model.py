from pathlib import Path

import pandas as pd
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

    model_data = future_data.dropna(
        subset=FUTURE_FEATURE_COLUMNS
    ).cache()

    test_months = [
        row["calendar_month"]
        for row in (
            model_data
            .select("calendar_month")
            .distinct()
            .orderBy(
                F.col("calendar_month").desc()
            )
            .limit(4)
            .collect()
        )
    ]
    test_months.sort()

    if not test_months:
        raise RuntimeError(
            "No test months available for rolling backtest."
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

    print(
        f"Latest data timestamp: {latest_timestamp}"
    )
    print(
        "Rolling backtest months: "
        + ", ".join(
            str(month)
            for month in test_months
        )
    )

    results = []

    for test_month in test_months:
        train_data = model_data.filter(
            F.col("calendar_month")
            < F.lit(test_month)
        )

        test_data = model_data.filter(
            F.col("calendar_month")
            == F.lit(test_month)
        )

        train_count = train_data.count()
        test_count = test_data.count()

        if train_count == 0 or test_count == 0:
            raise RuntimeError(
                f"Empty rolling split for {test_month}."
            )

        baseline_predictions = (
            test_data.withColumn(
                "prediction",
                F.col("zone_dow_hour_mean"),
            )
        )

        baseline_mae = mae_evaluator.evaluate(
            baseline_predictions
        )
        baseline_rmse = rmse_evaluator.evaluate(
            baseline_predictions
        )

        model = pipeline.fit(train_data)
        predictions = model.transform(test_data)

        rf_mae = mae_evaluator.evaluate(predictions)
        rf_rmse = rmse_evaluator.evaluate(predictions)

        results.append(
            {
                "test_month": str(test_month),
                "train_rows": train_count,
                "test_rows": test_count,
                "baseline_mae": baseline_mae,
                "baseline_rmse": baseline_rmse,
                "rf_mae": rf_mae,
                "rf_rmse": rf_rmse,
            }
        )

        print(
            f"\nTest month: {test_month}"
        )
        print(
            f"Training rows: {train_count:,}"
        )
        print(
            f"Test rows: {test_count:,}"
        )
        print(
            f"Baseline MAE:  {baseline_mae:.2f}"
        )
        print(
            f"Baseline RMSE: {baseline_rmse:.2f}"
        )
        print(
            f"Random Forest MAE:  {rf_mae:.2f}"
        )
        print(
            f"Random Forest RMSE: {rf_rmse:.2f}"
        )

    average_baseline_mae = sum(
        result["baseline_mae"]
        for result in results
    ) / len(results)

    average_baseline_rmse = sum(
        result["baseline_rmse"]
        for result in results
    ) / len(results)

    average_rf_mae = sum(
        result["rf_mae"]
        for result in results
    ) / len(results)

    average_rf_rmse = sum(
        result["rf_rmse"]
        for result in results
    ) / len(results)

    print("\nRolling backtest summary")
    print(
        f"Average baseline MAE:  "
        f"{average_baseline_mae:.2f}"
    )
    print(
        f"Average baseline RMSE: "
        f"{average_baseline_rmse:.2f}"
    )
    print(
        f"Average RF MAE:        "
        f"{average_rf_mae:.2f}"
    )
    print(
        f"Average RF RMSE:       "
        f"{average_rf_rmse:.2f}"
    )

    metrics_path = (
        project_root
        / "data"
        / "processed"
        / "future_model_backtest.csv"
    )

    metrics_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pd.DataFrame(results).to_csv(
        metrics_path,
        index=False,
    )

    print(
        f"Future-model backtest saved to: "
        f"{metrics_path}"
    )

    model_data.unpersist()

    return {
        "spark": spark,
        "results": results,
        "average_baseline_mae": average_baseline_mae,
        "average_baseline_rmse": average_baseline_rmse,
        "average_rf_mae": average_rf_mae,
        "average_rf_rmse": average_rf_rmse,
    }


if __name__ == "__main__":
    result = train_future_model()
    result["spark"].stop()
