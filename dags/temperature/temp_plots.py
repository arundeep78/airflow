from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
from sqlalchemy import column


db_conn = PostgresHook(postgres_conn_id = "arcticdata_pgsql")



# table
topic = "temp"
dataset1 = "cds_t2m_80n_daily"
tbl1 = f"t_{topic}_{dataset1}"
dataset2 = "psl_ncep_t2m_daily"
tbl2 = f"t_{topic}_{dataset2}"


df_ncep = pd.read_sql(tbl2,con=db_conn.get_sqlalchemy_engine())

df_cds = pd.read_sql(tbl1,con=db_conn.get_sqlalchemy_engine())


df_temp = df_cds.merge(df_ncep.iloc[:,:2].rename(columns={"t2m":"t2m_ncep"}), on="datetime_date")


cols = df_temp.columns[df_temp.columns.str.startswith("t2m")]

df_temp[cols].plot(title="Daily mean t2m from different sources and grid sizes",
          figsize=(15,6))