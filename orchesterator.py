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


# MongoDB connection details
mongo_uri = "mongodb+srv://doadmin:ro243kLaD0GN5796@db-mongodb-nyc3-59765-a337414d.mongo.ondigitalocean.com/admin?tls=true&authSource=admin&replicaSet=db-mongodb-nyc3-59765"


client = MongoClient(mongo_uri)
db = client.get_database()
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
    matching_trips = []

    try:
        # Query MongoDB for all trips matching the search location and excluding the current user's trips
        all_trips = db.proposed_trips.find({
            "location": {"$regex": f"^{search_location}$", "$options": "i"},
            "user_id": {"$ne": user_id}
        })

        matching_trips = list(all_trips)
        print(f"Total matching trips found: {len(matching_trips)}")  # Print the total number of matching trips

    except Exception as e:
        print(f"Error querying matching trips: {e}")  # Print any errors encountered
        raise

    return matching_trips

def query_new_trips(search_location, exclude_user_id):
    try:
        # Query MongoDB for trips matching the location and excluding the current user
        matching_trips = db.proposed_trips.find({
            "location": {"$regex": f"^{search_location}$", "$options": "i"},
            "user_id": {"$ne": exclude_user_id}
        })

        return list(matching_trips)

    except Exception as e:
        raise Exception(f"Error querying new trips: {e}")




def propose_new_trip(location, datetime_str, user_id):
    try:
        # Retrieve user's email from MongoDB
        user = db.users.find_one({"userID": user_id})
        if not user:
            return {'error': 'User not found'}
        user_email = user['email']

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

            # Insert trip data into the MongoDB 'proposed_trips' collection
            db.proposed_trips.insert_one(new_trip)

            return {'message': 'Trip suggested successfully',
                    'weather_info': weather_response}
        else:
            return {'error': 'Unable to fetch weather information'}

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
    try:
        # Check if the user has already expressed interest in this trip
        existing_interest = db.user_interests.find_one(
            {"_id": f"user_{user_id}", f"user_{user_id}": trip_id}
        )

        if existing_interest:
            return {'error': 'Interest already expressed in this trip'}

        # Update user interests in MongoDB
        db.user_interests.update_one(
            {"_id": f"user_{user_id}"},
            {"$addToSet": {f"user_{user_id}": trip_id}},
            upsert=True
        )

        return {'message': 'Interest recorded successfully'}

    except Exception as e:
        raise Exception(f"Error updating user interests: {e}")

    
def check_interests(user_id):
    try:
        # Query MongoDB for proposed trips related to the user
        proposed_trips = db.proposed_trips.find({"user_id": user_id})

        interest_data = []
        for trip in proposed_trips:
            trip_id = trip['trip_id']

            # Query MongoDB for users interested in the trip
            interested_users = db.user_interests.find({
                f"user_{user_id}": {"$in": [trip_id]}
            })

            for interested_user in interested_users:
                # Remove 'user_' prefix from interested user ID
                formatted_user_id = interested_user['_id'].replace('user_', '')

                # Query MongoDB for the interested user's email
                interested_user_email = db.users.find_one(
                    {"userID": formatted_user_id},
                    {"_id": 0, "email": 1}
                )

                if interested_user_email:
                    # Include trip details in the interest data
                    interest_data.append({
                        'interested_user_email': interested_user_email['email'],
                        'trip_id': trip_id,
                        'trip_details': trip  # Include the entire trip object
                    })

        return interest_data

    except Exception as e:
        print(f"Error checking interests: {e}")
        raise

def orchestrate_registration(user_data):
    try:
        # Check if the email already exists in the database
        existing_user = db.users.find_one({"email": user_data['email']})
        if existing_user:
            return {"message": "Email already exists. Please use a different email."}

        hashed_password = generate_password_hash(user_data['password'])

        # Generate a random 'userID' using the external service or other method
        user_id = generate_user_id()

        new_user = {
            'userID': user_id if user_id else '',  # Store the generated ID
            'email': user_data['email'],
            'password': hashed_password
        }

        # Insert the new user into the MongoDB 'users' collection
        db.users.insert_one(new_user)

        return {"message": "User registered successfully"}

    except Exception as e:
        return {"error": str(e)}

def orchestrate_login(login_credentials):
    try:
        # Ensure 'email' and 'password' are provided in login_credentials
        if 'email' not in login_credentials or 'password' not in login_credentials:
            return {"message": "Email and password are required"}

        # Query the MongoDB 'users' collection for the user with the provided email
        user = db.users.find_one({"email": login_credentials['email']})

        if user:
            # Check if the provided password matches the stored hashed password
            if check_password_hash(user['password'], login_credentials['password']):
                # Include the user ID in the response
                return {"message": "Login successful", "user_id": user['userID']}
            else:
                return {"message": "Invalid password"}
        else:
            return {"message": "Invalid email or password"}

    except Exception as e:
        return {"error": str(e)}


def get_user_email(user_id):
    try:
        # Query the MongoDB 'users' collection for the user with the provided user_id
        user = db.users.find_one({"userID": user_id})

        if user:
            return user.get('email')
        else:
            return None

    except Exception as e:
        raise e
