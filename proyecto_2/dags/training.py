from airflow import DAG, settings
import subprocess
from datetime import datetime, timedelta
from airflow.utils.state import State

from training_app.dataController import save_all_clean_data, store_raw_data, clear_all_data
from training_app.etl import get_batch_amount
from training_app.train import train_and_publish_best

from airflow.operators.python import PythonOperator, ShortCircuitOperator, BranchPythonOperator
from airflow.models import Variable, DagRun
from airflow.operators.empty import EmptyOperator
import os


BATCH_SIZE = int(os.getenv("BATCH_SIZE", 15000))
print("BATCH_SIZE type", type(BATCH_SIZE))
batch_number = get_batch_amount(BATCH_SIZE)

def dag_store_raw_data():
    key = "training_dag_run_count"
    count = int(Variable.get(key, default_var="0"))
    print("count in dag_store_raw_data", count)
    store_raw_data(count + 1, BATCH_SIZE)
    print(f"Stored raw data for run {count+1}/{batch_number}")
    Variable.set(key, str(count + 1))
    print(f"Run {count+1}/{batch_number}")

def pause_dag_if_failed(**context):
    dag_id = context['dag'].dag_id
    session = settings.Session()
    dag_runs = session.query(DagRun).filter(DagRun.dag_id == dag_id).order_by(DagRun.execution_date.desc()).all()
    subprocess.run(["airflow", "dags", "pause", dag_id])

def check_run_count(dag_id):
    # keep track of how many runs have happened
    key = "training_dag_run_count"
    count = int(Variable.get(key, default_var="0"))
    print(f"Current run count: {count}")
    if count + 1 >7:
        print("Reached maximum number of runs (7).")
        subprocess.run(["airflow", "dags", "pause", dag_id])
        print(f"[gate] limit reached ({count + 1}/{batch_number}) -> paused {dag_id}")
        return False
    # increment counter
    print(f"Run {count+1}/{7}")

def check_first_run():
    if Variable.get("dag_first_run_done", default_var="false") == "false":
        return True
    return False

def choose_branch():
    first_run = Variable.get("dag_first_run_done", default_var="false") == "false"
    return "clear_all_data_task" if first_run else "skip_first_time"

def mark_first_run_done():
    print("Marking first run as done")
    Variable.set("dag_first_run_done", "true")

with DAG (dag_id="training_dag",
    description="Entrenando modelos",
    schedule_interval=timedelta(minutes=4, seconds=0),   # every 5 minutes and 20 seconds
    start_date=datetime(2026, 5, 15, 21, 8, 0),   # change as needed
    catchup=False,

    max_active_runs=7,
    is_paused_upon_creation=False
) as dag:

    mark_done = PythonOperator(
        task_id="mark_done",
        python_callable=mark_first_run_done
    )

    pause_dag_task = PythonOperator(
        task_id="pause_dag_if_failed",
        python_callable=pause_dag_if_failed,
        provide_context=True,
        trigger_rule="one_failed",  # Se ejecuta si alguna tarea falla
    )

    branch = BranchPythonOperator(
        task_id="branch_first_run",
        python_callable=choose_branch,
    )

    skip_first_time = EmptyOperator(
        task_id="skip_first_time",
    )
    check = PythonOperator(
        task_id="gate_should_continue",
        python_callable=check_run_count,
        op_kwargs={"dag_id": "training_dag"}
    )
        
    store_raw_data_task = PythonOperator(task_id="store_raw_data",
        python_callable=dag_store_raw_data,
    )

    clear_all_data_task = PythonOperator(task_id="clear_all_data_task",
                      python_callable=clear_all_data)

    store_clean_data_task = PythonOperator(task_id="store_clean_data",
                       python_callable=save_all_clean_data)
    
    train_model = PythonOperator(task_id="train_model",
                      python_callable=train_and_publish_best)
    

    join_after_branch = EmptyOperator(
        task_id="join_after_branch",
        trigger_rule="none_failed_min_one_success",
    )

    check >> branch >> [clear_all_data_task, skip_first_time]>> join_after_branch >> mark_done >> store_raw_data_task >>store_clean_data_task >> train_model >> pause_dag_task
    