import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.image as mpimg
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
# SIDEBAR FILTERS
# ------------------------------------------------
st.sidebar.title("⚽ Player Selector")
positions = sorted(df['Position'].dropna().unique())
players = df[df['Minutes played'] >= 500]['Player'].unique()
selected_player = st.sidebar.selectbox("Select a Player", players)
selected_role = st.sidebar.radio("Select Role Type", ["Attacking", "Midfield", "Defensive"])

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
st.title("📊 Player Percentile Metrics")

fig, ax = plt.subplots(figsize=(10, 6), facecolor='white')
ax.set_facecolor('white')

for i, metric in enumerate(metrics):
    if metric in df.columns:
        metric_value = player_df[metric].values[0]
        percentile_rank = percentile_ranks[metric][player_df.index[0]]
        color = mcolors.LinearSegmentedColormap.from_list('custom_cmap', ['red', 'orange', 'green'])(percentile_rank / 99)

        bar = ax.barh(i, percentile_rank, alpha=0.8, color=color)
        ax.text(bar[0].get_width() + 2, bar[0].get_y() + bar[0].get_height() / 2,
                f'{int(percentile_rank)}', va='center', ha='left', color='black', fontsize=11)

ax.axvline(50, color='grey', linestyle='--')
ax.set_yticks(range(len(metrics)))
ax.set_yticklabels(metrics, color='black', fontsize=11)
ax.set_xlim(0, 100)
ax.set_xlabel('Percentile Rank', color='black')
ax.set_title(f"{selected_player} | {player_df['Team'].values[0]} | {selected_role} Profile", fontsize=16, color='black')

# Styling
ax.tick_params(axis='x', colors='black')
ax.tick_params(axis='y', colors='black')
for spine in ax.spines.values():
    spine.set_visible(False)

# ------------------------------------------------
# ADD LOGO
# ------------------------------------------------
logo_path = "wa2.png"
if os.path.exists(logo_path):
    logo_img = mpimg.imread(logo_path)
    fig.figimage(logo_img, xo=fig.bbox.xmax - 150, yo=fig.bbox.ymax - 130, zorder=10, alpha=0.5)

plt.tight_layout()
st.pyplot(fig)

st.caption("Percentile ranks vs players with >500 minutes | Data: Wyscout")
