import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
from sklearn.preprocessing import StandardScaler
from fpdf import FPDF

# ------------------------------------------------
# CONFIGURATION
# ------------------------------------------------
st.set_page_config(page_title="Wyscout Player Percentile Dashboard", layout="wide")

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------
DATA_PATH = os.path.join("Netherlands II.xlsx")
if not os.path.exists(DATA_PATH):
    st.error(f"Excel file not found at: {DATA_PATH}")
    st.stop()

@st.cache_data

def load_data(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    return df

df = load_data(DATA_PATH)

# ------------------------------------------------
# USER SELECTION
# ------------------------------------------------
st.title("⚽ Player Percentile Dashboard")

positions = sorted(df['Position'].dropna().unique())
players = df[df['Minutes played'] >= 500]['Player'].unique()

selected_player = st.selectbox("Select a Player", players)
selected_role = st.radio("Select Role Type", ["Attacking", "Midfield", "Defensive"], horizontal=True)

# ------------------------------------------------
# ROLE-BASED METRICS
# ------------------------------------------------
metric_groups = {
    "Attacking": [
        'Goals per 90', 'Non-penalty goals per 90', 'xG per 90', 'Head goals per 90',
        'Shots per 90', 'Shots on target, %', 'Touches in box per 90', 'Progressive runs per 90'
    ],
    "Midfield": [
        'Assists per 90', 'xA per 90', 'Key passes per 90', 'Dribbles per 90',
        'Successful dribbles, %', 'Smart passes per 90', 'Through passes per 90'
    ],
    "Defensive": [
        'Defensive duels per 90', 'Defensive duels won, %', 'Sliding tackles per 90',
        'Interceptions per 90', 'Fouls per 90', 'Shots blocked per 90', 'Aerial duels per 90'
    ]
}

metrics = metric_groups[selected_role]
player_df = df[df['Player'] == selected_player]

# ------------------------------------------------
# PERCENTILE CALCULATION
# ------------------------------------------------
percentile_ranks = {}
for metric in metrics:
    if metric in df.columns:
        percentile_ranks[metric] = df[metric].rank(pct=True) * 99

# ------------------------------------------------
# BAR PERCENTILE VISUAL
# ------------------------------------------------
st.markdown(f"### 📊 {selected_player} — {selected_role} Metrics")

fig, ax = plt.subplots(figsize=(12, 8), facecolor='#333333')
ax.set_facecolor('#333333')

for i, metric in enumerate(metrics):
    if metric in df.columns:
        metric_value = player_df[metric].values[0]
        percentile_rank = percentile_ranks[metric][player_df.index[0]]
        color = mcolors.LinearSegmentedColormap.from_list('custom_cmap', ['red', 'orange', 'green'])(percentile_rank / 99)

        bar = ax.barh(i, percentile_rank, alpha=0.8, color=color)
        ax.text(bar[0].get_width() + 2, bar[0].get_y() + bar[0].get_height() / 2,
                f'{int(percentile_rank)}', va='center', ha='left', color='white', fontsize=11)

ax.axvline(50, color='lightgrey', linestyle='--')
ax.set_yticks(range(len(metrics)))
ax.set_yticklabels(metrics, color='white', fontsize=12)
ax.set_xlim(0, 100)
ax.set_xlabel('Percentile Rank', color='white')
ax.set_title(f"{selected_player} | {player_df['Team'].values[0]} | {selected_role} Profile", fontsize=18, color='white')

# Styling
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')
for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout()
st.pyplot(fig)

st.caption("Percentile ranks vs players with >500 minutes | Data: Wyscout")
