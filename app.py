from flask import Flask, render_template, request
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

#########################################################################################
# WEBPAGES

# Landing page with overview of room occupancy and filtering options
@app.route("/", methods=['GET', 'POST'])
def home():

    # Initialize variables
    current_time = pd.to_datetime(dt.now()).time()
    current_date = dt.now()
    max_date = current_date + timedelta(days=30)
    current_date = current_date.strftime("%Y-%m-%d")
    max_date = max_date.strftime("%Y-%m-%d")
    
    # Display landing page for current time with no filters applied
    if request.method == 'GET':
        rooms_df = api.get_free_rooms(current_time.strftime(format="%H:%M"))
        return render_template('home.html', rooms_df=rooms_df, current_date=current_date, max_date=max_date)
    
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

        # Apply size filter
        if filter_size != np.inf:
            rooms_df = rooms_df.query(f'size <= {filter_size}')
        

        return render_template('home.html', rooms_df=rooms_df, current_date=current_date, max_date=max_date)


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

if __name__ == '__main__':
    app.run(debug=True)