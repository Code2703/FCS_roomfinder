from flask import Flask, flash, render_template, request, session, redirect, url_for
import requests
import numpy as np
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
from API_calls import API, euclidean_distance
from scraper import seatfinder

#########################################################################################
# SET-UP

# Set up application and connect database
app = Flask(__name__)

# Read API_token from config.py file
app.config.from_pyfile("config.py")

# Initialize instance of API with api_token
api = API(app.config['API_TOKEN'])

# Set secret key for session variables
app.secret_key = app.config['SECRET_KEY']


#########################################################################################
# WEBPAGES


# Landing page with overview of room occupancy and filtering options
@app.route("/", methods=['GET', 'POST'])
def home():

    # Initialize variables
    current_time = dt.now()
    current_date = dt.now()
    max_date = current_date + timedelta(days=30)
    min_date = current_date - timedelta(days=30)
    
    # Format dates as strings
    current_date = current_date.strftime("%Y-%m-%d")
    max_date = max_date.strftime("%Y-%m-%d")
    min_date = min_date.strftime("%Y-%m-%d")

    # Round up to the next full hour
    rounded_up_time = current_time + timedelta(minutes=30)
    rounded_up_time = rounded_up_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    rounded_up_time_str = rounded_up_time.strftime("%H:%M")
    
    # Check if filter_applied is in session, if not, set it to False
    filter_applied = session.get('filter_applied')
    if filter_applied is None:
        filter_applied = False  

    # Display landing page for current time with no filters applied
    if request.method == 'GET':
        
        # Set default session values
        session.setdefault('filter_time', current_time.strftime("%H:%M"))
        session.setdefault('filter_end_time', rounded_up_time_str)
        session.setdefault('filter_date', current_date)
        session.setdefault('filter_size', np.inf)
        session.setdefault('filter_applied', False)

        # Set filter_applied to False in the session
        session['filter_applied'] = False
        
        # Create mask for handling variables in HTML and Jinja2 (np.inf not available in Jinja2)
        filter_size = session.get('filter_size')
        filter_size_is_inf = filter_size == np.inf

        # Retrieve specified data from API
        rooms_df = api.get_free_rooms(current_time.strftime(format="%H:%M"), rounded_up_time_str)

        # Filter lecture rooms
        rooms_df = api.filter_rooms(rooms_df)

        # Starting locations to select for routing
        start_locations = api.get_rooms()

        return render_template('home.html', rooms_df=rooms_df, filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf, rounded_up_time_str=rounded_up_time_str, start_locations=start_locations, filter_applied=session['filter_applied'])
    
    # Apply filters and re-render template
    else:

        # Filter by size
        filter_size_input = request.form.get("filter_size", np.inf).strip()
        filter_size = int(filter_size_input) if filter_size_input.isdigit() else np.inf
        
        # Handle start-time user input
        filter_time_input = request.form.get('filter_time', current_time)
        if filter_time_input == 'Now':
            filter_time = current_time.strftime("%H:%M")
        elif len(filter_time_input.split(":")) == 2 and all(part.isdigit() for part in filter_time_input.split(":")):
            filter_time = filter_time_input
        else:
            filter_time = current_time.strftime("%H:%M")
        
        # Handle end-time user input
        filter_end_time_input = request.form.get('filter_end_time', None)
        if not (len(filter_end_time_input.split(":")) == 2 and all(part.isdigit() for part in filter_end_time_input.split(":"))):
            filter_end_time = None
        else:
            filter_end_time = filter_end_time_input

        # Filter by date
        filter_date_input = request.form.get('filter_date', None)
        if filter_date_input != None:
            try:
                # Validate the date format
                dt.strptime(filter_date_input, '%Y-%m-%d')
                filter_date = filter_date_input
            except ValueError:
                # Handle the case where the date format is incorrect
                print("Incorrect date format provided.")
                filter_date = current_date
        else:
            filter_date = current_date

        # Get free rooms for user-specified time-window    
        rooms_df = api.get_free_rooms(filter_time, filter_end_time, filter_date)
        
        # Filter lecture rooms
        rooms_df = api.filter_rooms(rooms_df)
        
        # Apply size filter
        if filter_size != np.inf:
            rooms_df = rooms_df.query(f'seats <= {filter_size}')

        # Starting locations to select for directions
        start_locations = api.get_rooms()
        
        # Get current location
        current_loc = request.form['start_location']
        current_coordinates = start_locations.query('room_nr == @current_loc')['point.coordinates'].values[0]
        current_height = start_locations.query('room_nr == @current_loc')['z'].values[0]
        
        # Calculate euclidean distances to show closest rooms
        rooms_df['distance'] = rooms_df.apply(lambda row: euclidean_distance([*row['point.coordinates'], row['z']*5], [*current_coordinates, current_height*5]), axis=1)

        # Set session variables to store filter configuration
        session['filter_time'] = filter_time
        session['filter_end_time'] = filter_end_time
        session['filter_date'] = filter_date
        session['filter_size'] = filter_size
        session['current_loc'] = current_loc

        # Create mask for handling variables in HTML and Jinja2 (np.inf not available in Jinja2)
        filter_size_is_inf = filter_size == np.inf
        

        # Set filter_applied to True in the session
        session['filter_applied'] = True

        # DELETE THIS: this is just for testing
        print("Filter Applied:", session['filter_applied'])

        return render_template('home.html', rooms_df=rooms_df.sort_values(by='distance'), filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf, rounded_up_time_str=rounded_up_time_str, start_locations=start_locations, filter_applied=session['filter_applied'])

# Route to clear filter session variables
@app.route('/clear_filters', methods=['POST'])
def clear_filters():
    session.pop('filter_time', None)
    session.pop('filter_end_time', None)
    session.pop('filter_date', None)
    session.pop('filter_size', None)
    session.pop('current_loc', None)
    session['filter_applied'] = False  # Set filter_applied to False in the session
    return redirect(url_for('home'))

# Display detailed information and directions for a selected room  
@app.route('/map', methods=['GET'])
def map():
    rooms = api.get_rooms()
    start_room_nr = request.args.get('room_nr')
    dest_room_nr = session.get('current_loc')
    current_time = dt.now()
    current_date = current_time.strftime("%Y-%m-%d")

    # Display room occupancy
    courses_today = api.get_courses(current_date)
    # Filter out courses and events that take place in the specified room
    if not isinstance(courses_today, pd.DataFrame):
        flash("Error retrieving course data.")
        return render_template('map.html', room_nr=start_room_nr, room_schedule_df=pd.DataFrame())
    
    # Convert start and end times to datetime, if not already done
    courses_today['start_time'] = pd.to_datetime(courses_today['start_time'])
    courses_today['end_time'] = pd.to_datetime(courses_today['end_time'])

    # Filter courses and events that take place in the specified room
    room_events = courses_today.query("room_nr == @start_room_nr and end_time >= @current_time")
    # Sort events by their start time
    room_events_sorted = room_events.sort_values(by='start_time')

    # Set the start time of the day and the end time of the day
    start_of_day = dt.now().replace(hour=7, minute=0, second=0, microsecond=0)
    end_of_day = dt.now().replace(hour=22, minute=0, second=0, microsecond=0)

    # Start with the start time of the day
    current_time = start_of_day

    # An empty list to collect new entries
    new_entries = []

    for index, row in room_events_sorted.iterrows():
        if current_time < row['start_time']:
            # There is a gap
            new_entry = {
                'start_time': current_time,
                'end_time': row['start_time'],
                'subject': 'Great! The room is free for you to study in.'
            }
            new_entries.append(new_entry)
        
        # Update the current time to the end of this event
        current_time = row['end_time']

    # Check after the last event
    if current_time < end_of_day:
        new_entry = {
            'start_time': current_time,
            'end_time': end_of_day,
            'subject': 'Great! The room is free for you to study in.'
        }
        new_entries.append(new_entry)

    # Add the new entries to the DataFrame
    if new_entries:
        room_events_sorted = pd.concat([room_events_sorted, pd.DataFrame(new_entries)]).sort_values(by='start_time').reset_index(drop=True)

    if room_events_sorted.empty:
        flash(f"No data available for room {start_room_nr}")

    room_schedule_df = api.get_schedule(start_room_nr)

    #display map
    if start_room_nr is not None and dest_room_nr is not None:
        start_poiId = rooms.query('room_nr == @start_room_nr')['poiId'].iloc[0]
        dest_poiId = rooms.query('room_nr == @dest_room_nr')['poiId'].iloc[0]

        # Construct the iframe URL with your parameters
        iframe_url = f"http://use.mazemap.com/embed.html?campusid=710&typepois=36317&desttype=poi&dest={start_poiId}&starttype=poi&start={dest_poiId}"

        # Pass the iframe URL to the template
        return render_template('map.html', iframe_url=iframe_url, start_poiId=start_poiId, dest_poiId=dest_poiId, room_nr=start_room_nr, room_schedule_df=room_events_sorted)
    else:
        # Provide more information for debugging
        error_message = f"Invalid request: start_room_nr={start_room_nr}, dest_room_nr={dest_room_nr}"
        return render_template('error.html', message=error_message)

# Navbar routing to apology
@app.route('/apology')
def apology():
    return render_template('apology.html')

# Navbar routing to allRooms
@app.route('/studySpots')
def allRooms():
    return render_template('studySpots.html')
    
if __name__ == '__main__':
    app.run(debug=True)