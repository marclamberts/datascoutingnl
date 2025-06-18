import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from datetime import datetime
import plotly.express as px
import numpy as np
from io import BytesIO
from PIL import Image
import base64

# ==============================================
# CONFIGURATION
# ==============================================

st.set_page_config(
    page_title="Wyscout Player Finder Pro",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================
# DATA MANAGEMENT
# ==============================================

@st.cache_resource(ttl=24*60*60)  # Refresh daily
def load_database():
    """Load and prepare the player database"""
    DB_URL = 'https://github.com/marclamberts/datascoutingnl/raw/main/players_database2.db'
    DB_PATH = 'players_database2.db'
    
    # Download database if needed
    if not os.path.exists(DB_PATH):
        try:
            response = requests.get(DB_URL, timeout=10)
            if response.status_code == 200:
                with open(DB_PATH, 'wb') as f:
                    f.write(response.content)
        except Exception as e:
            st.error(f"Download error: {str(e)}")
            st.stop()

    # Connect and load data
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM Player", conn)
        
        # Data cleaning and transformation
        df = df.rename(columns={'Player': 'Player Name'})  # Standardize column name
        df = df.dropna(subset=['Player Name'], how='all')
        
        # Calculate per 90 metrics if possible
        if 'Minutes played' in df.columns:
            minutes_condition = df['Minutes played'] > 0  # Avoid division by zero
            for metric in ['Goals', 'xG', 'Assists', 'xA']:
                if metric in df.columns:
                    col_name = f"{metric} per 90"
                    df[col_name] = np.where(
                        minutes_condition,
                        df[metric] / (df['Minutes played'] / 90),
                        0
                    )
        
        return df
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        st.stop()
    finally:
        if 'conn' in locals():
            conn.close()

# ==============================================
# FILTERING LOGIC
# ==============================================

@st.cache_data
def filter_players(_df, filters):
    """Apply all filters to the player dataframe"""
    filtered_df = _df.copy()
    
    # Position filter
    if filters.get('positions'):
        filtered_df = filtered_df[filtered_df['Position'].isin(filters['positions'])]
    
    # Team filter
    if filters.get('teams'):
        filtered_df = filtered_df[filtered_df['Team'].isin(filters['teams'])]
    
    # League filter
    if filters.get('leagues'):
        filtered_df = filtered_df[filtered_df['League'].isin(filters['leagues'])]
    
    # Age filter
    if 'Age' in filtered_df.columns and filters.get('age_range'):
        filtered_df = filtered_df[
            (filtered_df['Age'] >= filters['age_range'][0]) & 
            (filtered_df['Age'] <= filters['age_range'][1])
        ]
    
    # Minutes played filter
    if 'Minutes played' in filtered_df.columns and filters.get('minutes_range'):
        filtered_df = filtered_df[
            (filtered_df['Minutes played'] >= filters['minutes_range'][0]) & 
            (filtered_df['Minutes played'] <= filters['minutes_range'][1])
        ]
    
    # Metric range filters
    for metric, (min_val, max_val) in filters.get('metric_ranges', {}).items():
        if metric in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df[metric] >= min_val) & 
                (filtered_df[metric] <= max_val)
            ]
    
    # Nationality filter
    if filters.get('nationalities'):
        filtered_df = filtered_df[filtered_df['Passport country'].isin(filters['nationalities'])]
    
    # Sorting
    if filters.get('sort_by') and filters['sort_by'] in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=filters['sort_by'], 
            ascending=filters.get('sort_asc', True)
        )
    
    return filtered_df

# ==============================================
# UI COMPONENTS
# ==============================================

def create_player_card(player):
    """Create a visually appealing player card"""
    with st.container():
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Placeholder for player image
            st.image(
                "https://via.placeholder.com/150x200?text=Player+Image", 
                width=150, 
                caption=player['Player Name']
            )
        
        with col2:
            st.subheader(player['Player Name'])
            st.caption(f"{player.get('Position', 'N/A')} | {player.get('Team', 'N/A')} | {player.get('League', 'N/A')}")
            
            # Key metrics
            cols = st.columns(4)
            metric_config = [
                ('Age', 'Age'),
                ('Goals', 'Goals'),
                ('Assists', 'Assists'),
                ('Minutes', 'Minutes played')
            ]
            
            for i, (display_name, col_name) in enumerate(metric_config):
                if col_name in player:
                    cols[i].metric(display_name, int(player[col_name]) if isinstance(player[col_name], (int, float)) else player[col_name])
                else:
                    cols[i].metric(display_name, 'N/A')
            
            # Detailed stats in expander
            with st.expander("Detailed Performance Metrics"):
                detailed_metrics = [
                    ('Goals per 90', 'Goals per 90'),
                    ('xG per 90', 'xG per 90'),
                    ('Assists per 90', 'Assists per 90'),
                    ('xA per 90', 'xA per 90'),
                    ('Pass Accuracy %', 'Pass accuracy %'),
                    ('Defensive Duels Won %', 'Defensive duels won %')
                ]
                
                for display_name, col_name in detailed_metrics:
                    if col_name in player:
                        value = player[col_name]
                        if isinstance(value, (int, float)):
                            st.text(f"{display_name}: {value:.2f}" if isinstance(value, float) else f"{display_name}: {value}")
                        else:
                            st.text(f"{display_name}: {value}")

def create_metric_slider(metric_name, df):
    """Create a range slider for a specific metric"""
    if metric_name not in df.columns:
        return None
    
    min_val = float(df[metric_name].min())
    max_val = float(df[metric_name].max())
    step = 0.01 if max_val - min_val < 5 else 0.1
    
    values = st.slider(
        f"{metric_name} Range",
        min_val, max_val,
        (min_val, max_val),
        step=step,
        help=f"Filter players by {metric_name}"
    )
    return values

# ==============================================
# MAIN APP
# ==============================================

def main():
    # Load data with progress indicator
    with st.spinner("Loading player database..."):
        df = load_database()
    
    if df.empty:
        st.warning("No player data available. Please check the database connection.")
        st.stop()
    
    # ==============================================
    # SIDEBAR - FILTERS
    # ==============================================
    
    st.sidebar.title("🔍 Filters")
    st.sidebar.markdown("---")
    
    # Basic filters
    positions = sorted(df['Position'].dropna().unique())
    teams = sorted(df['Team'].dropna().unique())
    leagues = sorted(df['League'].dropna().unique())
    nationalities = sorted(df['Passport country'].dropna().unique())
    
    selected_positions = st.sidebar.multiselect(
        "Positions", 
        positions, 
        default=[],
        help="Select one or more positions"
    )
    
    selected_teams = st.sidebar.multiselect(
        "Teams", 
        teams, 
        default=[],
        help="Filter by current team"
    )
    
    selected_leagues = st.sidebar.multiselect(
        "Leagues", 
        leagues, 
        default=[],
        help="Filter by competition"
    )
    
    selected_nationalities = st.sidebar.multiselect(
        "Nationalities", 
        nationalities, 
        default=[],
        help="Filter by passport country"
    )
    
    # Age filter
    min_age, max_age = int(df['Age'].min()), int(df['Age'].max())
    age_range = st.sidebar.slider(
        "Age Range", 
        min_age, max_age, 
        (min_age, max_age)
    )
    
    # Minutes played filter
    min_minutes, max_minutes = 0, 0
    if 'Minutes played' in df.columns:
        min_minutes, max_minutes = int(df['Minutes played'].min()), int(df['Minutes played'].max())
        minutes_range = st.sidebar.slider(
            "Minutes Played", 
            min_minutes, max_minutes, 
            (min_minutes, max_minutes)
        )
    
    # Performance metric filters
    st.sidebar.markdown("### Performance Metrics")
    metric_ranges = {}
    
    for metric in ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']:
        if metric in df.columns:
            values = create_metric_slider(metric, df)
            if values:
                metric_ranges[metric] = values
    
    # Sorting options
    st.sidebar.markdown("### Sorting")
    sort_options = ['Player Name', 'Age', 'Minutes played', 'Goals', 'Assists'] + list(metric_ranges.keys())
    sort_by = st.sidebar.selectbox(
        "Sort by", 
        sort_options,
        index=0
    )
    sort_asc = st.sidebar.checkbox("Ascending", True)
    
    # ==============================================
    # MAIN CONTENT
    # ==============================================
    
    st.title("⚽ Wyscout Player Finder Pro")
    st.markdown("""
        <style>
            .big-font {
                font-size:18px !important;
                color: #4f8bf9;
            }
        </style>
        <p class="big-font">Find the perfect players for your team with advanced scouting metrics</p>
        """, unsafe_allow_html=True)
    
    # Prepare filters
    filters = {
        'positions': selected_positions,
        'teams': selected_teams,
        'leagues': selected_leagues,
        'nationalities': selected_nationalities,
        'age_range': age_range,
        'minutes_range': (min_minutes, max_minutes),
        'metric_ranges': metric_ranges,
        'sort_by': sort_by,
        'sort_asc': sort_asc
    }
    
    # Apply filters
    filtered_df = filter_players(df, filters)
    
    # Display summary stats
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:10px;border-radius:5px;margin-bottom:20px;">
        <h4 style="margin:0;">📊 Summary: {len(filtered_df)} players found</h4>
        <div style="display:flex;justify-content:space-between;">
            <span>Avg Age: {filtered_df['Age'].mean():.1f}</span>
            <span>Avg Goals/90: {filtered_df['Goals per 90'].mean():.2f if 'Goals per 90' in filtered_df.columns else 'N/A'}</span>
            <span>Avg xG/90: {filtered_df['xG per 90'].mean():.2f if 'xG per 90' in filtered_df.columns else 'N/A'}</span>
            <span>Avg Assists/90: {filtered_df['Assists per 90'].mean():.2f if 'Assists per 90' in filtered_df.columns else 'N/A'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Player List", "👤 Player Profiles", "📈 Analytics"])
    
    with tab1:
        # AG Grid configuration
        gb = GridOptionsBuilder.from_dataframe(filtered_df)
        
        # Configure default columns
        gb.configure_default_column(
            groupable=True,
            sortable=True,
            resizable=True,
            filterable=True,
            editable=False,
            wrapText=True
        )
        
        # Configure pagination
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=25
        )
        
        # Configure specific columns
        numeric_cols = [col for col in filtered_df.columns if pd.api.types.is_numeric_dtype(filtered_df[col])]
        for col in numeric_cols:
            gb.configure_column(col, type=["numericColumn", "numberColumnFilter"])
        
        # Add custom "View Profile" button
        gb.configure_column(
            "Player Name",
            cellRenderer=JsCode('''
                function(params) {
                    return `<a href="#${params.value.replace(/\s+/g, '-')}" 
                           style="color: #4f8bf9; text-decoration: none;"
                           onclick="window.parent.document.getElementById('${params.value.replace(/\s+/g, '-')}').scrollIntoView()">
                           ${params.value}</a>`;
                }
            ''')
        )
        
        grid_options = gb.build()
        
        # Display the grid
        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            height=600,
            width='100%',
            theme='streamlit',
            enable_enterprise_modules=False,
            update_mode='MODEL_CHANGED',
            fit_columns_on_grid_load=True,
            key='players_grid'
        )
        
        # Download button
        st.download_button(
            "💾 Download Filtered Data",
            filtered_df.to_csv(index=False),
            "filtered_players.csv",
            "text/csv",
            key='download-csv'
        )
    
    with tab2:
        st.subheader("Player Profiles")
        
        if len(filtered_df) == 0:
            st.warning("No players match your filters")
        else:
            # Display player cards with navigation
            player_names = filtered_df['Player Name'].unique()
            selected_player = st.selectbox("Select a player to view detailed profile", player_names)
            
            if selected_player:
                player_data = filtered_df[filtered_df['Player Name'] == selected_player].iloc[0]
                create_player_card(player_data)
                
                # Add analytics section
                st.markdown("---")
                st.subheader("Performance Analytics")
                
                # Create tabs for different analytics views
                analytics_tabs = st.tabs(["Trend Analysis", "Comparison", "Advanced Metrics"])
                
                with analytics_tabs[0]:
                    if 'Minutes played' in player_data:
                        st.markdown(f"**Minutes Played:** {int(player_data['Minutes played'])}")
                    
                    # Add more trend analysis here
                
                with analytics_tabs[1]:
                    # Comparison with league averages
                    if 'League' in player_data and player_data['League'] in df['League'].unique():
                        league_avg = df[df['League'] == player_data['League']].mean(numeric_only=True)
                        
                        comparison_data = pd.DataFrame({
                            'Metric': ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90'],
                            'Player': [
                                player_data.get('Goals per 90', 0),
                                player_data.get('xG per 90', 0),
                                player_data.get('Assists per 90', 0),
                                player_data.get('xA per 90', 0)
                            ],
                            'League Average': [
                                league_avg.get('Goals per 90', 0),
                                league_avg.get('xG per 90', 0),
                                league_avg.get('Assists per 90', 0),
                                league_avg.get('xA per 90', 0)
                            ]
                        })
                        
                        fig = px.bar(
                            comparison_data.melt(id_vars='Metric'), 
                            x='Metric', 
                            y='value',
                            color='variable',
                            barmode='group',
                            title='Comparison with League Averages'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                with analytics_tabs[2]:
                    # Radar chart for advanced metrics
                    if all(m in player_data for m in ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']):
                        metrics = ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']
                        values = [player_data[m] for m in metrics]
                        
                        fig = px.line_polar(
                            r=values,
                            theta=metrics,
                            line_close=True,
                            title='Performance Radar Chart'
                        )
                        fig.update_traces(fill='toself')
                        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("League Analytics")
        
        if 'League' in filtered_df.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                league_stats = filtered_df.groupby('League').agg({
                    'Age': 'mean',
                    'Goals per 90': 'mean',
                    'Assists per 90': 'mean'
                }).reset_index()
                
                fig = px.bar(
                    league_stats.sort_values('Goals per 90'),
                    x='Goals per 90',
                    y='League',
                    orientation='h',
                    title='Average Goals per 90 by League'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    league_stats.sort_values('Assists per 90'),
                    x='Assists per 90',
                    y='League',
                    orientation='h',
                    title='Average Assists per 90 by League'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Age distribution
        if 'Age' in filtered_df.columns:
            fig = px.histogram(
                filtered_df,
                x='Age',
                nbins=20,
                title='Player Age Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
