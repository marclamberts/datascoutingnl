import streamlit as st
import pandas as pd

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

st.title("Wyscout Player Finder")

# Load the Excel file directly
file_path = 'Netherlands II.xlsx'  # Change this to your actual file path
df = pd.read_excel(file_path)

st.subheader("Raw Data")
st.write(df)

# Automatically detect columns for filtering
st.sidebar.header("Filter Players")

# Example: Assuming 'Position', 'Team', 'Age', 'Minutes played' are in your dataset
# You can customize these fields based on your actual Wyscout data columns
positions = df['Position'].unique() if 'Position' in df.columns else []
teams = df['Team'].unique() if 'Team' in df.columns else []

selected_positions = st.sidebar.multiselect("Select Position(s)", positions)
selected_teams = st.sidebar.multiselect("Select Team(s)", teams)

min_age = int(df['Age'].min()) if 'Age' in df.columns else 15
max_age = int(df['Age'].max()) if 'Age' in df.columns else 40
age_range = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))

min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df.columns else 0
max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df.columns else 5000
minutes_range = st.sidebar.slider("Select Minutes Played Range", min_minutes, max_minutes, (min_minutes, max_minutes))

# New filters for performance metrics
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

if 'Age' in df.columns:
    filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

if 'Minutes played' in df.columns:
    filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

# Goals per 90 filter
if 'Goals per 90' in df.columns:
    if selected_goals_per_90 == '0 - 0.3':
        filtered_df = filtered_df[(filtered_df['Goals per 90'] >= 0) & (filtered_df['Goals per 90'] < 0.3)]
    elif selected_goals_per_90 == '0.3 - 0.6':
        filtered_df = filtered_df[(filtered_df['Goals per 90'] >= 0.3) & (filtered_df['Goals per 90'] < 0.6)]
    elif selected_goals_per_90 == '0.6+':
        filtered_df = filtered_df[(filtered_df['Goals per 90'] >= 0.6)]

# xG per 90 filter
if 'xG per 90' in df.columns:
    if selected_xg_per_90 == '0 - 0.3':
        filtered_df = filtered_df[(filtered_df['xG per 90'] >= 0) & (filtered_df['xG per 90'] < 0.3)]
    elif selected_xg_per_90 == '0.3 - 0.6':
        filtered_df = filtered_df[(filtered_df['xG per 90'] >= 0.3) & (filtered_df['xG per 90'] < 0.6)]
    elif selected_xg_per_90 == '0.6+':
        filtered_df = filtered_df[(filtered_df['xG per 90'] >= 0.6)]

# Assists per 90 filter
if 'Assists per 90' in df.columns:
    if selected_assists_per_90 == '0 - 0.3':
        filtered_df = filtered_df[(filtered_df['Assists per 90'] >= 0) & (filtered_df['Assists per 90'] < 0.3)]
    elif selected_assists_per_90 == '0.3 - 0.6':
        filtered_df = filtered_df[(filtered_df['Assists per 90'] >= 0.3) & (filtered_df['Assists per 90'] < 0.6)]
    elif selected_assists_per_90 == '0.6+':
        filtered_df = filtered_df[(filtered_df['Assists per 90'] >= 0.6)]

# xA per 90 filter
if 'xA per 90' in df.columns:
    if selected_xa_per_90 == '0 - 0.3':
        filtered_df = filtered_df[(filtered_df['xA per 90'] >= 0) & (filtered_df['xA per 90'] < 0.3)]
    elif selected_xa_per_90 == '0.3 - 0.6':
        filtered_df = filtered_df[(filtered_df['xA per 90'] >= 0.3) & (filtered_df['xA per 90'] < 0.6)]
    elif selected_xa_per_90 == '0.6+':
        filtered_df = filtered_df[(filtered_df['xA per 90'] >= 0.6)]

st.subheader("Filtered Players")
st.write(filtered_df)

st.download_button("Download Filtered Data", data=filtered_df.to_csv(index=False), file_name="filtered_players.csv", mime="text/csv")
