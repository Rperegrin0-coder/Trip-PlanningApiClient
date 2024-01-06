import json
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from flask import jsonify,request
import os.path
import string
from datetime import datetime
import  os
import random
import pytz
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from pymongo import MongoClient


def generate_user_id():
    # Make a GET request to the external service to fetch a random user ID
    url = 'https://www.random.org/integers/?num=1&min=1&max=1000&col=1&base=10&format=plain&rnd=new'
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # Assuming the response contains the random user ID
        random_user_id = response.text.strip()  # Extract the random user ID
        return random_user_id  # Return just the ID
    else:
        return None  # Return None or handle error case appropriately


def generate_trip_id():
    # Make a GET request to the external service to fetch a random number between 1 and 1000
    url = 'https://www.random.org/integers/?num=1&min=1&max=1000&col=1&base=10&format=plain&rnd=new'
    
    response = requests.get(url)
    
    if response.status_code == 200:
        # Assuming the response contains the random number
        random_number = response.text.strip()  # Extract the random number
        
        # Generate two random letters
        random_letters = ''.join(random.choice(string.ascii_uppercase) for _ in range(2))
        
        # Combine the random letters and number to create the trip ID
        trip_id = f"{random_letters}{random_number}"
        
        return trip_id  # Return the generated trip ID
    else:
        return None  # Return None or handle error case appropriately



def get_matching_trips(search_location, user_id):
    json_file_path = os.path.join(os.getcwd(), 'suggest_trip.json')
    matching_trips = []

    try:
        

        # Check if the file exists
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                all_trips = data.get('trips', [])
                print(f"Total trips found: {len(all_trips)}")  # Print the total number of trips

            # Filter trips based on the search location and exclude current user's trips
            for trip in all_trips:
                if trip['location'].lower() == search_location.lower() and trip['user_id'] != user_id:
                    matching_trips.append(trip)
                    print(f"Matching trip ID: {trip['trip_id']}")  # Print each matching trip ID

            print(f"Total matching trips found: {len(matching_trips)}")  # Print the total number of matching trips
    except Exception as e:
        print(f"Error reading from suggest_trip.json: {e}")  # Print any errors encountered
        raise

    return matching_trips

def query_new_trips(search_location, exclude_user_id):
    json_file_path = os.path.join(os.getcwd(), 'suggest_trip.json')
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # Filter trips based on location and exclude trips by the current user
            matching_trips = [trip for trip in data['trips'] 
                              if trip['location'].lower() == search_location.lower() 
                              and trip['user_id'] != exclude_user_id]
        return matching_trips
    except FileNotFoundError:
        raise FileNotFoundError('File not found.')
    except json.JSONDecodeError:
        raise Exception('Error decoding JSON.')





def propose_new_trip(location, datetime_str, user_id):
    try:
        # Retrieve user's email
        user_email = get_user_email(user_id)
        if not user_email:
            return {'error': 'User email not found'}

        # Ensure the datetime is in the correct format
        formatted_datetime = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")

        # Ensure location is correctly formatted
        latitude, longitude = geocode_location(location)
        if not latitude or not longitude:
            return {'error': 'Invalid location'}

        # Make the API call for weather information
        api_endpoint = f'http://www.7timer.info/bin/api.pl?lon={longitude}&lat={latitude}&product=civil&output=json'
        response = requests.get(api_endpoint)

        if response.status_code == 200:
            weather_info = response.json()
            temperature = weather_info['dataseries'][0]['temp2m']
            weather_response = f'The weather is {temperature} degrees on {formatted_datetime} at {location}'

            # Generate the trip ID
            trip_id = generate_trip_id()

            # Prepare trip data with email included
            new_trip = {
                'trip_id': trip_id,
                'user_id': user_id,
                'user_email': user_email,
                'location': location,
                'datetime': formatted_datetime.isoformat(),
                'weather_info': weather_response
            }

            # File path for the JSON file
            json_file_path = os.path.join(os.getcwd(), 'suggest_trip.json')

            # Check if file exists, create it if not
            if not os.path.isfile(json_file_path):
                with open(json_file_path, 'w', encoding='utf-8') as file:
                    json.dump({'trips': []}, file)

            # Write trip data to the file
            with open(json_file_path, 'r+', encoding='utf-8') as file:
                data = json.load(file)
                data['trips'].append(new_trip)
                file.seek(0)
                json.dump(data, file, indent=4)

            return {'message': 'Trip suggested successfully'}
        else:
            return {'error': 'Unable to fetch weather information'}

    except FileNotFoundError as e:
        return {'error': str(e)}
    except PermissionError as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}



    
def geocode_location(location):
    try:
        # Replace 'YOUR_API_KEY' with your actual Google Maps API key
        api_key = 'AIzaSyBPELEebdsZFbEQGkbHMKVvVSxu5PJ9jec'

        # Format the location string for the API request
        formatted_location = location.replace(' ', '+')

        # Make the API call to geocode the location
        api_endpoint = f'https://maps.googleapis.com/maps/api/geocode/json?address={formatted_location}&key={api_key}'
        response = requests.get(api_endpoint)

        if response.status_code == 200:
            geocode_data = response.json()
            if geocode_data['status'] == 'OK' and len(geocode_data['results']) > 0:
                # Extract the latitude and longitude from the API response
                latitude = geocode_data['results'][0]['geometry']['location']['lat']
                longitude = geocode_data['results'][0]['geometry']['location']['lng']
                return (latitude, longitude)  # Return coordinates as a tuple
            else:
                return None  # Unable to geocode the location
        else:
            return None  # Unable to fetch geocoding data

    except Exception as e:
        return None  # An error occurred during geocoding

def update_user_interests(user_id, trip_id):
    json_file_path = os.path.join(os.getcwd(), 'user_interest.json')
    try:
        # Read existing interests
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                interests = data.get("userInterests", {})
        else:
            interests = {}

        # Update interests
        user_key = f"user_{user_id}"
        if user_key in interests:
            if trip_id not in interests[user_key]["interestedTripIds"]:
                interests[user_key]["interestedTripIds"].append(trip_id)
            else:
                # User has already expressed interest in this trip
                return {'error': 'Interest already expressed in this trip'}
        else:
            interests[user_key] = {"interestedTripIds": [trip_id]}

        # Write back to file
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump({"userInterests": interests}, file, indent=4)

    except Exception as e:
        raise Exception(f"Error updating user interests: {e}")

    return {'message': 'Interest recorded successfully'}

    
def check_interests(user_id):
    json_file_path = os.path.join(os.getcwd(), 'suggest_trip.json')
    user_interest_path = os.path.join(os.getcwd(), 'user_interest.json')
    interest_data = []

    try:
        # Load proposed trips
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                proposed_trips = json.load(file).get('trips', [])
            print("Loaded proposed trips:", proposed_trips)  # Debugging line
        else:
            print("No proposed trips found.")  # Debugging line

        # Load user interests
        if os.path.exists(user_interest_path):
            with open(user_interest_path, 'r', encoding='utf-8') as file:
                user_interests = json.load(file).get('userInterests', {})
            print("Loaded user interests:", user_interests)  # Debugging line
        else:
            print("No user interests found.")  # Debugging line

        # Check for interests in the user's proposed trips
        for trip in proposed_trips:
            if trip['user_id'] == user_id:
                for interested_user_id, trips in user_interests.items():
                    if trip['trip_id'] in trips.get('interestedTripIds', []):
                        # Remove 'user_' prefix from interested_user_id
                        formatted_user_id = interested_user_id.replace('user_', '')
                        interested_user_email = get_user_email(formatted_user_id)
                        if interested_user_email:
                            # Include trip details in the interest data
                            interest_data.append({
                                'interested_user_email': interested_user_email,
                                'trip_id': trip['trip_id'],
                                'trip_details': trip  # Include the entire trip object
                            })
    except Exception as e:
        print(f"Error checking interests: {e}")
        raise

    print("Final interest data:", interest_data)  # Debugging line
    return interest_data

def orchestrate_registration(user_data):
    file_path = 'user_data.json'

    try:
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        else:
            data = {'users': []}

        # Check if the email already exists
        for existing_user in data['users']:
            if existing_user['email'] == user_data['email']:
                return {"message": "Email already exists. Please use a different email."}

        hashed_password = generate_password_hash(user_data['password'])

        # Generate a random 'userID' using the external service
        user_id = generate_user_id()

        new_user = {
            'userID': user_id if user_id else '',  # Store the generated ID
            'email': user_data['email'],
            'password': hashed_password
        }

        data['users'].append(new_user)


        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

        return {"message": "User registered successfully"}
    
    except Exception as e:
        return {"error": str(e)}

def orchestrate_login(login_credentials):
    with open('user_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    print("Login Credentials:", login_credentials)  # Print login credentials

    if 'email' not in login_credentials:
        return {"message": "Email not provided"}  # Return an error message if 'email' is missing

    for user in data['users']:
        print("User:", user['email'], user['password'])  # Print each user's email and password
        if user['email'] == login_credentials['email']:
            if check_password_hash(user['password'], login_credentials['password']):
                # Include the user ID in the response
                return {"message": "Login successful", "user_id": user['userID']}
            else:
                return {"message": "Invalid password"}
    
    return {"message": "Invalid email or password"}


def get_user_email(user_id):
    json_file_path = os.path.join(os.getcwd(), 'user_data.json')
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for user in data.get('users', []):
                if user.get('userID') == user_id:
                    return user.get('email')
            return None
    except FileNotFoundError:
        raise FileNotFoundError('User data file not found.')
    except json.JSONDecodeError:
        raise Exception('Error decoding JSON from user data file.')