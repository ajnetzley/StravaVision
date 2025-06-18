"""
app.py
v0.0.1, 6/13/2025
Author: Alexander Netzley, anetzley@uw.edu
This module provides the wrapper function for running the StravaVision App.
"""

# Import packages
import streamlit as st
from datetime import datetime
from functools import partial
import base64

from streamlit_card import card

# Import user modules
from utils import refresh_data_pipeline
from styles import apply_gradient_background

# Setting page formats
st.set_page_config(layout="wide")

# Apply home page styling
apply_gradient_background()

# Initialize session state for last refresh time
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None

###############
### CONTENT ###
###############

# Title
st.title('StravaVision')

# Description and Refresh Data Button
col1, col2 = st.columns([4, 1])
with col1:
    # Subtitle
    st.subheader('A Reimagined Exploration of my Strava Activities')

with col2:
    # Refresh Data Button
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

# Define a helper function for page switching
def switch_to(path):
    st.switch_page(path)

# Load the hardest_activities image and encode it in base64
with open("images/hardest_activities.png", "rb") as f:
    haImage = f.read()
    encoded = base64.b64encode(haImage)
haImage = "data:image/png;base64," + encoded.decode("utf-8")

# Load the grind_graph image and encode it in base64
with open("images/Grind_Graph.png", "rb") as f:
    data = f.read()
    encoded = base64.b64encode(data)
ggImage = "data:image/png;base64," + encoded.decode("utf-8")

# Load the sky_log image and encode it in base64
with open("images/Sky_Log.png", "rb") as f:
    slImage = f.read()
    encoded2 = base64.b64encode(slImage)
slImage = "data:image/png;base64," + encoded2.decode("utf-8")

# Define card metadata
card_metadata = [
    {
        "title": "Hardest Activities",
        "text": "A summary of my hardest Strava activities based on difficulty scores.",
        "image": haImage,
        "on_click": partial(switch_to, "pages/Hardest_Activities.py"),
        "key": "hardest_activities_card"
    },
    {
        "title": "Grind Graph",
        "text": "A summary of my hardest cumulative weeks of training.",
        "image": ggImage,
        "on_click": partial(switch_to, "pages/Grind_Graph.py"),
        "key": "grind_graph_card"
    },
    {
        "title": "Sky Log",
        "text": "A summary of my highest altitude activities.",
        "image": slImage,
        "on_click": partial(switch_to, "pages/Sky_Log.py"),
        "key": "sky_log_card"
    }
]

cols = st.columns(len(card_metadata))

for col, card_info in zip(cols, card_metadata):
    with col:
        card(
            title=card_info["title"],
            text=card_info["text"],
            image=card_info["image"],
            on_click=card_info["on_click"],
            key=card_info["key"]
        )
