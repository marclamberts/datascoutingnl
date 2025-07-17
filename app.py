import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

st.title("📊 Wyscout Player Finder")

# --- Upload Excel file ---
uploaded_file = st.file_uploader("Upload Wyscout Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()  # Clean column names

    st.subheader("Raw Data")
    st.dataframe(df, use_container_width=True)

    # Sidebar filters
    st.sidebar.header("🔎 Filter Players")

    # Basic filters
    positions = df['Position'].dropna().unique() if 'Position' in df else []
    teams = df['Team'].dropna().unique() if 'Team' in df else []

    selected_positions = st.sidebar.multiselect("Position(s)", sorted(positions))
    selected_teams = st.sidebar.multiselect("Team(s)", sorted(teams))

    min_age = int(df['Age'].min()) if 'Age' in df else 15
    max_age = int(df['Age'].max()) if 'Age' in df else 40
    age_range = st.sidebar.slider("Age Range", min_age, max_age, (min_age, max_age))

    min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df else 0
    max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df else 5000
    minutes_range = st.sidebar.slider("Minutes Played", min_minutes, max_minutes, (min_minutes, max_minutes))

    # Per 90 metric filters
    def range_filter(col, label):
        options = ['All', '0 - 0.3', '0.3 - 0.6', '0.6+']
        selected = st.sidebar.selectbox(label, options)
        if selected == '0 - 0.3':
            return lambda x: x >= 0 and x < 0.3
        elif selected == '0.3 - 0.6':
            return lambda x: x >= 0.3 and x < 0.6
        elif selected == '0.6+':
            return lambda x: x >= 0.6
        else:
            return lambda x: True

    filters = {
        "Goals per 90": range_filter(df, "Goals per 90 Range"),
        "xG per 90": range_filter(df, "xG per 90 Range"),
        "Assists per 90": range_filter(df, "Assists per 90 Range"),
        "xA per 90": range_filter(df, "xA per 90 Range")
    }

    # --- Apply filters ---
    filtered_df = df.copy()

    if selected_positions:
        filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

    if 'Age' in df:
        filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

    if 'Minutes played' in df:
        filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

    # Apply stat filters
    for col, func in filters.items():
        if col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[col].apply(lambda x: func(x) if pd.notnull(x) else False)]

    st.subheader(f"🎯 Filtered Players ({len(filtered_df)})")
    st.dataframe(filtered_df, use_container_width=True)

    # Download button
    st.download_button("Download Filtered Data", data=filtered_df.to_csv(index=False), file_name="filtered_players.csv", mime="text/csv")

    # --- Player Profile Viewer ---
    if len(filtered_df) > 0:
        st.subheader("📌 Player Profile")

        selected_player = st.selectbox("Select a player", filtered_df['Player'].unique())
        player_data = filtered_df[filtered_df['Player'] == selected_player].iloc[0]

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"**Name:** {player_data['Player']}")
            st.markdown(f"**Team:** {player_data['Team']}")
            st.markdown(f"**Position:** {player_data['Position']}")
            st.markdown(f"**Age:** {player_data['Age']}")
            st.markdown(f"**Contract ends:** {player_data.get('Contract expires', 'N/A')}")
            st.markdown(f"**Market Value:** {player_data.get('Market value', 'N/A')}")

        with col2:
            st.markdown("**Key Performance Stats:**")
            st.metric("Goals per 90", round(player_data.get("Goals per 90", 0), 2))
            st.metric("Assists per 90", round(player_data.get("Assists per 90", 0), 2))
            st.metric("xG per 90", round(player_data.get("xG per 90", 0), 2))
            st.metric("xA per 90", round(player_data.get("xA per 90", 0), 2))

        # Radar chart
        if st.checkbox("Show Radar Chart"):
            radar_metrics = {
                "Goals per 90": player_data.get("Goals per 90", 0),
                "Assists per 90": player_data.get("Assists per 90", 0),
                "xG per 90": player_data.get("xG per 90", 0),
                "xA per 90": player_data.get("xA per 90", 0),
                "Shots per 90": player_data.get("Shots per 90", 0),
                "Key passes per 90": player_data.get("Key passes per 90", 0),
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
            ax.set_title(f"{selected_player} — Radar", fontsize=14)
            st.pyplot(fig)
