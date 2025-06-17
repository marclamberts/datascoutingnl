import streamlit as st
import pandas as pd
import sqlite3
import requests
import os

# --- Step 1: Download the database from GitHub if not already present ---
db_url = 'https://github.com/marclamberts/datascoutingnl/blob/main/players_database1.db'  # Replace with your actual link
db_path = 'players_database1).db'

if not os.path.exists(db_path):
    st.info('Downloading database...')
    response = requests.get(db_url)
    if response.status_code == 200:
        with open(db_path, 'wb') as f:
            f.write(response.content)
        st.success('Database downloaded successfully!')
    else:
        st.error('Failed to download database. Check the URL.')
        st.stop()

# --- Step 2: Connect to SQLite database ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
st.write("Tables found in database:", tables)

if ('Player',) not in tables:
    st.error("Player table not found!")
    st.stop()
else:
    st.success("Player table found!")

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")
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

# --- Sidebar Filters ---
st.sidebar.header("Filter Players")

positions = sorted(df['Position'].dropna().unique()) if 'Position' in df.columns else []
teams = sorted(df['Team'].dropna().unique()) if 'Team' in df.columns else []
leagues = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []

selected_positions = st.sidebar.multiselect("Select Position(s)", positions)
selected_teams = st.sidebar.multiselect("Select Team(s)", teams)
selected_leagues = st.sidebar.multiselect("Select League(s)", leagues)

min_age = int(df['Age'].min()) if 'Age' in df.columns else 15
max_age = int(df['Age'].max()) if 'Age' in df.columns else 40
age_range = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))

min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df.columns else 0
max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df.columns else 5000
minutes_range = st.sidebar.slider("Select Minutes Played Range", min_minutes, max_minutes, (min_minutes, max_minutes))

# Performance metric filter options
metric_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']

selected_goals_per_90 = st.sidebar.selectbox("Select Goals per 90 Range", metric_options)
selected_xg_per_90 = st.sidebar.selectbox("Select xG per 90 Range", metric_options)
selected_assists_per_90 = st.sidebar.selectbox("Select Assists per 90 Range", metric_options)
selected_xa_per_90 = st.sidebar.selectbox("Select xA per 90 Range", metric_options)

# --- Filtering logic ---
filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

if selected_leagues:
    filtered_df = filtered_df[filtered_df['League'].isin(selected_leagues)]

if 'Age' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

if 'Minutes played' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

def apply_metric_filter(df, col_name, selected_range):
    if col_name not in df.columns or selected_range == 'All':
        return df
    if selected_range == '0 - 0.3':
        return df[(df[col_name] >= 0) & (df[col_name] < 0.3)]
    if selected_range == '0.3 - 0.6':
        return df[(df[col_name] >= 0.3) & (df[col_name] < 0.6)]
    if selected_range == '0.6+':
        return df[df[col_name] >= 0.6]
    return df

filtered_df = apply_metric_filter(filtered_df, 'Goals per 90', selected_goals_per_90)
filtered_df = apply_metric_filter(filtered_df, 'xG per 90', selected_xg_per_90)
filtered_df = apply_metric_filter(filtered_df, 'Assists per 90', selected_assists_per_90)
filtered_df = apply_metric_filter(filtered_df, 'xA per 90', selected_xa_per_90)

st.subheader("Filtered Players")
st.dataframe(filtered_df)

# Download button
st.download_button(
    label="Download Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_players.csv",
    mime="text/csv"
)

conn.close()
