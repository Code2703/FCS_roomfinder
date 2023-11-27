import requests
import pandas as pd
import numpy as np
from datetime import datetime as dt
from datetime import timedelta
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
        campus_rooms['room_nr'] = campus_rooms['shortName'].apply(lambda x: re.split(r"[\s/]", x)[0].strip("#"))

        # Second mask to ensure consistency
        mask = campus_rooms['room_nr'].str.contains(pattern, na=False)
        campus_rooms = campus_rooms[mask]

        # Group by shortName as unique identifier and collect all IDs assigned in the system, seating capacity and floor
        campus_rooms_clean = campus_rooms.groupby('room_nr')[['id', 'floor', 'seats']].agg(list).reset_index()

        # Keep only one of the (identical) floor values and only the largest capacity value
        campus_rooms_clean['floor'] = campus_rooms_clean['floor'].apply(lambda x: x[0])
        campus_rooms_clean['seats'] = campus_rooms_clean['seats'].apply(lambda x: max(x))

        return campus_rooms_clean
    
    def get_courses(self, date=None):
        """Takes in date as a string in the format '%Y-%m-%d'. Returns the schedule for the specified day, i.e., a timetable of all courses and their locations."""
        # Insert current date as default
        if date is None:
            date_obj = dt.now()
        else:
            # Convert string to datetime object
            date_obj = dt.strptime(date, '%Y-%m-%d')

        # Calculate the end date (next day)
        end_date = date_obj + timedelta(days=1)

        # Format the start and end dates to strings
        start_date_str = date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Assign corresponding url for API-call
        url = f"https://integration.preprod.unisg.ch/eventapi/EventDates/byStartDate/{start_date_str}/byEndDate/{end_date_str}"
        
        headers = {
            "X-ApplicationId": self.api_token,
            "API-Version": "3",
            "X-RequestedLanguage": "en"
        }

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
        rooms_df['date'] = rooms_df['start_time'].dt.date
        rooms_df['date'] = pd.to_datetime(rooms_df['date'])

        return rooms_df
    

    def next_event(self, df, room_nr, filter_end, room_info):
        room_events = df.query("room_nr == @room_nr and start_time.dt.time > @filter_end")
        if not room_events.empty:
            return room_events.sort_values(by='start_time').head(1)
        else:
            # Create a row for rooms with no more events
            room_details = room_info.loc[room_info['room_nr'] == room_nr]
            no_event_row = pd.DataFrame({
                'room_nr': [room_nr],
                'id': [room_details.iloc[0]['id']],
                'floor': [None],
                'seats': [room_details.iloc[0]['seats']],
                'size': [None],
                'start_time': [None],
                'end_time': [None],
                'subject': ['No more events planned for today'],
                'start_time_only': [None],
                'end_time_only': [None],
                'date': [None]
            })
            return no_event_row

    def get_free_rooms(self, filter_start, filter_end=None, date=None):
        """
        Input: Filter_start & filter_end as strings with format '%H:%M'; date as string with format '%Y-%m-%d'. Defaults to current date if none is specified.
        Returns a dataframe of free rooms that match the filter.
        """
        # Convert filter times to time objects
        filter_start = dt.strptime(filter_start, '%H:%M').time()
        courses = self.get_courses(date)
        rooms = self.get_rooms()
        merged_df = rooms.merge(courses, on='room_nr', how='left')

        if filter_end != None:
            filter_end = dt.strptime(filter_end, '%H:%M').time()
            occupied = merged_df.query("(start_time.dt.time < @filter_end) and (end_time.dt.time > @filter_start)").room_nr.unique()
            free_rooms = list(filter(lambda x: x not in occupied, rooms['room_nr']))
            filtered_dfs = []
            for room in free_rooms:
                filtered_df = self.next_event(merged_df, room, filter_end, rooms)
                filtered_dfs.append(filtered_df)

            result_df = pd.concat(filtered_dfs)
        
        else:
            occupied = merged_df.query("(start_time.dt.time <= @filter_start) and (end_time.dt.time > @filter_start)").room_nr.unique()
            free_rooms = list(filter(lambda x: x not in occupied, rooms['room_nr']))
            filtered_dfs = []
            for room in free_rooms:
                filtered_df = self.next_event(merged_df, room, filter_start, rooms)
                filtered_dfs.append(filtered_df)

            result_df = pd.concat(filtered_dfs)

        # Define placeholders for NaT entries
        placeholder_datetime = pd.to_datetime('1970-01-01 00:00:00')

        # Replace NaT and NaN values with placeholders, resp. None
        result_df.replace(np.nan, None, inplace=True)
        result_df['start_time'] = result_df['start_time'].fillna(placeholder_datetime)
        result_df['end_time'] = result_df['end_time'].fillna(placeholder_datetime)
        result_df['date'] = result_df['date'].fillna(placeholder_datetime)

        return result_df