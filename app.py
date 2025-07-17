import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from fpdf import FPDF

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
# PERCENTILE RANKING
# ------------------------------------------------
numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
for col in numeric_cols:
    perc_col = col + " Percentile"
    df[perc_col] = df[col].rank(pct=True) * 100

# ------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------
st.sidebar.title("⚽ Player Scouting Tool (FBref Style)")

st.sidebar.subheader("🎛 Filters")
positions = sorted(df['Position'].dropna().unique())
teams = sorted(df['Team'].dropna().unique())
selected_positions = st.sidebar.multiselect("📌 Position(s)", positions)
selected_teams = st.sidebar.multiselect("🏟 Team(s)", teams)
age_range = st.sidebar.slider("🎂 Age Range", int(df['Age'].min()), int(df['Age'].max()), (18, 30))
minutes_range = st.sidebar.slider("⏱ Minutes Played", int(df['Minutes played'].min()), int(df['Minutes played'].max()), (500, 3000))

roles = ["None", "Striker", "Creator", "Destroyer"]
selected_role = st.sidebar.selectbox("🧮 Role (Scoring Model)", roles)

# ------------------------------------------------
# SCORING FUNCTION
# ------------------------------------------------
def calculate_role_score(row, role):
    if role == "Striker":
        return 0.4 * row.get("xG per 90", 0) + 0.4 * row.get("Goals per 90", 0) + 0.2 * row.get("Shots on target, %", 0)
    elif role == "Creator":
        return 0.4 * row.get("xA per 90", 0) + 0.4 * row.get("Assists per 90", 0) + 0.2 * row.get("Key passes per 90", 0)
    elif role == "Destroyer":
        return 0.4 * row.get("Defensive duels per 90", 0) + 0.3 * row.get("Interceptions per 90", 0) + 0.3 * row.get("Sliding tackles per 90", 0)
    else:
        return np.nan

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
# FILTERING
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

if selected_role != "None":
    filtered_df["Role Score"] = filtered_df.apply(lambda row: calculate_role_score(row, selected_role), axis=1)
    filtered_df = filtered_df.sort_values("Role Score", ascending=False)

# ------------------------------------------------
# TABS
# ------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Filtered Players", "Player Profile", "Analytics"])

with tab1:
    st.markdown("## 🎯 Filtered Players")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("⬇ Download CSV", filtered_df.to_csv(index=False), "filtered_players.csv")

with tab2:
    st.markdown("## 🧍‍♂️ Player Profile")
    if not filtered_df.empty:
        selected_players = st.multiselect("Compare up to 3 players", filtered_df['Player'].unique(), max_selections=3)
        for player in selected_players:
            pdata = filtered_df[filtered_df['Player'] == player].iloc[0]

            st.markdown(f"### {pdata['Player']}")
            st.markdown(f"**Team:** {pdata['Team']} | **Position:** {pdata['Position']} | **Age:** {pdata['Age']}")
            st.markdown(f"**Market Value:** {pdata.get('Market value', 'N/A')} | **Contract Expires:** {pdata.get('Contract expires', 'N/A')}")

            with st.expander("📊 Stats Summary"):
                stats_cols = [
                    ("Goals/90", "Goals per 90"),
                    ("xG/90", "xG per 90"),
                    ("Assists/90", "Assists per 90"),
                    ("xA/90", "xA per 90"),
                    ("Shots/90", "Shots per 90"),
                    ("Key Passes/90", "Key passes per 90"),
                    ("Dribbles/90", "Dribbles per 90"),
                    ("Successful Dribbles %", "Successful dribbles, %"),
                    ("Def. Duels/90", "Defensive duels per 90"),
                    ("Def. Duels Won %", "Defensive duels won, %")
                ]
                for i in range(0, len(stats_cols), 4):
                    cols = st.columns(4)
                    for j, (label, key) in enumerate(stats_cols[i:i+4]):
                        value = pdata.get(key, 0)
                        percentile = pdata.get(key + " Percentile", 0)
                        display = f"{value:.2f} ({percentile:.0f}th %ile)"
                        cols[j].metric(label, display)

            st.markdown("### 📈 Radar Chart")
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
            ax.set_title(f"{pdata['Player']} Radar Chart", fontsize=14)
            st.pyplot(fig)

with tab3:
    st.markdown("## 📊 Analytics")
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    numeric_cols = [col for col in numeric_cols if df[col].nunique() > 1]

    if not filtered_df.empty:
        x_axis = st.selectbox("📈 X-axis", numeric_cols, index=0)
        y_axis = st.selectbox("📉 Y-axis", numeric_cols, index=1)

        st.markdown("### 🔹 Scatter Plot")
        st.scatter_chart(filtered_df[[x_axis, y_axis]])

        st.markdown("### 🔸 Correlation Heatmap")
        corr = filtered_df[numeric_cols].corr()
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr, cmap="coolwarm", annot=False, fmt=".2f", ax=ax)
        st.pyplot(fig)

        st.markdown("### 🔺 PCA Clustering")
        pca_features = filtered_df[numeric_cols].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(pca_features)
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        kmeans = KMeans(n_clusters=4, random_state=42)
        clusters = kmeans.fit_predict(X_pca)

        fig, ax = plt.subplots()
        scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=clusters, cmap='viridis', alpha=0.6)
        ax.set_xlabel("PCA Component 1")
        ax.set_ylabel("PCA Component 2")
        ax.set_title("Player Clusters")
        st.pyplot(fig)
    else:
        st.info("No data available for analytics.")
