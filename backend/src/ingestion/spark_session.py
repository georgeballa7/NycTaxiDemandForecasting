import os

os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")
os.environ.setdefault("SPARK_LOCAL_HOSTNAME", "localhost")

from pyspark.sql import SparkSession


def create_spark_session(app_name: str = "NYC Taxi Demand Forecasting"):
    """Create the locally configured Spark session used by the project.

    Parameters
    ----------
    app_name : str
        Name shown for the Spark application.

    Returns
    -------
    SparkSession
        Existing compatible Spark session or a newly created local session.

    Notes
    -----
    The session runs on local[8], binds the driver to localhost, assigns 8 GB
    of driver memory, extends network and heartbeat timeouts, and uses 200 SQL
    shuffle partitions.
    """
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[8]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.memory", "8g")
        .config("spark.network.timeout", "300s")
        .config(
            "spark.executor.heartbeatInterval",
            "30s",
        )
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )