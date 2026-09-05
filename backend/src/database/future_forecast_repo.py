import json

import pandas as pd
from sqlalchemy import text

from backend.src.database.connection import engine


_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS taxi_analytics.future_demand_profile (
    location_id INTEGER NOT NULL,
    day_of_week SMALLINT NOT NULL,
    hour SMALLINT NOT NULL,
    predicted_demand DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (location_id, day_of_week, hour),
    FOREIGN KEY (location_id)
        REFERENCES taxi_analytics.dim_zone (location_id),
    CHECK (day_of_week BETWEEN 1 AND 7),
    CHECK (hour BETWEEN 0 AND 23),
    CHECK (predicted_demand >= 0)
);

CREATE TABLE IF NOT EXISTS taxi_analytics.future_model_metric (
    model VARCHAR PRIMARY KEY,
    mae DOUBLE PRECISION NOT NULL,
    rmse DOUBLE PRECISION NOT NULL,
    backtest_months INTEGER NOT NULL,
    CHECK (backtest_months > 0)
);

CREATE TABLE IF NOT EXISTS taxi_analytics.future_forecast_metadata (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    production_model VARCHAR NOT NULL,
    trained_through TIMESTAMP NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    profile_dimensions JSONB NOT NULL,
    profile_rows INTEGER NOT NULL,
    CHECK (id = 1),
    CHECK (profile_rows >= 0)
);
"""


def ensure_future_forecast_tables(db_engine) -> None:
    with db_engine.begin() as connection:
        connection.execute(text(_CREATE_TABLES_SQL))


def replace_future_forecast_data(
    profiles: pd.DataFrame,
    metrics: pd.DataFrame,
    metadata: dict,
    db_engine,
) -> None:
    """Atomically replace the forecast serving snapshot in one database."""
    ensure_future_forecast_tables(db_engine)

    profile_rows = [
        {
            "location_id": int(row.LocationID),
            "day_of_week": int(row.day_of_week),
            "hour": int(row.hour),
            "predicted_demand": float(row.predicted_demand),
        }
        for row in profiles.itertuples(index=False)
    ]
    metric_rows = [
        {
            "model": str(row.model),
            "mae": float(row.mae),
            "rmse": float(row.rmse),
            "backtest_months": int(row.backtest_months),
        }
        for row in metrics.itertuples(index=False)
    ]

    with db_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM taxi_analytics.future_demand_profile")
        )
        connection.execute(
            text("DELETE FROM taxi_analytics.future_model_metric")
        )
        connection.execute(
            text("DELETE FROM taxi_analytics.future_forecast_metadata")
        )

        if profile_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO taxi_analytics.future_demand_profile (
                        location_id,
                        day_of_week,
                        hour,
                        predicted_demand
                    ) VALUES (
                        :location_id,
                        :day_of_week,
                        :hour,
                        :predicted_demand
                    )
                    """
                ),
                profile_rows,
            )

        if metric_rows:
            connection.execute(
                text(
                    """
                    INSERT INTO taxi_analytics.future_model_metric (
                        model,
                        mae,
                        rmse,
                        backtest_months
                    ) VALUES (
                        :model,
                        :mae,
                        :rmse,
                        :backtest_months
                    )
                    """
                ),
                metric_rows,
            )

        connection.execute(
            text(
                """
                INSERT INTO taxi_analytics.future_forecast_metadata (
                    id,
                    production_model,
                    trained_through,
                    generated_at,
                    profile_dimensions,
                    profile_rows
                ) VALUES (
                    1,
                    :production_model,
                    :trained_through,
                    :generated_at,
                    CAST(:profile_dimensions AS JSONB),
                    :profile_rows
                )
                """
            ),
            {
                "production_model": metadata["production_model"],
                "trained_through": metadata["trained_through"],
                "generated_at": metadata["generated_at"],
                "profile_dimensions": json.dumps(
                    metadata["profile_dimensions"]
                ),
                "profile_rows": int(metadata["profile_rows"]),
            },
        )


def get_future_model_metrics():
    query = text(
        """
        SELECT model, mae, rmse, backtest_months
        FROM taxi_analytics.future_model_metric
        ORDER BY model;
        """
    )

    with engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(query)]


def get_future_forecast_metadata():
    query = text(
        """
        SELECT
            production_model,
            trained_through,
            generated_at,
            profile_dimensions,
            profile_rows
        FROM taxi_analytics.future_forecast_metadata
        WHERE id = 1;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query).one_or_none()
        return dict(row._mapping) if row is not None else None


def get_future_prediction_profile(
    location_id: int,
    day_of_week: int,
    hour: int,
):
    query = text(
        """
        SELECT
            COUNT(*) AS profile_rows,
            MAX(
                CASE
                    WHEN day_of_week = :day_of_week AND hour = :hour
                    THEN predicted_demand
                END
            ) AS exact_demand,
            AVG(
                CASE
                    WHEN hour = :hour THEN predicted_demand
                END
            ) AS hour_demand,
            AVG(predicted_demand) AS zone_demand
        FROM taxi_analytics.future_demand_profile
        WHERE location_id = :location_id;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {
                "location_id": location_id,
                "day_of_week": day_of_week,
                "hour": hour,
            },
        ).one()
        return dict(row._mapping)
