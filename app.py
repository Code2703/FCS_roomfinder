from flask import Flask, render_template, request, session, redirect, url_for
import requests
import numpy as np
import pandas as pd
from datetime import datetime as dt
from datetime import timedelta
from API_calls import API

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
    
    # Display landing page for current time with no filters applied
    if request.method == 'GET':
        
        # Set default session values
        session.setdefault('filter_time', current_time.strftime("%H:%M"))
        session.setdefault('filter_end_time', rounded_up_time_str)
        session.setdefault('filter_date', current_date)
        session.setdefault('filter_size', np.inf)
        
        # Create mask for handling variables in HTML and Jinja2 (np.inf not available in Jinja2)
        filter_size = session.get('filter_size')
        filter_size_is_inf = filter_size == np.inf

        # Retrieve specified data from API
        rooms_df = api.get_free_rooms(current_time.strftime(format="%H:%M"), rounded_up_time_str)

        # Filter lecture rooms
        rooms_df = api.filter_rooms(rooms_df)

        return render_template('home.html', rooms_df=rooms_df, filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf, rounded_up_time_str=rounded_up_time_str)
    
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

        # Set session variables to store filter configuration
        session['filter_time'] = filter_time
        session['filter_end_time'] = filter_end_time
        session['filter_date'] = filter_date
        session['filter_size'] = filter_size

        filter_size_is_inf = filter_size == np.inf
        

        return render_template('home.html', rooms_df=rooms_df, filter_date=session['filter_date'], filter_time=session['filter_time'], filter_end_time=session['filter_end_time'], filter_size=session['filter_size'], max_date=max_date, min_date=min_date, filter_size_is_inf=filter_size_is_inf)

# Route to clear filter session variables
@app.route('/clear_filters', methods=['POST'])
def clear_filters():
    for key in list(session.keys()):
        session.pop(key)
    return redirect(url_for('home'))


# Detailed schedule of a given room
@app.route("/room", methods=['GET', 'POST'])
def room():
    if request.method == 'GET':
        my_variable = ['This', 'is', 'a', 'quick', 'demo']

        # The render_template function will render the html file you see when calling the webpage by passing the variables and executing the logic you specified.
        # Placeholders can be specified as seen below -> the expression before the comma refers to the variable as used in the HTML template, 
        # the one after the comma to the variable as it's used in this Python script (Note, you don't have to name them the same but it helps with keeping track of your variable names).
        return render_template('room.html', my_variable=my_variable)
    
    # If method = POST -> this route must be specified when you want to re-render a webpage based on the user's input
    # e.g., when the user fills in and submits a form and you want to display changes to the webpages based on the input
    # Have a look at how it's implemented in the landing page above and also have a look at how you have to specify the HTML forms in the "home.html" template to post to the page.
    else:
        return render_template('apology.html')
    
@app.route('/map')
def map():
    # Example coordinates - replace with your actual coordinates
    latitude = 59.911491
    longitude = 10.757933

    # Construct the iframe URL with your parameters
    iframe_url = f"http://use.mazemap.com/embed.html?campusid=710&typepois=36317&desttype=poi&dest=1000725770&starttype=poi&start=1000725329"

    # Pass the iframe URL to the template
    return render_template('map.html', iframe_url=iframe_url)

if __name__ == '__main__':
    app.run(debug=True)