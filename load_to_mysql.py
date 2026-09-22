"""
load_to_mysql.py
----------------
Step 4 helper: loads the CSV files into the MySQL tables created by sql/database_schema.sql

Order matters because of foreign keys:
    sales_reps  ->  sales_leads  ->  sales_activities

Setup (once):
    pip install mysql-connector-python pandas

Run:
    1) Run sql/database_schema.sql in MySQL Workbench first
    2) python load_to_mysql.py         (it asks for your MySQL password; nothing is stored in the file)
"""

import getpass
import os

import mysql.connector
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "dataset")

DB_NAME = "b2b_sales_analytics"
CHUNK = 500

# (table, csv file, integer columns that may contain blanks)
LOAD_PLAN = [
    ("sales_reps", "sales_reps.csv", []),
    ("sales_leads", "cleaned_leads.csv", ["Deal_Value", "Days_Since_Last_Contact"]),
    ("sales_activities", "sales_activities.csv", []),
]


def to_python(v):
    """Convert pandas/numpy values into plain Python values (NaN -> None) for the MySQL driver."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def read_csv(filename, nullable_int_cols):
    df = pd.read_csv(os.path.join(DATA_DIR, filename))
    for col in nullable_int_cols:
        df[col] = df[col].astype("Int64")
    return df


def load_table(cur, table, df):
    cols = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    rows = [tuple(to_python(v) for v in row) for row in df.itertuples(index=False, name=None)]
    for i in range(0, len(rows), CHUNK):
        cur.executemany(sql, rows[i:i + CHUNK])
    return len(rows)


def main():
    host = input("MySQL host [localhost]: ").strip() or "localhost"
    user = input("MySQL user [root]: ").strip() or "root"
    password = getpass.getpass("MySQL password: ")

    conn = mysql.connector.connect(host=host, user=user, password=password, database=DB_NAME)
    cur = conn.cursor()
    try:
        # start clean so the script can be re-run (children first)
        for table, _, _ in reversed(LOAD_PLAN):
            cur.execute(f"DELETE FROM {table}")

        for table, csv_file, int_cols in LOAD_PLAN:
            df = read_csv(csv_file, int_cols)
            n = load_table(cur, table, df)
            print(f"Loaded {n:>6} rows into {table}")
        conn.commit()

        print("\nRow counts in MySQL:")
        for table, _, _ in LOAD_PLAN:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table:<18} {cur.fetchone()[0]}")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
