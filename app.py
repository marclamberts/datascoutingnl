import streamlit as st
import pandas as pd
import sqlite3
import requests
import os

# ✅ Set page configuration (must be first)
st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

# --- Step 1: Download the database from GitHub if not already present ---
db_url = 'https://github.com/marclamberts/datascoutingnl/raw/main/players_database2.db'
db_path = 'players_database2.db'

if not os.path.exists(db_path):
    response = requests.get(db_url)
    if response.status_code == 200:
        with open(db_path, 'wb') as f:
            f.write(response.content)
    else:
        st.error('Failed to download database. Check the URL.')
        st.stop()

# --- Step 2: Connect to SQLite database ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

if ('Player',) not in tables:
    st.error("Player table not found!")
    st.stop()

# ✅ Clean start of the app
st.title("Wyscout Player Finder")

# Load data from 'Player' table
try:
    df = pd.read_sql_query("SELECT * FROM Player", conn)
except Exception as e:
    st.error(f"Error loading table: {e}")
    st.stop()

if df.empty:
    st.warning("The table 'Player' is empty.")
    st.stop()

st.subheader("Raw Data from table: Player")
st.dataframe(df)
