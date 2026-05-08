FROM apache/airflow:2.9.3-python3.10

COPY ./airflow/requirements.txt /requirements.txt

USER root

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
USER airflow

RUN pip install --no-cache-dir -r /requirements.txt
