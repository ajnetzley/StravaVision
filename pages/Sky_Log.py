"""
sky_log.py
v0.0.1, 6/18/2025
Author: Alexander Netzley, anetzley@uw.edu

This page provides the tabular visualization of the highest altitudes I have acheived during my Strava activities.
"""

import pandas as pd
import streamlit as st

# Import the styling module
from utils import filter_dataframe
from styles import apply_gradient_background

# Apply styling for this data page
apply_gradient_background()

# Read in the cleaned activities data
df = pd.read_csv("activities_data/cleaned_activities.csv")

# Formatting with the dataframe on the left, image ikon on the right
col1, col2 = st.columns([6, 1])

with col1:
    st.title("Sky Log")
    st.dataframe(filter_dataframe(df), use_container_width=True)

with col2:
    st.image("images/Sky_Log.png", caption="Sky Log Visualization", use_container_width=True)