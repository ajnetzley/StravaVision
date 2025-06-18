"""
styles.py
v0.0.1, 6/18/2025
Author: Alexander Netzley, anetzley@uw.edu

This module provides reusable CSS styling functions for the StravaVision app.

USAGE EXAMPLES:

1. Just Gradient Background:
   from styles import apply_gradient_background
   apply_gradient_background()

"""

import streamlit as st

def apply_gradient_background():
    """
    Apply a gradient background to the Streamlit app
    """
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
        }
        
        /* Add some transparency to content containers for better readability */
        .block-container {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 2rem;
            margin-top: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        /* Style the title */
        h1 {
            color: #2c3e50;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
