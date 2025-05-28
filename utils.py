"""
utils.py
v0.0.1, 5/26/2025
Author: Alexander Netzley, anetzley@uw.edu

This module provides helper functions for the StravaVision app.
"""

# Import packages
import pandas as pd
import os
import time
import pickle
import requests

from stravalib import Client

# Import User Modules
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET



def load_data(refresh):
    '''
    Loads the full activities data, either the previously saved csv, or by generating a new csv via a strava api call

    returns:
    - df (the dataframe of the full activities)
    
    '''
    if not refresh:
        df = pd.read_csv("activities_data/full_activities.csv")

    else:

        token_response = get_strava_token()

        client = Client(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            token_expires=token_response["expires_at"],
            )

        activities = client.get_activities(limit=1000)

        data = []

        for activity in activities:
            activity_dict = vars(activity)
            data.append(activity_dict)

        # Convert list of dicts to DataFrame
        df = pd.DataFrame(data)

        # Convert list of dicts to DataFrame
        df = pd.DataFrame(data)
        df.to_csv("activities_data/full_activities.csv", index=False)

    return df



def get_strava_token(token_path="strava_token.pkl"):
    """
    Loads and refreshes the Strava access token using the refresh_token.
    
    Returns:
        dict: A dictionary with access_token, refresh_token, expires_at, etc.
    """
    # Ensure env vars are set
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise EnvironmentError("STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in environment variables.")

    # Load saved token info
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"Token file not found at {token_path}. You must manually authorize and save tokens first.")

    with open(token_path, "rb") as f:
        token_data = pickle.load(f)

    # Refresh token if expired
    if token_data['expires_at'] < time.time():
        response = requests.post("https://www.strava.com/oauth/token", data={
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': token_data['refresh_token']
        })

        if response.status_code != 200:
            raise RuntimeError(f"Failed to refresh token: {response.text}")

        token_data = response.json()

        # Save the new token data
        with open(token_path, "wb") as f:
            pickle.dump(token_data, f)

    return token_data