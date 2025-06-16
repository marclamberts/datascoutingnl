#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 16 14:40:50 2025

@author: user
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Wyscout Player Finder", layout="wide")

st.title("Wyscout Player Finder")

# File uploader
uploaded_file = st.file_uploader("Upload your Wyscout Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("Raw Data")
    st.write(df)

    # Automatically detect columns for filtering
    st.sidebar.header("Filter Players")

    # Example: Assuming 'Position', 'Team', 'Age', 'Minutes played' are in your dataset
    # You can customize these fields based on your actual Wyscout data columns
    positions = df['Position'].unique() if 'Position' in df.columns else []
    teams = df['Team'].unique() if 'Team' in df.columns else []

    selected_positions = st.sidebar.multiselect("Select Position(s)", positions)
    selected_teams = st.sidebar.multiselect("Select Team(s)", teams)

    min_age = int(df['Age'].min()) if 'Age' in df.columns else 15
    max_age = int(df['Age'].max()) if 'Age' in df.columns else 40
    age_range = st.sidebar.slider("Select Age Range", min_age, max_age, (min_age, max_age))

    min_minutes = int(df['Minutes played'].min()) if 'Minutes played' in df.columns else 0
    max_minutes = int(df['Minutes played'].max()) if 'Minutes played' in df.columns else 5000
    minutes_range = st.sidebar.slider("Select Minutes Played Range", min_minutes, max_minutes, (min_minutes, max_minutes))

    # Filtering logic
    filtered_df = df.copy()

    if selected_positions:
        filtered_df = filtered_df[filtered_df['Position'].isin(selected_positions)]

    if selected_teams:
        filtered_df = filtered_df[filtered_df['Team'].isin(selected_teams)]

    if 'Age' in df.columns:
        filtered_df = filtered_df[(filtered_df['Age'] >= age_range[0]) & (filtered_df['Age'] <= age_range[1])]

    if 'Minutes played' in df.columns:
        filtered_df = filtered_df[(filtered_df['Minutes played'] >= minutes_range[0]) & (filtered_df['Minutes played'] <= minutes_range[1])]

    st.subheader("Filtered Players")
    st.write(filtered_df)

    st.download_button("Download Filtered Data", data=filtered_df.to_csv(index=False), file_name="filtered_players.csv", mime="text/csv")
else:
    st.info("Please upload an Excel file to get started.")