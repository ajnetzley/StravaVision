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
import numpy as np
import warnings
from datetime import datetime
import streamlit as st
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import base64

from stravalib import Client
import reverse_geocoder as rg

# Import User Modules
from config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET

###############
### Home.py ###
###############
def load_data(refresh):
    '''
    Loads the full activities data, either the previously saved csv, or by generating a new csv via a strava api call

    returns:
    - df (the dataframe of the full activities)
    
    '''
    if not refresh:
        df = pd.read_csv("activities_data/full_raw_activities.csv")

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
        df.to_csv("activities_data/full_raw_activities.csv", index=False)

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

def refresh_data_pipeline():
    """
    Executes the complete data refresh pipeline that processes Strava activities data.
    This includes fetching new data, cleaning it, calculating difficulty scores, and saving processed data.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Suppress all warnings
        warnings.filterwarnings("ignore")
        
        # Load data with refresh=True to get latest activities
        df = load_data(refresh=True)
        
        # Clean up sport_type and start_latlng dtype
        df['sport_type'] = df['sport_type'].astype(str).str.extract(r"root='(.+?)'")

        df["start_latlng"] = df["start_latlng"].astype(str).str.extract(r"root=\[([\d\.\-]+),\s*([\d\.\-]+)\]"
            ).apply(lambda x: (float(x[0]), float(x[1])) if pd.notnull(x[0]) and pd.notnull(x[1]) else None, axis=1)

        filtered_df = df[{
            "name", "start_date", "type", "sport_type",
            "distance", "total_elevation_gain", "elev_high", "elev_low", 
            "start_latlng"
        }]
        
        # Hardcoded adjustments for activities with mixed types
        activities_distance_scalar = {
            "Ride": 4,
            "MountainBikeRide": 2.5,
            "GravelRide": 3,
            "Run": 1,
            "TrailRun": 1,
            "NordicSki": 1,
            "Hike": (4/3)
        }

        activities_elevation_scalar = {
            "Ride": 2,
            "MountainBikeRide": 2,
            "GravelRide": 2,
            "Run": 2,
            "TrailRun": 2,
            "NordicSki": 2,
            "Hike": 2
        }

        partial_trail_run_adjustment = {
            "Mt. Teneriffe + Mt. Si": 0.25,
            "Spray Park Loop": 0.5,
            "Oyster Dome Loop": 0.75,
            "Cutthroat Pass": 0.25,
            "Trappers Peak / Thornton Lakes": 0.25,
            "Trap Pass": 0.25,
            "Mailbox Peak": 0.5,
            "Goat Lake": 0.75,
            "Green Mountain": 0.75,
            "Granite Lake": 0.5,
            "Earl + Bean + Devil’s Head": 0.25,
            "Olallie & Talapus Lakes": 0.5,
            "Black Peak": 0.25,
        }

        def update_ptra(partial_trail_run_adjustment):
            updated_ptra = {}
            for key, value in partial_trail_run_adjustment.items():
                if value == 0.25:
                    # if the value is 0.25, this means it is designated as a hike and has already been scaled, so we need to unscale
                    updated_ptra[key] = (4/3)*(3/4 + value/4)
                else:
                    # other values indicate that this is categorized as a TrailRun, meaning we need to scale down.
                    updated_ptra[key] = (3/4 + value/4)
            return updated_ptra

        updated_partial_trail_run_adjustment = update_ptra(partial_trail_run_adjustment)

        partial_gravel_ride_adjustment = {
             "BLOM / Island Lake": 2.5/(0.25*2.5 + 0.75*3),
             "Island Lake": 2.5/(0.25*2.5 + 0.75*3),
             "Waterloo + DTE": 2.5/(0.25*2.5 + 0.75*3)
        }

        def convert_timestamp(timestamp):
            if isinstance(timestamp, datetime):
                dt = timestamp
            else:
                dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%m/%d/%y")

        elevation_to_capacity = {
            0: 1.0,
            1000: 0.992,
            2000: 0.983,
            3000: 0.972,
            4000: 0.959,
            5000: 0.944,
            6000: 0.927,
            7000: 0.907,
            8000: 0.886,
            9000: 0.863,
            10000: 0.837,
            11000: 0.809,
            12000: 0.78,
        }
        
        def extract_location(latlng):
            if not latlng or pd.isna(latlng):
                return None, None, None
            result = rg.search(latlng, mode=1)[0]  # mode=1 disables multithreading (safer for row-wise)
            return result['name'], result['admin1'], result['cc']
        
        # Compute the difficulty score
        filtered_activities = filtered_df.copy()

        # Calculate the city, state, and country from the start_latlng
        filtered_activities["location_city"], filtered_activities["location_state"], filtered_activities["location_country"] = zip(*filtered_activities["start_latlng"].apply(extract_location))

        # Calculate the distance score (miles, adjusted for sport type. There is also custom adjustments for partial gravel rides and trail runs
        filtered_activities["distance_score"] = (df["distance"]*0.000621371)/ df["sport_type"].map(lambda x: activities_distance_scalar.get(x, 1))
        filtered_activities["distance_score"] = (filtered_activities["distance_score"]*df["name"].map(lambda x: partial_gravel_ride_adjustment.get(x, 1))).round(2)
        filtered_activities["distance_score"] = (filtered_activities["distance_score"]*df["name"].map(lambda x: updated_partial_trail_run_adjustment.get(x, 1))).round(2)

        # Calculate the elevation score (2x for cycling, 3x for everything else)
        filtered_activities["elev_high"] = filtered_activities["elev_high"].fillna(0) #Temporary fix for missing elevation data
        filtered_activities["elev_low"] = filtered_activities["elev_low"].fillna(0)
        filtered_activities["total_elevation_gain"] = filtered_activities["total_elevation_gain"].fillna(0) #Temporary fix for missing elevation data
        filtered_activities["elevation_score"] = (filtered_activities["total_elevation_gain"] * 3.28084 * 0.001) * filtered_activities["sport_type"].map(lambda x: activities_elevation_scalar.get(x, 1))
        
        # Calculate the combined difficulty score
        filtered_activities["difficulty_score_without_altitude"] = filtered_activities["distance_score"] + filtered_activities["elevation_score"]

        # Add adjustments for the average elevation of the activity (altitude performance capacity)
        filtered_activities["average_elevation"] = (((filtered_activities["elev_high"] + filtered_activities["elev_low"])/2)*3.28084).round(2)
        filtered_activities["performance_capacity"] = (filtered_activities["average_elevation"].round(-3)).map(elevation_to_capacity)
        filtered_activities["difficulty_score"] = (filtered_activities["difficulty_score_without_altitude"] / filtered_activities["performance_capacity"]).round(2)

        # Convert raw distance, elevation, and date to readable formats
        filtered_activities["Distance (miles)"] = (filtered_activities["distance"]*0.000621371).round(2)
        filtered_activities["Total Elevation Gain (ft)"] = (filtered_activities["total_elevation_gain"]*3.28084).round(0).astype(int)
        filtered_activities["Date"] = filtered_activities["start_date"].apply(convert_timestamp)

        filtered_activities["elev_high"] *= 3.28084

        # Rename columns for clarity
        filtered_activities.rename(columns={"name": "Activity Name", 
                                            "sport_type": "Sport Type",
                                            "difficulty_score": "Difficulty Score",
                                            "location_city": "City",
                                            "location_state": "State",
                                            "location_country": "Country"
                                            }, inplace=True)

        # Save the cleaned activities data
        filtered_activities.to_csv("activities_data/cleaned_activities.csv", index=False)

        # Execute the data processing for each page, saving each after
        hardest_overall_activities = process_hardest_activities(filtered_activities)
        hardest_overall_activities.to_csv("activities_data/hardest_activities.csv", index=False)

        sky_log_activities = process_sky_log(filtered_activities)
        sky_log_activities.to_csv("activities_data/sky_log_activities.csv", index=False)
        
        return True
        
    except Exception as e:
        print(f"Error in data refresh pipeline: {str(e)}")
        return False
    
def process_hardest_activities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the hardest activities DataFrame to filter and sort by difficulty score.

    Args:
        df (pd.DataFrame): The DataFrame containing activity data.

    Returns:
        pd.DataFrame: Processed DataFrame with relevant columns and sorted by difficulty score.
    """
    # Filter out ski activities
    df = df[df['Sport Type'] != 'AlpineSki']

    # Extract relevant columns
    df = df[["Activity Name", "Date", "Sport Type", "Distance (miles)", "Total Elevation Gain (ft)", "Difficulty Score"]]

    # Sort by difficulty score
    hardest_overall_activities = df.sort_values(by="Difficulty Score", ascending=False).reset_index(drop=True)

    return hardest_overall_activities

def process_sky_log(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the the cleaned dataframe to generate the Sky Log DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame containing activity data.

    Returns:
        pd.DataFrame: Processed DataFrame with relevant columns and sorted by difficulty score.
    """
    # Filter out activities without elevation
    df = df[df['elev_high'] > 0]

    # Extract relevant columns
    #df = df[["Activity Name", "Date", "Sport Type", "Distance (miles)", "Total Elevation Gain (ft)", "Difficulty Score"]]

    # Sort by difficulty score
    sky_log_activities = df.sort_values(by="elev_high", ascending=False).reset_index(drop=True)

    return sky_log_activities


def load_and_encode_image(image_path: str) -> str:
    """
    Loads an image from the specified path and encodes it in base64 format for use in Streamlit.

    Args:
        image_path (str): Path to the image file.

    Returns:
        str: Base64 encoded string of the image.
    """
    with open(image_path, "rb") as f:
        image = f.read()
        encoded = base64.b64encode(image)
    image = "data:image/png;base64," + encoded.decode("utf-8")
    return image

def switch_to(path: str):
    """
    Switches to a different page in the Streamlit app.

    Args:
        path (str): The path of the page to switch to.
    """
    st.switch_page(path)

#############################
### Hardest_Activities.py ###
#############################
def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns.
    Adapted from https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            left.write("↳")
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    _min,
                    _max,
                    (_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].str.contains(user_text_input)]

    return df
