from sqlalchemy import text

from backend.src.database.connection import engine
from backend.workflows.build_business_trips import build_business_trips
from backend.workflows.build_dataset import build_dataset
from backend.workflows.load_businessdata_to_postgres import main as load_businessdata_to_postgres
from backend.workflows.load_demanddata_to_postgres import load_demanddata_to_postgres
from backend.workflows.prepare_eda_data import prepare_eda_data


def reset_analytics_schema():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    taxi_analytics.fact_demand,
                    taxi_analytics.fact_trips,
                    taxi_analytics.dim_payment,
                    taxi_analytics.dim_hour,
                    taxi_analytics.dim_date,
                    taxi_analytics.dim_zone;
                """
            )
        )


def run_data_pipeline():
    build_dataset()
    build_business_trips()
    prepare_eda_data()

    reset_analytics_schema()

    load_demanddata_to_postgres()
    load_businessdata_to_postgres()


if __name__ == "__main__":
    run_data_pipeline()