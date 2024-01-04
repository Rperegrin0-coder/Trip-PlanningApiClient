"""This module contains utilities for handling trip proposals in the Travel Buddy Finder app."""
from flask import Flask, jsonify,session,request,render_template, redirect, url_for
from orchesterator import update_user_interests,generate_user_id, query_new_trips, propose_new_trip, check_interests, orchestrate_registration, orchestrate_login,get_matching_trips

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/Travelbuddyhome', methods =['POST','GET'])
def travel_buddy_home():
    # Logic for Travelbuddyhome.html page
    return render_template('Travelbuddyhome.html')


@app.route('/register-page', methods=['POST', 'GET'])
def register_page():
    if request.method == 'POST':
        user_data = request.json
        # Generate userID within the backend
        user_data['userID'] = generate_user_id()  # Function to generate userID
        response = orchestrate_registration(user_data)
        if 'message' in response and response['message'] == 'User registered successfully':
            return redirect(url_for('login_page'))  # Redirect to the login page
        return jsonify(response), 200
    
    return render_template('register.html')



@app.route('/login-page', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        login_credentials = request.json
        response = orchestrate_login(login_credentials)
        
        if response.get('message') == 'Login successful':
            session['user_id'] = response.get('user_id')  # Storing the user ID in session
            return jsonify(response), 200
        else:
            return jsonify(response), 401
    
    return render_template('login.html')




@app.route('/generate-user-id', methods=['GET'])
def generate_user_id_route():
    generated_id = generate_user_id()
    return jsonify({"user_id": generated_id}), 200



    
@app.route('/query-new-trips', methods=['GET'])
def query_new_trips_route():
    search_location = request.args.get('location')

    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    current_user_id = session['user_id']

    if search_location:
        try:
            # Call the orchestrator function to get matching trips
            matching_trips = get_matching_trips(search_location, current_user_id)
            return jsonify(matching_trips)
        except FileNotFoundError as e:
            return jsonify({'error': str(e)}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return render_template('query_trips.html')

    
@app.route('/suggest_trip', methods=['GET', 'POST'])
def suggest_trip():
    if request.method == 'POST':
        user_id = session.get('user_id')  # Retrieve user ID from session
        print("User ID from session:", user_id)
        if user_id:
            trip_data = request.json
            location = trip_data.get('location')
            datetime = trip_data.get('datetime')

            # Call propose_new_trip function to suggest the trip
            response = propose_new_trip(location, datetime, user_id)
            return jsonify(response)
        else:
            return jsonify({'error': 'User not authenticated'}), 401
    else:
        return render_template('suggest_trips.html')


   
@app.route('/express-interest', methods=['POST'])
def express_interest():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user_id = session['user_id']
    data = request.json
    trip_id = data.get('tripId')

    if not trip_id:
        return jsonify({'error': 'Missing trip ID'}), 400

    try:
        update_user_interests(user_id, trip_id)
        return jsonify({'message': 'Interest recorded successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check-interests', methods=['GET'])
def check_interests_route():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    user_id = session['user_id']
    interest_data = check_interests(user_id)

    print("Interest data:", interest_data)  # Debugging line

    return render_template('check_interest.html', interests=interest_data)

if __name__ == '__main__':
    app.secret_key = '3Equantum'
    app.run(debug=True)
    
