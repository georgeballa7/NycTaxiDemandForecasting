from sqlalchemy import text

from backend.src.database.connection import engine


_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS taxi_analytics.historical_model_metric (
    model VARCHAR PRIMARY KEY,
    mae DOUBLE PRECISION NOT NULL,
    rmse DOUBLE PRECISION NOT NULL,
    trained_through TIMESTAMP NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS taxi_analytics.historical_feature_importance (
    feature VARCHAR PRIMARY KEY,
    importance DOUBLE PRECISION NOT NULL,
    trained_through TIMESTAMP NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    CHECK (importance >= 0)
);

CREATE TABLE IF NOT EXISTS taxi_analytics.historical_model_prediction (
    location_id INTEGER NOT NULL,
    pickup_hour TIMESTAMP NOT NULL,
    actual_demand DOUBLE PRECISION NOT NULL,
    predicted_demand DOUBLE PRECISION NOT NULL,
    trained_through TIMESTAMP NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (location_id, pickup_hour),
    FOREIGN KEY (location_id)
        REFERENCES taxi_analytics.dim_zone (location_id),
    CHECK (actual_demand >= 0),
    CHECK (predicted_demand >= 0)
);
"""


def ensure_historical_model_tables(db_engine) -> None:
    with db_engine.begin() as connection:
        connection.execute(text(_CREATE_TABLES_SQL))


def replace_historical_model_data(
    metrics,
    feature_importance,
    predictions,
    trained_through,
    generated_at,
    db_engine,
) -> None:
    """Atomically replace the historical model serving snapshot."""
    ensure_historical_model_tables(db_engine)

    metric_rows = [
        {
            "model": str(row.model),
            "mae": float(row.mae),
            "rmse": float(row.rmse),
            "trained_through": trained_through,
            "generated_at": generated_at,
        }
        for row in metrics.itertuples(index=False)
    ]

    importance_rows = [
        {
            "feature": str(row.feature),
            "importance": float(row.importance),
            "trained_through": trained_through,
            "generated_at": generated_at,
        }
        for row in feature_importance.itertuples(index=False)
    ]

    prediction_rows = [
        {
            "location_id": int(row.LocationID),
            "pickup_hour": row.pickup_hour,
            "actual_demand": float(row.actual_demand),
            "predicted_demand": float(row.predicted_demand),
            "trained_through": trained_through,
            "generated_at": generated_at,
        }
        for row in predictions.itertuples(index=False)
    ]

    with db_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM taxi_analytics.historical_model_prediction")
        )
        connection.execute(
            text("DELETE FROM taxi_analytics.historical_feature_importance")
        )
        connection.execute(
            text("DELETE FROM taxi_analytics.historical_model_metric")
        )

        if metric_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO taxi_analytics.historical_model_metric (
                        model, mae, rmse, trained_through, generated_at
                    ) VALUES (
                        :model, :mae, :rmse, :trained_through, :generated_at
                    )
                    """
                ),
                metric_rows,
            )

        if importance_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO taxi_analytics.historical_feature_importance (
                        feature, importance, trained_through, generated_at
                    ) VALUES (
                        :feature, :importance, :trained_through, :generated_at
                    )
                    """
                ),
                importance_rows,
            )

        if prediction_rows:
            statement = text(
                """
                INSERT INTO taxi_analytics.historical_model_prediction (
                    location_id,
                    pickup_hour,
                    actual_demand,
                    predicted_demand,
                    trained_through,
                    generated_at
                ) VALUES (
                    :location_id,
                    :pickup_hour,
                    :actual_demand,
                    :predicted_demand,
                    :trained_through,
                    :generated_at
                )
                """
            )
            batch_size = 5000
            for start in range(0, len(prediction_rows), batch_size):
                connection.execute(
                    statement,
                    prediction_rows[start:start + batch_size],
                )


def get_historical_model_metrics():
    query = text(
        """
        SELECT model, mae, rmse
        FROM taxi_analytics.historical_model_metric
        ORDER BY model;
        """
    )
    with engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(query)]


def get_historical_feature_importance():
    query = text(
        """
        SELECT feature, importance
        FROM taxi_analytics.historical_feature_importance
        ORDER BY importance DESC, feature;
        """
    )
    with engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(query)]


def get_historical_predictions(
    location_id: int,
    start_date=None,
    end_date=None,
):
    query = text(
        """
        SELECT
            p.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone,
            p.pickup_hour,
            p.actual_demand,
            p.predicted_demand
        FROM taxi_analytics.historical_model_prediction AS p
        JOIN taxi_analytics.dim_zone AS z
          ON z.location_id = p.location_id
        WHERE p.location_id = :location_id
          AND (:start_date IS NULL OR p.pickup_hour::date >= :start_date)
          AND (:end_date IS NULL OR p.pickup_hour::date <= :end_date)
        ORDER BY p.pickup_hour;
        """
    )
    with engine.connect() as connection:
        return [
            dict(row._mapping)
            for row in connection.execute(
                query,
                {
                    "location_id": location_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        ]
