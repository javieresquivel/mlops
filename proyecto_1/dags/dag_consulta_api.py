from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from consulta_api import fetch_api_and_store

default_args = {
    'start_date': datetime(2026, 3, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

with DAG(
    dag_id='consulta_api',
    default_args=default_args,
    schedule_interval=timedelta(minutes=2),
    catchup=False
) as dag:

    consulta_api = PythonOperator(
        task_id='fetch_api_and_store',
        python_callable=fetch_api_and_store,
        op_kwargs={'group_number': 9},
    )

    consulta_api
