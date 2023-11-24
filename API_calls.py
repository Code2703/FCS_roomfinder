import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re


class API:

    # API-KEY
    def __init__(self, api_token):
        self.api_token = api_token
    
    # Define method to call on-campus rooms
    def get_rooms(self):
        """Returns a pandas dataframe containing all campus rooms of format xx-(U)xxx, including their capacity and system IDs. Note that some rooms have multiple IDs."""
        # API URL for Rooms
        url = "https://integration.preprod.unisg.ch/toolapi/Rooms"

        # Headers for API call
        headers = {
            "X-ApplicationId": self.api_token,
            "API-Version": "1",
            "X-RequestedLanguage": "en"
        }

        # Get response from API
        response = requests.get(url, headers=headers)

        # Error handling for API call
        if response.ok:
            json_response = response.json()
            print(json_response)
            df = pd.DataFrame(json_response)
        else:
            print("Error: ", response.status_code)

        # Define RegEx pattern to look for on-campus rooms (pattern: xx-(U)xxx)
        pattern = r"\b\d{2}-[U]?\d{3}\b"

        # Boolean mask based on specified RegEx pattern
        mask = df['shortName'].str.contains(pattern, na=False)

        # Filter rooms using RegEx mask
        campus_rooms = df[mask].copy()

        # Extract clean room number from shortName column
        campus_rooms['shortName_clean'] = campus_rooms['shortName'].apply(lambda x: re.split(r"[\s/]", x)[0].strip("#"))

        # Second mask to ensure consistency
        mask = campus_rooms['shortName_clean'].str.contains(pattern, na=False)
        campus_rooms = campus_rooms[mask]

        # Group by shortName as unique identifier and collect all IDs assigned in the system, seating capacity and floor
        campus_rooms_clean = campus_rooms.groupby('shortName_clean')[['id', 'floor', 'seats']].agg(list).reset_index()

        # Keep only one of the (identical) floor values and only the largest capacity value
        campus_rooms_clean['floor'] = campus_rooms_clean['floor'].apply(lambda x: x[0])
        campus_rooms_clean['seats'] = campus_rooms_clean['seats'].apply(lambda x: max(x))

        return campus_rooms_clean
    
    def get_courses(self):
        """Returns the schedule for the specified day, i.e., a timetable of all courses and their locations."""
        # Assign corresponding url for API-call
        url = "https://integration.preprod.unisg.ch/eventapi/EventDates/byStartDate/2023-11-20/byEndDate/2023-11-21"

        headers = {
            "X-ApplicationId": self.api_token,
            "API-Version": "3",
            "X-RequestedLanguage": "en"
        }

        # params = {
        #     'byStartDate': date,
        #     'byEndDate': date + timedelta(days=1)
        # }

        response = requests.get(url, headers=headers)

        if response.ok:
            json_response = response.json()
            print(json_response)
            courses = pd.DataFrame(json_response)
        else:
            print("Error encountered: ", response.status_code)

        room_nr = courses['location']
        size = courses['room'].str['seats']
        start_time = courses['startTime']
        end_time = courses['endTime']
        subject = courses['description']

        rooms_df = pd.DataFrame({'room_nr':room_nr, 'size':size, 'start_time':start_time, 'end_time':end_time, 'subject':subject})

        # Transform start and end time to datetime format to enable filtering by time
        rooms_df['start_time'] = pd.to_datetime(rooms_df['start_time'], format='%Y-%m-%dT%H:%M:%S')
        rooms_df['end_time'] = pd.to_datetime(rooms_df['end_time'], format='%Y-%m-%dT%H:%M:%S')

        # Create separate columns only containing times for filtering
        rooms_df['start_time_only'] = rooms_df['start_time'].dt.time
        rooms_df['end_time_only'] = rooms_df['end_time'].dt.time

        return rooms_df