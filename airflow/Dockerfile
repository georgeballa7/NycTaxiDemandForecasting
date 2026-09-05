FROM apache/airflow:3.3.1

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY airflow/requirements.txt /requirements-airflow.txt

RUN pip install --no-cache-dir -r /requirements-airflow.txt
