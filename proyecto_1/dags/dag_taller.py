from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from train import delete_database, load_csv_to_mysql, preprocess, train

default_args = {
	'start_date': datetime(2026, 3, 1),
	'retries': 1,
}
# Cambio
with DAG(
	dag_id='penguins_ml_pipeline',
	default_args=default_args,
	schedule_interval=None,
) as dag:
	t1 = PythonOperator(
		task_id='delete_database',
		python_callable=delete_database
	)
	t2 = PythonOperator(
		task_id='load_csv_to_mysql',
		python_callable=load_csv_to_mysql,
		op_args=['/opt/airflow/dags/Data/penguins.csv']
	)
	t3 = PythonOperator(
		task_id='preprocess',
		python_callable=preprocess
	)
	t4 = PythonOperator(
		task_id='train',
		python_callable=train
	)

	t1 >> t2 >> t3 >> t4
