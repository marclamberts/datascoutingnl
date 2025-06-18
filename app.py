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

# Configure page settings
st.set_page_config(
    page_title="Wyscout Player Finder Pro",
    page_icon=":soccer:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load custom CSS (create a file called 'style.css' in the same directory)
# local_css("style.css")

# ==============================================
# DATA MANAGEMENT
# ==============================================

@st.cache_resource(ttl=24*60*60)  # Refresh daily
def load_database():
    """Load the player database with caching and automatic updates"""
    DB_URL = 'https://github.com/marclamberts/datascoutingnl/raw/main/players_database2.db'
    DB_PATH = 'players_database2.db'
    LAST_UPDATED_FILE = 'last_updated.txt'

    def download_database():
        try:
            response = requests.get(DB_URL, timeout=10)
            if response.status_code == 200:
                with open(DB_PATH, 'wb') as f:
                    f.write(response.content)
                with open(LAST_UPDATED_FILE, 'w') as f:
                    f.write(datetime.now().isoformat())
                return True
            return False
        except Exception as e:
            st.error(f"Download error: {str(e)}")
            return False

    # Check if we need to download the database
    if not os.path.exists(DB_PATH):
        st.info("Downloading player database for the first time...")
        if not download_database():
            st.error("Failed to download database. Check your internet connection.")
            st.stop()

    # Connect to database and load data
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM Player", conn)
        
        # Add derived metrics if needed
        if 'Minutes played' in df.columns and 'Goals' in df.columns:
            df['Goals per 90'] = df['Goals'] / (df['Minutes played'] / 90)
        
        # Clean data
        df = df.dropna(subset=['Player Name'], how='all')  # Remove completely empty rows
        df = df.fillna('Unknown')  # Fill other NAs
        
        return df
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        st.stop()
    finally:
        if 'conn' in locals():
            conn.close()

# ==============================================
# UTILITY FUNCTIONS
# ==============================================

def get_img_as_base64(file):
    """Convert image to base64 for HTML embedding"""
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def create_radar_chart(player_data, metrics):
    """Generate a radar chart for player metrics"""
    fig = px.line_polar(
        player_data, 
        r=metrics, 
        theta=metrics,
        line_close=True,
        template="plotly_dark"
    )
    fig.update_traces(fill='toself')
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=False
    )
    return fig

def format_value(x):
    """Format numeric values for display"""
    if isinstance(x, (int, float)):
        if x == int(x):
            return str(int(x))
        return f"{x:.2f}"
    return str(x)

# ==============================================
# FILTERING LOGIC
# ==============================================

@st.cache_data
def filter_players(_df, filters):
    """Apply all filters to the player dataframe"""
    filtered_df = _df.copy()
    
    # Position filter
    if filters['positions']:
        filtered_df = filtered_df[filtered_df['Position'].isin(filters['positions'])]
    
    # Team filter
    if filters['teams']:
        filtered_df = filtered_df[filtered_df['Team'].isin(filters['teams'])]
    
    # League filter
    if filters['leagues']:
        filtered_df = filtered_df[filtered_df['League'].isin(filters['leagues'])]
    
    # Age filter
    if 'Age' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['Age'] >= filters['age_range'][0]) & 
            (filtered_df['Age'] <= filters['age_range'][1])
        ]
    
    # Minutes played filter
    if 'Minutes played' in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df['Minutes played'] >= filters['minutes_range'][0]) & 
            (filtered_df['Minutes played'] <= filters['minutes_range'][1])
        ]
    
    # Metric range filters
    for metric, (min_val, max_val) in filters['metric_ranges'].items():
        if metric in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df[metric] >= min_val) & 
                (filtered_df[metric] <= max_val)
            ]
    
    # Nationality filter
    if filters['nationalities']:
        filtered_df = filtered_df[filtered_df['Passport country'].isin(filters['nationalities'])]
    
    return filtered_df.sort_values(by=filters['sort_by'], ascending=filters['sort_asc'])

# ==============================================
# UI COMPONENTS
# ==============================================

def create_metric_slider(metric_name, df, default_min=None, default_max=None):
    """Create a range slider for a metric"""
    if metric_name not in df.columns:
        return None, None
    
    min_val = float(df[metric_name].min())
    max_val = float(df[metric_name].max())
    
    if default_min is None:
        default_min = min_val
    if default_max is None:
        default_max = max_val
    
    values = st.slider(
        f"{metric_name} Range",
        min_val, max_val,
        (default_min, default_max),
        help=f"Filter players by {metric_name}"
    )
    return values

def create_player_card(player):
    """Create a visually appealing player card"""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Placeholder for player image (would be from API in production)
        st.image("https://via.placeholder.com/150x200?text=Player+Image", 
                width=150, caption=player['Player Name'])
    
    with col2:
        st.subheader(player['Player Name'])
        st.caption(f"{player['Position']} | {player['Team']} | {player['League']}")
        
        cols = st.columns(4)
        cols[0].metric("Age", player['Age'])
        cols[1].metric("Goals", player.get('Goals', 'N/A'))
        cols[2].metric("Assists", player.get('Assists', 'N/A'))
        cols[3].metric("Minutes", player.get('Minutes played', 'N/A'))
        
        # Add more detailed stats in an expander
        with st.expander("Detailed Stats"):
            detailed_stats = {
                'Goals per 90': player.get('Goals per 90', 'N/A'),
                'xG per 90': player.get('xG per 90', 'N/A'),
                'Assists per 90': player.get('Assists per 90', 'N/A'),
                'xA per 90': player.get('xA per 90', 'N/A'),
                'Pass Accuracy': player.get('Pass accuracy %', 'N/A'),
                'Tackles Won': player.get('Defensive duels won %', 'N/A')
            }
            for stat, value in detailed_stats.items():
                st.text(f"{stat}: {format_value(value)}")

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
    if 'Minutes played' in df.columns:
        min_minutes, max_minutes = int(df['Minutes played'].min()), int(df['Minutes played'].max())
        minutes_range = st.sidebar.slider(
            "Minutes Played", 
            min_minutes, max_minutes, 
            (min_minutes, max_minutes)
        )
    
    # Metric filters
    st.sidebar.markdown("### Performance Metrics")
    metric_ranges = {}
    
    for metric in ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']:
        if metric in df.columns:
            min_val = float(df[metric].min())
            max_val = float(df[metric].max())
            values = st.sidebar.slider(
                f"{metric} Range",
                min_val, max_val,
                (min_val, max_val)
            )
            metric_ranges[metric] = values
    
    # Sorting options
    st.sidebar.markdown("### Sorting")
    sort_by = st.sidebar.selectbox(
        "Sort by", 
        ['Player Name', 'Age', 'Minutes played', 'Goals', 'Assists'] + 
        [m for m in metric_ranges.keys()],
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
        'minutes_range': minutes_range if 'Minutes played' in df.columns else (0, 0),
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
            <span>Avg Goals/90: {filtered_df['Goals per 90'].mean():.2f}</span>
            <span>Avg xG/90: {filtered_df['xG per 90'].mean():.2f}</span>
            <span>Avg Assists/90: {filtered_df['Assists per 90'].mean():.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ==============================================
    # VISUALIZATION AND DATA DISPLAY
    # ==============================================
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Player List", "📊 Player Comparison", "📈 Analytics"])
    
    with tab1:
        # AG Grid for data display
        gb = GridOptionsBuilder.from_dataframe(filtered_df)
        
        # Configure grid options
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)
        gb.configure_default_column(
            groupable=True, 
            sortable=True, 
            resizable=True,
            filterable=True,
            editable=False,
            wrapText=True
        )
        
        # Add custom formatting for numeric columns
        for col in filtered_df.columns:
            if pd.api.types.is_numeric_dtype(filtered_df[col]):
                gb.configure_column(col, type=["numericColumn", "numberColumnFilter"])
        
        # Add a custom "View Profile" button
        gb.configure_column(
            "Player Name",
            cellRenderer=JsCode('''
                function(params) {
                    return `<a href="#${params.value}" style="color: #4f8bf9; text-decoration: none;">${params.value}</a>`;
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
            fit_columns_on_grid_load=True
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
        st.subheader("Player Comparison Tool")
        
        # Select players to compare
        selected_players = st.multiselect(
            "Select up to 5 players to compare",
            filtered_df['Player Name'].unique(),
            max_selections=5
        )
        
        if selected_players:
            compare_df = filtered_df[filtered_df['Player Name'].isin(selected_players)]
            
            # Radar chart comparison
            metrics_to_compare = ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']
            if all(m in compare_df.columns for m in metrics_to_compare):
                fig = px.line_polar(
                    compare_df, 
                    r=metrics_to_compare, 
                    theta=metrics_to_compare,
                    line_close=True,
                    color='Player Name',
                    template="plotly_white"
                )
                fig.update_traces(fill='toself')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Some metrics are missing for comparison")
            
            # Display comparison table
            st.dataframe(
                compare_df.set_index('Player Name')[metrics_to_compare].style
                    .background_gradient(cmap='Blues')
                    .format("{:.2f}"),
                use_container_width=True
            )
    
    with tab3:
        st.subheader("League Analytics")
        
        # League comparison charts
        if 'League' in filtered_df.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                league_goals = filtered_df.groupby('League')['Goals per 90'].mean().sort_values()
                fig = px.bar(
                    league_goals,
                    orientation='h',
                    title='Average Goals per 90 by League',
                    labels={'value': 'Goals per 90', 'index': 'League'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                league_xg = filtered_df.groupby('League')['xG per 90'].mean().sort_values()
                fig = px.bar(
                    league_xg,
                    orientation='h',
                    title='Average xG per 90 by League',
                    labels={'value': 'xG per 90', 'index': 'League'}
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
