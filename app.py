import streamlit as st
import pandas as pd
import sqlite3
import requests
import os
from st_aggrid import AgGrid, GridOptionsBuilder
from glicko2 import Player as GlickoPlayer

# Configure page
st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

# Download DB if missing
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

conn = sqlite3.connect(db_path)

try:
    df = pd.read_sql_query("SELECT * FROM Player", conn)
except Exception as e:
    st.error(f"Error loading table: {e}")
    st.stop()

if df.empty:
    st.warning("The table 'Player' is empty.")
    st.stop()

st.title("Wyscout Player Finder")

# ---- Define Aerial Duel Player class ----
class AerialDuelPlayer(GlickoPlayer):
    def __init__(self, name, height, position, aerial_duels_per_90, aerial_win_pct, team, rating=1500, rd=350, vol=0.06):
        super().__init__(rating, rd, vol)
        self.name = name
        self.height = height
        self.position = position
        self.aerial_duels_per_90 = aerial_duels_per_90
        self.aerial_win_pct = aerial_win_pct
        self.team = team

    def calculate_weighted_score(self):
        return (
            0.5 * self.aerial_duels_per_90 +
            1.0 * self.height +
            1.5 * self.aerial_win_pct
        )

    def match_outcome(self, opponent):
        win_margin = self.calculate_weighted_score() - opponent.calculate_weighted_score()
        if win_margin > 5:
            return 1
        elif win_margin < -5:
            return 0
        else:
            return 0.5

    def constrained_update_player(self, opponent_ratings, opponent_rds, outcomes):
        self.rd = min(max(self.rd, 30), 350)
        opponent_rds = [min(max(rd, 30), 350) for rd in opponent_rds]
        self.rating = min(max(self.rating, 1000), 2000)
        self.vol = min(max(self.vol, 0.01), 1.2)
        try:
            self.update_player(opponent_ratings, opponent_rds, outcomes)
        except (OverflowError, ValueError):
            pass

# --- Filter original df first to players with needed data and minutes + exclude goalkeepers
filtered_base = df[
    (df['Minutes played'] >= 180) &
    (df['Position'] != 'GK') &
    df['Height'].notnull() &
    df['Aerial duels per 90'].notnull() &
    df['Aerial duels won, %'].notnull()
].copy()

# Create AerialDuelPlayer objects
players = []
for _, row in filtered_base.iterrows():
    players.append(AerialDuelPlayer(
        name=row['Player'],
        height=row['Height'],
        position=row['Position'],
        aerial_duels_per_90=row['Aerial duels per 90'],
        aerial_win_pct=row['Aerial duels won, %'],
        team=row['Team']
    ))

# Simulate matches to update ratings
for player in players:
    opponents = [op for op in players if op != player]
    outcomes = [player.match_outcome(op) for op in opponents]
    opponent_ratings = [op.rating for op in opponents]
    opponent_rds = [op.rd for op in opponents]

    weights = [op.aerial_duels_per_90 for op in opponents]
    if sum(weights) > 0:
        weights = [w / sum(weights) for w in weights]
    else:
        weights = [1] * len(weights)

    player.constrained_update_player(opponent_ratings, opponent_rds, outcomes)

# Build a DataFrame with computed ratings
rating_data = []
for player in players:
    weighted_rating = (
        0.5 * player.aerial_duels_per_90 +
        1.0 * player.height +
        1.5 * player.aerial_win_pct +
        player.rating
    )
    rating_data.append({
        "Player": player.name,
        "Weighted Rating": weighted_rating
    })

rating_df = pd.DataFrame(rating_data)

# Normalize weighted rating 0-100
min_rating = rating_df['Weighted Rating'].min()
max_rating = rating_df['Weighted Rating'].max()
rating_df['Aerial Duel Score'] = ((rating_df['Weighted Rating'] - min_rating) / (max_rating - min_rating)) * 100

# Merge this score back to the original df on Player name
df = df.merge(rating_df[['Player', 'Aerial Duel Score']], on='Player', how='left')

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

# New slider filter for Aerial Duel Score
min_aerial = float(df['Aerial Duel Score'].min()) if 'Aerial Duel Score' in df.columns else 0
max_aerial = float(df['Aerial Duel Score'].max()) if 'Aerial Duel Score' in df.columns else 100
aerial_range = st.sidebar.slider("Select Aerial Duel Score Range", min_aerial, max_aerial, (min_aerial, max_aerial))

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

if selected_passport_countries:
    filtered_df = filtered_df[filtered_df['Passport country'].isin(selected_passport_countries)]

if selected_contracts:
    filtered_df = filtered_df[filtered_df['Contract expires'].isin(selected_contracts)]

if 'Age' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

if 'Minutes played' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

# Filter by aerial duel score
filtered_df = filtered_df[(filtered_df['Aerial Duel Score'] >= aerial_range[0]) & (filtered_df['Aerial Duel Score'] <= aerial_range[1])]

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

st.subheader(f"Showing {len(filtered_df)} filtered players")

# --- AgGrid setup ---
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

# --- Download Button ---
st.download_button(
    label="Download Full Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_players.csv",
    mime="text/csv"
)

conn.close()
