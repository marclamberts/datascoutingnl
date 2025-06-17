import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")
st.title("Wyscout Player Finder")

# Load the SQLite database
db_path = 'players_database(3).db'  # Ensure this is your correct DB file
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

if not tables:
    st.error("No tables found in the database.")
    st.stop()

# For debugging: Show tables available
# st.write(f"Tables found: {tables}")

# Try to pick the right table (e.g., Player, players, or first table)
table_name = None
for t in tables:
    if t.lower() == 'player' or t.lower() == 'players':
        table_name = t
        break
if not table_name:
    table_name = tables[0]  # fallback to the first table

# Load data from selected table
try:
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
except Exception as e:
    st.error(f"Failed to read data from table {table_name}: {e}")
    conn.close()
    st.stop()

if df.empty:
    st.warning("The selected table is empty.")
    conn.close()
    st.stop()

st.subheader(f"Raw Data from table: {table_name}")
st.write(df)

# Sidebar Filters
st.sidebar.header("Filter Players")

positions = df['Position'].dropna().unique() if 'Position' in df.columns else []
teams = df['Team'].dropna().unique() if 'Team' in df.columns else []
leagues = df['League'].dropna().unique() if 'League' in df.columns else []

selected_positions = st.sidebar.multiselect("Select Position(s)", sorted(positions))
selected_teams = st.sidebar.multiselect("Select Team(s)", sorted(teams))
selected_leagues = st.sidebar.multiselect("Select League(s)", sorted(leagues))

min_age = int(df['Age'].min()) if 'Age' in df.columns else 15
max_age = int(df['Age'].max()) if 'Age' in df.columns else 40
age_range = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))

min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df.columns else 0
max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df.columns else 5000
minutes_range = st.sidebar.slider("Select Minutes Played Range", min_minutes, max_minutes, (min_minutes, max_minutes))

# Performance metric filters
goals_per_90_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
xg_per_90_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
assists_per_90_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
xa_per_90_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']

selected_goals_per_90 = st.sidebar.selectbox("Select Goals per 90 Range", goals_per_90_options)
selected_xg_per_90 = st.sidebar.selectbox("Select xG per 90 Range", xg_per_90_options)
selected_assists_per_90 = st.sidebar.selectbox("Select Assists per 90 Range", assists_per_90_options)
selected_xa_per_90 = st.sidebar.selectbox("Select xA per 90 Range", xa_per_90_options)

# Filtering logic
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

def filter_metric(df, column, selection):
    if column not in df.columns:
        return df
    if selection == '0 - 0.3':
        return df[(df[column] >= 0) & (df[column] < 0.3)]
    elif selection == '0.3 - 0.6':
        return df[(df[column] >= 0.3) & (df[column] < 0.6)]
    elif selection == '0.6+':
        return df[df[column] >= 0.6]
    return df

filtered_df = filter_metric(filtered_df, 'Goals per 90', selected_goals_per_90)
filtered_df = filter_metric(filtered_df, 'xG per 90', selected_xg_per_90)
filtered_df = filter_metric(filtered_df, 'Assists per 90', selected_assists_per_90)
filtered_df = filter_metric(filtered_df, 'xA per 90', selected_xa_per_90)

st.subheader("Filtered Players")
st.write(filtered_df)

# Download button
st.download_button(
    label="Download Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_players.csv",
    mime="text/csv"
)

conn.close()
