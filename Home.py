"""
app.py
v0.0.1, 6/13/2025
Author: Alexander Netzley, anetzley@uw.edu
This module provides the wrapper function for running the StravaVision App.
"""

# Import packages
import streamlit as st
from datetime import datetime

# Import user modules
from utils import refresh_data_pipeline

# Setting page formats
st.set_page_config(layout="wide")

# Title of the app
st.title('StravaVision')

st.subheader('An exploration into my world of Strava activities')

# Add Refresh Data button on the far right

# Initialize session state for last refresh time
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

# Create columns for right-aligned refresh button
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🔄 Refresh Data", help="Click to refresh your Strava activities data"):
        with st.spinner("Refreshing data... This may take a few moments."):
            success = refresh_data_pipeline()
            if success:
                st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.success("✅ Data refreshed successfully!")
                st.balloons()
            else:
                st.error("❌ Failed to refresh data. Please check your Strava token and try again.")
    
    # Display last refresh time
    if st.session_state.last_refresh:
        st.caption(f"Last refreshed: {st.session_state.last_refresh}")

# Carousel Placeholder
cols = st.columns(3)

pages = [
    {"name": "Hardest Activities", "image": "https://via.placeholder.com/150?text=Hardest Activities"},
    {"name": "Placeholder2", "image": "https://via.placeholder.com/150?text=Viz"},
    {"name": "Placeholder3", "image": "https://via.placeholder.com/150?text=Analysis"},
]

for col, page in zip(cols, pages):
    with col:
        if st.button(f"{page['name']}", type="primary"):
            st.switch_page(f"pages/{page['name'].replace(' ', '_')}.py")  # Requires streamlit >= 1.22
        st.image(page["image"])

