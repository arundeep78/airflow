
import datetime

import pendulum
from siextent.siextent_nsidc_g02135 import update_sie_data
from airflow import DAG
from airflow.operators.python import PythonOperator


with DAG(
 dag_id='siextent_nsidc_g02135_daily',
    schedule_interval='0 10 * * *',
    
    start_date=pendulum.datetime(2021, 1, 1,tz="UTC"),
    catchup=False,
    dagrun_timeout=datetime.timedelta(minutes=60),
    tags=['sea ice extent', 'nsidc', "g02135"],
) as dag:

  get_sie = PythonOperator(
    task_id="update_sie_nsidc_g02135",
    python_callable= update_sie_data
  )

  get_sie
