from sqlalchemy import text

from backend.src.database.connection import engine


def get_business_summary():
    query = text("""
        SELECT
            SUM(trip_count)::bigint AS total_trips,
            ROUND(SUM(fare_amount), 2) AS total_fare_amount,
            ROUND(SUM(total_amount), 2) AS total_amount,
            ROUND(SUM(tip_amount), 2) AS total_tip_amount,
            ROUND(
                SUM(trip_distance) / NULLIF(SUM(trip_count), 0),
                2
            ) AS avg_trip_distance
        FROM taxi_business.fact_trips;
    """)

    with engine.connect() as connection:
        row = connection.execute(query).mappings().one()

    return {
        "total_trips": row["total_trips"],
        "total_fare_amount": float(row["total_fare_amount"]),
        "total_amount": float(row["total_amount"]),
        "total_tip_amount": float(row["total_tip_amount"]),
        "avg_trip_distance": float(row["avg_trip_distance"]),
    }





def get_revenue_over_time():
    query = text("""
        SELECT
            pickup_date,
            SUM(trip_count)::bigint AS total_trips,
            ROUND(SUM(fare_amount), 2) AS fare_amount,
            ROUND(SUM(total_amount), 2) AS total_amount,
            ROUND(SUM(tip_amount), 2) AS tip_amount
        FROM taxi_business.fact_trips
        GROUP BY pickup_date
        ORDER BY pickup_date;
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        return [
            {
                "pickup_date": row["pickup_date"],
                "total_trips": row["total_trips"],
                "fare_amount": float(row["fare_amount"]),
                "total_amount": float(row["total_amount"]),
                "tip_amount": float(row["tip_amount"]),
            }
            for row in result.mappings()
        ]



def get_revenue_by_zone(limit: int = 10):
    query = text("""
        SELECT
            f.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            z.service_zone,
            SUM(f.trip_count)::bigint AS total_trips,
            ROUND(SUM(f.fare_amount), 2) AS fare_amount,
            ROUND(SUM(f.total_amount), 2) AS total_amount,
            ROUND(
                SUM(f.fare_amount)
                / NULLIF(SUM(f.trip_count), 0),
                2
            ) AS avg_fare_per_trip
        FROM taxi_business.fact_trips AS f
        JOIN taxi_demand.dim_zone AS z
            ON f.location_id = z.location_id
        GROUP BY
            f.location_id,
            z.borough,
            z.zone,
            z.service_zone
        ORDER BY fare_amount DESC
        LIMIT :limit;
    """)

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {"limit": limit},
        )

        return [
            {
                "LocationID": row["LocationID"],
                "Borough": row["Borough"],
                "Zone": row["Zone"],
                "service_zone": row["service_zone"],
                "total_trips": row["total_trips"],
                "fare_amount": float(row["fare_amount"]),
                "total_amount": float(row["total_amount"]),
                "avg_fare_per_trip": float(row["avg_fare_per_trip"]),
            }
            for row in result.mappings()
        ]



def get_payment_breakdown():
    query = text("""
        SELECT
            f.payment_type,
            p.payment_method,
            SUM(f.trip_count)::bigint AS total_trips,
            ROUND(SUM(f.fare_amount), 2) AS fare_amount,
            ROUND(SUM(f.total_amount), 2) AS total_amount,
            ROUND(SUM(f.tip_amount), 2) AS tip_amount,
            ROUND(
                100.0 * SUM(f.trip_count)
                / NULLIF(
                    SUM(SUM(f.trip_count)) OVER (),
                    0
                ),
                2
            ) AS trip_share_pct
        FROM taxi_business.fact_trips AS f
        JOIN taxi_business.dim_payment AS p
            ON f.payment_type = p.payment_type
        GROUP BY
            f.payment_type,
            p.payment_method
        ORDER BY total_trips DESC;
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        return [
            {
                "payment_type": row["payment_type"],
                "payment_method": row["payment_method"],
                "total_trips": row["total_trips"],
                "fare_amount": float(row["fare_amount"]),
                "total_amount": float(row["total_amount"]),
                "tip_amount": float(row["tip_amount"]),
                "trip_share_pct": float(row["trip_share_pct"]),
            }
            for row in result.mappings()
        ]




def get_tip_analysis():
    query = text("""
        SELECT
            ROUND(SUM(tip_amount), 2) AS total_tips,
            ROUND(
                SUM(tip_amount)
                / NULLIF(SUM(trip_count), 0),
                2
            ) AS avg_tip_per_trip,
            ROUND(
                100.0 * SUM(tip_amount)
                / NULLIF(SUM(fare_amount), 0),
                2
            ) AS tip_to_fare_pct,
            SUM(trip_count)::bigint AS total_credit_card_trips
        FROM taxi_business.fact_trips
        WHERE payment_type = 1;
    """)

    with engine.connect() as connection:
        row = connection.execute(query).mappings().one()

    return {
        "total_tips": float(row["total_tips"]),
        "avg_tip_per_trip": float(row["avg_tip_per_trip"]),
        "tip_to_fare_pct": float(row["tip_to_fare_pct"]),
        "total_credit_card_trips": row["total_credit_card_trips"],
    }


def get_tip_analysis_by_zone(limit: int = 10):
    query = text("""
        SELECT
            f.location_id AS "LocationID",
            z.borough AS "Borough",
            z.zone AS "Zone",
            SUM(f.trip_count)::bigint AS total_credit_card_trips,
            ROUND(SUM(f.tip_amount), 2) AS total_tips,
            ROUND(
                SUM(f.tip_amount)
                / NULLIF(SUM(f.trip_count), 0),
                2
            ) AS avg_tip_per_trip,
            ROUND(
                100.0 * SUM(f.tip_amount)
                / NULLIF(SUM(f.fare_amount), 0),
                2
            ) AS tip_to_fare_pct
        FROM taxi_business.fact_trips AS f
        JOIN taxi_demand.dim_zone AS z
            ON f.location_id = z.location_id
        WHERE f.payment_type = 1
        GROUP BY
            f.location_id,
            z.borough,
            z.zone
        ORDER BY total_tips DESC
        LIMIT :limit;
    """)

    with engine.connect() as connection:
        result = connection.execute(
            query,
            {"limit": limit},
        )

        return [
            {
                "LocationID": row["LocationID"],
                "Borough": row["Borough"],
                "Zone": row["Zone"],
                "total_credit_card_trips":
                    row["total_credit_card_trips"],
                "total_tips": float(row["total_tips"]),
                "avg_tip_per_trip":
                    float(row["avg_tip_per_trip"]),
                "tip_to_fare_pct":
                    float(row["tip_to_fare_pct"]),
            }
            for row in result.mappings()
        ]


def get_trip_distance_analysis():
    query = text("""
        SELECT
            CASE
                WHEN trip_distance < 2 THEN '0-2 miles'
                WHEN trip_distance < 5 THEN '2-5 miles'
                WHEN trip_distance < 10 THEN '5-10 miles'
                WHEN trip_distance < 20 THEN '10-20 miles'
                ELSE '20+ miles'
            END AS distance_band,

            CASE
                WHEN trip_distance < 2 THEN 1
                WHEN trip_distance < 5 THEN 2
                WHEN trip_distance < 10 THEN 3
                WHEN trip_distance < 20 THEN 4
                ELSE 5
            END AS distance_order,

            SUM(trip_count)::bigint AS total_trips,

            ROUND(
                SUM(fare_amount)
                / NULLIF(SUM(trip_count), 0),
                2
            ) AS avg_fare_per_trip,

            ROUND(
                SUM(total_amount)
                / NULLIF(SUM(trip_count), 0),
                2
            ) AS avg_total_per_trip,

            ROUND(
                SUM(tip_amount)
                / NULLIF(SUM(trip_count), 0),
                2
            ) AS avg_recorded_tip_per_trip

        FROM taxi_business.fact_trips

        GROUP BY
            distance_band,
            distance_order

        ORDER BY distance_order;
    """)

    with engine.connect() as connection:
        result = connection.execute(query)

        return [
            {
                "distance_band": row["distance_band"],
                "distance_order": row["distance_order"],
                "total_trips": row["total_trips"],
                "avg_fare_per_trip":
                    float(row["avg_fare_per_trip"]),
                "avg_total_per_trip":
                    float(row["avg_total_per_trip"]),
                "avg_recorded_tip_per_trip":
                    float(row["avg_recorded_tip_per_trip"]),
            }
            for row in result.mappings()
        ]