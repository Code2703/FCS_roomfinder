from flask import Flask, flash, render_template, request, session, redirect, url_for
import requests
import numpy as np
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
from API_calls import API, euclidean_distance
from scraper import seatfinder
from flask_sqlalchemy import SQLAlchemy

##### SET-UP ##############################################################################

# Set up application
app = Flask(__name__)

# Read API_token from config.py file
app.config.from_pyfile("config.py")

# Initialize instance of API with api_token
api = API(app.config['API_TOKEN'])

# Set secret key for session variables
app.secret_key = app.config['SECRET_KEY']

# Intitialize sqlite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
db = SQLAlchemy(app)

# Create database schema for room booking (see route: /book_room)
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_nr = db.Column(db.String(10), nullable=False)
    time_slot = db.Column(db.String(10), nullable=False)
    booking_count = db.Column(db.Integer, default=0) # Counter of number of bookings for a given room_nr and time_slot

    def __repr__(self):
        return f'<Booking {self.room_nr} {self.time_slot}>'

# Set up database in the application context
with app.app_context():
    db.create_all() # Create all tables outlined above

##### ROUTES ###############################################################################

# Landing page with overview of room occupancy and filtering options
@app.route("/", methods=['GET', 'POST'])
def home():
    # Initialize variables for filter settings
    current_time = dt.now()
    current_date = dt.now()
    max_date = current_date + timedelta(days=30)
    min_date = current_date - timedelta(days=30)
    
    # Format dates as strings
    current_date = current_date.strftime("%Y-%m-%d")
    max_date = max_date.strftime("%Y-%m-%d")
    min_date = min_date.strftime("%Y-%m-%d")

    # Default filtering timeframe set to at least 30min: current time until ((current time + 30min) rounded to next full hour)
    rounded_up_time = current_time + timedelta(minutes=30) # Add 30min to current time
    rounded_up_time = rounded_up_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1) # Round to next full hour
    rounded_up_time_str = rounded_up_time.strftime("%H:%M")
    
    # Filte to not display any rooms if no filter is applied 
    filter_applied = session.get('filter_applied') # Check if filter_applied is in session, if not, set it to False
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
        
        # Create mask for handling filter size in HTML and Jinja2 (np.inf not available in Jinja2)
        filter_size = session.get('filter_size')
        filter_size_is_inf = filter_size == np.inf

        # Retrieve specified data from API
        rooms_df = api.get_free_rooms(current_time.strftime(format="%H:%M"), rounded_up_time_str)

        # Filter lecture rooms to exclude unwanted buildings and room types
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
        try:
            current_loc = request.form['start_location']
        except:
            current_loc = None
        print(current_loc)
        if current_loc != None:
            current_coordinates = start_locations.query('room_nr == @current_loc')['point.coordinates'].values[0]
            current_height = start_locations.query('room_nr == @current_loc')['z'].values[0]
        
            # Calculate euclidean distances to show closest rooms
            rooms_df['distance'] = rooms_df.apply(lambda row: euclidean_distance([*row['point.coordinates'], row['z']*5], [*current_coordinates, current_height*5]), axis=1)
            rooms_df = rooms_df.sort_values(by='distance')
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

        return render_template('home.html', rooms_df=rooms_df, filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf, rounded_up_time_str=rounded_up_time_str, start_locations=start_locations, filter_applied=session['filter_applied'])

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
    start_room_nr = session.get('current_loc')
    
    # Get destination room_nr from form or session variable in case of redirect (from /book_room)
    dest_room_nr = request.args.get('room_nr')
    if dest_room_nr is not None:
        session['dest_room_nr'] = dest_room_nr
    else:
        dest_room_nr = session.get('dest_room_nr')
    
    equipment = rooms.query('room_nr == @dest_room_nr')['description'].values[0]
    if equipment != None:
        equipment = equipment.split("\n")
    # Display room occupancy
    date = session.get('filter_date')
    courses_today = api.get_schedule(dest_room_nr, start_date=dt.strptime(date, '%Y-%m-%d'))
    
    schedule = pd.DataFrame({'endTime':['09:00', '10:00', '11:00', '12:00','13:00', '14:00','15:00', '16:00','17:00', '18:00', '19:00', '20:00', '21:00', '22:00'], 
                             'course':['-' for i in range(14)], 
                             'startTime':['08:15', '09:15', '10:15', '11:15', '12:15', '13:15', '14:15', '15:15', '16:15', '17:15', '18:15', '19:15', '20:15', '21:15']}, 
                             columns=['startTime', 'endTime', 'course']
                             )
    schedule['endTime'] = schedule['endTime'].apply(lambda x: dt.strptime(x, '%H:%M').time())
    schedule['startTime'] = schedule['startTime'].apply(lambda x: dt.strptime(x, '%H:%M').time())
    
    courses_today['startTime'] = courses_today['startTime'].apply(lambda x: dt.strptime(x, '%Y-%m-%dT%H:%M:%S').time()) 
    courses_today['endTime'] = courses_today['endTime'].apply(lambda x: dt.strptime(x, '%Y-%m-%dT%H:%M:%S').time()) 

    for i in range(len(schedule)):
        for k in range(len(courses_today)):
            if courses_today['endTime'].iloc[k] > schedule['startTime'].iloc[i] and courses_today['startTime'].iloc[k] < schedule['endTime'].iloc[i]:
                schedule['course'].iloc[i] = courses_today['description'].iloc[k]

    # Create a column to help identify consecutive blocks with the same course
    schedule['group'] = ((schedule['course'] != schedule['course'].shift()) | (schedule['course'] == '-')).cumsum()

    # Aggregate the blocks
    aggregated_schedule = schedule.groupby(['group', 'course'], as_index=False).agg({'startTime': 'first', 'endTime': 'last'}).reset_index(drop=True)
    schedule = aggregated_schedule.drop(columns=['group'])

    for index, row in schedule.iterrows():
        time_slot = row['startTime'].strftime('%H:%M')
        booking = Booking.query.filter_by(room_nr=dest_room_nr, time_slot=time_slot).first()
        if booking:
            schedule.at[index, 'booking_count'] = booking.booking_count
        else:
            schedule.at[index, 'booking_count'] = 0

    # Display map
    if start_room_nr is not None and dest_room_nr is not None:
        start_poiId = rooms.query('room_nr == @start_room_nr')['poiId'].iloc[0]
        dest_poiId = rooms.query('room_nr == @dest_room_nr')['poiId'].iloc[0]

        # Specify map configuration
        iframe_url = f"http://use.mazemap.com/embed.html?campusid=710&typepois=36317&desttype=poi&dest={dest_poiId}&starttype=poi&start={start_poiId}"

        # Pass the iframe URL to the template
        return render_template('map.html', iframe_url=iframe_url, start_poiId=start_poiId, dest_poiId=dest_poiId, room_nr=dest_room_nr, room_schedule_df=schedule, equipment=equipment, date=date)
    else:
        dest_poiId = rooms.query('room_nr == @dest_room_nr')['poiId'].iloc[0]
        # Specify map configuration
        iframe_url = f"http://use.mazemap.com/embed.html?campusid=710&typepois=36317&desttype=poi&dest={dest_poiId}"
        # Provide more information for debugging
        return render_template('map.html', iframe_url=iframe_url, dest_poiId=dest_poiId, room_nr=dest_room_nr, room_schedule_df=schedule, equipment=equipment, date=date)

# Navbar routing to apology
@app.route('/apology')
def apology():
    return render_template('apology.html')

@app.route('/seatfinder', methods=['GET'])
def studyspots():
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
    
    # Retrieve specified data from API
    rooms_df = api.get_free_rooms(current_time.strftime(format="%H:%M"), rounded_up_time_str)

    # Filter lecture rooms
    rooms_df = api.filter_rooms(rooms_df)

    seatfinder_df = seatfinder()
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

    # Starting locations to select for routing
    start_locations = api.get_rooms()

    return render_template('seatfinder.html', seatfinder_df=seatfinder_df, rooms_df=rooms_df, filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], 
                           filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf, rounded_up_time_str=rounded_up_time_str, 
                           start_locations=start_locations, filter_applied=session['filter_applied'])

@app.route('/book_room', methods=['POST'])
def book_room():
    room_nr = request.form['room_nr']
    time_slot = request.form['time_slot']

    booking = Booking.query.filter_by(room_nr=room_nr, time_slot=time_slot).first()
    if booking:
        booking.booking_count += 1
    else:
        new_booking = Booking(room_nr=room_nr, time_slot=time_slot, booking_count=1)
        db.session.add(new_booking)
    db.session.commit()
    
    return redirect(url_for('map')) 

if __name__ == '__main__':
    app.run(debug=True)