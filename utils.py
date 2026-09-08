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
import re
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

        activities = client.get_activities(limit=1500)

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
            "TrailRun": 1/1.1,
            "NordicSki": 1,
            "Hike": 4/3, #1
            "BackcountrySki": 2
        }

        activities_elevation_scalar = {
            "Ride": 1.5,
            "MountainBikeRide": 1.5,
            "GravelRide": 1.5,
            "Run": 2,
            "TrailRun": 2*1.1,
            "NordicSki": 2,
            "Hike": 2,
            "BackcountrySki": 2
        }

        partial_scramble_adjustment = { # Currently, 1 + (the percentage of mileage off trail rounded to nearest 0.1)
            'Longs Peak & Mt. Meeker': 1.3,
            "Andrew’s Glacier + Taylor + Hallett": 1.1,
            'Black Peak': 1.2,
            "Earl + Bean + Devil’s Head": 1.2,
            "Mount Storm King": 1.1,
            "Luahna Peak": 1.3,
            "Mount Daniel": 1.1,
            "Carne High Route": 1.1,
            "P3 + Web + Defiance + Bandera": 1.1,
            "Switchback + Martin + Bigelow": 1.1,
            "Three Fingers": 1.3,
            "Vesper Peak": 1.2,
            "South Ingalls": 1.3,
            "Dragontail + Little Annapurna": 1.2,
            "Cathedral Slam - Day 1": 1.1,
            "Cathedral Slam - Day 2": 1.1,
        }

        # Partial Backpacking adjustment ( currently, 1.10x the hike score for both distance and elevation) My pack is ~35lbs, vs ~15lb on a regular hike)
        partial_backpacking_adjustment = {
            "Red Deer Lake - Day 1": 1.1,
            "Red Deer Lake - Day 2": 1.1,
            "Strawberry Point - Day 1": 1.1,
            "Strawberry Point - Day 2": 1.1,
            "Hannegan Peak + Copper Creek - Day 1": 1.075, # Peak without backpack
            "Copper Creek - Day 2": 1.1,
            "Devil’s Dome - Day 1": 1.1,
            "Devil’s Dome - Day 2": 1.1,
            "Devil’s Dome - Day 3": 1.075, # Peak without backpack
            "Devil’s Dome - Day 4": 1.1,
            "Camp Muir": 1.1,
            "Crystal Uphill": 1.1,
            "Table Mountain Circumnav": 1.1,
            "Hyak Laps": 1.1,
            "Summit West Laps": 1.1,
            "Silver Fir Laps": 1.1,
            "Silver Fir": 1.1,
            "Cathedral Slam - Day 1": 1.075, # Peak without Backpack
            "Cathedral Slam - Day 2": 1.05, # Peaks without Backpack
        }

#https://medium.com/aha-science/walk-vs-run-which-is-most-efficient-93e444279443
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
            "McClellan Butte": 0.5,
            "Alta Mountain + Rampart Ridge": 0.25,
            "Mount Daniel": 0.25,
            "Carne High Route": 0.25,
            "P3 + Web + Defiance + Bandera": 0.25,
            "Dirty Harry’s Balcony": 0.5,
            "West Tiger 1 & 2": 0.75,
            "West Tiger #3": 0.5,
            "West Tiger 1 2 3": 0.75,
            "Mt. Si": 0.5,
            "Poo Poo Point": 0.5,
            "French Cabin + Kachess Ridge": 0.25,
            "Johnson + Malcolm + Koppen": 0.5,
            "High Divide Loop": 0.75,
            "Mount Dickerman": 0.5,
            "Guye Peak": 0.5,
            "Cable Line": 0.75,
            "Dragontail + Little Annapurna": 0.25,
            "Cathedral Slam - Day 2": 0.5
        }

        # For partial trail/run activities we will compute a blended scalar
        # when applying scalars below. The previous two-step approach (precompute
        # `updated_partial_trail_run_adjustment` and also apply a correction
        # factor) could double-apply the adjustment; we'll replace that with a
        # single blended scalar function used for both distance and elevation.

        partial_gravel_ride_adjustment = {
             "BLOM / Island Lake": 2.5/(0.25*2.5 + 0.75*3),
             "Island Lake": 2.5/(0.25*2.5 + 0.75*3),
             "Waterloo + DTE": 2.5/(0.25*2.5 + 0.75*3),
             "Thrilla + North Lake Washington": 3/(0.5*3.5 + 0.5*4), # Gravel with the new bike gets 3.5, closer to road
             "Duvall + Marckworth Forest": 3/(0.5*3.5 + 0.5*4),
             "Snoqualmie Valley Trail": 3/(0.5*3.5 + 0.5*4),
             "Palouse to Cascades Trail": 3/3.5


        }

        # Manual elevation overrides (feet) for specific activities.
        # Add entries here as: "Activity Name": elevation_in_feet
        elevation_override = {
            # Example:
            "Luahna Peak": 7069,
            "Johnson + Malcolm + Koppen": 4949, #5430,
            "Camp Muir": 4664,
            "French Cabin + Kachess Ridge": 4775, #5012,
            "P3 + Web + Defiance + Bandera": 5554, #6018,
            "Carne High Route": 5769,#6094,
            "Mount Daniel": 5519, #5730,
            "Alta Mountain + Rampart Ridge": 4385,
            "Vesper Peak": 4247,
            "Black Peak": 5278,#5319,
            "Earl + Bean + Devil’s Head": 4720,
            "Oyster Dome Loop": 3844,
            "Trappers Peak + Thornton Lake": 4242,
            "Spray Park Loop": 5282, #5148,
            "Old Snowy + Knife’s Edge": 4790,
            "Enchanments": 5173,#5251,
            "Granite Mountain": 3560,
            "Johnston’s + Harry’s Ridge": 3499,
            "Mailbox Peak": 4035,
            "Mt. Teneriffe + Mt. Si": 7531,
            "Longs Peak & Mt. Meeker": 6247,
            "Andrew’s Glacier + Taylor + Hallett": 5128,#4798,
            "Switchback + Martin + Bigelow": 6894,
            "High Divide Loop": 5184,
            "Three Fingers": 5803,
            "South Ingalls": 4380,
            "Dragontail + Little Annapurna": 7285,
            "Cathedral Slam - Day 1": 6877,
            "Cathedral Slam - Day 2": 3473
        }

        def convert_timestamp(timestamp):
            if isinstance(timestamp, datetime):
                dt = timestamp
            else:
                dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%m/%d/%y")
    #https://journals.lww.com/acsm-msse/fulltext/1999/11000/comparing_cycling_world_hour_records,_1967_1996_.25.aspx
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

        # Calculate the distance score (miles) using a blended base scalar for
        # partial trail/run activities (applied once). For activities listed in
        # `partial_trail_run_adjustment`, the value N is the portion that is a
        # trail run, so the blended scalar = N*trail_scalar + (1-N)*hike_scalar.
        def _base_distance_scalar(row):
            sport = row.get("sport_type")
            name = row.get("name")
            p = partial_trail_run_adjustment.get(name, None)
            if p is not None:
                trail = activities_distance_scalar.get("TrailRun", 1)
                hike = activities_distance_scalar.get("Hike", 1)
                return p * trail + (1 - p) * hike
            return activities_distance_scalar.get(sport, 1)

        base_distance = df.apply(_base_distance_scalar, axis=1)
        filtered_activities["distance_score"] = (df["distance"] * 0.000621371) / base_distance
        filtered_activities["distance_score"] = (filtered_activities["distance_score"] * df["name"].map(lambda x: partial_gravel_ride_adjustment.get(x, 1))).round(2)
        filtered_activities["distance_score"] = (filtered_activities["distance_score"] * df["name"].map(lambda x: partial_scramble_adjustment.get(x, 1))).round(2)
        filtered_activities["distance_score"] = (filtered_activities["distance_score"] * df["name"].map(lambda x: partial_backpacking_adjustment.get(x, 1))).round(2)

                # Attach debug columns with partial adjustment details used by distance
        # and elevation calculations. Include base scalars (blended where
        # applicable) and each per-activity manual adjustment (or 1 if absent).
        def _partial_adjustments_distance(row):
            name = row.get("name")
            try:
                base_val = float(base_distance.loc[row.name])
            except Exception:
                base_val = activities_distance_scalar.get(row.get("sport_type"), 1)
            return {
                "base_distance": 1/base_val,
                "partial_trail_run": partial_trail_run_adjustment.get(name, 1),
                "partial_gravel_ride": partial_gravel_ride_adjustment.get(name, 1),
                "partial_scramble": partial_scramble_adjustment.get(name, 1),
                "partial_backpacking": partial_backpacking_adjustment.get(name, 1),
            }

        def _partial_adjustments_elevation(row):
            name = row.get("name")
            try:
                base_val = float(base_elev.loc[row.name])
            except Exception:
                base_val = activities_elevation_scalar.get(row.get("sport_type"), 1)
            return {
                "base_elevation": base_val,
                "partial_trail_run": partial_trail_run_adjustment.get(name, 1),
                "partial_backpacking": partial_backpacking_adjustment.get(name, 1),
            }




        # Calculate the elevation score (1.5x for cycling, 2x for everything else)
        filtered_activities["elev_high"] = filtered_activities["elev_high"].fillna(0) #Temporary fix for missing elevation data
        filtered_activities["elev_low"] = filtered_activities["elev_low"].fillna(0)
        filtered_activities["total_elevation_gain"] = filtered_activities["total_elevation_gain"].fillna(0) * 3.28084 #Temporary fix for missing elevation data

        # Apply elevation manual override here
        if elevation_override:
            # elevation_override keys are activity names, values are elevation in feet
            for act_name, elev_ft in elevation_override.items():
                try:
                    mask = filtered_activities["name"] == act_name
                except Exception:
                    # If name column is missing, skip
                    mask = pd.Series(False, index=filtered_activities.index)

                if mask.any():
                    filtered_activities.loc[mask, "total_elevation_gain"] = float(elev_ft)
                    warnings.warn(f"Applied elevation override for '{act_name}': {elev_ft} ft")

        # --- Debug: per-activity elevation scaler combining elevation adjustments ---
        def _base_elevation_scalar(row):
            sport = row.get("sport_type")
            name = row.get("name")
            p = partial_trail_run_adjustment.get(name, None)
            if p is not None:
                trail = activities_elevation_scalar.get("TrailRun", 1)
                hike = activities_elevation_scalar.get("Hike", 1)
                return p * trail + (1 - p) * hike
            return activities_elevation_scalar.get(sport, 1)

        def _compute_activity_elevation_scaler(row):
            base = _base_elevation_scalar(row)
            backpack = partial_backpacking_adjustment.get(row.get("name"), 1)
            scramble = partial_scramble_adjustment.get(row.get("name"), 1)
            try:
                scaler = float(base) * float(backpack) * float(scramble)
            except Exception:
                scaler = 1.0
            return round(scaler, 6)

        # Apply blended elevation base scalar once, then apply backpacking adjustment
        base_elev = df.apply(_base_elevation_scalar, axis=1)
        filtered_activities["elevation_score"] = (filtered_activities["total_elevation_gain"] * 0.001) * base_elev
        filtered_activities["elevation_score"] = (filtered_activities["elevation_score"] * df["name"].map(lambda x: partial_backpacking_adjustment.get(x, 1))).round(2)


        filtered_activities["partial_adjustments_distance"] = df.apply(_partial_adjustments_distance, axis=1)
        filtered_activities["partial_adjustments_elevation"] = df.apply(_partial_adjustments_elevation, axis=1)

        #Mulitply all the dict items together to get the scalers for distance and elevation
        
        filtered_activities["activity_distance_scaler"] = filtered_activities["partial_adjustments_distance"].apply(
            lambda d: (float(d.get("base_distance", 1))) * float(d.get("partial_gravel", 1)) * float(d.get("partial_scramble", 1)) * float(d.get("partial_backpacking", 1))
        )
        filtered_activities["activity_elevation_scaler"] = filtered_activities["partial_adjustments_elevation"].apply(
            lambda d:  float(d.get("base_elevation", 1)) * float(d.get("partial_backpacking", 1)) 
        )

        # Calculate the combined difficulty score
        filtered_activities["difficulty_score_without_altitude"] = filtered_activities["distance_score"] + filtered_activities["elevation_score"]

        # Add adjustments for the average elevation of the activity (altitude performance capacity)
        filtered_activities["average_elevation"] = (((filtered_activities["elev_high"] + filtered_activities["elev_low"])/2)*3.28084).round(2)
        filtered_activities["performance_capacity"] = (filtered_activities["average_elevation"].round(-3)).map(elevation_to_capacity)
        filtered_activities["difficulty_score"] = (filtered_activities["difficulty_score_without_altitude"] / filtered_activities["performance_capacity"]).round(2)

        # Convert raw distance, elevation, and date to readable formats
        filtered_activities["Distance (miles)"] = (filtered_activities["distance"]*0.000621371).round(2)
        filtered_activities["Total Elevation Gain (ft)"] = (filtered_activities["total_elevation_gain"]).round(0).astype(int)
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

        # filter filtered activies to only the trail run and hike activities, with only the c,olumns of name and all the pieces that make up the elevatio nand distance score
        filtered_activities = filtered_activities[filtered_activities['Sport Type'].isin(['TrailRun', 'Hike'])]
        filtered_activities = filtered_activities[["Activity Name", 
                                                   "Sport Type",
                                                   "Distance (miles)", 
                                                   "distance_score",
                                                   "activity_distance_scaler",
                                                   "average_elevation",
                                                   "Total Elevation Gain (ft)", 
                                                   "elevation_score",
                                                   "activity_elevation_scaler",
                                                   "difficulty_score_without_altitude",
                                                   "performance_capacity",
                                                   "Difficulty Score",
                                                   "partial_adjustments_distance",
                                                   "partial_adjustments_elevation"
                                                   ]]


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
    #df = df[df['elev_high'] > 0]

    # Extract relevant columns
    #df = df[["Activity Name", "Date", "Sport Type", "Distance (miles)", "Total Elevation Gain (ft)", "Difficulty Score"]]

    # Sort by difficulty score
    sky_log_activities = df#.sort_values(by="elev_high", ascending=False).reset_index(drop=True)

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
                    # Safely handle NaNs and treat the input as a literal substring by default
                    # Use regex=False to avoid bad escape errors from user input
                    try:
                        mask = df[column].fillna("").astype(str).str.contains(
                            user_text_input, case=False, regex=False, na=False
                        )
                    except Exception:
                        # Fallback: escape the pattern and try again as regex
                        escaped = re.escape(user_text_input)
                        mask = df[column].fillna("").astype(str).str.contains(
                            escaped, case=False, regex=True, na=False
                        )

                    df = df[mask]

    return df
