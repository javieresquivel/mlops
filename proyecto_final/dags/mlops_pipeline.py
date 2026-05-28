from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from datetime import datetime

from training_app.data_pipeline import (
    fetch_batch,
    validate_schema,
    validate_data_quality,
    detect_new_categories,
    detect_data_drift,
    preprocess_data,
    decide_training,
    skip_training,
    train_model,
    evaluate_model,
    register_model,
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

    preprocess_data_task = PythonOperator(
        task_id="preprocess_data",
        python_callable=preprocess_data,
    )

    decide_training_task = BranchPythonOperator(
        task_id="decide_training",
        python_callable=decide_training,
    )

    skip_training_task = PythonOperator(
        task_id="skip_training",
        python_callable=skip_training,
    )

    train_model_task = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
    )

    evaluate_model_task = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    register_model_task = PythonOperator(
        task_id="register_model",
        python_callable=register_model,
    )

    start_task >> fetch_task >> validate_schema_task >> validate_data_quality_task
    validate_data_quality_task >> detect_new_categories_task >> detect_data_drift_task >> preprocess_data_task
    preprocess_data_task >> decide_training_task
    decide_training_task >> [train_model_task, skip_training_task]
    train_model_task >> evaluate_model_task >> register_model_task