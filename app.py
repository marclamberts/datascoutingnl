import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from st_aggrid import AgGrid, GridOptionsBuilder

# Configure page first
st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

@st.cache_resource
def load_database():
    # --- Download the database from GitHub if not already present ---
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

    # --- Connect to SQLite database ---
    conn = sqlite3.connect(db_path)
    
    # Load data from 'Player' table
    try:
        df = pd.read_sql_query("SELECT * FROM Player", conn)
    except Exception as e:
        st.error(f"Error loading table: {e}")
        st.stop()
    finally:
        conn.close()
    
    return df

@st.cache_data
def filter_data(df, filters):
    filtered_df = df.copy()
    
    # Apply all filters
    if filters['positions']:
        filtered_df = filtered_df[filtered_df['Position'].isin(filters['positions'])]
    if filters['teams']:
        filtered_df = filtered_df[filtered_df['Team'].isin(filters['teams'])]
    if filters['leagues']:
        filtered_df = filtered_df[filtered_df['League'].isin(filters['leagues'])]
    if filters['passport_countries']:
        filtered_df = filtered_df[filtered_df['Passport country'].isin(filters['passport_countries'])]
    if filters['contracts']:
        filtered_df = filtered_df[filtered_df['Contract expires'].isin(filters['contracts'])]
    if 'Age' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['Age'] >= filters['age_range'][0]) & 
                                (filtered_df['Age'] <= filters['age_range'][1])]
    if 'Minutes played' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['Minutes played'] >= filters['minutes_range'][0]) & 
                                (filtered_df['Minutes played'] <= filters['minutes_range'][1])]
    
    # Apply metric filters
    for metric, selected_range in filters['metrics'].items():
        if selected_range != 'All':
            if selected_range == '0 - 0.3':
                filtered_df = filtered_df[(filtered_df[metric] >= 0) & (filtered_df[metric] < 0.3)]
            elif selected_range == '0.3 - 0.6':
                filtered_df = filtered_df[(filtered_df[metric] >= 0.3) & (filtered_df[metric] < 0.6)]
            elif selected_range == '0.6+':
                filtered_df = filtered_df[filtered_df[metric] >= 0.6]
    
    return filtered_df

def main():
    st.title("Wyscout Player Finder")
    
    # Load data with caching
    df = load_database()
    
    if df.empty:
        st.warning("The table 'Player' is empty.")
        st.stop()

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Players")

    positions = sorted(df['Position'].dropna().unique()) if 'Position' in df.columns else []
    teams = sorted(df['Team'].dropna().unique()) if 'Team' in df.columns else []
    leagues = sorted(df['League'].dropna().unique()) if 'League' in df.columns else []
    passport_countries = sorted(df['Passport country'].dropna().unique()) if 'Passport country' in df.columns else []
    contracts = sorted(df['Contract expires'].dropna().unique()) if 'Contract expires' in df.columns else []

    selected_positions = st.sidebar.multiselect("Select Position(s)", positions)
    selected_teams = st.sidebar.multiselect("Select Team(s)", teams)
    selected_leagues = st.sidebar.multiselect("Select League(s)", leagues)
    selected_passport_countries = st.sidebar.multiselect("Select Passport Country(s)", passport_countries)
    selected_contracts = st.sidebar.multiselect("Select Contract Expiry Year(s)", contracts)

    min_age = int(df['Age'].min()) if 'Age' in df.columns else 15
    max_age = int(df['Age'].max()) if 'Age' in df.columns else 40
    age_range = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))

    min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df.columns else 0
    max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df.columns else 5000
    minutes_range = st.sidebar.slider("Select Minutes Played Range", min_minutes, max_minutes, (min_minutes, max_minutes))

    metric_options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
    metrics = {
        'Goals per 90': st.sidebar.selectbox("Select Goals per 90 Range", metric_options),
        'xG per 90': st.sidebar.selectbox("Select xG per 90 Range", metric_options),
        'Assists per 90': st.sidebar.selectbox("Select Assists per 90 Range", metric_options),
        'xA per 90': st.sidebar.selectbox("Select xA per 90 Range", metric_options)
    }

    # Prepare filters dictionary
    filters = {
        'positions': selected_positions,
        'teams': selected_teams,
        'leagues': selected_leagues,
        'passport_countries': selected_passport_countries,
        'contracts': selected_contracts,
        'age_range': age_range,
        'minutes_range': minutes_range,
        'metrics': metrics
    }

    # Apply filters with caching
    filtered_df = filter_data(df, filters)

    st.subheader(f"Showing {len(filtered_df)} filtered players")

    # --- AgGrid setup for pagination & styling ---
    gb = GridOptionsBuilder.from_dataframe(filtered_df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=50)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)

    grid_options = gb.build()

    AgGrid(
        filtered_df,
        gridOptions=grid_options,
        enable_enterprise_modules=False,
        theme='blue',
        height=600,
        width='100%',
        reload_data=True,
    )

    # --- Download Button for Full Dataset ---
    st.download_button(
        label="Download Full Filtered Data",
        data=filtered_df.to_csv(index=False),
        file_name="filtered_players.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
