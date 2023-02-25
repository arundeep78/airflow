
import netCDF4 as nc
import numpy as np
import requests
import datetime
import pandas as pd
# from common import utils

from io import StringIO, BytesIO
from airflow.providers.postgres.hooks.postgres import PostgresHook

#### Daily 2m temperature data from NCEP/NCAR Reanalysis 1: Surface

### https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.surface.html


#Get DB connection 

db_conn = PostgresHook(postgres_conn_id = "arcticdata_pgsql")


# table
topic = "temp"
dataset = "psl_ncep_t2m_daily"
tbl_name = f"t_{topic}_{dataset}"


indicator= "air"

url_base= "https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.dailyavgs/surface_gauss/"
filename_base= "air.2m.gauss.{}.nc"

yyyy = 1979
filename =filename_base.format(yyyy)

url = url_base + filename

r= requests.get(url)

data_nc=nc.Dataset("in-mem-file", mode="r", memory=r.content)


# Find how many rows belong to 80N+
index_80n = (data_nc["lat"][:]>80).sum()

# Get daily mean and convert into degree celsius
data_daily_mean = data_nc[indicator][:,:index_80n,:].mean(axis=(1,2)) - 273.15


start_date = datetime.datetime(1800,1,1) + datetime.timedelta(hours=data_nc["time"][:][0])

date_range = pd.date_range(start=start_date,periods=len(data_nc["time"]))

df_temp = pd.DataFrame(data=data_daily_mean)

df_temp.columns=["t2m"]

# Add date information
df_temp.insert(0,column="datetime_date", value=date_range)

df_temp[["yyyy","mm","dd"]] = df_temp["datetime_date"].dt.strftime(date_format="%Y/%m/%d").str.split("/",expand=True).astype(int)


df_temp["doy"] = df_temp["datetime_date"].dt.day_of_year


# Save data to DB

df_temp.to_sql(tbl_name, con=db_conn.get_sqlalchemy_engine(), 
          index=False,
          if_exists="append")


df_temp["t2m"].plot()