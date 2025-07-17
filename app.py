import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ------------------------------------------------
# CONFIGURATION
# ------------------------------------------------
st.set_page_config(page_title="Wyscout Scouting Tool", layout="wide")

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
st.sidebar.title("⚽ Player Scouting Tool")

# --- Sidebar Filters ---
st.sidebar.subheader("Player Filters")

positions = sorted(df['Position'].dropna().unique())
teams = sorted(df['Team'].dropna().unique())

selected_positions = st.sidebar.multiselect("Position(s)", positions)
selected_teams = st.sidebar.multiselect("Team(s)", teams)

age_range = st.sidebar.slider("Age Range", int(df['Age'].min()), int(df['Age'].max()), (18, 30))
minutes_range = st.sidebar.slider("Minutes Played", int(df['Minutes played'].min()), int(df['Minutes played'].max()), (500, 3000))

# Dynamic metric filters
def metric_range(label):
    options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
    selected = st.sidebar.selectbox(label, options, key=label)
    if selected == '0 - 0.3':
        return lambda x: 0 <= x < 0.3
    elif selected == '0.3 - 0.6':
        return lambda x: 0.3 <= x < 0.6
    elif selected == '0.6+':
        return lambda x: x >= 0.6
    return lambda x: True

filters = {
    "Goals per 90": metric_range("Goals per 90"),
    "xG per 90": metric_range("xG per 90"),
    "Assists per 90": metric_range("Assists per 90"),
    "xA per 90": metric_range("xA per 90")
}

# ------------------------------------------------
# FILTERING LOGIC
# ------------------------------------------------
filtered_df = df.copy()

if selected_positions:
    filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

if selected_teams:
    filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]
filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

for col, condition in filters.items():
    if col in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[col].apply(lambda x: condition(x) if pd.notnull(x) else False)]

# ------------------------------------------------
# TOP TABS
# ------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Filtered Players", "Player Profile", "Analytics"])

with tab1:
    st.title("🎯 Filtered Players")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("Download CSV", filtered_df.to_csv(index=False), "filtered_players.csv")

with tab2:
    st.title("📌 Player Profile Viewer")

    if not filtered_df.empty:
        player = st.selectbox("Select a player", filtered_df['Player'].unique())
        pdata = filtered_df[filtered_df['Player'] == player].iloc[0]

        st.markdown(f"### {pdata['Player']}")
        st.markdown(f"**Team:** {pdata['Team']} | **Position:** {pdata['Position']} | **Age:** {pdata['Age']}")
        st.markdown(f"**Market Value:** {pdata.get('Market value', 'N/A')} | **Contract Expires:** {pdata.get('Contract expires', 'N/A')}")

        st.subheader("Key Stats")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Goals/90", round(pdata.get("Goals per 90", 0), 2))
        col2.metric("xG/90", round(pdata.get("xG per 90", 0), 2))
        col3.metric("Assists/90", round(pdata.get("Assists per 90", 0), 2))
        col4.metric("xA/90", round(pdata.get("xA per 90", 0), 2))

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Shots/90", round(pdata.get("Shots per 90", 0), 2))
        col6.metric("Key Passes/90", round(pdata.get("Key passes per 90", 0), 2))
        col7.metric("Dribbles/90", round(pdata.get("Dribbles per 90", 0), 2))
        col8.metric("Successful Dribbles %", f"{pdata.get('Successful dribbles, %', 0)}%")

        col9, col10 = st.columns(2)
        col9.metric("Def. Duels/90", round(pdata.get("Defensive duels per 90", 0), 2))
        col10.metric("Def. Duels Won %", f"{pdata.get('Defensive duels won, %', 0)}%")

        st.markdown("---")
        st.subheader("Radar Chart")
        if st.checkbox("📈 Show Radar Chart"):
            radar_metrics = {
                "Goals per 90": pdata.get("Goals per 90", 0),
                "xG per 90": pdata.get("xG per 90", 0),
                "Assists per 90": pdata.get("Assists per 90", 0),
                "xA per 90": pdata.get("xA per 90", 0),
                "Shots per 90": pdata.get("Shots per 90", 0),
                "Key passes per 90": pdata.get("Key passes per 90", 0),
                "Dribbles per 90": pdata.get("Dribbles per 90", 0),
                "Progressive runs per 90": pdata.get("Progressive runs per 90", 0)
            }
            labels = list(radar_metrics.keys())
            values = list(radar_metrics.values())
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
            values += values[:1]
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            ax.plot(angles, values, "o-", linewidth=2)
            ax.fill(angles, values, alpha=0.25)
            ax.set_thetagrids(np.degrees(angles[:-1]), labels)
            ax.set_title(f"{pdata['Player']} Performance Radar", fontsize=14)
            st.pyplot(fig)
    else:
        st.warning("No players match current filters.")

with tab3:
    st.title("📊 Analytics")

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    numeric_cols = [col for col in numeric_cols if df[col].nunique() > 1]

    x_axis = st.selectbox("X-axis", numeric_cols, index=0)
    y_axis = st.selectbox("Y-axis", numeric_cols, index=1)

    if not filtered_df.empty:
        st.subheader("Scatter Plot")
        st.scatter_chart(filtered_df[[x_axis, y_axis]])

        st.subheader("Correlation Heatmap")
        corr = filtered_df[numeric_cols].corr()
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, cmap="coolwarm", annot=False, fmt=".2f", ax=ax)
        st.pyplot(fig)
    else:
        st.info("No data available for chart.")
