import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

# =============================================
# CONFIG & LOAD EXCEL
# =============================================

EXCEL_PATH = os.path.join("data", "Netherlands II.xlsx")

if not os.path.exists(EXCEL_PATH):
    st.error(f"Excel file not found at: {EXCEL_PATH}")
    st.stop()

@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()
    return df

df = load_data(EXCEL_PATH)

# =============================================
# SIDEBAR FILTERS
# =============================================

st.title("⚽ Wyscout Player Finder")

st.sidebar.header("🔎 Filter Players")

positions = sorted(df['Position'].dropna().unique()) if 'Position' in df else []
teams = sorted(df['Team'].dropna().unique()) if 'Team' in df else []

selected_positions = st.sidebar.multiselect("Position(s)", positions)
selected_teams = st.sidebar.multiselect("Team(s)", teams)

age_min = int(df['Age'].min()) if 'Age' in df else 15
age_max = int(df['Age'].max()) if 'Age' in df else 40
age_range = st.sidebar.slider("Age Range", age_min, age_max, (age_min, age_max))

minutes_min = int(df['Minutes played'].min()) if 'Minutes played' in df else 0
minutes_max = int(df['Minutes played'].max()) if 'Minutes played' in df else 5000
minutes_range = st.sidebar.slider("Minutes Played", minutes_min, minutes_max, (minutes_min, minutes_max))

# Range filters for metrics
def per_90_filter(col, label):
    options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
    selected = st.sidebar.selectbox(label, options)
    if selected == '0 - 0.3':
        return lambda x: 0 <= x < 0.3
    elif selected == '0.3 - 0.6':
        return lambda x: 0.3 <= x < 0.6
    elif selected == '0.6+':
        return lambda x: x >= 0.6
    else:
        return lambda x: True

filters = {
    "Goals per 90": per_90_filter(df, "Goals per 90 Range"),
    "xG per 90": per_90_filter(df, "xG per 90 Range"),
    "Assists per 90": per_90_filter(df, "Assists per 90 Range"),
    "xA per 90": per_90_filter(df, "xA per 90 Range"),
}

# =============================================
# APPLY FILTERS
# =============================================

filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

if 'Age' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

if 'Minutes played' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

for col, func in filters.items():
    if col in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[col].apply(lambda x: func(x) if pd.notnull(x) else False)]

# =============================================
# DISPLAY FILTERED DATA
# =============================================

st.subheader(f"🎯 Filtered Players ({len(filtered_df)})")
st.dataframe(filtered_df, use_container_width=True)

st.download_button(
    "💾 Download Filtered Data",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_players.csv",
    mime="text/csv"
)

# =============================================
# PLAYER PROFILE & RADAR
# =============================================

if not filtered_df.empty:
    st.subheader("📌 Player Profile")

    selected_player = st.selectbox("Select a player", filtered_df['Player'].unique())
    player_data = filtered_df[filtered_df['Player'] == selected_player].iloc[0]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**Name:** {player_data['Player']}")
        st.markdown(f"**Team:** {player_data['Team']}")
        st.markdown(f"**Position:** {player_data['Position']}")
        st.markdown(f"**Age:** {player_data['Age']}")
        st.markdown(f"**Market Value:** {player_data.get('Market value', 'N/A')}")
        st.markdown(f"**Contract Expiry:** {player_data.get('Contract expires', 'N/A')}")

    with col2:
        st.metric("Goals/90", round(player_data.get("Goals per 90", 0), 2))
        st.metric("xG/90", round(player_data.get("xG per 90", 0), 2))
        st.metric("Assists/90", round(player_data.get("Assists per 90", 0), 2))
        st.metric("xA/90", round(player_data.get("xA per 90", 0), 2))

    if st.checkbox("📈 Show Radar Chart"):
        import matplotlib.pyplot as plt

        metrics = {
            "Goals per 90": player_data.get("Goals per 90", 0),
            "xG per 90": player_data.get("xG per 90", 0),
            "Assists per 90": player_data.get("Assists per 90", 0),
            "xA per 90": player_data.get("xA per 90", 0),
            "Shots per 90": player_data.get("Shots per 90", 0),
            "Key passes per 90": player_data.get("Key passes per 90", 0),
        }

        labels = list(metrics.keys())
        values = list(metrics.values())
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.plot(angles, values, "o-", linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids(np.degrees(angles[:-1]), labels)
        ax.set_title(f"{selected_player} Radar Chart", fontsize=14)
        st.pyplot(fig)
