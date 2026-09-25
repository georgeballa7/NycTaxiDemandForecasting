from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def complete_zone_hour_grid(
    hourly_demand: DataFrame,
    zones: DataFrame,
    start_date: str,
    end_date: str,
) -> DataFrame:
    """Create a complete hourly time grid for every NYC taxi zone.

    Parameters
    ----------
    hourly_demand : DataFrame
        Aggregated demand containing LocationID, pickup_hour, and demand.
    zones : DataFrame
        Taxi-zone lookup containing LocationID.
    start_date : str
        Inclusive first timestamp of the hourly grid.
    end_date : str
        Inclusive last timestamp of the hourly grid.

    Returns
    -------
    DataFrame
        Every LocationID/hour combination in the requested interval, joined
        with observed demand and filled with zero where no pickups occurred.
    """

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