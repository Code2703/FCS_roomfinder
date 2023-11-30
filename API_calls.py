import requests
import pandas as pd
import numpy as np
from datetime import datetime as dt
from datetime import timedelta
import re
from pandas import json_normalize


class API:

    # API-KEY
    def __init__(self, api_token):
        self.api_token = api_token
    
    # Define method to call on-campus rooms
    def get_rooms(self):
        """Returns a pandas dataframe containing all lecture rooms, including their capacity and system IDs. Note that some rooms have multiple IDs."""
        url = "http://api.mazemap.com/api/pois/?campusid=710&srid=4326"

        response = requests.get(url)

        if response.ok:
            json_response = response.json()

            # Extract the 'pois' list
            pois_data = json_response.get('pois', [])

            # Flatten the data and create DataFrame
            df = json_normalize(pois_data)
        else:
            print("Error calling the API: ", response.status_code)


        # Normalize JSON data excluding 'infos' and 'types'
        df = json_normalize(
            json_response['pois'],
            meta=[
                'poiId', 'kind', ['point', 'type'], ['point', 'coordinates'],
                ['geometry', 'type'], ['geometry', 'coordinates'],
                'campusId', 'floorId', 'floorName', 'buildingId', 'buildingName',
                'identifierId', 'identifier', 'title', 'deleted',
                'z', 'infoUrl', 'infoUrlText', 'description', 'peopleCapacity',
                'images', 'types'
            ],
            errors='ignore'
        )

        # Extract only the first entry from each 'types' list
        def extract_first_type(types_list):
            return types_list[0] if types_list else {}

        df['first_type'] = df['types'].apply(extract_first_type)

        # Normalize the first type data
        df_first_type = df['first_type'].apply(pd.Series)

        # Concatenate the first type data back to the main DataFrame
        df_final = pd.concat([df.drop(columns=['types', 'first_type']), df_first_type], axis=1)

        # Drop and rename columns
        df_final.drop(columns=['identifierId', 'identifier', 'images', 'nodeId', 'kind', 'deleted', 'campusId'], inplace=True)
        df_final.rename({'peopleCapacity':'seats'}, axis=1,inplace=True)

        # Define pattern to extract for room_nr
        pattern = r"(?<!\w)(\d{2}-\d{3,4})\b"

        # Boolean mask based on specified RegEx pattern
        df_final['room_nr'] = df_final['title'].str.extract(pattern)

        # Exclude rooms that don't fit room_nr pattern
        df_final = df_final.loc[~df_final['room_nr'].isna()]

        return df_final
    
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
    

    # def next_event(self, df, room_nr, filter_end, room_info):
    def next_event(self, df, room_nr, filter_end):
        room_events = df.query("room_nr == @room_nr and start_time.dt.time > @filter_end")
        if not room_events.empty:
            return room_events.sort_values(by='start_time').head(1)
        else:
            # Create a row for rooms with no more events
            room_details = df.loc[df['room_nr'] == room_nr].head(1).copy()
            room_details['start_time'] = None
            room_details['end_time'] = None
            room_details['start_time_only'] = None
            room_details['end_time_only'] = None

            no_event_row = pd.DataFrame(room_details)
            no_event_row['subject'] = ['No more events planned for today']
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
                filtered_df = self.next_event(merged_df, room, filter_end) # removed kwarg: , rooms
                filtered_dfs.append(filtered_df)

            result_df = pd.concat(filtered_dfs)
        
        else:
            occupied = merged_df.query("(start_time.dt.time <= @filter_start) and (end_time.dt.time > @filter_start)").room_nr.unique()
            free_rooms = list(filter(lambda x: x not in occupied, rooms['room_nr']))
            filtered_dfs = []
            for room in free_rooms:
                filtered_df = self.next_event(merged_df, room, filter_start)  # removed kwarg: , rooms
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