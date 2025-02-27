from supabase import create_client, Client
from flask import Flask, request, jsonify, session
from supabase import create_client, Client
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import os
from datetime import timedelta
from flask import Blueprint, request, jsonify
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY
import requests
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

bp = Blueprint('connection', __name__)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_supabase_token(token):
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_KEY
    }
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

# Utility function to interact with Supabase
def execute_query(sql):
    return supabase.rpc("execute_sql", {"sql": sql})

@bp.route('/create_patient', methods=['POST'])
def create_patient():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    
    # Extract patient data from request, default to None if not provided
    name = data.get('name')
    aadhar_number = data.get('aadhar_number')
    email = data.get('email')
    phone = data.get('phone')
    address = data.get('address')
    emergency_contact = data.get('emergency_contact')
    medical_history = data.get('medical_history')
    insurance_number = data.get('insurance_number')
    dob = data.get('dob')
    gender = data.get('gender')
    occupation = data.get('occupation')
    marital_status = data.get('marital_status')
    blood_group = data.get('blood_group')
    allergies = data.get('allergies')
    family_medical_history = data.get('family_medical_history')

    # Check if required fields are provided
    if not all([name, aadhar_number, email, phone]):
        return jsonify({"message": "Missing required fields"}), 400
    
    try:
        # Insert the patient into the database
        supabase.table('patients').insert({
            'name': name,
            'aadhar_number': aadhar_number,
            'email': email,
            'phone': phone,
            'address': address,
            'emergency_contact': emergency_contact,
            'medical_history': medical_history,
            'insurance_number': insurance_number,
            'dob': dob,
            'gender': gender,
            'occupation': occupation,
            'marital_status': marital_status,
            'blood_group': blood_group,
            'allergies': allergies,
            'family_medical_history': family_medical_history
        }).execute()

        return jsonify({"message": "Patient created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@bp.route('/get_patient_by_id', methods=['POST'])
def get_patient_by_id():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400
    
    try:
        # Query the patients table using the provided patient_id
        result = supabase.table('patients').select('*').eq('patient_id', patient_id).execute()
        patient = result if isinstance(result, list) else result.data  # Adjust based on response type
        
        if not patient:
            return jsonify({"message": "No patient found with the provided ID"}), 404

        return jsonify(patient), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/update_patient_verified', methods=['POST'])
def update_patient_verified():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]  # Extract token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    try:
        # Check if the patient exists
        result = supabase.table('patients').select('*').eq('patient_id', patient_id).execute()
        patient = result.data  # Extract patient data
        
        if not patient:
            return jsonify({"message": "No patient found with the provided ID"}), 404

        # Update the 'verified' field
        update_result = supabase.table('patients').update({"verified": True}).eq('patient_id', patient_id).execute()

        if update_result.data:  # Check if the update was successful
            return jsonify({"message": "Patient verified successfully"}), 200
        else:
            return jsonify({"error": "Failed to update patient verification status"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/update_patient', methods=['PUT'])
def update_patient():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    
    # Extract patient data from request, default to None if not provided
    patient_id = data.get('patient_id')
    if not patient_id:
        return jsonify({"error": "Missing required field: patient_id"}), 400

    # Check for optional fields to update
    updates = {key: value for key, value in data.items() if key != 'patient_id' and value is not None}

    try:
        # Update the patient in the database
        response = supabase.table('patients').update(updates).eq('patient_id', patient_id).execute()

        # Check if the update was successful by checking response.data
        if response.data:
            return jsonify({"message": "Patient updated successfully"}), 200
        else:
            return jsonify({"error": "Patient not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/profile_pic', methods=['POST', 'GET', 'DELETE'])
def handle_profile_pic():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({"error": "Missing required field: patient_id"}), 400

    # Upload or update profile picture
    if request.method == 'POST':
        # Check if 'file' is in the request files
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        # Ensure a file is selected
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Secure the filename and create the full path for the image in the bucket
        filename = secure_filename(file.filename)
        file_path = f'profile_pics/{filename}'

        try:
            # Upload the file to the bucket (patient/profile_pics folder)
            file_bytes = file.read()  # Read file as bytes
            # Upload to Supabase (Supabase storage expects bytes directly)
            upload_response = supabase.storage.from_('patient').upload(file_path, file_bytes)
            public_url_response = supabase.storage.from_('patient').get_public_url(file_path)
            if public_url_response and public_url_response.endswith('?'):
                public_url_response = public_url_response[:-1] 
            # Update the patient's record with the image URL
            update_response = supabase.table('patients').update({
                'profile_pic_url': public_url_response
            }).eq('patient_id', patient_id).execute()

            if update_response.data:
                return jsonify({"message": "Profile picture uploaded/updated successfully", "url": public_url_response}), 200
            else:
                return jsonify({"error": "Patient not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Fetch profile picture URL
    elif request.method == 'GET':
        try:
            # Fetch the patient record from the database
            response = supabase.table('patients').select('profile_pic_url').eq('patient_id', patient_id).execute()
            
            if response.data:
                profile_pic_url = response.data[0].get('profile_pic_url')
                if profile_pic_url:
                    return jsonify({"profile_pic_url": profile_pic_url}), 200
                else:
                    return jsonify({"message": "No profile picture found"}), 404
            else:
                return jsonify({"error": "Patient not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Delete profile picture
    elif request.method == 'DELETE':
        try:
            # Fetch the patient record to get the existing profile_pic_url
            response = supabase.table('patients').select('profile_pic_url').eq('patient_id', patient_id).execute()
            
            if response.data:
                profile_pic_url = response.data[0].get('profile_pic_url')
                if profile_pic_url:
                    # Extract the file path from the public URL (after the domain part)
                    file_path = profile_pic_url.split('/storage/v1/object/public/patient/')[1]
                    
                    # Delete the file from the bucket
                    delete_response = supabase.storage.from_('patient').remove([file_path])
                    
                    if delete_response.get('error'):
                        return jsonify({"error": delete_response['error']['message']}), 500

                    # Remove the image URL from the patient's record
                    supabase.table('patients').update({
                        'profile_pic_url': None
                    }).eq('patient_id', patient_id).execute()

                    return jsonify({"message": "Profile picture deleted successfully"}), 200
                else:
                    return jsonify({"message": "No profile picture found to delete"}), 404
            else:
                return jsonify({"error": "Patient not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Route for handling all hospital operations
@bp.route('/hospitals', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_hospitals():
    token = request.headers.get("Authorization")
    
    # Authorization check
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401
    
    # Extract the token from the "Bearer <token>"
    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    # Handle GET request - Retrieve entire hospital list
    if request.method == 'GET':
        try:
            response = supabase.table('hospitals').select('*').execute()
            
            if response.data:  # Check if data exists
                hospitals = response.data
                return jsonify(hospitals), 200
            else:
                return jsonify({"error": response.error}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Handle POST request - Add a new hospital
    elif request.method == 'POST':
        data = request.json
        name = data.get('name')
        location = data.get('location')
        contact = data.get('contact')
        
        # Check if required fields are provided
        if not name:
            return jsonify({"message": "Hospital name is required"}), 400
        
        try:
            # Insert the new hospital into the database
            response = supabase.table('hospitals').insert({
                'name': name,
                'location': location,
                'contact': contact
            }).execute()

            if response.data:  # Check if the insert was successful
                return jsonify({"message": "Hospital added successfully"}), 201
            else:
                return jsonify({"error": response.error}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Handle PUT request - Update an existing hospital
    elif request.method == 'PUT':
        data = request.json
        hospital_id = data.get('id')
        name = data.get('name')
        location = data.get('location')
        contact = data.get('contact')

        if not hospital_id:
            return jsonify({"message": "Hospital ID is required"}), 400
        
        try:
            # Update the hospital record
            response = supabase.table('hospitals').update({
                'name': name,
                'location': location,
                'contact': contact
            }).eq('id', hospital_id).execute()

            if response.data:  # Check if the update was successful
                return jsonify({"message": "Hospital updated successfully"}), 200
            else:
                return jsonify({"error": response.error}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Handle DELETE request - Delete a hospital
    elif request.method == 'DELETE':
        hospital_id = request.args.get('id')

        if not hospital_id:
            return jsonify({"message": "Hospital ID is required"}), 400
        
        try:
            # Delete the hospital record
            response = supabase.table('hospitals').delete().eq('id', hospital_id).execute()

            if response.data:  # Check if the delete was successful
                return jsonify({"message": "Hospital deleted successfully"}), 200
            else:
                return jsonify({"error": response.error}), 500

        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
@bp.route('/get_appointments', methods=['GET'])
def get_appointments_by_patient():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    
    # Get patient_id from qery parameters
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    try:
        # Fetch appointments for the given patient_id
        response = supabase.table('appointments').select('*').eq('patient_id', patient_id).execute()
        
        # Check if the response contains data
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"message": "No appointments found for this patient."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bp.route('/get_patient', methods=['POST'])
def get_session():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    try:
        # Query the patients table using the provided email
        patient = supabase.table('patients').select('*').eq('email', email).execute().data
        
        if not patient:
            return jsonify({"message": "No patient found with the provided email"}), 404

        return jsonify(patient), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
@bp.route('/create_appointment', methods=['POST'])
def create_appointment(appointment=None):
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    if not appointment:
        data = request.json
    else:
        data = appointment  # Use appointment from scheduler if available

    # Extract appointment data
    patient_id = data.get('patient_id')
    hospital_id = data.get('hospital_id')
    department_id = data.get('department_id')
    doctor_id = data.get('doctor_id')
    date_time = data.get('date_time')  # Expected in ISO8601 format
    status = data.get('status', 'scheduled')  # Default to 'scheduled'
    priority_level = data.get('priority_level', 'normal')  # Default to 'normal'
    service_type = data.get('department_name')
    slot_id = data.get('slot_id')

    # Validate priority level and status values against allowed constraints
    allowed_priority_levels = ['low', 'normal', 'high']
    allowed_status = ['scheduled', 'completed', 'canceled']

    if priority_level not in allowed_priority_levels:
        return jsonify({"error": f"Invalid priority_level. Allowed values are: {allowed_priority_levels}"}), 400
    if status not in allowed_status:
        return jsonify({"error": f"Invalid status. Allowed values are: {allowed_status}"}), 400

    # Check for available counters for the service type
    eligible_counters = supabase.table('counters').select('*').eq('service_type', service_type).eq('enabled', True).execute().data
    if not eligible_counters:
        return jsonify({"message": "No available counters for the service type"}), 400

    # Find the counter with the least number of tokens
    selected_counter = min(eligible_counters, key=lambda x: len(x['allocated_tokens']))

    # Generate a new token number
    token_number = len(selected_counter['allocated_tokens']) + 1
    token_id = f"{selected_counter['counter_id']}-{token_number}"

    try:
        # Insert into appointments table
        appointment_result = supabase.table('appointments').insert({
            'patient_id': patient_id,
            'hospital_id': hospital_id,
            'department_id' : department_id,
            'doctor_id': doctor_id,
            'date_time': date_time,
            'status': status,
            'priority_level': priority_level,
            'service_type': service_type,
            'slot_id': slot_id,
            'token_id' : token_id
        }).execute()

        # Insert token into tokens table
        supabase.table('tokens').insert({
            'token_id': token_id,
            'patient_id': patient_id,
            'counter_id': selected_counter['counter_id'],
            'service_type': service_type,
            'status': 'waiting'
        }).execute()

        # Update the selected counter's token list
        selected_counter['allocated_tokens'].append(token_id)
        supabase.table('counters').update({'allocated_tokens': selected_counter['allocated_tokens']}).eq('counter_id', selected_counter['counter_id']).execute()

        return jsonify({
            "message": "Appointment and token created successfully",
            "appointment_id": appointment_result.data[0]['id'],
            "token_id": token_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/counters_status', methods=['GET'])
def counters_status():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    counters = supabase.table('counters').select('*').execute().data
    
    if not counters:
        return jsonify({"message": "No counters found"}), 404

    result = []

    for counter in counters:
        allocated_tokens = counter.get('allocated_tokens', [])
        if allocated_tokens:
            # The first token in the queue
            first_token_id = allocated_tokens[0]
            token_details = supabase.table('tokens').select('*').eq('token_id', first_token_id).execute().data
            if token_details:
                result.append({
                    'counter_id': counter['counter_id'],
                    'first_token_id': first_token_id,
                    'patient_id': token_details[0]['patient_id'],
                    'service_type': token_details[0]['service_type']
                })
            else:
                result.append({
                    'counter_id': counter['counter_id'],
                    'first_token_id': first_token_id,
                    'patient_id': 'Unknown',
                    'service_type': 'Unknown'
                })
        else:
            result.append({
                'counter_id': counter['counter_id'],
                'first_token_id': 'None',
                'patient_id': 'None',
                'service_type': 'None'
            })
    
    return jsonify(result), 200

@bp.route('/estimate_wait_time/<string:token_id>', methods=['GET'])
def estimate_wait_time(token_id):
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    print(token_id)
    token = supabase.table('tokens').select('*').eq('token_id', token_id).execute().data
    print(token)
    if not token:
        return jsonify({"message": "Token not found"}), 404
    
    # Retrieve the corresponding counter
    counter = supabase.table('counters').select('*').eq('counter_id', token[0]['counter_id']).execute().data
    print(counter)
    # Calculate the position in queue
    position_in_queue = counter[0]['allocated_tokens'].index(token_id) + 1
    estimated_wait_time = position_in_queue * counter[0]['expected_time']
    
    return jsonify({"estimated_wait_time": estimated_wait_time}), 200

@bp.route('/token_skip_recall', methods=['POST'])
def token_skip_recall():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    token_id = data['token_id']
    action = data['action']  # skip or recall

    token = supabase.table('tokens').select('*').eq('token_id', token_id).execute().data

    if not token:
        return jsonify({"message": "Token not found"}), 404
    
    counter = supabase.table('counters').select('*').eq('counter_id', token['counter_id']).execute().data

    if action == "skip":
        supabase.table('tokens').update({'status': 'skipped'}).eq('token_id', token_id).execute()
        counter['allocated_tokens'].remove(token_id)
    elif action == "recall":
        supabase.table('tokens').update({'status': 'recalled'}).eq('token_id', token_id).execute()
        counter['allocated_tokens'].append(token_id)

    # Update the counter's allocated tokens
    supabase.table('counters').update({'allocated_tokens': counter['allocated_tokens']}).eq('counter_id', counter['counter_id']).execute()

    return jsonify({"message": f"Token {action} successful for {token_id}"}), 200

@bp.route('/destroy_token/<token_id>', methods=['DELETE'])
def destroy_token(token_id):
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    # Remove token from tokens and counters collection
    token = supabase.table('tokens').select('*').eq('token_id', token_id).execute().data
    
    if not token:
        return jsonify({"message": "Token not found"}), 404
    
    # Fetch the associated counter
    counter = supabase.table('counters').select('*').eq('counter_id', token[0]['counter_id']).execute().data
    
    # Fetch the associated appointment using both patient_id and token_id
    patient_id = token[0]['patient_id']
    appointment = supabase.table('appointments').select('*').eq('patient_id', patient_id).eq('token_id', token[0]['token_id']).execute().data
    
    # Remove the token from the allocated_tokens array of the counter
    counter[0]['allocated_tokens'].remove(token_id)

    # Update the counter with the modified allocated_tokens
    supabase.table('counters').update({'allocated_tokens': counter[0]['allocated_tokens']}).eq('counter_id', counter[0]['counter_id']).execute()
    
    # Change the status of the appointment from 'scheduled' to 'completed'
    if appointment:
        supabase.table('appointments').update({'status': 'completed'}).eq('id', appointment[0]['id']).execute()
    
    # Delete the token from the tokens table
    supabase.table('tokens').delete().eq('token_id', token_id).execute()

    return jsonify({"message": f"Token {token_id} destroyed and appointment status updated"}), 200



# def check_and_process_appointments():
#     # Get current time (timezone-naive)
#     now = datetime.now().replace(tzinfo=None)

#     # Fetch scheduled appointments
#     appointments = supabase.table('appointments').select('*').eq('status', 'scheduled').execute().data

#     for appointment in appointments:
#         appointment_time_str = appointment['date_time']

#         # Convert the appointment_time string to a datetime object (ISO 8601 format)
#         appointment_time = datetime.strptime(appointment_time_str, '%Y-%m-%dT%H:%M:%S')

#         # Compare datetime objects
#         if appointment_time <= now:
#             # Change status to expired if time has passed
#             supabase.table('appointments').update({'status': 'completed'}).eq('id', appointment['id']).execute()

#             # Call the function to handle expired appointments
#             create_appointment(appointment)
                             
# Configurations

@bp.route('/refresh_session', methods=[''])
def refresh_session():
    try:
        response = supabase.auth.refresh_session()
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.route('/protected', methods=['GET'])
def protected():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401
    user = session.get('user')
    if not user:
        return jsonify({"message": "Unauthorized"}), 401
    return jsonify({"message": f"Welcome, {user['email']}!"}), 200

@bp.route('/', methods=['GET'])
def Welcome():
    return jsonify({"message": "You have successfully connected"}), 200







#other routes
@bp.route('/get_departments', methods=['POST'])
def get_departments_by_hospital():
    token = request.headers.get("Authorization")
    
    # Authorization check
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the "Bearer <token>"
    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json  # Get the JSON body from the request
    hospital_id = data.get('hospital_id')  # Extract hospital_id from the body
    
    try:
        if hospital_id:
            # Fetch departments where hospital_id matches
            response = supabase.table('departments').select('id, hospital_id, name, description').eq('hospital_id', hospital_id).execute()
        else:
            # Fetch all departments if no hospital_id is provided
            response = supabase.table('departments').select('id, hospital_id, name, description').execute()

        if response.data:  # If departments are found
            departments = response.data
            return jsonify(departments), 200
        else:
            return jsonify({"message": "No departments found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



#route to get doctor list based on first hospital id then department id
@bp.route('/get_doctors', methods=['POST'])
def get_doctors_by_department_and_hospital():
    token = request.headers.get("Authorization")

    # Authorization check
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from "Bearer <token>"
    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json  # Get the JSON body from the request
    department_id = data.get('department_id')
    hospital_id = data.get('hospital_id')

    if not department_id or not hospital_id:
        return jsonify({"error": "Both department_id and hospital_id are required"}), 400

    try:
        # Fetch doctors where department_id and hospital_id match
        response = supabase.table('doctors').select('id, department_id, hospital_id, name, specialization, contact') \
            .eq('department_id', department_id).eq('hospital_id', hospital_id).execute()

        if response.data:  # If doctors are found
            doctors = response.data
            return jsonify(doctors), 200
        else:
            return jsonify({"message": "No doctors found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/get_appointments_bypatientid', methods=['POST'])
def get_appointments_by_patient_id():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    
    # Get patient_id from the JSON body
    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    try:
        # Fetch appointments for the given patient_id
        response = supabase.table('appointments').select('*').eq('patient_id', patient_id).execute()
        
        # Check if the response contains data
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"message": "No appointments found for this patient."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get_doctor_by_id', methods=['POST'])
def get_doctor_by_id():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    doctor_id = data.get('doctor_id')

    if not doctor_id:
        return jsonify({"error": "Doctor ID is required"}), 400

    try:
        result = supabase.table('doctors').select('*').eq('id', doctor_id).execute()
        doctor = result if isinstance(result, list) else result.data
        
        if not doctor:
            return jsonify({"message": "No doctor found with the provided ID"}), 404

        return jsonify(doctor), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get_hospital_by_id', methods=['POST'])
def get_hospital_by_id():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    hospital_id = data.get('hospital_id')

    if not hospital_id:
        return jsonify({"error": "Hospital ID is required"}), 400

    try:
        result = supabase.table('hospitals').select('*').eq('id', hospital_id).execute()
        hospital = result if isinstance(result, list) else result.data
        
        if not hospital:
            return jsonify({"message": "No hospital found with the provided ID"}), 404

        return jsonify(hospital), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get_department_by_id', methods=['POST'])
def get_department_by_id():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    department_id = data.get('department_id')

    if not department_id:
        return jsonify({"error": "Department ID is required"}), 400

    try:
        result = supabase.table('departments').select('*').eq('id', department_id).execute()
        department = result if isinstance(result, list) else result.data
        
        if not department:
            return jsonify({"message": "No department found with the provided ID"}), 404

        return jsonify(department), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Route for handling all counter operations
@bp.route('/counters', methods=['GET'])
def get_counters_with_tokens():
    token = request.headers.get("Authorization")
    
    # Authorization check
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401
    
    # Extract the token from the "Bearer <token>"
    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    # Handle GET request - Retrieve all counters with their tokens
    if request.method == 'GET':
        try:
            # Fetch all counters from the database
            response = supabase.table('counters').select('*').execute()
            
            if response.data:  # Check if data exists
                counters = response.data
                
                # Structure the response to include service_type and allocated_tokens
                result = []
                for counter in counters:
                    result.append({
                        "counter_id": counter['counter_id'],
                        "service_type": counter['service_type'],
                        "enabled": counter['enabled'],
                        "allocated_tokens": counter['allocated_tokens'],
                        "expected_time": counter['expected_time'],
                        "token_start_time": counter['token_start_time'],
                    })
                
                return jsonify(result), 200
            else:
                return jsonify({"message": "No counters found."}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500



@bp.route('/get_all_updates', methods=['GET'])
def get_all_updates():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Fetch all updates from the updates table
        response = supabase.table('updates').select('*').execute()

        # Check if there are no updates
        if not response.data:
            return jsonify({"message": "No updates found"}), 404

        updates = response.data  # Get the data from the response
        print(updates)

        # Fetch hospital data for each update and bind it
        for update in updates:
            hospital_id = update.get('hospital_id')  # Get hospital_id from each update

            # Fetch the hospital data using the hospital_id
            hospital_result = supabase.table('hospitals').select('name').eq('id', hospital_id).execute()

            if hospital_result.data:
                hospital = hospital_result.data
                # Bind hospital name to the update
                update['name'] = hospital[0]['name'] if hospital else 'Unknown Hospital'
            else:
                update['name'] = 'Unknown Hospital'

        return jsonify(updates), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get_all_maps', methods=['GET'])
def get_all_maps():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Fetch all maps from the maps table
        response = supabase.table('maps').select('*').execute()

        # Check if there are no maps
        if not response.data:
            return jsonify({"message": "No maps found"}), 404

        maps = response.data  # Get the data from the response
        print(maps)

        # Fetch hospital data for each map and bind it (hospital name and location)
        for map_entry in maps:
            hospital_id = map_entry.get('hospital_id')  # Get hospital_id from each map

            # Fetch the hospital data using the hospital_id
            hospital_result = supabase.table('hospitals').select('name', 'location').eq('id', hospital_id).execute()

            if hospital_result.data:
                hospital = hospital_result.data
                # Bind hospital name and location to the map entry
                map_entry['hospital_name'] = hospital[0]['name'] if hospital else 'Unknown Hospital'
                map_entry['hospital_location'] = hospital[0]['location'] if hospital else 'Unknown Location'
            else:
                map_entry['hospital_name'] = 'Unknown Hospital'
                map_entry['hospital_location'] = 'Unknown Location'

        return jsonify(maps), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get_health_guide', methods=['GET'])
def get_health_guide():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    token = token.split(" ")[1]
    user_info = verify_supabase_token(token)

    if not user_info:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Fetch all entries from the healthGuide table
        response = supabase.table('healthGuide').select('*').execute()

        # Check if there are no entries
        if not response.data:
            return jsonify({"message": "No health guide entries found"}), 404

        health_guide_entries = response.data

        return jsonify(health_guide_entries), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



#donors endpoints
@bp.route('/checkIfDonor', methods=['POST'])
def check_if_donor():
    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    response = supabase.table('donors').select('*').eq('patient_id', patient_id).execute()
    
    return jsonify({"is_donor": bool(response.data)}), 200

@bp.route('/registerDonor', methods=['POST'])
def register_donor():
    data = request.json
    
    required_fields = ['patient_id', 'weight', 'age']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    donor_data = {
        "patient_id": data["patient_id"],
        "weight": data["weight"],
        "age": data["age"],
        "last_donation_date": data.get("last_donation_date"),
        "current_medications": data.get("current_medication"),
        "recent_vaccinations": data.get("recent_vaccinations"),
        "recent_travel_risk_area": data.get("recent_travel_risk_area"),
        "status": "pending",
        "can_donate": False
    }
    
    response = supabase.table('donors').insert(donor_data).execute()
    
    return jsonify(response.data), 201


@bp.route('/fetchDonor', methods=['POST'])
def fetch_donor():
    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    response = supabase.table('donors').select('*').eq('patient_id', patient_id).execute()
    
    if not response.data:
        return jsonify({"message": "No donor found."}), 404
    
    return jsonify(response.data), 200

@bp.route('/updateDonor', methods=['POST'])
def update_donor():
    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    donor_data = {k: v for k, v in data.items() if k != 'patient_id'}
    response = supabase.table('donors').update(donor_data).eq('patient_id', patient_id).execute()
    
    return jsonify(response.data), 200

@bp.route('/removeDonor', methods=['POST'])
def remove_donor():
    data = request.json
    patient_id = data.get('patient_id')
    
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    
    response = supabase.table('donors').delete().eq('patient_id', patient_id).execute()
    
    return jsonify({"message": "Donor removed successfully."}), 200


@bp.route('/fetchAllDonors', methods=['GET'])
def fetch_all_donors():
    # Fetch all approved donors from donors table
    donors_response = supabase.table('donors').select('*').eq('status', 'approved').execute()
    donors_data = donors_response.data
    
    if not donors_data:
        return jsonify({"message": "No donors found."}), 404
    
    patient_ids = [donor['patient_id'] for donor in donors_data]
    
    # Fetch patient details for the donor patient_ids
    patients_response = supabase.table('patients').select('patient_id, name, email, phone, address, medical_history, gender, blood_group, allergies, family_medical_history').in_('patient_id', patient_ids).execute()
    patients_data = {patient['patient_id']: patient for patient in patients_response.data}
    
    # Merge donor data with patient details
    merged_data = []
    for donor in donors_data:
        patient_info = patients_data.get(donor['patient_id'], {})
        merged_data.append({**donor, **patient_info})
    
    return jsonify(merged_data), 200


#sending requests to donors
@bp.route('/send_donor_request', methods=['POST'])
def send_request():
    data = request.json
    
    required_fields = ['donor_id', 'receiver_id', 'message']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check if a request already exists
    existing_request = (
        supabase.table('donor_requests')
        .select("status")
        .eq("donor_id", data["donor_id"])
        .eq("receiver_id", data["receiver_id"])
        .execute()
    )
    
    if existing_request.data:
        return jsonify({
            "message": "Request already made",
            "status": existing_request.data[0]["status"]
        }), 409
    
    request_data = {
        "donor_id": data["donor_id"],
        "receiver_id": data["receiver_id"],
        "message": data["message"],
        "request_date": datetime.utcnow().isoformat(),  # Get current UTC time
        "status": "pending",  # Default status
        "can_call": False  # Default value
    }
    
    response = supabase.table('donor_requests').insert(request_data).execute()
    
    return jsonify({
        "message": "Request sent successfully",
        "data": response.data
    }), 201


#requests as receiver
@bp.route('/fetch_my_requests', methods=['POST'])
def fetch_my_requests():
    # Get receiver_id from request body
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    
    if not receiver_id:
        return jsonify({"message": "Receiver ID is required"}), 400
    
    # Fetch all requests for the given receiver_id from donor_requests table
    requests_response = supabase.table('donor_requests').select('*').eq('receiver_id', receiver_id).execute()
    requests_data = requests_response.data
    
    if not requests_data:
        return jsonify({"message": "No requests found for this receiver."}), 404
    
    # Extract donor_ids from the requests
    donor_ids = [request['donor_id'] for request in requests_data]
    
    # Fetch patient details for the donor_ids from patients table
    patients_response = supabase.table('patients').select('patient_id, name, dob, gender, email, phone, address').in_('patient_id', donor_ids).execute()
    patients_data = {patient['patient_id']: patient for patient in patients_response.data}
    
    # Merge request data with patient details
    merged_data = []
    for request_item in requests_data:
        donor_id = request_item['donor_id']
        patient_info = patients_data.get(donor_id, {})
        merged_data.append({**request_item, **patient_info})
    
    return jsonify(merged_data), 200

#requests as donor
@bp.route('/fetch_requests_to_me', methods=['POST'])
def fetch_requests_to_me():
    # Get donor_id from request body
    data = request.get_json()
    donor_id = data.get('donor_id')  # Corrected variable name
    
    if not donor_id:
        return jsonify({"message": "Donor ID is required"}), 400
    
    # Fetch all requests for the given donor_id
    requests_response = supabase.table('donor_requests').select('*').eq('donor_id', donor_id).execute()
    requests_data = requests_response.data
    
    if not requests_data:
        return jsonify({"message": "No requests found for this donor."}), 404
    
    # Extract receiver_ids from the requests
    receiver_ids = [request['receiver_id'] for request in requests_data]
    
    # Fetch patient details for the receiver_ids
    patients_response = supabase.table('patients').select('patient_id, name, dob, gender, email, phone, address').in_('patient_id', receiver_ids).execute()
    patients_data = {patient['patient_id']: patient for patient in patients_response.data}
    
    # Merge request data with patient details
    merged_data = []
    for request_item in requests_data:
        receiver_id = request_item['receiver_id']
        patient_info = patients_data.get(receiver_id, {})
        merged_data.append({**request_item, **patient_info})
    
    return jsonify(merged_data), 200




@bp.route('/delete_request', methods=['DELETE'])
def delete_request():
    data = request.json

    required_fields = ['donor_id', 'receiver_id']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Delete the request from the table
    response = (
        supabase.table('donor_requests')
        .delete()
        .eq("donor_id", data["donor_id"])
        .eq("receiver_id", data["receiver_id"])
        .execute()
    )

    if response.data:
        return jsonify({"message": "Request deleted successfully"}), 200
    else:
        return jsonify({"error": "Request not found"}), 404



#approve and reject request

@bp.route('/approve_request', methods=['POST'])
def approve_request():
    data = request.json
    request_id = data.get("request_id")
    
    if not request_id:
        return jsonify({"error": "Missing request ID"}), 400
    
    # Update request status to 'approved' and set can_call to True
    response = (
        supabase.table('donor_requests')
        .update({"status": "approved", "can_call": True})
        .eq("id", request_id)
        .execute()
    )
    
    if response.data:
        return jsonify({"message": "Request approved successfully"}), 200
    else:
        return jsonify({"error": "Request not found or update failed"}), 404

@bp.route('/reject_request', methods=['POST'])
def reject_request():
    data = request.json
    request_id = data.get("request_id")
    
    if not request_id:
        return jsonify({"error": "Missing request ID"}), 400
    
    # Update request status to 'rejected' and set can_call to False
    response = (
        supabase.table('donor_requests')
        .update({"status": "rejected", "can_call": False})
        .eq("id", request_id)
        .execute()
    )
    
    if response.data:
        return jsonify({"message": "Request rejected successfully"}), 200
    else:
        return jsonify({"error": "Request not found or update failed"}), 404


#bed endpoints
# Mapping for categorical values to numeric weights
priority_weights = {'high': 3, 'medium': 2, 'low': 1}
proximity_weights = {'high': 3, 'medium': 2, 'low': 1}

# Function to get the load of a department
def get_department_load(department):
    total_beds = supabase.table('beds').select('bed_id').eq('department', department).execute().data
    occupied_beds = supabase.table('beds').select('bed_id').eq('department', department).eq('available', False).execute().data
    return len(occupied_beds) / len(total_beds) if total_beds else 1

# Function to calculate priority based on severity
def calculate_priority(severity):
    severity = severity.lower()
    if severity == 'high':
        return 3
    elif severity == 'medium':
        return 2
    else:  # Assuming 'low'
        return 1

# Endpoint to allocate a bed based on severity, patient-specific needs, and department load balancing
@bp.route('/allocate_bed', methods=['POST'])
def allocate_bed():
    data = request.json
    patient_id = data.get('patient_id')
    severity = data.get('severity')
    equipment_needed = data.get('equipment', '').split(',')
    room_type_needed = data.get('room_type', 'shared')
    isolation_needed = data.get('isolation', 'False')
    deallocate_date = data.get('deallocate_date')
    current_date = data.get('current_date')  # Use the date from frontend
    
    try:
        deallocate_datetime = datetime.fromisoformat(deallocate_date).date()
        current_date = datetime.fromisoformat(current_date).date()  # Convert to date format
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD format.'}), 400
    
    severity_priority = calculate_priority(severity)
    beds = supabase.table('beds').select('*').eq('available', True).execute().data

    suitable_beds = [
        bed for bed in beds
        if priority_weights.get(bed['priority'], 1) >= severity_priority
        and all(equip in (bed.get('equipment', '') or '').split(',') for equip in equipment_needed if equip)
        and bed['room_type'] == room_type_needed
        and bed['isolation'] == isolation_needed
    ]
    
    if not suitable_beds:
        suitable_beds = sorted(beds, key=lambda x: (
            0 if x['proximity'] == 'high' else 1,  
            x['bed_id']
        ))

    suitable_beds.sort(key=lambda x: (
        priority_weights.get(x['priority'], 1), 
        proximity_weights.get(x['proximity'], 1), 
        get_department_load(x['department'])
    ))

    if suitable_beds:
        allocated_bed = suitable_beds[0]
        supabase.table('beds').update({'available': False}).eq('bed_id', allocated_bed['bed_id']).execute()

        supabase.table('admissions').insert({
            'patient_id': patient_id,
            'bed_id': allocated_bed['bed_id'],
            'admission_date': current_date.isoformat(),  # Use received date
            'deallocate_date': deallocate_datetime.isoformat(),
            'status': 'active'
        }).execute()

        return jsonify({
            'message': f"Bed {allocated_bed['bed_id']} allocated. Deallocates on {deallocate_datetime.isoformat()}."
        })

    return jsonify({'message': "No suitable beds available."}), 404


# Function to deallocate beds after the specified date has passed
def deallocate_beds():
    admissions = supabase.table('admissions').select('*').eq('status', 'active').execute().data
    current_date = datetime.now(UTC).date()  # Get only the current date

    for admission in admissions:
        if 'deallocate_date' in admission:
            deallocate_date = datetime.fromisoformat(admission['deallocate_date']).date()  # Store only the date
            if current_date >= deallocate_date:
                # Deallocate bed
                supabase.table('beds').update({'available': True}).eq('bed_id', admission['bed_id']).execute()

                # Update the admissions table for the bed being deallocated
                supabase.table('admissions').update({
                    'discharge_date': current_date.isoformat(),  # Convert to ISO format
                    'status': 'discharged'  # Update status to 'discharged' once bed is deallocated
                }).eq('bed_id', admission['bed_id']).eq('status', 'active').execute()

                print(f"Bed {admission['bed_id']} has been deallocated and corresponding admission record updated.")

# Function to automatically schedule deallocation to run once a day
def schedule_deallocation():
    scheduler = BackgroundScheduler()
    # Run the deallocation process every day at midnight (UTC)
    scheduler.add_job(deallocate_beds, 'interval', days=1, next_run_time=datetime.now(UTC))
    scheduler.start()

# Endpoint to check the status of a specific bed
@bp.route('/bed_status/<int:bed_id>', methods=['GET'])
def bed_status(bed_id):
    bed = supabase.table('beds').select('*').eq('bed_id', bed_id).execute().data
    if bed:
        bed[0]['admission_date'] = bed[0]['admission_date'].isoformat()  # Convert to ISO format
        return jsonify(bed[0])
    return jsonify({'message': 'Bed not found.'}), 404

# Endpoint to get all available beds
@bp.route('/available_beds', methods=['GET'])
def available_beds():
    # Fetch all available beds from the database
    beds = supabase.table('beds').select('*').execute().data
    if beds:
        return jsonify(beds), 200
    return jsonify({'message': 'No available beds found.'}), 404

# Endpoint to fetch available departments
@bp.route('/departments', methods=['GET'])
def get_departments():
    # Fetch available beds from the beds table
    beds = supabase.table('beds').select('department').eq('available', True).execute().data
    
    # Use a set to get unique departments
    unique_departments = {bed['department'] for bed in beds}  # Using a set comprehension to filter unique departments

    # Convert the set back to a list of dictionaries
    departments_list = [{'department': dept} for dept in unique_departments]
    
    return jsonify(departments_list), 200

# Endpoint to fetch available beds in a specific department
@bp.route('/beds', methods=['GET'])
def get_beds_by_department():
    department = request.args.get('department')

    if not department:
        return jsonify({'message': 'Department query parameter is required.'}), 400

    # Fetch available beds in the specified department
    beds = supabase.table('beds').select('*').eq('available', True).eq('department', department).execute().data
    
    if beds:
        return jsonify(beds), 200
    else:
        return jsonify([]), 500  # Return an empty list if no beds found



@bp.route('/department_beds', methods=['POST'])
def get_department_beds():
    data = request.get_json()
    department = data.get('department')
    
    if not department:
        return jsonify({'message': 'Department is required.'}), 400
    
    try:
        # Fetch all beds in the specified department
        beds = supabase.table('beds').select('*').eq('department', department).execute().data
        
        if not beds:
            return jsonify({'message': f'No beds found in {department} department.'}), 404
        
        # Get unique hospital_ids from the beds
        hospital_ids = {bed['hospital_id'] for bed in beds}
        
        # Fetch all relevant hospitals in a single query
        hospitals_data = supabase.table('hospitals').select('id,name').in_('id', list(hospital_ids)).execute().data
        
        # Create a lookup dictionary for faster access
        hospitals_dict = {hospital['id']: hospital for hospital in hospitals_data}
        
        # Merge hospital data with each bed
        for bed in beds:
            hospital_id = bed['hospital_id']
            if hospital_id in hospitals_dict:
                # Add hospital name to the bed data
                bed['hospital_name'] = hospitals_dict[hospital_id]['name']
            else:
                bed['hospital_name'] = None
        
        return jsonify(beds), 200
    
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
