from pyspark.sql import SparkSession


def create_spark_session(app_name: str = "NYC Taxi Demand Forecasting"):
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.memory", "8g")
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )