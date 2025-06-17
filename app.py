import streamlit as st
import pandas as pd
import sqlite3
import os

# Set page config
st.set_page_config(page_title="Wyscout Player Finder", layout="wide")
st.title("Wyscout Player Finder")

# --- Database path ---
db_path = 'players_database(4).db'  # Rename your DB file to this for simplicity
st.write(f"Using database file: `{db_path}`")

# Check if database file exists
if not os.path.exists(db_path):
    st.error(f"Database file not found at: {db_path}")
    st.stop()
else:
    st.success(f"Database file found, size: {os.path.getsize(db_path)} bytes")

# Connect to DB and check tables
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    st.write("Tables found in database:", tables)

    # Check if 'Player' table exists (case-insensitive)
    player_table = None
    for table in tables:
        if table.lower() == 'player':
            player_table = table
            break

    if not player_table:
        st.error("Table named 'Player' not found in the database.")
        conn.close()
        st.stop()
    else:
        st.success(f"Using table: {player_table}")

    # Load data from the Player table
    df = pd.read_sql_query(f"SELECT * FROM {player_table}", conn)

except Exception as e:
    st.error(f"Error loading database or reading table: {e}")
    st.stop()

if df.empty:
    st.warning(f"The table '{player_table}' is empty.")
    conn.close()
    st.stop()

st.subheader(f"Raw Data from table: {player_table}")
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
