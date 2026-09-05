from datetime import date
from decimal import Decimal

from sqlalchemy import text

from backend.src.database.connection import engine


def _serialize_rows(result):
    rows = []

    for row in result:
        record = dict(row._mapping)

        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = float(value)

        rows.append(record)

    return rows


def get_demand_date_range():
    query = text(
        """
        SELECT
            MIN(pickup_date) AS min_date,
            MAX(pickup_date) AS max_date
        FROM taxi_analytics.fact_demand;
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query).one()
        return dict(row._mapping)


def get_zones():
    query = text(
        """
        SELECT
            location_id AS "LocationID",
            borough AS "Borough",
            zone AS "Zone",
            service_zone
        FROM taxi_analytics.dim_zone
        ORDER BY borough, zone;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)

        return _serialize_rows(result)


def get_zone_demand_over_time(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    query = text(
        """
        SELECT
            f.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone,
            f.pickup_date AS date,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_zone AS z
            ON f.location_id = z.location_id
        WHERE f.location_id = :location_id
          AND (
              :start_date IS NULL
              OR f.pickup_date >= :start_date
          )
          AND (
              :end_date IS NULL
              OR f.pickup_date <= :end_date
          )
        GROUP BY
            f.location_id,
            z.borough,
            z.zone,
            z.service_zone,
            f.pickup_date
        ORDER BY f.pickup_date;
        """
    )

    params = {
        "location_id": location_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    with engine.connect() as connection:
        result = connection.execute(
            query,
            params,
        )

        return _serialize_rows(result)


def get_zone_demand_by_hour(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    query = text(
        """
        SELECT
            f.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone,
            h.hour,
            AVG(f.demand) AS avg_demand,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_zone AS z
            ON f.location_id = z.location_id
        JOIN taxi_analytics.dim_hour AS h
            ON f.hour = h.hour
        WHERE f.location_id = :location_id
          AND (
              :start_date IS NULL
              OR f.pickup_date >= :start_date
          )
          AND (
              :end_date IS NULL
              OR f.pickup_date <= :end_date
          )
        GROUP BY
            f.location_id,
            z.borough,
            z.zone,
            z.service_zone,
            h.hour
        ORDER BY h.hour;
        """
    )

    params = {
        "location_id": location_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    with engine.connect() as connection:
        result = connection.execute(
            query,
            params,
        )

        return _serialize_rows(result)


def get_zone_demand_by_weekday(
    location_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
):
    query = text(
        """
        SELECT
            f.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone,
            d.weekday_number,
            d.weekday,
            AVG(f.demand) AS avg_demand,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_zone AS z
            ON f.location_id = z.location_id
        JOIN taxi_analytics.dim_date AS d
            ON f.pickup_date = d.full_date
        WHERE f.location_id = :location_id
          AND (
              :start_date IS NULL
              OR f.pickup_date >= :start_date
          )
          AND (
              :end_date IS NULL
              OR f.pickup_date <= :end_date
          )
        GROUP BY
            f.location_id,
            z.borough,
            z.zone,
            z.service_zone,
            d.weekday_number,
            d.weekday
        ORDER BY d.weekday_number;
        """
    )

    params = {
        "location_id": location_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    with engine.connect() as connection:
        result = connection.execute(
            query,
            params,
        )

        return _serialize_rows(result)


def get_demand_by_hour():
    query = text(
        """
        SELECT
            h.hour,
            AVG(f.demand) AS avg_demand,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_hour AS h
            ON f.hour = h.hour
        GROUP BY h.hour
        ORDER BY h.hour;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)
        return _serialize_rows(result)


def get_demand_by_weekday():
    query = text(
        """
        SELECT
            d.weekday_number,
            d.weekday,
            AVG(f.demand) AS avg_demand,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_date AS d
            ON f.pickup_date = d.full_date
        GROUP BY
            d.weekday_number,
            d.weekday
        ORDER BY d.weekday_number;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)
        return _serialize_rows(result)


def get_demand_over_time():
    query = text(
        """
        SELECT
            f.pickup_date AS date,
            SUM(f.demand) AS total_demand
        FROM taxi_analytics.fact_demand AS f
        GROUP BY f.pickup_date
        ORDER BY f.pickup_date;
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)
        return _serialize_rows(result)


def get_top_zones(limit: int = 10):
    query = text("""
        SELECT
            z.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone AS "service_zone",
            AVG(f.demand)::float AS avg_hourly_demand,
            SUM(f.demand)::bigint AS total_demand
        FROM taxi_analytics.fact_demand AS f
        JOIN taxi_analytics.dim_zone AS z
            ON f.location_id = z.location_id
        GROUP BY
            z.location_id,
            z.borough,
            z.zone,
            z.service_zone
        ORDER BY
            total_demand DESC
        LIMIT :limit
    """)

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {"limit": limit},
        )

        return _serialize_rows(result)
