from flask import Flask, render_template, request
import requests
import numpy as np
import pandas as pd
from datetime import datetime
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
    # Call API
    rooms_df = api.get_courses()

    # Initialize variables
    filter_size = np.inf
    time = pd.to_datetime(datetime.now()).time()
    
    # Display landing page for current time with no filters applied
    if request.method == 'GET':
        filtered_df = rooms_df.query(f'(size < {filter_size}) and (start_time_only < @time < end_time_only)')
        return render_template('home.html', rooms_df=filtered_df)
    
    # Apply filters and re-render template
    else:

        # Filter by size
        filter_size_input = request.form.get("filter_size", np.inf).strip()
        if filter_size_input.isdigit():
            filter_size = int(filter_size_input)
        
        # Filter by time
        filter_time_input = request.form.get('filter_time', time)
        filter_time = pd.to_datetime(filter_time_input, format="%H:%M").time()

        # Apply availability filter if checkbox is checked
        # if request.form.get("filter_available") is not None:
        #     rooms_df_filtered = rooms_df_filtered.query("subject == 'Free'")
        
        filtered_df = rooms_df.query(f'(size <= {filter_size}) and (start_time_only <= @filter_time < end_time_only)')

        return render_template('home.html', rooms_df=filtered_df)


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