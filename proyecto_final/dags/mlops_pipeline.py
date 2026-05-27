from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from training_app.data_pipeline import (
    fetch_batch,
    store_raw_batch,
    validate_schema,
    validate_data_quality,
    detect_new_categories,
    detect_data_drift,
)


def start():
    print("Inicio del DAG")


with DAG(
    dag_id="mlops_ingestion_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["mlops"],
) as dag:

    start_task = PythonOperator(
        task_id="start",
        python_callable=start,
    )

    fetch_task = PythonOperator(
        task_id="fetch_batch_from_api",
        python_callable=fetch_batch,
    )

    store_task = PythonOperator(
        task_id="store_raw_batch",
        python_callable=store_raw_batch,
    )

    validate_schema_task = PythonOperator(
        task_id="validate_schema",
        python_callable=validate_schema,
    )

    validate_data_quality_task = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_data_quality,
    )

    detect_new_categories_task = PythonOperator(
        task_id="detect_new_categories",
        python_callable=detect_new_categories,
    )

    detect_data_drift_task = PythonOperator(
        task_id="detect_data_drift",
        python_callable=detect_data_drift,
    )

    start_task >> fetch_task >> store_task >> validate_schema_task >> validate_data_quality_task
    validate_data_quality_task >> detect_new_categories_task >> detect_data_drift_task