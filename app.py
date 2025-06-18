The current time is Wednesday, June 18, 2025 at 9:52:40 AM CEST.

Let's elevate your Wyscout Player Finder Pro to a more complete, sophisticated, and professional level. This involves adding more detailed metrics, enhanced visualizations, customizability, and a more robust user experience.

Here's a breakdown of the planned enhancements and the full, revised code:

**Key Enhancements:**

1.  **More Metrics & Categories:**
    * **Attacking:** Shots, Shots on Target, Dribbles, Touches in Box, Key Passes, Crosses.
    * **Passing:** Total Passes, Accurate Passes, Long Passes, Short Passes, Progressive Passes.
    * **Defensive:** Interceptions, Tackles, Blocks, Clearances, Aerial Duels Won.
    * **Goalkeeping (if applicable):** Saves, Clean Sheets, Goals Conceded.
    * **New "Per 90" Calculations:** Extend per 90 calculations to all relevant new metrics (e.g., Shots per 90, Interceptions per 90).

2.  **Advanced Filtering Options:**
    * **Foot Preference:** Left, Right, Both.
    * **Contract Expiration (if available):** Slider for contract year.
    * **Market Value (if available):** Slider for estimated market value.
    * **Role-Specific Filters:** Allow filtering by more granular roles (e.g., "Deep-lying Playmaker" within "Midfielder"). This would require adding a 'Role' column or deriving it. For simplicity, we'll stick to 'Position' but expand on how you *could* add roles.

3.  **Sophisticated Visualizations (Plotly Express):**
    * **Player Profile Radar Charts (or similar):** A comparison of a selected player's key stats against the average of filtered players in their position/league. This requires more complex data processing.
    * **Metric Distribution Histograms:** Visualize the distribution of key metrics (e.g., 'Goals per 90') across the filtered dataset.
    * **Scatter Plots for Player Comparison:** e.g., 'xG per 90' vs. 'xA per 90' to identify creative forwards.
    * **Team/League Comparison Charts:** Bar charts for average stats across teams/leagues.

4.  **Enhanced Player Profile Display:**
    * **Metric Categorization:** Group metrics into sections (General, Attacking, Passing, Defensive, Goalkeeping).
    * **Percentage-based Metrics:** Display relevant metrics as percentages (e.g., Pass Accuracy %).
    * **Contextual Information:** Add Passport Country, Preferred Foot, Height, Weight.

5.  **Professional UI/UX:**
    * **Clearer Headings and Explanations.**
    * **More Tooltips/Help Text.**
    * **Dynamic UI Elements:** Filters update based on available data.
    * **Improved AgGrid Configuration:** More custom column formatting (decimals, percentages).
    * **Export Options:** Keep CSV export.

6.  **Data Robustness:**
    * **More comprehensive error handling** in data loading and processing.
    * **Handling of missing data** more gracefully for calculations and displays (e.g., `fillna(0)` or 'N/A').

**Assumptions & Notes for New Metrics:**

For the new metrics, I'll add them as columns in the code with default values (0 or 'N/A') and placeholder comments. In a real Wyscout database, you would need to ensure these columns actually exist and are populated.

---

Here's the expanded code:

```python
import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
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
        st.info("Downloading player database for the first time... This may take a moment.")
        try:
            response = requests.get(DB_URL, timeout=30) # Increased timeout
            if response.status_code == 200:
                with open(DB_PATH, 'wb') as f:
                    f.write(response.content)
                st.success("Database downloaded successfully!")
            else:
                st.error(f"Failed to download database. Status code: {response.status_code}. Please check the URL.")
                st.stop()
        except requests.exceptions.Timeout:
            st.error("Download timed out. Please check your internet connection or try again.")
            st.stop()
        except requests.exceptions.RequestException as e:
            st.error(f"Network error during download: {str(e)}. Please check your internet connection.")
            st.stop()
        except Exception as e:
            st.error(f"An unexpected error occurred during database download: {str(e)}")
            st.stop()

    # Connect and load data
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM Player", conn)

        # Initial Data Cleaning and Transformation
        df = df.rename(columns={'Player': 'Player Name'})
        df = df.dropna(subset=['Player Name'], how='all') # Ensure valid player names

        # Standardize column names (e.g., remove leading/trailing spaces, replace problematic characters)
        df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('%', 'Perc')

        # Convert relevant columns to numeric, coercing errors and filling NaNs
        numeric_cols_to_process = [
            'Age', 'Height', 'Weight', 'Minutes_played',
            'Goals', 'xG', 'Assists', 'xA', 'Shots', 'Shots_on_target',
            'Dribbles_attempted', 'Dribbles_completed', 'Touches_in_box', 'Key_passes',
            'Crosses_attempted', 'Crosses_completed', 'Total_passes', 'Accurate_passes',
            'Long_passes', 'Short_passes', 'Progressive_passes',
            'Interceptions', 'Tackles', 'Blocks', 'Clearances', 'Aerial_duels_won',
            'Saves', 'Clean_sheets', 'Goals_conceded' # Add new metrics
        ]

        for col in numeric_cols_to_process:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                # Add missing columns with default 0 if they don't exist in the database
                # In a real scenario, you'd ensure your DB schema is complete
                df[col] = 0

        # Calculate per 90 metrics for a comprehensive set of stats
        # Ensure 'Minutes_played' is numeric and > 0 for division
        minutes_condition = df['Minutes_played'] > 0
        metrics_for_per90 = [
            'Goals', 'xG', 'Assists', 'xA', 'Shots', 'Shots_on_target',
            'Dribbles_completed', 'Touches_in_box', 'Key_passes',
            'Accurate_passes', 'Progressive_passes',
            'Interceptions', 'Tackles', 'Blocks', 'Clearances', 'Aerial_duels_won',
            'Saves', 'Goals_conceded'
        ]

        for metric in metrics_for_per90:
            per90_col_name = f"{metric}_per_90"
            if metric in df.columns:
                df[per90_col_name] = np.where(
                    minutes_condition,
                    (df[metric] / df['Minutes_played']) * 90,
                    0
                )
            else:
                df[per90_col_name] = 0 # Default to 0 if base metric missing

        # Calculate percentage metrics
        if 'Accurate_passes' in df.columns and 'Total_passes' in df.columns:
            df['Pass_Accuracy_Perc'] = np.where(
                df['Total_passes'] > 0,
                (df['Accurate_passes'] / df['Total_passes']) * 100,
                0
            )
        else:
            df['Pass_Accuracy_Perc'] = 0

        if 'Dribbles_completed' in df.columns and 'Dribbles_attempted' in df.columns:
            df['Dribble_Success_Perc'] = np.where(
                df['Dribbles_attempted'] > 0,
                (df['Dribbles_completed'] / df['Dribbles_attempted']) * 100,
                0
            )
        else:
            df['Dribble_Success_Perc'] = 0

        # Ensure 'Passport_country' and 'Preferred_foot' exist and are string types
        if 'Passport_country' not in df.columns:
            df['Passport_country'] = 'Unknown'
        if 'Preferred_foot' not in df.columns:
            df['Preferred_foot'] = 'Unknown' # Add Preferred_foot if not exists

        # Example: Add 'Contract_expires' and 'Market_value_eur' if they don't exist
        # In a real Wyscout DB, these would be present.
        if 'Contract_expires' not in df.columns:
            df['Contract_expires'] = pd.to_datetime('2025-06-30') # Example default
        df['Contract_expires_year'] = pd.to_datetime(df['Contract_expires'], errors='coerce').dt.year.fillna(2100).astype(int)

        if 'Market_value_eur' not in df.columns:
            df['Market_value_eur'] = np.random.randint(500000, 50000000, size=len(df)) # Placeholder random values

        # Normalize Position names for better grouping (optional, depends on data)
        # e.g., 'AML', 'AMR', 'AMC' -> 'Attacking Midfielder'
        # This requires detailed knowledge of your 'Position' column values.
        # For this example, we'll assume 'Position' is already somewhat consistent.

        return df
    except sqlite3.Error as e:
        st.error(f"SQLite database error: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Database loading or processing error: {str(e)}")
        st.stop()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# ==============================================
# UTILITY FUNCTIONS
# ==============================================

def safe_mean(series, format_str=".2f"):
    """Safely calculate mean with formatting, handling missing columns and non-numeric data"""
    if series is None or series.empty or not pd.api.types.is_numeric_dtype(series) or series.isnull().all():
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
    with st.spinner("Loading and processing player database..."):
        df = load_database()

    if df.empty:
        st.warning("No player data available after loading. Please check the database file and processing steps.")
        st.stop()

    # ==============================================
    # SIDEBAR - FILTERS
    # ==============================================

    st.sidebar.title("🔍 Advanced Filters")
    st.sidebar.markdown("---")

    # Dynamic filter options based on available data
    positions = sorted(df['Position'].dropna().unique())
    teams = sorted(df['Team'].dropna().unique())
    leagues = sorted(df['League'].dropna().unique())
    nationalities = sorted(df['Passport_country'].dropna().unique())
    preferred_feet = sorted(df['Preferred_foot'].dropna().unique())

    selected_positions = st.sidebar.multiselect(
        "Positions",
        positions,
        default=[],
        help="Select one or more playing positions (e.g., CB, CM, ST)."
    )

    selected_teams = st.sidebar.multiselect(
        "Teams",
        teams,
        default=[],
        help="Filter players by their current club team."
    )

    selected_leagues = st.sidebar.multiselect(
        "Leagues",
        leagues,
        default=[],
        help="Filter players by the competition they currently play in."
    )

    selected_nationalities = st.sidebar.multiselect(
        "Nationalities",
        nationalities,
        default=[],
        help="Filter players by their passport country."
    )

    selected_foot = st.sidebar.multiselect(
        "Preferred Foot",
        preferred_feet,
        default=[],
        help="Filter by the player's preferred foot (Left, Right, Both)."
    )

    # Age filter
    min_age_val, max_age_val = int(df['Age'].min()), int(df['Age'].max())
    age_range = st.sidebar.slider(
        "Age Range",
        min_age_val, max_age_val,
        (min_age_val, max_age_val),
        help="Filter players by their age."
    )

    # Minutes played filter
    min_minutes, max_minutes = 0, 0
    if 'Minutes_played' in df.columns and not df['Minutes_played'].empty:
        min_minutes, max_minutes = int(df['Minutes_played'].min()), int(df['Minutes_played'].max())
        minutes_range = st.sidebar.slider(
            "Minutes Played (Season)",
            min_minutes, max_minutes,
            (min_minutes, max_minutes),
            help="Filter players by total minutes played in the season."
        )
    else:
        minutes_range = (0, 0)
        st.sidebar.info("Minutes Played data not available.")

    # Contract Expiration Filter
    if 'Contract_expires_year' in df.columns and not df['Contract_expires_year'].empty:
        min_contract_year, max_contract_year = int(df['Contract_expires_year'].min()), int(df['Contract_expires_year'].max())
        contract_year_range = st.sidebar.slider(
            "Contract Expiration Year",
            min_contract_year, max_contract_year,
            (min_contract_year, max_contract_year),
            help="Filter players by the year their contract expires."
        )
    else:
        contract_year_range = (0, 0)
        st.sidebar.info("Contract Expiration data not available.")

    # Market Value Filter (Example, assuming EUR)
    if 'Market_value_eur' in df.columns and not df['Market_value_eur'].empty:
        min_value, max_value = int(df['Market_value_eur'].min()), int(df['Market_value_eur'].max())
        market_value_range = st.sidebar.slider(
            "Market Value (€)",
            min_value, max_value,
            (min_value, max_value),
            format="€%d",
            help="Filter players by their estimated market value in Euros."
        )
    else:
        market_value_range = (0, 0)
        st.sidebar.info("Market Value data not available.")


    # Performance Metric filters
    st.sidebar.markdown("### Performance Metrics (per 90)")
    metric_ranges = {}

    # Define a broader set of metrics for filtering
    advanced_metric_columns = [
        'Goals_per_90', 'xG_per_90', 'Assists_per_90', 'xA_per_90',
        'Shots_per_90', 'Key_passes_per_90', 'Dribbles_completed_per_90', 'Touches_in_box_per_90',
        'Accurate_passes_per_90', 'Progressive_passes_per_90',
        'Interceptions_per_90', 'Tackles_per_90', 'Aerial_duels_won_per_90'
    ]

    for metric in advanced_metric_columns:
        if metric in df.columns and not df[metric].empty:
            min_val = float(df[metric].min())
            max_val = float(df[metric].max())
            step = 0.01 if max_val - min_val < 5 else 0.1
            values = st.sidebar.slider(
                f"{metric.replace('_', ' ').replace('per 90', '/90')}", # Nicer display name
                min_val, max_val,
                (min_val, max_val),
                step=step,
                help=f"Filter players by {metric.replace('_', ' ').lower()} per 90 minutes."
            )
            metric_ranges[metric] = values

    # Sorting options
    st.sidebar.markdown("### Sorting Options")
    # Include all relevant columns for sorting
    sort_options_list = ['Player Name', 'Age', 'Minutes_played', 'Goals', 'Assists',
                         'Goals_per_90', 'xG_per_90', 'Assists_per_90', 'xA_per_90',
                         'Market_value_eur', 'Contract_expires_year'] + list(metric_ranges.keys())
    # Filter sort options to only include columns actually present in the DataFrame
    sort_options_list = [col for col in sort_options_list if col in df.columns]
    sort_by = st.sidebar.selectbox(
        "Sort by",
        sort_options_list,
        index=0 if sort_options_list else None,
        help="Choose a metric to sort the player list by."
    )
    sort_asc = st.sidebar.checkbox("Ascending", False, help="Check for ascending (A-Z, 0-9) order, uncheck for descending.")


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
        <p class="big-font">**Find, Analyze, and Compare** Football Players with Advanced Scouting Metrics.</p>
        <p>Utilize the filters on the sidebar to refine your search and explore detailed player profiles and analytics.</p>
        """, unsafe_allow_html=True)

    # Prepare filters dictionary
    filters = {
        'positions': selected_positions,
        'teams': selected_teams,
        'leagues': selected_leagues,
        'nationalities': selected_nationalities,
        'preferred_foot': selected_foot,
        'age_range': age_range,
        'minutes_range': minutes_range,
        'contract_year_range': contract_year_range,
        'market_value_range': market_value_range,
        'metric_ranges': metric_ranges,
        'sort_by': sort_by,
        'sort_asc': sort_asc
    }

    # Apply filters
    filtered_df = df.copy()

    # Apply all general filters
    if filters.get('positions'):
        filtered_df = filtered_df[filtered_df['Position'].isin(filters['positions'])]
    if filters.get('teams'):
        filtered_df = filtered_df[filtered_df['Team'].isin(filters['teams'])]
    if filters.get('leagues'):
        filtered_df = filtered_df[filtered_df['League'].isin(filters['leagues'])]
    if filters.get('nationalities'):
        filtered_df = filtered_df[filtered_df['Passport_country'].isin(filters['nationalities'])]
    if filters.get('preferred_foot'):
        filtered_df = filtered_df[filtered_df['Preferred_foot'].isin(filters['preferred_foot'])]

    # Apply range filters
    if 'Age' in filtered_df.columns and filters.get('age_range'):
        filtered_df = filtered_df[
            (filtered_df['Age'] >= filters['age_range'][0]) &
            (filtered_df['Age'] <= filters['age_range'][1])
        ]
    if 'Minutes_played' in filtered_df.columns and filters.get('minutes_range'):
        filtered_df = filtered_df[
            (filtered_df['Minutes_played'] >= filters['minutes_range'][0]) &
            (filtered_df['Minutes_played'] <= filters['minutes_range'][1])
        ]
    if 'Contract_expires_year' in filtered_df.columns and filters.get('contract_year_range'):
        filtered_df = filtered_df[
            (filtered_df['Contract_expires_year'] >= filters['contract_year_range'][0]) &
            (filtered_df['Contract_expires_year'] <= filters['contract_year_range'][1])
        ]
    if 'Market_value_eur' in filtered_df.columns and filters.get('market_value_range'):
        filtered_df = filtered_df[
            (filtered_df['Market_value_eur'] >= filters['market_value_range'][0]) &
            (filtered_df['Market_value_eur'] <= filters['market_value_range'][1])
        ]

    # Apply metric range filters
    for metric, (min_val, max_val) in filters.get('metric_ranges', {}).items():
        if metric in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df[metric] >= min_val) &
                (filtered_df[metric] <= max_val)
            ]

    # Sorting
    if filters.get('sort_by') and filters['sort_by'] in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=filters['sort_by'],
            ascending=filters.get('sort_asc', False) # Default to descending for performance metrics
        )

    # Display summary stats
    st.markdown(f"""
    <div style="background-color:#e6f7ff;padding:15px;border-left:5px solid #4f8bf9;border-radius:5px;margin-bottom:20px;">
        <h4 style="margin:0;color:#0056b3;">📊 Search Results Summary: <span style="color:#28a745;">{len(filtered_df)}</span> Players Found</h4>
        <div style="display:flex;justify-content:space-around;flex-wrap:wrap;margin-top:10px;">
            <div style="margin:5px 15px;"><strong>Avg. Age:</strong> {safe_mean(filtered_df.get('Age', pd.Series()), '.1f')}</div>
            <div style="margin:5px 15px;"><strong>Avg. Mins Played:</strong> {safe_mean(filtered_df.get('Minutes_played', pd.Series()), 'd')}</div>
            <div style="margin:5px 15px;"><strong>Avg. Goals/90:</strong> {safe_mean(filtered_df.get('Goals_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. xG/90:</strong> {safe_mean(filtered_df.get('xG_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. Assists/90:</strong> {safe_mean(filtered_df.get('Assists_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. xA/90:</strong> {safe_mean(filtered_df.get('xA_per_90', pd.Series()))}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 Player List", "👤 Player Profiles", "📈 Advanced Analytics"])

    with tab1:
        st.header("Player List")
        st.write("Browse and filter players. Select a row to view the player's detailed profile in the 'Player Profiles' tab.")

        # AG Grid configuration
        gb = GridOptionsBuilder.from_dataframe(filtered_df)

        # Configure default columns
        gb.configure_default_column(
            groupable=True,
            sortable=True,
            resizable=True,
            filterable=True,
            editable=False,
            wrapText=True,
            # Set default width for all columns. Can be overridden individually.
            # This is a good starting point for professional look.
            width=150
        )

        # Configure pagination
        gb.configure_pagination(
            paginationAutoPageSize=False,
            paginationPageSize=25 # Display 25 rows per page
        )

        # Configure specific columns with custom formatting
        # Make a list of columns to display prominently, order them
        display_cols = [
            'Player Name', 'Position', 'Team', 'League', 'Age', 'Minutes_played',
            'Goals', 'Assists', 'Goals_per_90', 'xG_per_90', 'Assists_per_90', 'xA_per_90',
            'Shots_per_90', 'Key_passes_per_90', 'Accurate_passes_Perc', 'Dribble_Success_Perc',
            'Interceptions_per_90', 'Tackles_per_90', 'Aerial_duels_won_per_90',
            'Passport_country', 'Preferred_foot', 'Height', 'Weight',
            'Contract_expires_year', 'Market_value_eur'
        ]

        # Hide columns not in display_cols or that were only for intermediate calculation
        for col in filtered_df.columns:
            if col not in display_cols:
                gb.configure_column(col, hide=True)

        # Explicitly configure display columns for order and formatting
        for col in display_cols:
            if col in filtered_df.columns: # Ensure column exists
                if '_per_90' in col:
                    gb.configure_column(col, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? params.value.toFixed(2) : 'N/A'; }").js_code,
                                        headerName=col.replace('_', ' ').replace('per 90', '/90')) # Make header name prettier
                elif '_Perc' in col:
                     gb.configure_column(col, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? params.value.toFixed(1) + '%' : 'N/A'; }").js_code,
                                        headerName=col.replace('_', ' '))
                elif col == 'Market_value_eur':
                    gb.configure_column(col, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? '€' + params.value.toLocaleString() : 'N/A'; }").js_code,
                                        headerName="Market Value (€)")
                elif col == 'Player Name':
                    gb.configure_column(col, headerName="Player Name", width=200, sortable=True, filterable=True)
                elif col in ['Goals', 'Assists', 'Minutes_played', 'Age', 'Height', 'Weight', 'Contract_expires_year']:
                    gb.configure_column(col, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? Math.round(params.value) : 'N/A'; }").js_code,
                                        headerName=col.replace('_', ' '))
                else:
                    gb.configure_column(col, headerName=col.replace('_', ' '))


        # Enable row selection for detailed view
        gb.configure_selection('single', use_checkbox=True, groupSelectsChildren=True)

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
            fit_columns_on_grid_load=False, # Set to False to respect manual column widths
            key='players_grid'
        )

        # Get selected rows
        selected_players_from_grid = grid_response.get('selected_rows', [])

        # If a player is selected in the grid, update session state to reflect in profile tab
        if selected_players_from_grid:
            st.session_state['selected_player_for_profile_tab'] = selected_players_from_grid[0]['Player Name']
        elif 'selected_player_for_profile_tab' not in st.session_state:
            st.session_state['selected_player_for_profile_tab'] = None

        st.download_button(
            "💾 Download Filtered Data (CSV)",
            filtered_df.to_csv(index=False).encode('utf-8'), # Ensure UTF-8 encoding
            "filtered_players.csv",
            "text/csv",
            key='download-csv'
        )

    with tab2:
        st.header("Player Profiles")
        st.write("View detailed statistics and performance insights for a selected player.")

        if filtered_df.empty:
            st.warning("No players match your filters. Adjust filters to see profiles.")
        else:
            player_names = filtered_df['Player Name'].unique()

            # Determine default selection for the selectbox
            default_player_index = 0
            if st.session_state.get('selected_player_for_profile_tab') and \
               st.session_state['selected_player_for_profile_tab'] in player_names:
                default_player_index = list(player_names).index(st.session_state['selected_player_for_profile_tab'])
            elif player_names.size > 0:
                # If no specific player selected (e.g., first run or grid cleared), select the first one in the filtered list
                st.session_state['selected_player_for_profile_tab'] = player_names[0]
                default_player_index = 0
            else: # No players at all
                st.session_state['selected_player_for_profile_tab'] = None
                default_player_index = 0 # Fallback

            selected_player = st.selectbox(
                "Select a player to view detailed profile:",
                player_names,
                index=default_player_index,
                key='player_profile_selector'
            )

            if selected_player:
                player_data = filtered_df[filtered_df['Player Name'] == selected_player].iloc[0]

                st.markdown(f"<h3 id='player-profile-{selected_player.replace(' ', '-')}' style='color:#4f8bf9;'>{player_data['Player Name']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Position:** {player_data.get('Position', 'N/A')} | **Team:** {player_data.get('Team', 'N/A')} | **League:** {player_data.get('League', 'N/A')}")
                st.markdown(f"**Nationality:** {player_data.get('Passport_country', 'N/A')} | **Preferred Foot:** {player_data.get('Preferred_foot', 'N/A')}")
                st.markdown(f"**Age:** {int(player_data.get('Age', 0))} | **Height:** {int(player_data.get('Height', 0))} cm | **Weight:** {int(player_data.get('Weight', 0))} kg")
                st.markdown(f"**Contract Expires:** {player_data.get('Contract_expires_year', 'N/A')} | **Market Value:** {'€' + f'{player_data.get("Market_value_eur", 0):,.0f}' if player_data.get('Market_value_eur') else 'N/A'}")

                st.markdown("---")

                # Player Profile Radar Chart (Comparison against filtered average)
                st.subheader("Performance Radar Chart")
                st.write("Compares the player's key per 90 metrics against the average of all currently filtered players in their primary position.")

                # Filter by primary position for comparison average
                position_filtered_df = filtered_df[filtered_df['Position'] == player_data['Position']]
                if not position_filtered_df.empty:
                    # Metrics for radar chart
                    radar_metrics = [
                        'Goals_per_90', 'xG_per_90', 'Assists_per_90', 'xA_per_90',
                        'Shots_per_90', 'Key_passes_per_90', 'Dribbles_completed_per_90',
                        'Interceptions_per_90', 'Tackles_per_90', 'Aerial_duels_won_per_90'
                    ]
                    # Ensure metrics are present and numeric
                    radar_metrics = [m for m in radar_metrics if m in position_filtered_df.columns and pd.api.types.is_numeric_dtype(position_filtered_df[m])]

                    if radar_metrics:
                        player_values = [player_data[m] for m in radar_metrics]
                        avg_values = [position_filtered_df[m].mean() for m in radar_metrics]

                        # Scale values for radar chart (0-1) based on max values in the filtered set
                        max_values = [position_filtered_df[m].max() for m in radar_metrics]
                        max_values = [mv if mv > 0 else 1 for mv in max_values] # Avoid division by zero

                        player_scaled = [val / mx if mx > 0 else 0 for val, mx in zip(player_values, max_values)]
                        avg_scaled = [val / mx if mx > 0 else 0 for val, mx in zip(avg_values, max_values)]

                        fig_radar = go.Figure()

                        fig_radar.add_trace(go.Scatterpolar(
                            r=player_scaled,
                            theta=[m.replace('_', ' ').replace('per 90', '/90') for m in radar_metrics],
                            fill='toself',
                            name=player_data['Player Name'],
                            marker_color='blue',
                            opacity=0.7
                        ))
                        fig_radar.add_trace(go.Scatterpolar(
                            r=avg_scaled,
                            theta=[m.replace('_', ' ').replace('per 90', '/90') for m in radar_metrics],
                            fill='toself',
                            name=f'Avg. {player_data["Position"]}',
                            marker_color='red',
                            opacity=0.4
                        ))

                        fig_radar.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 1]
                                )),
                            showlegend=True,
                            title=f"Performance Comparison: {player_data['Player Name']} vs. Avg. {player_data['Position']}"
                        )
                        st.plotly_chart(fig_radar, use_container_width=True)
                    else:
                        st.info("Insufficient numeric data for radar chart.")
                else:
                    st.info(f"Not enough players in {player_data['Position']} to generate a meaningful comparison radar chart.")


                st.subheader("Key Performance Metrics")
                cols_general = st.columns(4)
                cols_general[0].metric("Age", int(player_data.get('Age', 'N/A')))
                cols_general[1].metric("Minutes Played", int(player_data.get('Minutes_played', 'N/A')))
                cols_general[2].metric("Height (cm)", int(player_data.get('Height', 'N/A')))
                cols_general[3].metric("Weight (kg)", int(player_data.get('Weight', 'N/A')))

                st.markdown("#### Attacking")
                cols_att = st.columns(4)
                cols_att[0].metric("Goals", int(player_data.get('Goals', 0)))
                cols_att[1].metric("xG", f"{player_data.get('xG', 0):.2f}")
                cols_att[2].metric("Assists", int(player_data.get('Assists', 0)))
                cols_att[3].metric("xA", f"{player_data.get('xA', 0):.2f}")

                cols_att_p90 = st.columns(4)
                cols_att_p90[0].metric("Goals/90", f"{player_data.get('Goals_per_90', 0):.2f}")
                cols_att_p90[1].metric("xG/90", f"{player_data.get('xG_per_90', 0):.2f}")
                cols_att_p90[2].metric("Assists/90", f"{player_data.get('Assists_per_90', 0):.2f}")
                cols_att_p90[3].metric("xA/90", f"{player_data.get('xA_per_90', 0):.2f}")

                cols_att_detail = st.columns(4)
                cols_att_detail[0].metric("Shots/90", f"{player_data.get('Shots_per_90', 0):.2f}")
                cols_att_detail[1].metric("Key Passes/90", f"{player_data.get('Key_passes_per_90', 0):.2f}")
                cols_att_detail[2].metric("Dribbles Comp./90", f"{player_data.get('Dribbles_completed_per_90', 0):.2f}")
                cols_att_detail[3].metric("Touches in Box/90", f"{player_data.get('Touches_in_box_per_90', 0):.2f}")


                st.markdown("#### Passing")
                cols_pass = st.columns(3)
                cols_pass[0].metric("Total Passes/90", f"{player_data.get('Total_passes_per_90', 0):.2f}")
                cols_pass[1].metric("Accurate Passes/90", f"{player_data.get('Accurate_passes_per_90', 0):.2f}")
                cols_pass[2].metric("Pass Accuracy %", f"{player_data.get('Pass_Accuracy_Perc', 0):.1f}%")


                st.markdown("#### Defensive")
                cols_def = st.columns(3)
                cols_def[0].metric("Interceptions/90", f"{player_data.get('Interceptions_per_90', 0):.2f}")
                cols_def[1].metric("Tackles/90", f"{player_data.get('Tackles_per_90', 0):.2f}")
                cols_def[2].metric("Aerial Duels Won/90", f"{player_data.get('Aerial_duels_won_per_90', 0):.2f}")

                # Goalkeeper Stats (Only if position suggests GK)
                if 'GK' in player_data.get('Position', ''):
                    st.markdown("#### Goalkeeping")
                    cols_gk = st.columns(3)
                    cols_gk[0].metric("Saves", int(player_data.get('Saves', 0)))
                    cols_gk[1].metric("Goals Conceded", int(player_data.get('Goals_conceded', 0)))
                    cols_gk[2].metric("Clean Sheets", int(player_data.get('Clean_sheets', 0)))


    with tab3:
        st.header("Advanced Analytics & Visualizations")
        st.write("Explore trends and relationships within the filtered player dataset.")

        if filtered_df.empty:
            st.warning("No players match your filters. Adjust filters to see analytics.")
        else:
            st.subheader("League Performance Overview")

            if 'League' in filtered_df.columns and not filtered_df.empty:
                col1, col2 = st.columns(2)

                agg_metrics = {
                    'Age': 'mean',
                    'Goals_per_90': 'mean',
                    'Assists_per_90': 'mean',
                    'xG_per_90': 'mean',
                    'xA_per_90': 'mean',
                    'Pass_Accuracy_Perc': 'mean',
                    'Dribble_Success_Perc': 'mean'
                }
                # Filter agg_metrics to only include columns that exist in filtered_df
                existing_agg_metrics = {k: v for k, v in agg_metrics.items() if k in filtered_df.columns}

                if existing_agg_metrics:
                    league_stats = filtered_df.groupby('League').agg(existing_agg_metrics).reset_index()

                    with col1:
                        if 'Goals_per_90' in league_stats.columns:
                            fig_goals = px.bar(
                                league_stats.sort_values('Goals_per_90', ascending=False),
                                x='Goals_per_90',
                                y='League',
                                orientation='h',
                                title='Average Goals per 90 by League',
                                color='Goals_per_90',
                                color_continuous_scale=px.colors.sequential.Plasma
                            )
                            fig_goals.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_goals, use_container_width=True)
                        else:
                            st.info("Goals per 90 data not available for league comparison.")

                    with col2:
                        if 'Assists_per_90' in league_stats.columns:
                            fig_assists = px.bar(
                                league_stats.sort_values('Assists_per_90', ascending=False),
                                x='Assists_per_90',
                                y='League',
                                orientation='h',
                                title='Average Assists per 90 by League',
                                color='Assists_per_90',
                                color_continuous_scale=px.colors.sequential.Viridis
                            )
                            fig_assists.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_assists, use_container_width=True)
                        else:
                            st.info("Assists per 90 data not available for league comparison.")
                else:
                    st.info("No suitable numeric metrics found for league aggregation.")
            else:
                st.info("No 'League' column or data available for league analytics.")


            st.subheader("Player Performance Distribution")
            selected_dist_metric = st.selectbox(
                "Select a metric to view its distribution:",
                options=[m for m in advanced_metric_columns if m in filtered_df.columns] + ['Age', 'Minutes_played', 'Market_value_eur'],
                key='dist_metric_selector'
            )
            if selected_dist_metric and selected_dist_metric in filtered_df.columns:
                fig_hist = px.histogram(
                    filtered_df,
                    x=selected_dist_metric,
                    nbins=20,
                    title=f'Distribution of {selected_dist_metric.replace("_", " ").replace("per 90", "/90")}',
                    marginal="rug", # Add rug plot
                    hover_data=filtered_df[['Player Name', 'Team', 'Position']].columns
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No data for the selected distribution metric.")

            st.subheader("Player Comparison Scatter Plot")
            st.write("Identify player archetypes by comparing two key performance metrics.")

            col_x, col_y = st.columns(2)
            # Exclude non-numeric and identity columns for scatter plot axes
            scatter_options = [
                m for m in advanced_metric_columns + ['Pass_Accuracy_Perc', 'Dribble_Success_Perc', 'Age', 'Minutes_played', 'Market_value_eur']
                if m in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[m])
            ]

            x_axis_metric = col_x.selectbox(
                "X-Axis Metric:",
                options=scatter_options,
                index=scatter_options.index('xG_per_90') if 'xG_per_90' in scatter_options else 0,
                key='x_axis_metric'
            )
            y_axis_metric = col_y.selectbox(
                "Y-Axis Metric:",
                options=scatter_options,
                index=scatter_options.index('xA_per_90') if 'xA_per_90' in scatter_options else (1 if len(scatter_options)>1 else 0),
                key='y_axis_metric'
            )

            if x_axis_metric and y_axis_metric and not filtered_df.empty:
                fig_scatter = px.scatter(
                    filtered_df,
                    x=x_axis_metric,
                    y=y_axis_metric,
                    hover_name="Player Name",
                    hover_data=['Team', 'Position', 'Age', 'Minutes_played'],
                    color='Position', # Color by position for better insights
                    size='Market_value_eur' if 'Market_value_eur' in filtered_df.columns else None, # Size by market value
                    title=f'{x_axis_metric.replace("_", " ").replace("per 90", "/90")} vs. {y_axis_metric.replace("_", " ").replace("per 90", "/90")}'
                )
                fig_scatter.update_layout(
                    xaxis_title=x_axis_metric.replace("_", " ").replace("per 90", "/90"),
                    yaxis_title=y_axis_metric.replace("_", " ").replace("per 90", "/90")
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Select two numeric metrics for the scatter plot.")


# Run the app
if __name__ == "__main__":
    main()
```
