import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import plotly.express as px
import plotly.graph_objects as go
import os
import sqlite3
from sqlite3 import Error

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

@st.cache_data(ttl=24*60*60)  # Refresh daily
def load_database(db_path):
    """Load and prepare the player data from SQLite database"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Read the entire table (assuming it's named 'players')
        df = pd.read_sql_query("SELECT * FROM players", conn)
        
        # Close the connection
        conn.close()

        # Standardize column names: strip spaces, replace spaces with underscores, handle special chars, convert to lowercase
        df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('%', '_perc').str.replace(',', '').str.replace('__', '_').str.lower()

        # Rename specific columns for clarity and consistency (all lowercase now)
        df = df.rename(columns={
            'player': 'player_name',
            'market_value': 'market_value_eur',
            'contract_expires': 'contract_expires_date',
            'birth_country': 'passport_country',
            'foot': 'preferred_foot',
            'minutes_played': 'minutes_played_total',
            'goals': 'goals_total',
            'assists': 'assists_total',
            'shots': 'shots_total',
            'key_passes': 'key_passes_total',
            'dribbles_per_90': 'dribbles_attempted_per_90',
        })

        # Drop rows where 'player_name' is entirely NaN
        df = df.dropna(subset=['player_name'], how='all')

        # Convert 'contract_expires_date' to datetime and extract year
        if 'contract_expires_date' in df.columns:
            df['contract_expires_date'] = pd.to_datetime(df['contract_expires_date'], errors='coerce')
            df['contract_expires_year'] = df['contract_expires_date'].dt.year.fillna(2100).astype(int)
        else:
            df['contract_expires_year'] = 2100

        # Convert relevant columns to numeric, coercing errors and filling NaNs
        numeric_cols_to_process = [
            'age', 'height', 'weight', 'market_value_eur',
            'goals_total', 'xg', 'assists_total', 'xa',
            'shots_total', 'shots_on_target_perc',
            'dribbles_attempted_per_90', 'successful_dribbles_perc', 'touches_in_box_per_90', 'key_passes_total',
            'passes_per_90', 'accurate_passes_per_90', 'pass_accuracy_perc',
            'interceptions_per_90', 'tackles_per_90', 'shots_blocked_per_90', 'successful_defensive_actions_per_90',
            'aerial_duels_won_perc', 'defensive_duels_won_perc',
            'saves', 'clean_sheets', 'conceded_goals',
            'minutes_played_total',
            'progressive_runs_per_90'
        ]

        for col in numeric_cols_to_process:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0

        # Calculate per 90 metrics (using 'minutes_played_total')
        minutes_condition = df['minutes_played_total'] > 0
        metrics_for_per90_conversion = {
            'goals_total': 'goals_per_90',
            'xg': 'xg_per_90',
            'assists_total': 'assists_per_90',
            'xa': 'xa_per_90',
            'shots_total': 'shots_per_90',
            'key_passes_total': 'key_passes_per_90',
        }

        for base_metric, new_per90_col in metrics_for_per90_conversion.items():
            if base_metric in df.columns:
                df[new_per90_col] = np.where(
                    minutes_condition,
                    (df[base_metric] / df['minutes_played_total']) * 90,
                    0
                )
            else:
                df[new_per90_col] = 0

        # Ensure essential columns exist after all processing
        essential_str_cols = ['position', 'team', 'league', 'Passport country', 'preferred_foot']
        for col in essential_str_cols:
            if col not in df.columns:
                df[col] = 'Unknown'
            else:
                df[col] = df[col].fillna('Unknown').astype(str)

        return df

    except Error as e:
        st.error(f"Error connecting to SQLite database: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"An error occurred while loading or processing the data: {str(e)}")
        st.stop()

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
    # Define the database file path
    db_file_path = 'players_database2.db'

    if not os.path.exists(db_file_path):
        st.error(f"The required database file '{db_file_path}' was not found. Please ensure it's in the same directory.")
        st.stop()

    # Load data with progress indicator
    with st.spinner("Loading and processing player data from database..."):
        df = load_database(db_file_path)

    if df.empty:
        st.warning("No player data available after loading. Please check the database file and processing steps.")
        st.stop()

    # ==============================================
    # SIDEBAR - FILTERS
    # ==============================================

    st.sidebar.title("🔍 Advanced Filters")
    st.sidebar.markdown("---")

    # Dynamic filter options based on available data
    positions = sorted(df['position'].dropna().unique())
    teams = sorted(df['team'].dropna().unique())
    leagues = sorted(df['league'].dropna().unique())
    nationalities = sorted(df['passport_country'].dropna().unique())
    preferred_feet = sorted(df['preferred_foot'].dropna().unique())

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
        help="Filter by the player's preferred foot (left, right, both)."
    )

    # Age filter
    min_age_val, max_age_val = int(df['age'].min()), int(df['age'].max())
    age_range = st.sidebar.slider(
        "Age Range",
        min_age_val, max_age_val,
        (min_age_val, max_age_val),
        help="Filter players by their age."
    )

    # Minutes played filter
    min_minutes, max_minutes = 0, 0
    if 'minutes_played_total' in df.columns and not df['minutes_played_total'].empty:
        min_minutes, max_minutes = int(df['minutes_played_total'].min()), int(df['minutes_played_total'].max())
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
    if 'contract_expires_year' in df.columns and not df['contract_expires_year'].empty:
        min_contract_year, max_contract_year = int(df['contract_expires_year'].min()), int(df['contract_expires_year'].max())
        contract_year_range = st.sidebar.slider(
            "Contract Expiration Year",
            min_contract_year, max_contract_year,
            (min_contract_year, max_contract_year),
            help="Filter players by the year their contract expires."
        )
    else:
        contract_year_range = (0, 0)
        st.sidebar.info("Contract Expiration data not available.")

    # Market Value Filter
    if 'market_value_eur' in df.columns and not df['market_value_eur'].empty:
        slider_max_value = max(int(df['market_value_eur'].max() * 1.2), 1000000)
        min_value, max_value = int(df['market_value_eur'].min()), int(df['market_value_eur'].max())

        market_value_range = st.sidebar.slider(
            "Market Value (€)",
            0, slider_max_value,
            (min_value, max_value),
            format="€%d",
            help="Filter players by their estimated market value in Euros."
        )
    else:
        market_value_range = (0, 0)
        st.sidebar.info("Market Value data not available.")

    # Performance Metric filters
    st.sidebar.markdown("### Performance Metrics (per 90 & Percentages)")
    metric_ranges = {}

    advanced_metric_columns = [
        'goals_per_90', 'xg_per_90', 'assists_per_90', 'xa_per_90',
        'shots_per_90', 'key_passes_per_90', 'dribbles_attempted_per_90',
        'touches_in_box_per_90',
        'pass_accuracy_perc', 'successful_dribbles_perc',
        'interceptions_per_90', 'tackles_per_90', 'aerial_duels_won_perc', 'defensive_duels_won_perc',
        'passes_per_90', 'progressive_runs_per_90'
    ]

    for metric in advanced_metric_columns:
        if metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]) and not df[metric].empty:
            min_val = float(df[metric].min())
            max_val = float(df[metric].max())
            step = 0.01 if max_val - min_val < 5 else 0.1
            if metric.endswith('_perc'):
                step = 1.0
                min_val = max(0.0, min_val)
                max_val = min(100.0, max_val)

            values = st.sidebar.slider(
                f"{metric.replace('_', ' ').replace('per 90', '/90').replace('perc', '%')}",
                float(f"{min_val:.2f}"), float(f"{max_val:.2f}"),
                (float(f"{min_val:.2f}"), float(f"{max_val:.2f}")),
                step=step,
                help=f"Filter players by {metric.replace('_', ' ').lower()}."
            )
            metric_ranges[metric] = values
        else:
            st.sidebar.info(f"{metric.replace('_', ' ').replace('per 90', '/90').replace('perc', '%')} data not available for filtering.")

    # Sorting options
    st.sidebar.markdown("### Sorting Options")
    sort_options_list = [
        'player_name', 'age', 'minutes_played_total',
        'goals_total', 'assists_total', 'market_value_eur', 'contract_expires_year',
        'goals_per_90', 'xg_per_90', 'assists_per_90', 'xa_per_90',
        'pass_accuracy_perc', 'successful_dribbles_perc', 'shots_per_90', 'key_passes_per_90',
        'interceptions_per_90', 'tackles_per_90'
    ]
    sort_options_list = [col for col in sort_options_list if col in df.columns and (pd.api.types.is_numeric_dtype(df[col]) or col == 'player_name')]

    sort_by = st.sidebar.selectbox(
        "Sort by",
        sort_options_list,
        index=sort_options_list.index('market_value_eur') if 'market_value_eur' in sort_options_list else (0 if sort_options_list else None),
        help="Choose a metric to sort the player list by."
    )
    default_sort_asc = False if sort_by in ['market_value_eur', 'goals_per_90', 'xg_per_90', 'assists_per_90'] else True
    sort_asc = st.sidebar.checkbox("Ascending", default_sort_asc, help="Check for ascending (A-Z, 0-9) order, uncheck for descending.")

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

    if filters.get('positions'):
        filtered_df = filtered_df[filtered_df['position'].isin(filters['positions'])]
    if filters.get('teams'):
        filtered_df = filtered_df[filtered_df['team'].isin(filters['teams'])]
    if filters.get('leagues'):
        filtered_df = filtered_df[filtered_df['league'].isin(filters['leagues'])]
    if filters.get('nationalities'):
        filtered_df = filtered_df[filtered_df['passport_country'].isin(filters['nationalities'])]
    if filters.get('preferred_foot'):
        filtered_df = filtered_df[filtered_df['preferred_foot'].isin(filters['preferred_foot'])]

    if 'age' in filtered_df.columns and filters.get('age_range'):
        filtered_df = filtered_df[
            (filtered_df['age'] >= filters['age_range'][0]) &
            (filtered_df['age'] <= filters['age_range'][1])
        ]
    if 'minutes_played_total' in filtered_df.columns and filters.get('minutes_range'):
        filtered_df = filtered_df[
            (filtered_df['minutes_played_total'] >= filters['minutes_range'][0]) &
            (filtered_df['minutes_played_total'] <= filters['minutes_range'][1])
        ]
    if 'contract_expires_year' in filtered_df.columns and filters.get('contract_year_range'):
        filtered_df = filtered_df[
            (filtered_df['contract_expires_year'] >= filters['contract_year_range'][0]) &
            (filtered_df['contract_expires_year'] <= filters['contract_year_range'][1])
        ]
    if 'market_value_eur' in filtered_df.columns and filters.get('market_value_range'):
        filtered_df = filtered_df[
            (filtered_df['market_value_eur'] >= filters['market_value_range'][0]) &
            (filtered_df['market_value_eur'] <= filters['market_value_range'][1])
        ]

    for metric, (min_val, max_val) in filters.get('metric_ranges', {}).items():
        if metric in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df[metric] >= min_val) &
                (filtered_df[metric] <= max_val)
            ]

    if filters.get('sort_by') and filters['sort_by'] in filtered_df.columns:
        filtered_df = filtered_df.sort_values(
            by=filters['sort_by'],
            ascending=filters.get('sort_asc', False)
        )

    # Display summary stats
    st.markdown(f"""
    <div style="background-color:#e6f7ff;padding:15px;border-left:5px solid #4f8bf9;border-radius:5px;margin-bottom:20px;">
        <h4 style="margin:0;color:#0056b3;">📊 Search Results Summary: <span style="color:#28a745;">{len(filtered_df)}</span> Players Found</h4>
        <div style="display:flex;justify-content:space-around;flex-wrap:wrap;margin-top:10px;">
            <div style="margin:5px 15px;"><strong>Avg. Age:</strong> {safe_mean(filtered_df.get('age', pd.Series()), '.1f')}</div>
            <div style="margin:5px 15px;"><strong>Avg. Mins Played:</strong> {safe_mean(filtered_df.get('minutes_played_total', pd.Series()), 'd')}</div>
            <div style="margin:5px 15px;"><strong>Avg. Goals/90:</strong> {safe_mean(filtered_df.get('goals_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. xG/90:</strong> {safe_mean(filtered_df.get('xg_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. Assists/90:</strong> {safe_mean(filtered_df.get('assists_per_90', pd.Series()))}</div>
            <div style="margin:5px 15px;"><strong>Avg. xA/90:</strong> {safe_mean(filtered_df.get('xa_per_90', pd.Series()))}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Player List", "👤 Player Profiles", "📈 Advanced Analytics"])

    with tab1:
        st.header("Player List")
        st.write("Browse and filter players. Select a row to view the player's detailed profile in the 'Player Profiles' tab.")

        gb = GridOptionsBuilder.from_dataframe(filtered_df)

        gb.configure_default_column(
            groupable=True, sortable=True, resizable=True, filterable=True,
            editable=False, wrapText=True, width=150
        )
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)

        display_cols = [
            'player_name', 'position', 'team', 'league', 'age', 'minutes_played_total',
            'goals_total', 'assists_total', 'goals_per_90', 'xg_per_90', 'assists_per_90', 'xa_per_90',
            'shots_per_90', 'key_passes_per_90', 'pass_accuracy_perc', 'successful_dribbles_perc',
            'interceptions_per_90', 'tackles_per_90', 'aerial_duels_won_perc', 'defensive_duels_won_perc',
            'passport_country', 'preferred_foot', 'height', 'weight',
            'contract_expires_year', 'market_value_eur'
        ]

        for col in filtered_df.columns:
            if col not in display_cols:
                gb.configure_column(col, hide=True)

        for col_name in display_cols:
            if col_name in filtered_df.columns:
                header_name = col_name.replace('_', ' ').replace('perc', '%').replace('total', '(Total)').replace('per 90', '/90')
                if col_name.endswith('_per_90') or col_name in ['xg', 'xa', 'shots_per_90']:
                    gb.configure_column(col_name, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? params.value.toFixed(2) : 'N/A'; }").js_code,
                                        headerName=header_name)
                elif col_name.endswith('_perc'):
                    gb.configure_column(col_name, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? params.value.toFixed(1) + '%' : 'N/A'; }").js_code,
                                        headerName=header_name)
                elif col_name == 'market_value_eur':
                    gb.configure_column(col_name, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? '€' + params.value.toLocaleString() : 'N/A'; }").js_code,
                                        headerName="Market Value (€)")
                elif col_name in ['player_name', 'position', 'team', 'league', 'passport_country', 'preferred_foot']:
                    gb.configure_column(col_name, headerName=header_name, width=150, sortable=True, filterable=True)
                elif col_name in ['age', 'minutes_played_total', 'goals_total', 'assists_total', 'height', 'weight', 'contract_expires_year']:
                    gb.configure_column(col_name, type=["numericColumn", "numberColumnFilter"],
                                        valueFormatter=JsCode("function(params) { return params.value != null ? Math.round(params.value) : 'N/A'; }").js_code,
                                        headerName=header_name)
                else:
                    gb.configure_column(col_name, headerName=header_name)

        gb.configure_selection('single', use_checkbox=True, groupSelectsChildren=True)
        grid_options = gb.build()

        grid_response = AgGrid(
            filtered_df, gridOptions=grid_options, height=600, width='100%',
            theme='streamlit', enable_enterprise_modules=False, update_mode='MODEL_CHANGED',
            fit_columns_on_grid_load=False, key='players_grid'
        )

        selected_players_from_grid = grid_response.get('selected_rows', [])
        if selected_players_from_grid:
            st.session_state['selected_player_for_profile_tab'] = selected_players_from_grid[0]['player_name']
        elif 'selected_player_for_profile_tab' not in st.session_state:
            st.session_state['selected_player_for_profile_tab'] = None

        st.download_button(
            "💾 Download Filtered Data (CSV)",
            filtered_df.to_csv(index=False).encode('utf-8'),
            "filtered_players.csv", "text/csv", key='download-csv'
        )

    with tab2:
        st.header("Player Profiles")
        st.write("View detailed statistics and performance insights for a selected player.")

        if filtered_df.empty:
            st.warning("No players match your filters. Adjust filters to see profiles.")
        else:
            player_names = filtered_df['player_name'].unique()

            default_player_index = 0
            if st.session_state.get('selected_player_for_profile_tab') and \
               st.session_state['selected_player_for_profile_tab'] in player_names:
                default_player_index = list(player_names).index(st.session_state['selected_player_for_profile_tab'])
            elif player_names.size > 0:
                st.session_state['selected_player_for_profile_tab'] = player_names[0]
                default_player_index = 0
            else:
                st.session_state['selected_player_for_profile_tab'] = None
                default_player_index = 0

            selected_player = st.selectbox(
                "Select a player to view detailed profile:",
                player_names, index=default_player_index, key='player_profile_selector'
            )

            if selected_player:
                player_data = filtered_df[filtered_df['player_name'] == selected_player].iloc[0]

                st.markdown(f"<h3 id='player-profile-{selected_player.replace(' ', '-')}' style='color:#4f8bf9;'>{player_data['player_name']}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Position:** {player_data.get('position', 'N/A')} | **Team:** {player_data.get('team', 'N/A')} | **League:** {player_data.get('league', 'N/A')}")
                st.markdown(f"**Nationality:** {player_data.get('Passport country', 'N/A')} | **Preferred Foot:** {player_data.get('preferred_foot', 'N/A')}")
                st.markdown(f"**Age:** {int(player_data.get('age', 0))} | **Height:** {int(player_data.get('height', 0))} cm | **Weight:** {int(player_data.get('weight', 0))} kg")
                market_value_display = f"€{player_data.get('market_value_eur', 0):,.0f}" if player_data.get('market_value_eur') else 'N/A'
                st.markdown(f"**Contract Expires:** {player_data.get('contract_expires_year', 'N/A')} | **Market Value:** {market_value_display}")

                st.markdown("---")

                st.subheader("Performance Radar Chart")
                st.write("Compares the player's key per 90 metrics against the average of all currently filtered players in their primary position.")

                position_filtered_df = filtered_df[filtered_df['position'] == player_data['position']]
                if not position_filtered_df.empty:
                    radar_metrics = [
                        'goals_per_90', 'xg_per_90', 'assists_per_90', 'xa_per_90',
                        'shots_per_90', 'key_passes_per_90', 'dribbles_attempted_per_90',
                        'interceptions_per_90', 'tackles_per_90', 'aerial_duels_won_perc'
                    ]
                    radar_metrics = [m for m in radar_metrics if m in position_filtered_df.columns and pd.api.types.is_numeric_dtype(position_filtered_df[m])]

                    if radar_metrics:
                        player_values = [player_data.get(m, 0) for m in radar_metrics]
                        avg_values = [position_filtered_df[m].mean() for m in radar_metrics]

                        max_values = [position_filtered_df[m].max() for m in radar_metrics]
                        max_values = [mv if mv > 0 else 1 for mv in max_values]

                        player_scaled = [val / mx if mx > 0 else 0 for val, mx in zip(player_values, max_values)]
                        avg_scaled = [val / mx if mx > 0 else 0 for val, mx in zip(avg_values, max_values)]

                        fig_radar = go.Figure()
                        fig_radar.add_trace(go.Scatterpolar(
                            r=player_scaled,
                            theta=[m.replace('_', ' ').replace('per 90', '/90').replace('perc', '%') for m in radar_metrics],
                            fill='toself', name=player_data['player_name'], marker_color='blue', opacity=0.7
                        ))
                        fig_radar.add_trace(go.Scatterpolar(
                            r=avg_scaled,
                            theta=[m.replace('_', ' ').replace('per 90', '/90').replace('perc', '%') for m in radar_metrics],
                            fill='toself', name=f'Avg. {player_data["position"]}', marker_color='red', opacity=0.4
                        ))
                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                            showlegend=True,
                            title=f"Performance Comparison: {player_data['player_name']} vs. Avg. {player_data['position']}"
                        )
                        st.plotly_chart(fig_radar, use_container_width=True)
                    else:
                        st.info("Insufficient numeric data for radar chart from the selected metrics.")
                else:
                    st.info(f"Not enough players in {player_data['position']} to generate a meaningful comparison radar chart from the filtered data.")

                st.subheader("Key Performance Metrics")
                cols_general = st.columns(4)
                cols_general[0].metric("Age", int(player_data.get('age', 0)))
                cols_general[1].metric("Minutes Played", int(player_data.get('minutes_played_total', 0)))
                cols_general[2].metric("Height (cm)", int(player_data.get('height', 0)))
                cols_general[3].metric("Weight (kg)", int(player_data.get('weight', 0)))

                st.markdown("#### Attacking")
                cols_att = st.columns(4)
                cols_att[0].metric("Goals (Total)", int(player_data.get('goals_total', 0)))
                cols_att[1].metric("xG (Total)", f"{player_data.get('xg', 0):.2f}")
                cols_att[2].metric("Assists (Total)", int(player_data.get('assists_total', 0)))
                cols_att[3].metric("xA (Total)", f"{player_data.get('xa', 0):.2f}")

                cols_att_p90 = st.columns(4)
                cols_att_p90[0].metric("Goals/90", f"{player_data.get('goals_per_90', 0):.2f}")
                cols_att_p90[1].metric("xG/90", f"{player_data.get('xg_per_90', 0):.2f}")
                cols_att_p90[2].metric("Assists/90", f"{player_data.get('assists_per_90', 0):.2f}")
                cols_att_p90[3].metric("xA/90", f"{player_data.get('xa_per_90', 0):.2f}")

                cols_att_detail = st.columns(4)
                cols_att_detail[0].metric("Shots/90", f"{player_data.get('shots_per_90', 0):.2f}")
                cols_att_detail[1].metric("Shots on Target %", f"{player_data.get('shots_on_target_perc', 0):.1f}%")
                cols_att_detail[2].metric("Key Passes/90", f"{player_data.get('key_passes_per_90', 0):.2f}")
                cols_att_detail[3].metric("Touches in Box/90", f"{player_data.get('touches_in_box_per_90', 0):.2f}")

                st.markdown("#### Passing & Ball Progression")
                cols_pass = st.columns(3)
                cols_pass[0].metric("Total Passes/90", f"{player_data.get('passes_per_90', 0):.2f}")
                cols_pass[1].metric("Accurate Passes/90", f"{player_data.get('accurate_passes_per_90', 0):.2f}")
                cols_pass[2].metric("Pass Accuracy %", f"{player_data.get('pass_accuracy_perc', 0):.1f}%")

                cols_prog = st.columns(2)
                cols_prog[0].metric("Progressive Runs/90", f"{player_data.get('progressive_runs_per_90', 0):.2f}")
                cols_prog[1].metric("Dribbles Comp. %", f"{player_data.get('successful_dribbles_perc', 0):.1f}%")

                st.markdown("#### Defensive")
                cols_def = st.columns(3)
                cols_def[0].metric("Interceptions/90", f"{player_data.get('interceptions_per_90', 0):.2f}")
                cols_def[1].metric("Tackles/90", f"{player_data.get('tackles_per_90', 0):.2f}")
                cols_def[2].metric("Defensive Duels Won %", f"{player_data.get('defensive_duels_won_perc', 0):.1f}%")

                cols_def_det = st.columns(2)
                cols_def_det[0].metric("Shots Blocked/90", f"{player_data.get('shots_blocked_per_90', 0):.2f}")
                cols_def_det[1].metric("Successful Def. Actions/90", f"{player_data.get('successful_defensive_actions_per_90', 0):.2f}")

                if 'gk' in player_data.get('position', '').lower():
                    st.markdown("#### Goalkeeping")
                    cols_gk = st.columns(3)
                    cols_gk[0].metric("Saves", int(player_data.get('saves', 0)))
                    cols_gk[1].metric("Goals Conceded", int(player_data.get('conceded_goals', 0)))
                    cols_gk[2].metric("Clean Sheets", int(player_data.get('clean_sheets', 0)))

    with tab3:
        st.header("Advanced Analytics & Visualizations")
        st.write("Explore trends and relationships within the filtered player dataset.")

        if filtered_df.empty:
            st.warning("No players match your filters. Adjust filters to see analytics.")
        else:
            st.subheader("League Performance Overview")

            if 'league' in filtered_df.columns and not filtered_df.empty:
                col1, col2 = st.columns(2)

                agg_metrics = {
                    'age': 'mean',
                    'goals_per_90': 'mean',
                    'assists_per_90': 'mean',
                    'xg_per_90': 'mean',
                    'xa_per_90': 'mean',
                    'pass_accuracy_perc': 'mean',
                    'successful_dribbles_perc': 'mean',
                    'interceptions_per_90': 'mean',
                    'tackles_per_90': 'mean'
                }
                existing_agg_metrics = {k: v for k, v in agg_metrics.items() if k in filtered_df.columns}

                if existing_agg_metrics:
                    league_stats = filtered_df.groupby('league').agg(existing_agg_metrics).reset_index()

                    with col1:
                        if 'goals_per_90' in league_stats.columns:
                            fig_goals = px.bar(
                                league_stats.sort_values('goals_per_90', ascending=False),
                                x='goals_per_90',
                                y='league',
                                orientation='h',
                                title='Average Goals per 90 by League',
                                color='goals_per_90',
                                color_continuous_scale=px.colors.sequential.Plasma
                            )
                            fig_goals.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_goals, use_container_width=True)
                        else:
                            st.info("Goals per 90 data not available for league comparison.")

                    with col2:
                        if 'assists_per_90' in league_stats.columns:
                            fig_assists = px.bar(
                                league_stats.sort_values('assists_per_90', ascending=False),
                                x='assists_per_90',
                                y='league',
                                orientation='h',
                                title='Average Assists per 90 by League',
                                color='assists_per_90',
                                color_continuous_scale=px.colors.sequential.Viridis
                            )
                            fig_assists.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_assists, use_container_width=True)
                        else:
                            st.info("Assists per 90 data not available for league comparison.")
                else:
                    st.info("No suitable numeric metrics found for league aggregation.")
            else:
                st.info("No 'league' column or data available for league analytics.")

            st.subheader("Player Performance Distribution")
            distribution_options = [
                m for m in advanced_metric_columns + ['age', 'minutes_played_total', 'market_value_eur', 'height', 'weight']
                if m in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[m])
            ]
            display_distribution_options = [opt.replace('_', ' ').replace('perc', '%').replace('per 90', '/90') for opt in distribution_options]
            selected_dist_metric_display = st.selectbox(
                "Select a metric to view its distribution:",
                options=display_distribution_options,
                key='dist_metric_selector'
            )
            selected_dist_metric = distribution_options[display_distribution_options.index(selected_dist_metric_display)]

            if selected_dist_metric and selected_dist_metric in filtered_df.columns:
                fig_hist = px.histogram(
                    filtered_df, x=selected_dist_metric, nbins=20,
                    title=f'Distribution of {selected_dist_metric_display}',
                    marginal="rug", hover_data=['player_name', 'team', 'position', 'age']
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No data for the selected distribution metric.")

            st.subheader("Player Comparison Scatter Plot")
            st.write("Identify player archetypes by comparing two key performance metrics.")

            col_x, col_y = st.columns(2)
            scatter_options = [
                m for m in advanced_metric_columns + ['pass_accuracy_perc', 'successful_dribbles_perc', 'age', 'minutes_played_total', 'market_value_eur', 'height', 'weight']
                if m in filtered_df.columns and pd.api.types.is_numeric_dtype(filtered_df[m])
            ]

            display_scatter_options = [opt.replace('_', ' ').replace('perc', '%').replace('per 90', '/90') for opt in scatter_options]

            x_axis_metric_display = col_x.selectbox(
                "X-Axis Metric:",
                options=display_scatter_options,
                index=display_scatter_options.index('xg /90') if 'xg /90' in display_scatter_options else 0,
                key='x_axis_metric'
            )
            y_axis_metric_display = col_y.selectbox(
                "Y-Axis Metric:",
                options=display_scatter_options,
                index=display_scatter_options.index('xa /90') if 'xa /90' in display_scatter_options else (1 if len(display_scatter_options)>1 else 0),
                key='y_axis_metric'
            )
            x_axis_metric = scatter_options[display_scatter_options.index(x_axis_metric_display)]
            y_axis_metric = scatter_options[display_scatter_options.index(y_axis_metric_display)]

            if x_axis_metric and y_axis_metric and not filtered_df.empty:
                fig_scatter = px.scatter(
                    filtered_df,
                    x=x_axis_metric, y=y_axis_metric,
                    hover_name="player_name",
                    hover_data=['team', 'position', 'age', 'minutes_played_total', 'market_value_eur'],
                    color='position',
                    size='market_value_eur' if 'market_value_eur' in filtered_df.columns else None,
                    title=f'{x_axis_metric_display} vs. {y_axis_metric_display}'
                )
                fig_scatter.update_layout(
                    xaxis_title=x_axis_metric_display,
                    yaxis_title=y_axis_metric_display
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("Select two numeric metrics for the scatter plot.")

if __name__ == "__main__":
    main()
