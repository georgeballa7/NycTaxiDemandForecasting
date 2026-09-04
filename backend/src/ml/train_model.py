from datetime import datetime
from pathlib import Path
import pandas as pd

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.sql import functions as F

from backend.src.ingestion.spark_session import create_spark_session
from backend.src.persistence.load_parquet import load_parquet
from backend.src.persistence.save_parquet import save_parquet


FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "day_of_month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_mean_24h",
    "rolling_mean_168h",
]


def train_model():
    spark = create_spark_session("NYC Taxi Demand - ML")

    project_root = Path(__file__).resolve().parents[3]
    processed_path = project_root / "data" / "processed"

    # 1. Persistierte Features laden
    features = load_parquet(
        spark,
        processed_path / "features",
    )

    # 2. Nur Daten mit vollständiger 7-Tage-Historie
    model_data = (
        features
        .filter(F.col("history_count_168h") == 168)
        .withColumn("demand", F.col("demand").cast("double"))
    )

    # 3. Dynamischer zeitbasierter Split:
    # letzter vorhandener Monat = Testset
    latest_timestamp = (
        model_data
        .agg(F.max("pickup_hour").alias("latest"))
        .first()["latest"]
    )

    if latest_timestamp is None:
        raise RuntimeError("No feature data available for model training.")

    test_start = datetime(
        latest_timestamp.year,
        latest_timestamp.month,
        1,
    )

    print(f"Latest data timestamp: {latest_timestamp}")
    print(f"Test period starts:    {test_start:%Y-%m-%d}")

    train_data = model_data.filter(
        F.col("pickup_hour") < F.lit(test_start)
    )

    test_data = model_data.filter(
        F.col("pickup_hour") >= F.lit(test_start)
    )

    print(f"Training rows: {train_data.count():,}")
    print(f"Test rows:     {test_data.count():,}")

    # 4. Baseline: Nachfrage vor 24 Stunden
    baseline = test_data.withColumn(
        "prediction",
        F.col("lag_24h").cast("double"),
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

    baseline_mae = mae_evaluator.evaluate(baseline)
    baseline_rmse = rmse_evaluator.evaluate(baseline)

    print(f"Baseline MAE:  {baseline_mae:.2f}")
    print(f"Baseline RMSE: {baseline_rmse:.2f}")

    # 5. Spark ML erwartet einen Feature-Vektor
    assembler = VectorAssembler(
        inputCols=FEATURE_COLUMNS,
        outputCol="features_vector",
    )

    train_ml = assembler.transform(train_data)
    test_ml = assembler.transform(test_data)

    # 6. Random Forest
    rf = RandomForestRegressor(
        featuresCol="features_vector",
        labelCol="demand",
        predictionCol="prediction",
        numTrees=100,
        maxDepth=10,
        seed=42,
    )

    rf_model = rf.fit(train_ml)

    importance_df = pd.DataFrame({
        "feature": FEATURE_COLUMNS,
        "importance": rf_model.featureImportances.toArray(),
    }).sort_values(
        "importance",
        ascending=False,
    )

    importance_output_path = processed_path / "feature_importance.csv"

    importance_df.to_csv(
        importance_output_path,
        index=False,
    )

    print(f"Feature importances saved to: {importance_output_path}")

    # 7. Vorhersagen
    predictions = rf_model.transform(test_ml)

    rf_mae = mae_evaluator.evaluate(predictions)
    rf_rmse = rmse_evaluator.evaluate(predictions)

    print(f"Random Forest MAE:  {rf_mae:.2f}")
    print(f"Random Forest RMSE: {rf_rmse:.2f}")

    metrics_df = pd.DataFrame(
        [
            {
                "model": "24h Persistence Baseline",
                "mae": baseline_mae,
                "rmse": baseline_rmse,
            },
            {
                "model": "Random Forest",
                "mae": rf_mae,
                "rmse": rf_rmse,
            },
        ]
    )

    metrics_output_path = processed_path / "model_metrics.csv"

    metrics_df.to_csv(
        metrics_output_path,
        index=False,
    )

    print(f"Model metrics saved to: {metrics_output_path}")

    # 8. Nur App-relevante Ergebnisse persistieren
    prediction_output = predictions.select(
        "LocationID",
        "pickup_hour",
        "demand",
        "prediction",
    )

    save_parquet(
        prediction_output,
        processed_path / "predictions",
    )

    model_path = processed_path / "models" / "random_forest"

    rf_model.write().overwrite().save(str(model_path))

    print(f"Model saved to: {model_path}")

    return spark


if __name__ == "__main__":
    spark = train_model()
    spark.stop()
