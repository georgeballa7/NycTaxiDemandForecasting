from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def complete_zone_hour_grid(
    hourly_demand: DataFrame,
    zones: DataFrame,
    start_date: str,
    end_date: str,
) -> DataFrame:

    hours = hourly_demand.sparkSession.sql(
    f"""
    SELECT explode(
        sequence(
            CAST('{start_date}' AS TIMESTAMP_NTZ),
            CAST('{end_date}' AS TIMESTAMP_NTZ),
            INTERVAL 1 HOUR
        )
    ) AS pickup_hour
    """
)

    grid = (
        zones
        .select("LocationID")
        .crossJoin(hours)
    )

    return (
        grid
        .join(
            hourly_demand,
            ["LocationID", "pickup_hour"],
            "left"
        )
        .fillna({"demand": 0})
    )