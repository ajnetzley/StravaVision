"""
grind_graph.py
v0.0.1, 6/18/2025
Author: Alexander Netzley, anetzley@uw.edu

This page provides the tabular visualization of the hardest cumulative weeks of training throughout my Strava history.
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

# Create the rolling 7-day sum of difficulty reading from the "date" column. However, not every day has an activity, and some may have multiple. Output a vector that has every day present in the dataset and the rolling 7-day difficulty total
df = df[df["Sport Type"] != "AlpineSki"]
# Convert Date column to datetime
df['Date'] = pd.to_datetime(df['Date'])

# Group by date and sum difficulty scores for days with multiple activities
daily_difficulty = df.groupby('Date')['Difficulty Score'].sum().reset_index()

# Create a complete date range from min to max date
date_range = pd.date_range(start=daily_difficulty['Date'].min(), 
                          end=daily_difficulty['Date'].max(), 
                          freq='D')

# Create a complete dataframe with all dates
complete_dates_df = pd.DataFrame({'Date': date_range})

# Merge with daily difficulty, filling missing days with 0
daily_complete = complete_dates_df.merge(daily_difficulty, on='Date', how='left')
daily_complete['Difficulty Score'] = daily_complete['Difficulty Score'].fillna(0)

# Calculate rolling 7-day sum
daily_complete['rolling_7day_difficulty'] = daily_complete['Difficulty Score'].rolling(window=7, min_periods=1).sum()

# Sort by date to ensure proper order
daily_complete = daily_complete.sort_values('Date').reset_index(drop=True)

# Find the hardest weeks (top rolling 7-day periods) with no overlapping periods
def get_non_overlapping_hardest_weeks(daily_complete_df, original_df, max_periods=20):
    """
    Get non-overlapping 7-day periods with highest difficulty scores
    """
    # Sort by rolling difficulty score descending
    sorted_periods = daily_complete_df.sort_values('rolling_7day_difficulty', ascending=False).reset_index(drop=True)
    
    selected_periods = []
    used_dates = set()
    
    for _, row in sorted_periods.iterrows():
        end_date = row['Date']
        start_date = end_date - pd.Timedelta(days=6)  # 7-day window
        
        # Check if this period overlaps with any already selected period
        period_dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        if not any(date in used_dates for date in period_dates):
            # Get activities for this 7-day period
            period_activities = original_df[
                (original_df['Date'] >= start_date) & 
                (original_df['Date'] <= end_date)
            ].copy().sort_values('Difficulty Score', ascending=False)
            
            # Create activity details as formatted string
            activity_details = []
            activity_strings = []
            for _, activity in period_activities.iterrows():
                activity_detail = {
                    'name': activity['Activity Name'],
                    'date': activity['Date'].strftime('%m/%d/%y'),
                    'difficulty': round(activity['Difficulty Score'], 2)
                }
                activity_details.append(activity_detail)
                
                # Create readable string for display
                activity_strings.append(f"• {activity['Activity Name']} ({activity['Date'].strftime('%m/%d/%y')}): {round(activity['Difficulty Score'], 2)}")
            
            # Join all activities into a multi-line string
            activities_formatted = "\n".join(activity_strings)
            
            selected_periods.append({
                'Week_Ending': end_date,
                'Week_Starting': start_date,
                'Total_Difficulty_Score': round(row['rolling_7day_difficulty'], 2),
                'Activities_Raw': activity_details,  # Keep raw data for potential future use
                'Activities_Display': activities_formatted,  # Formatted string for display
                'Num_Activities': len(period_activities)
            })
            
            # Mark all dates in this period as used
            used_dates.update(period_dates)
            
            if len(selected_periods) >= max_periods:
                break
    
    return pd.DataFrame(selected_periods)

# Get non-overlapping hardest weeks
hardest_weeks = get_non_overlapping_hardest_weeks(daily_complete, df, max_periods=20)

# Format the display columns
display_weeks = hardest_weeks.copy()
display_weeks['Week_Period'] = display_weeks['Week_Starting'].dt.strftime('%m/%d/%y') + ' - ' + display_weeks['Week_Ending'].dt.strftime('%m/%d/%y')
display_weeks = display_weeks[['Week_Period', 'Total_Difficulty_Score', 'Num_Activities', 'Activities_Display']]
display_weeks = display_weeks.rename(columns={'Activities_Display': 'Activities'})


with col1:
    st.title("Grind Graph")
    st.subheader("Hardest Non-Overlapping 7-Day Training Periods")
    st.dataframe(display_weeks, use_container_width=True)
    
    # Optional: Show the complete daily data with rolling averages
    with st.expander("View Complete Daily Data with Rolling 7-Day Totals"):
        st.dataframe(daily_complete, use_container_width=True)

with col2:
    st.image("images/grind_graph.png", caption="Grind Graph Visualization", use_container_width=True)