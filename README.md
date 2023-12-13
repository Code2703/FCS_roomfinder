# RoomRadar

## Project Description
With our project we set out to create an overview of study spots at the University of St. Gallen. Such spots include Group Study Rooms, Study Zones (e.g., the library and coworking spaces) and empty lecture rooms. Currently, there are separate pages for booking Group Study Rooms and viewing the capacity of the Study Zones. For lecture rooms, no overview exists at all. Our Web-App introduces the latter and creates a consolidated view.

## Table of Contents

### Python
| Filename      | Description                                                        |
|---------------|--------------------------------------------------------------------|
| `app.py`      | Flask application, including all routes.                           |
| `API_calls.py`| Defines API class, including functions used for API calls.         |
| `scraper.py`  | Selenium-based web-scraper used for scraping dynamically generated data. |





### HTML/CSS/JavaScript
| Filename          | Description                                                                                                  |
|-------------------|--------------------------------------------------------------------------------------------------------------|
| `layout.html`     | Base layout, defines menu and logo                                                                           |
| `home.html`       | Landing-page, displays routes for lecture rooms and group study rooms                                       |
| `seatfinder.html` | Displays information scraped from <https://seatfinder.unisg.ch/> using `scraper.py`                          |
| `map.html`        | Displays detailed schedule, equipment, and location for a specified room. If a start-location is provided, directions are given. |


### General
| Filename         | Description                                                                                                                                                              |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `config.py`      | Needs to be set up with API-Token for the API of the University of St.Gallen, an encryption key for the flask session cache, and the path to the browser-driver (see instructions below). |
| `requirement.txt`| Library dependencies and versions.                                                                                                                                       |
| `.gitignore`     | Ignore `test.py` and `config.py` when committing to remote repository.                                                                                                   |

## Instructions and Dependencies
To get the app running, please create a file 'config.py' in the same directory as app.py. In app.py, specify the following constants:
- `API_TOKEN` - API key access token for the API of the University of St.Gallen (not shareable)
- `SECRET_KEY` - a random encryption key (e.g., a random hex token)
- `DRIVER_PATH` - the path to your browser-driver (required by Selenium; used driver: Google Chrome Driver (https://chromedriver.chromium.org/downloads/version-selection))

Please refer to requirements.txt for the required modules and used versions (run `pip install -r requirements.txt`). This app was built with Python 3.11.4.

## Implementation Details

### Backend
The app is set up around the `API` class defined in `API_calls.py`. An api object can be initialized as follows: `api = API(API_TOKEN)` 

```python
from API_calls import API
from config import API_TOKEN

# First option using flask function "config.from_pyfile()"
app = Flask(__name__) # Set up the Flask application
app.config.from_pyfile("config.py") # Read API_token from config.py file
api = API(app.config['API_TOKEN']) # Initialize instance of API with api_token

# Second option, importing API_TOKEN from config.py
api = API(API_TOKEN)
```
#### Available functions:
The available functions for the API object are the following:
| Name                                          | Description                                                                                                                                                   |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `get_rooms(self)`                             | Returns a pandas dataframe containing all lecture rooms, including their capacity and system IDs. Note that some rooms have multiple IDs.                     |
| `get_courses(self, date=None)`                | Takes in date as a string in the format '%Y-%m-%d'. Returns the schedule for the specified day, i.e., a timetable of all courses and their locations.       |
| `next_event(self, df, room_nr, filter_end)`   | Returns a dataframe containing the next event for a specified room given the day's schedule.                                                                 |
| `get_courses(self, date=None)`                | Input: Filter_start & filter_end as strings with format '%H:%M'; date as string with format '%Y-%m-%d'. Defaults to current date if none is specified. Returns a dataframe of free rooms that match the filter. |
| `filter_rooms(self, rooms_df)`                | Excludes certain buildings and types of rooms when passed a dataframe returned by `get_rooms()`.                                                             |
| `get_schedule(self, room_nr, start_date=None)`| Returns a pandas dataframe containing all events taking place in the specified room for a given date (defaults to current date).                              |
| `old_rooms(self)`                             | Returns a pandas dataframe containing all campus rooms of format xx-(U)xxx, including their capacity and system IDs. Note that some rooms have multiple IDs. Note: use the `get_rooms()` method instead, which accesses the MazeMap API and provides more room details. |


#### Calling API functions:
```python

# Get all room information
rooms_df = api.get_rooms()

# Exclude inaccessible buildings and rooms
filtered_rooms = api.filter_rooms(rooms_df)
```

### Frontend
