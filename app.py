import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode # JsCode is still imported but not used for cellRenderer as before
from datetime import datetime
import plotly.express as px
import numpy as np

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
            else:
                st.error(f"Failed to download database. Status code: {response.status_code}")
                st.stop()
        except requests.exceptions.RequestException as e:
            st.error(f"Download error: {str(e)}. Please check your internet connection or the URL.")
            st.stop()
        except Exception as e:
            st.error(f"An unexpected error occurred during download: {str(e)}")
            st.stop()


    # Connect and load data
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM Player", conn)

        # Data cleaning and transformation
        df = df.rename(columns={'Player': 'Player Name'})  # Standardize column name
        df = df.dropna(subset=['Player Name'], how='all') # Drop rows where 'Player Name' is entirely NaN

        # Convert numeric columns to appropriate types to avoid future errors
        numeric_cols_to_convert = ['Age', 'Minutes played', 'Goals', 'xG', 'Assists', 'xA', 'Pass accuracy %', 'Defensive duels won %']
        for col in numeric_cols_to_convert:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # Coerce to numeric, fill NaN with 0

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
    except sqlite3.Error as e:
        st.error(f"SQLite database error: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Database loading or processing error: {str(e)}")
        st.stop()
    finally:
        if 'conn' in locals() and conn: # Ensure conn exists and is not None before closing
            conn.close()

# ==============================================
# UTILITY FUNCTIONS
# ==============================================

def safe_mean(series, format_str=".2f"):
    """Safely calculate mean with formatting, handling missing columns and non-numeric data"""
    if series is None or series.empty or not pd.api.types.is_numeric_dtype(series):
        return "N/A"
    mean_val = series.mean()
    if pd.isna(mean_val):
        return "N/A"
    return f"{mean_val:{format_str}}"

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
    min_age_val, max_age_val = int(df['Age'].min()), int(df['Age'].max())
    age_range = st.sidebar.slider(
        "Age Range",
        min_age_val, max_age_val,
        (min_age_val, max_age_val)
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
    else:
        minutes_range = (0, 0) # Default if 'Minutes played' column is missing

    # Performance metric filters
    st.sidebar.markdown("### Performance Metrics")
    metric_ranges = {}

    metric_columns = ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90']
    for metric in metric_columns:
        if metric in df.columns:
            min_val = float(df[metric].min())
            max_val = float(df[metric].max())
            step = 0.01 if max_val - min_val < 5 else 0.1 # Adjust step for small ranges
            values = st.sidebar.slider(
                f"{metric} Range",
                min_val, max_val,
                (min_val, max_val),
                step=step,
                help=f"Filter players by {metric}"
            )
            metric_ranges[metric] = values

    # Sorting options
    st.sidebar.markdown("### Sorting")
    # Dynamically build sort options based on available columns
    available_sort_columns = [col for col in ['Player Name', 'Age', 'Minutes played', 'Goals', 'Assists'] + list(metric_ranges.keys()) if col in df.columns]
    sort_by = st.sidebar.selectbox(
        "Sort by",
        available_sort_columns,
        index=0 if available_sort_columns else None
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
        'minutes_range': minutes_range, # Use the defined minutes_range
        'metric_ranges': metric_ranges,
        'sort_by': sort_by,
        'sort_asc': sort_asc
    }

    # Apply filters
    filtered_df = df.copy()

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

    # Display summary stats with safe formatting
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:10px;border-radius:5px;margin-bottom:20px;">
        <h4 style="margin:0;">📊 Summary: {len(filtered_df)} players found</h4>
        <div style="display:flex;justify-content:space-between;">
            <span>Avg Age: {safe_mean(filtered_df['Age'], '.1f')}</span>
            <span>Avg Goals/90: {safe_mean(filtered_df.get('Goals per 90', pd.Series()))}</span>
            <span>Avg xG/90: {safe_mean(filtered_df.get('xG per 90', pd.Series()))}</span>
            <span>Avg Assists/90: {safe_mean(filtered_df.get('Assists per 90', pd.Series()))}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs for different views (MOVED INSIDE main())
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
            # Format numeric columns for display
            if col in ['Goals per 90', 'xG per 90', 'Assists per 90', 'xA per 90', 'Pass accuracy %', 'Defensive duels won %']:
                 gb.configure_column(col, type=["numericColumn", "numberColumnFilter"], valueFormatter=JsCode("function(params) { return params.value != null ? params.value.toFixed(2) : 'N/A'; }").js_code)
            elif col in ['Age', 'Minutes played', 'Goals', 'Assists', 'xG', 'xA']: # Integer-like metrics
                 gb.configure_column(col, type=["numericColumn", "numberColumnFilter"], valueFormatter=JsCode("function(params) { return params.value != null ? Math.round(params.value) : 'N/A'; }").js_code)
            else:
                 gb.configure_column(col, type=["numericColumn", "numberColumnFilter"])


        # Enable row selection
        gb.configure_selection('single', use_checkbox=True) # or 'multiple' if you want

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

        # Get selected rows
        selected_players_from_grid = grid_response.get('selected_rows', [])

        # If a player is selected in the grid, set it in session state for the profile tab
        # This will trigger a rerun and update the selectbox in tab2
        if selected_players_from_grid:
            st.session_state['selected_player_for_profile_tab'] = selected_players_from_grid[0]['Player Name']
        elif 'selected_player_for_profile_tab' not in st.session_state:
            st.session_state['selected_player_for_profile_tab'] = None

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
            player_names = filtered_df['Player Name'].unique()

            # Determine default value for selectbox
            default_player_index = 0
            if st.session_state.get('selected_player_for_profile_tab') and \
               st.session_state['selected_player_for_profile_tab'] in player_names:
                default_player_index = list(player_names).index(st.session_state['selected_player_for_profile_tab'])
            elif player_names.size > 0: # If no specific player selected but there are players, select the first one
                st.session_state['selected_player_for_profile_tab'] = player_names[0]
                default_player_index = 0
            else: # No players at all
                st.session_state['selected_player_for_profile_tab'] = None
                default_player_index = 0


            selected_player = st.selectbox(
                "Select a player to view detailed profile",
                player_names,
                index=default_player_index,
                key='player_profile_selector' # Add a key for uniqueness if needed elsewhere
            )

            if selected_player:
                player_data = filtered_df[filtered_df['Player Name'] == selected_player].iloc[0]

                with st.container():
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        # Placeholder image (replace with actual player images if available)
                        st.image(
                            "https://via.placeholder.com/150x200?text=Player+Image",
                            width=150,
                            caption=player_data['Player Name']
                        )

                    with col2:
                        st.subheader(player_data['Player Name'])
                        st.caption(f"{player_data.get('Position', 'N/A')} | {player_data.get('Team', 'N/A')} | {player_data.get('League', 'N/A')}")

                        cols = st.columns(4)
                        metric_config = [
                            ('Age', 'Age'),
                            ('Goals', 'Goals'),
                            ('Assists', 'Assists'),
                            ('Minutes', 'Minutes played')
                        ]

                        for i, (display_name, col_name) in enumerate(metric_config):
                            if col_name in player_data and pd.notna(player_data[col_name]):
                                value = player_data[col_name]
                                cols[i].metric(display_name, int(value) if isinstance(value, (int, float)) else value)
                            else:
                                cols[i].metric(display_name, 'N/A')

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
                                if col_name in player_data and pd.notna(player_data[col_name]):
                                    value = player_data[col_name]
                                    if isinstance(value, (int, float)):
                                        st.text(f"{display_name}: {value:.2f}" if isinstance(value, float) else f"{display_name}: {value}")
                                    else:
                                        st.text(f"{display_name}: {value}")
                                else:
                                    st.text(f"{display_name}: N/A")

    with tab3:
        st.subheader("League Analytics")

        if 'League' in filtered_df.columns and not filtered_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                # Ensure only numeric columns are used for aggregation
                agg_cols = [col for col in ['Age', 'Goals per 90', 'Assists per 90'] if col in filtered_df.columns]
                if agg_cols:
                    league_stats = filtered_df.groupby('League')[agg_cols].mean().reset_index()

                    if 'Goals per 90' in league_stats.columns:
                        fig = px.bar(
                            league_stats.sort_values('Goals per 90'),
                            x='Goals per 90',
                            y='League',
                            orientation='h',
                            title='Average Goals per 90 by League'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Goals per 90 data not available for league analytics.")
                else:
                    st.info("No numeric columns available for league aggregation.")


            with col2:
                if agg_cols and 'Assists per 90' in league_stats.columns:
                    fig = px.bar(
                        league_stats.sort_values('Assists per 90'),
                        x='Assists per 90',
                        y='League',
                        orientation='h',
                        title='Average Assists per 90 by League'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Assists per 90 data not available for league analytics.")

        else:
            st.info("No 'League' column or data available for league analytics.")

        # Age distribution
        if 'Age' in filtered_df.columns and not filtered_df.empty:
            fig = px.histogram(
                filtered_df,
                x='Age',
                nbins=20,
                title='Player Age Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No 'Age' data available for age distribution analysis.")

if __name__ == "__main__":
    main()
