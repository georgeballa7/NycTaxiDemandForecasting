import pandas as pd

from backend.src.config.settings import (
    APP_DATA_DIR,
    DATABASE_SCHEMA,
)
from backend.src.database.connection import engine


def load_demanddata_to_postgres():
    # --------------------------------------------------
    # Paths
    # --------------------------------------------------

    zones_path = APP_DATA_DIR / "zones.parquet"

    demand_path = (
        APP_DATA_DIR
        / "eda"
        / "zone_hour_daily.parquet"
    )

    # --------------------------------------------------
    # Load source data
    # --------------------------------------------------

    zones_df = pd.read_parquet(zones_path)

    demand_df = pd.read_parquet(demand_path)

    demand_df["date"] = pd.to_datetime(
        demand_df["date"]
    )

    # --------------------------------------------------
    # dim_zone
    # --------------------------------------------------

    dim_zone = (
        zones_df[
            [
                "LocationID",
                "Borough",
                "Zone",
                "service_zone",
            ]
        ]
        .rename(
            columns={
                "LocationID": "location_id",
                "Borough": "borough",
                "Zone": "zone",
            }
        )
        .drop_duplicates(
            subset=["location_id"]
        )
        .sort_values("location_id")
    )

    # --------------------------------------------------
    # dim_date
    # --------------------------------------------------

    dim_date = (
        demand_df[
            [
                "date",
                "weekday_number",
                "weekday",
            ]
        ]
        .drop_duplicates(
            subset=["date"]
        )
        .rename(
            columns={
                "date": "full_date",
            }
        )
        .sort_values("full_date")
    )

    dim_date["year"] = (
        dim_date["full_date"].dt.year
    )

    dim_date["month"] = (
        dim_date["full_date"].dt.month
    )

    dim_date["month_name"] = (
        dim_date["full_date"].dt.month_name()
    )

    dim_date["day"] = (
        dim_date["full_date"].dt.day
    )

    dim_date["is_weekend"] = (
        dim_date["weekday_number"]
        .isin([6, 7])
    )

    dim_date = dim_date[
        [
            "full_date",
            "year",
            "month",
            "month_name",
            "day",
            "weekday_number",
            "weekday",
            "is_weekend",
        ]
    ]

    # PostgreSQL DATE instead of Timestamp
    dim_date["full_date"] = (
        dim_date["full_date"].dt.date
    )

    # --------------------------------------------------
    # dim_hour
    # --------------------------------------------------

    dim_hour = pd.DataFrame(
        {
            "hour": list(range(24))
        }
    )

    def get_day_part(hour):
        if 0 <= hour <= 5:
            return "Night"

        if 6 <= hour <= 11:
            return "Morning"

        if 12 <= hour <= 17:
            return "Afternoon"

        return "Evening"

    dim_hour["day_part"] = (
        dim_hour["hour"]
        .apply(get_day_part)
    )

    # --------------------------------------------------
    # fact_demand
    # --------------------------------------------------

    fact_demand = (
        demand_df[
            [
                "LocationID",
                "date",
                "hour",
                "demand",
            ]
        ]
        .rename(
            columns={
                "LocationID": "location_id",
                "date": "pickup_date",
            }
        )
    )

    fact_demand["pickup_date"] = (
        fact_demand["pickup_date"].dt.date
    )

    # --------------------------------------------------
    # Load PostgreSQL tables
    # --------------------------------------------------

    with engine.begin() as connection:

        print("Loading dim_zone...")

        dim_zone.to_sql(
            name="dim_zone",
            con=connection,
            schema=DATABASE_SCHEMA,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        print("Loading dim_date...")

        dim_date.to_sql(
            name="dim_date",
            con=connection,
            schema=DATABASE_SCHEMA,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        print("Loading dim_hour...")

        dim_hour.to_sql(
            name="dim_hour",
            con=connection,
            schema=DATABASE_SCHEMA,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        print("Loading fact_demand...")

        fact_demand.to_sql(
            name="fact_demand",
            con=connection,
            schema=DATABASE_SCHEMA,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print()
    print("Demand data loaded successfully.")
    print(f"Zones:      {len(dim_zone):,}")
    print(f"Dates:      {len(dim_date):,}")
    print(f"Hours:      {len(dim_hour):,}")
    print(f"Fact rows:  {len(fact_demand):,}")


if __name__ == "__main__":
    load_demanddata_to_postgres()