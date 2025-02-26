from supabase import create_client, Client
from flask import Flask, request, jsonify, session, Blueprint
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import os
from datetime import timedelta
import requests
import json,random
from werkzeug.utils import secure_filename
from io import BytesIO
import google.generativeai as genai
from sinch import SinchClient
from app.config import SUPABASE_URL, SUPABASE_KEY
import fitz  # PyMuPDF

bp = Blueprint('ocr', __name__)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
sinch_client = SinchClient(
    key_id="e86a4385-c576-4e96-8bd1-e1513bf58a08",
    key_secret="M3S.a-rF4Jmuwt4L6rM~AX_RBG",
    project_id="5f27a568-815e-4d81-bb92-93d15ba17c89"
)

def verify_supabase_token(token):
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_KEY
    }
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

def extract_text_from_pdf_file(file):
    """
    Extract text from a PDF file using PyMuPDF.
    The file parameter is a Flask FileStorage object.
    """
    # Read the entire file as bytes
    file_bytes = file.read()
    file.seek(0)  # reset pointer for subsequent operations (like OCR)
    # Open the PDF from bytes
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Utility function to interact with Supabase
def execute_query(sql):
    return supabase.rpc("execute_sql", {"sql": sql})

def ocr_post(api_key, file):
    url = 'https://api.ocr.space/parse/image'
    
    # Prepare payload
    payload = {
        'apikey': api_key,
        'language': 'eng',
        'isOverlayRequired': False
    }
    
    if file:
        files = {
            'file': (file.filename, file.stream, 'application/pdf')  # Set content type for PDF
        }
        response = requests.post(url, data=payload, files=files)
        return response.json()
    
    return {'Error': 'No valid PDF input provided.'}

def extract_information(parsed_text):
    genai.configure(api_key="AIzaSyBXPkjm3aSTVsmAUIXymH6SxXmr6NHWv44")
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

    prompt = f"""
    Extract the following information in JSON format only:
    Name
    Gender
    DOB
    Address
    Phone Number
    Aadhaar Number
    Other Important Information

    Text: {parsed_text}
    
    Response format: {{"name": "", "address": "", "Gender":"", "DOB":"", "phone_number": "", "aadhaar_number": "", "other_information": ""}}
    """
    try:
       chat_session = model.start_chat(history=[])
       response = chat_session.send_message(prompt)
       return response.text  # Assuming response.text is JSON formatted
    except genai.types.generation_types.StopCandidateException as e:
          print("Safety filter triggered:", e)
          return {'Error': 'Response blocked by safety filters.'}

def trim_text(text):
    text = text.replace('\n', '')
    text = text.replace('\\', '')


    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index != -1 and end_index != -1 and start_index < end_index:
        trimmed_text = text[start_index:end_index + 1]
    else:
        trimmed_text = text

    try:
        json_data = json.loads(trimmed_text)
        for key in json_data:
            if isinstance(json_data[key], str):
                json_data[key] = json_data[key].replace('\n', '')
                json_data[key] = json_data[key].replace('\\', '')
        cleaned_json = json.dumps(json_data)
        return cleaned_json
    except json.JSONDecodeError:
        return trimmed_text

def clean_text(parsed_text):
    genai.configure(api_key="AIzaSyBXPkjm3aSTVsmAUIXymH6SxXmr6NHWv44")
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

    prompt = f"""
       Remove unnecessary or illogical things from json {parsed_text}
    """
    try:
       chat_session = model.start_chat(history=[])
       response = chat_session.send_message(prompt)
       return trim_text(response.text)
    except genai.types.generation_types.StopCandidateException as e:
          print("Safety filter triggered:", e)
          return {'Error': 'Response blocked by safety filters.'}


@bp.route('/upload', methods=['POST'])
def upload_pdf():
    ocr_api_key = 'K86403013788957'
    token = request.headers.get('Authorization')
    if token:
        token = token.split(" ")[1]
        user_info = verify_supabase_token(token)
        
        if user_info is None:
            return jsonify({"error": "Unauthorized"}), 401

    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({"error": "Missing required field: patient_id"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.pdf') or filename_lower.endswith(('.jpg', '.jpeg', '.png'))):
        return jsonify({'Error': 'Invalid file type. Please upload a PDF or image file.'}), 400

    # Make a copy of the file to avoid stream issues
    file_copy = BytesIO(file.read())
    file.seek(0)
    
    try:
            
        # OCR processing
        combined_text = ""
        if filename_lower.endswith('.pdf'):
            pdf_text = extract_text_from_pdf_file(file)
            file.seek(0)
            ocr_result = ocr_post(ocr_api_key, file=file)
            if ocr_result.get('OCRExitCode') == 1 and not ocr_result.get('IsErroredOnProcessing'):
                ocr_text = ocr_result['ParsedResults'][0]['ParsedText']
                combined_text = pdf_text + "\n" + ocr_text
            else:
                return jsonify({"Error": ocr_result.get('ErrorMessage', 'Unknown OCR error')}), 500
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png')):
            ocr_result = ocr_post(ocr_api_key, file=file)
            if ocr_result.get('OCRExitCode') == 1 and not ocr_result.get('IsErroredOnProcessing'):
                combined_text = ocr_result['ParsedResults'][0]['ParsedText']
            else:
                return jsonify({"Error": ocr_result.get('ErrorMessage', 'Unknown OCR error')}), 500
        
        # Process text with Gemini
        json_response = extract_information(combined_text)
        refined_text = trim_text(json_response)
        final_text = clean_text(refined_text)
        
        try:
            json_data = json.loads(final_text)
                
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to decode JSON from Gemini response."}), 500
            
        formatted_json = json.dumps(json_data, indent=4)
        return formatted_json, 200
        
    except Exception as e:
        print(f"Upload PDF error: {str(e)}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500
    
# Route to generate and send OTP
@bp.route('/send-otp/<phone_number>', methods=['GET'])
def send_otp(phone_number):
    # Generate a 4-digit OTP
    otp = random.randint(1000, 9999)
    
    # SMS body with the OTP
    message_body = f"Your OTP is {otp}. Please use it to verify your identity."

    try:
        # Send SMS via Sinch
        send_batch_response = sinch_client.sms.batches.send(
            body=message_body,
            to=[f"+{phone_number}"],  # Assuming you pass the phone number in international format (e.g., +91 for India)
            from_="447418631268",  # Your Sinch sender ID or phone number
            delivery_report="none"
        )
        
        # Return a success message with the OTP (for demo purposes)
        return jsonify({"message": "OTP sent successfully!", "otp": otp, "send_batch_response": send_batch_response}), 200

    except Exception as e:
        return jsonify({"message": "Failed to send OTP", "error": str(e)}), 500
