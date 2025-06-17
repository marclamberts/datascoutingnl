import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")
st.title("Wyscout Player Finder")

# --- Load SQLite Database ---
db_path = 'players_database(3).db'  # Update with your actual database filename
import os
print(os.path.exists('players_database(3).db'))

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get list of tables in DB
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        st.error("No tables found in the database.")
        st.stop()

    # Choose table (prefer 'Player' or 'players', else first table)
    table_name = None
    for t in tables:
        if t.lower() in ['player', 'players']:
            table_name = t
            break
    if not table_name:
        table_name = tables[0]

    # Load data from table
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

except Exception as e:
    st.error(f"Error loading database or reading table: {e}")
    st.stop()

if df.empty:
    st.warning(f"The table '{table_name}' is empty.")
    st.stop()

st.subheader(f"Raw Data from table: {table_name}")
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
