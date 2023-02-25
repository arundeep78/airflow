import cdsapi
import netCDF4 as nc
import numpy as np
import datetime
import pandas as pd
from common import utils
from airflow.providers.postgres.hooks.postgres import PostgresHook
import requests
import calendar

import os
#Get DB connection 

db_conn = PostgresHook(postgres_conn_id = "arcticdata_pgsql")


# table
topic = "temp"
dataset = "cds_t2m_80n_daily"
tbl_name = f"t_{topic}_{dataset}"

indicator = "t2m"

cds_req_params= {    
        'product_type': 'reanalysis',
        'format': 'netcdf',
        'variable': '2m_temperature',
        'year': '1979',
        'month': '01',
        'day': list(range(1,31+1)),
        # "grid": [2.0,2.0],
        'time': [
            '00:00', '01:00', '02:00',
            '03:00', '04:00', '05:00',
            '06:00', '07:00', '08:00',
            '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00',
            '15:00', '16:00', '17:00',
            '18:00', '19:00', '20:00',
            '21:00', '22:00', '23:00',
        ],
        'area': [90, -180, 80.1, 180],
    }


c = cdsapi.Client()


def get_cds_data(c, req, year, month,grid=[0.25,0.25]):
    """
    Get daily mean temp data from CDS server for given year and month
   
    Input:
        c (cdsapi.Client): CDS api client connection object
        req(Dict): Default dictionary for CDS request for temp data
        year(int): year for which to retrieve the data
        month(int): month for which to retrieve the data
    Output:
        df_temp [DataFrame]: dataframe with daily mean temperatures in Celsius
    """
    filename = "download.nc"

    req["month"] = month
    req["year"] = year
    req["grid"] = grid

    c.retrieve(name="reanalysis-era5-single-levels",
        request= cds_req_params,
        target= filename)

    # Read local file

    data = nc.Dataset(filename)

    # read NetCDF4 into numpy array
    data_np = data[indicator][:]

    # get time data
    data_time = data["time"][:]
    # temp mean per hour
    data_mean_h = data_np.mean(axis=(1,2))[:,np.newaxis]

    # temp mean per day for every 24 hours and convert to degree celsius from kelvin
    data_mean_d = utils.groupedAvg(data_mean_h,N=24) - 273.15

    # start date of the data
    start_date = datetime.datetime(1900,1,1) + datetime.timedelta(hours=float(data_time[0]))

    date_dates = pd.date_range(start=start_date, periods=data_mean_d.shape[0])

    df_temp = pd.DataFrame(data=data_mean_d)

    df_temp.columns=["t2m"]

    # Add date information
    df_temp.insert(0,column="datetime_date", value=date_dates)

    df_temp[["yyyy","mm","dd"]] = df_temp["datetime_date"].dt.strftime(date_format="%Y/%m/%d").str.split("/",expand=True).astype(int)


    df_temp["doy"] = df_temp["datetime_date"].dt.day_of_year

    return df_temp


df_temp_list =[]



def get_cds_stats_data(c, year, month, grid="2.0/2.0", frequency="1-hourly"):
    """
    Get data daily mean t2m from CDS stats application for each grid cell
    https://cds.climate.copernicus.eu/cdsapp#!/software/app-c3s-daily-era5-statistics?tab=doc

    Input:
        c (cdapi.Client): CDSAPI Client object
        year (Int): year for the data to be fetched
        month (Int): month for which data to be fetched
        grid (str): Grid size in degrees for which data to be fetched
        frequency(str): frequency of the data 1, 3 and 6 hourly
    Output:
        np.array: Numpy array with days as Dxlatxlon array for given month
    """

    result = c.service(
            "tool.toolbox.orchestrator.workflow",
            params={
                "realm": "user-apps",
                "project": "app-c3s-daily-era5-statistics",
                "version": "master",
                "kwargs": {
                    "dataset": "reanalysis-era5-single-levels",
                    "product_type": "reanalysis",
                    "variable": "2m_temperature",
                    "statistic": "daily_mean",
                    "year": year,
                    "month": month,
                    "time_zone": "UTC+00:0",
                    "frequency": frequency,
    #
    # Users can change the output grid resolution and selected area
    #
                    "grid": grid
                #    "area":{"lat": [80.1, 90], "lon": [-180, 180]}
    
                    },
            "workflow_name": "application"
            })

    location = result[0]["location"]
    res = requests.get(location)

    data_nc=nc.Dataset("in-mem-file", mode="r", memory=res.content)

    data_np = data_nc["t2m"][:]

    return data_np    




def get_cds_daily_ts_by_region_year(year,regions):
    """
    Fetch and calculate daily means by regions for a given year.

    Input:
        year(int): year for which to fetch the data
        regions(Dict): Dictionary with key-value pairs for respective geopgraphic zones
                e.g. 
                {
                    "80n": {
                           "lat" :[80,90],
                           "lon" :[-180, 180]
                           },
                    "NH": {
                           "lat" :[0,90],
                           "lon" :[-180, 180]
                        },
                    "GL":{
                           "lat" :[-90,90],
                           "lon" :[-180, 180]
                        },
                    }

    Output:
        DataFrame: with daily dates and mean values per region in columns        
    """


df_temp_list =[]



for month in range(1,12+1):
    print(f"Downlading data for month: {month} - {calendar.month_name[month]}")
    df_temp = get_cds_stats_data(c,year=1979, month= month,grid=".25/0.25")

    df_temp_list.append(df_temp)


date_dates = pd.date_range(start=datetime.datetime(1979,1,1), periods=365)

df_temp_l = [pd.DataFrame(data=df) for df in df_temp_list]

df_temp_cds_80n_t = pd.concat(df_temp_l)


df_temp_cds_80n_t.columns=["t2m_stats_025_1h"]

# Add date information
df_temp_cds_80n_t.insert(0,column="datetime_date", value=date_dates)

# df_temp[["yyyy","mm","dd"]] = df_temp["datetime_date"].dt.strftime(date_format="%Y/%m/%d").str.split("/",expand=True).astype(int)


# df_temp["doy"] = df_temp["datetime_date"].dt.day_of_year


df_temp_cds_80n = df_temp_cds_80n.merge(df_temp_cds_80n_t,on="datetime_date")



# Add to database
df_temp_cds_80n.to_sql(name=tbl_name, con=db_conn.get_sqlalchemy_engine(),
            index=False,
            if_exists="replace")
