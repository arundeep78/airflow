# %%
import datetime
import pandas as pd
import numpy as np
import json
from sqlalchemy import text
import io
import sys
import requests

from airflow.providers.postgres.hooks.postgres import PostgresHook


def update_sie_data():
  '''
  Updates Sea ice extent dataset from NSIDC servers

  '''
  # %%
  topic = "siextent"
  dataset = "nsidc_g02135"
  tbl_name = f"t_{topic}_{dataset}"

  db_conn = PostgresHook(postgres_conn_id = "arcticdata_pgsql")

  # Download latest data from NSIDC

  SOURCE_URL = "http://masie_web.apps.nsidc.org/pub/DATASETS/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v3.0.csv"


  # %%
  try:
    num_records_before= db_conn.get_first(sql=f"select count(*) from {tbl_name}")[0]
  
  except:
    num_records_before=0

  print(num_records_before)

  try:
    max_date= db_conn.get_first(f"SELECT MAX(datetime_date) FROM {tbl_name}")[0]
  except:
    max_date = datetime.datetime(1950,1,1)

  print(max_date)


  # %%
  r= requests.get(SOURCE_URL)


  if r.ok:

    df = pd.read_csv(io.StringIO(r.text), skiprows=[1], skipinitialspace=True)


    df = df.rename(columns= lambda x: x.lower().strip().replace(" ", "_"),)

    df["datetime_date"] = pd.to_datetime(df[["year","month","day"]])
        
    del df["year"]
    del df["month"]
    del df["day"]

    df = df[df["datetime_date"]>max_date]
    new_records = len(df)
    df.to_sql(tbl_name,con = db_conn.get_sqlalchemy_engine(), if_exists="append",index=False)
      
    num_records_after= db_conn.get_first(sql=f"select count(*) from {tbl_name}")[0]
    print(num_records_after)

    status = "OK"
  else:
    new_records = 0
    num_records_after = num_records_before
    status = "NOK"




