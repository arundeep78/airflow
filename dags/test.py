from airflow import DAG
import datetime

from airflow.operators.python import PythonOperator

from pprint import pprint

dag = DAG(
        dag_id='test_context',
        schedule_interval='0 10 * * *',
        
        start_date=datetime.datetime(2021, 1, 1),
        catchup=False,
        dagrun_timeout=datetime.timedelta(minutes=60),
        tags=['test context'],
    )


def print_context(ds, **kwargs):
    """Print the Airflow context and ds variable from the context."""
    print(ds)
    pprint(kwargs)
    return 'Whatever you return gets printed in the logs'


run_this = PythonOperator(
    task_id='print_the_context',
    provide_context=True,
    python_callable=print_context,
    dag=dag,
)

run_this