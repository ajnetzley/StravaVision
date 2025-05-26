"""
utils.py
v0.0.1, 5/26/2025
Author: Alexander Netzley, anetzley@uw.edu

This module provides helper functions for the StravaVision app.
"""

# Import packages
import os
import json
import pandas as pd

# This function loads and concats all the activities jsons, and then extracts relevant fields and converts to a df
def load_data():

    folder_path = os.path.join(os.getcwd(), "activities_data")
    extracted_data = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, "r") as f:
                try:
                    dataset = json.load(f)
                except json.JSONDecodeError:
                    print(f"Skipping malformed JSON: {filename}")
                    continue
                for activity in dataset:
                    extracted_data.append({
                        "id": activity["id"],
                        "name": activity["name"],
                        "distance": activity["distance"],
                        "moving_time": activity["moving_time"],
                        "elapsed_time": activity["elapsed_time"],
                        "total_elevation_gain": activity["total_elevation_gain"],
                        "type": activity["type"],
                        "start_date": activity["start_date"],
                        "start_date_local": activity["start_date_local"],
                        "timezone": activity["timezone"],
                        "kudos_count": activity["kudos_count"],
                        "average_speed": activity["average_speed"],
                        "max_speed": activity["max_speed"],
                        "sport_type": activity["sport_type"],
                        "elev_high": activity.get("elev_high", 0),
                        "elev_low": activity.get("elev_low", 0)
                    })

    df = pd.DataFrame(extracted_data)

    return df
