from supabase import create_client, Client
from flask import Flask, request, jsonify, session, Blueprint
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from datetime import timedelta
import requests
from werkzeug.utils import secure_filename
from io import BytesIO
import google.generativeai as genai
import threading,time
from app.config import SUPABASE_URL, SUPABASE_KEY

bp = Blueprint('schedular_opd', __name__)
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

def check_counters():
    response = supabase.table('counters').select('*').execute()
    counters = response.data
    print(counters)  # For debugging purposes

    for counter in counters:
        tokens = counter['allocated_tokens']
        token_start_time = counter['token_start_time']
                # Ensure token_start_time is correctly formatted
        if token_start_time:
            # Split by the dot to handle fractional seconds
            parts = token_start_time.split('.')
            if len(parts) == 2:
                # Truncate or pad to ensure we have 6 digits
                seconds = parts[1]
                if len(seconds) > 6:
                    seconds = seconds[:6]  # Truncate if longer than 6 digits
                elif len(seconds) < 6:
                    seconds = seconds.ljust(6, '0')  # Pad with zeros if shorter

                token_start_time = f"{parts[0]}.{seconds}"

        # Handle None values for tokens and token_start_time
        if token_start_time is None and not tokens:
            continue
        elif token_start_time is None and tokens:
            supabase.table('counters').update({
                'token_start_time': datetime.now().isoformat()
            }).eq('counter_id', counter['counter_id']).execute()
        elif token_start_time is not None and not tokens:
            supabase.table('counters').update({
                'token_start_time': None
            }).eq('counter_id', counter['counter_id']).execute()
        elif tokens and token_start_time:
            try:
                token_start_time = datetime.fromisoformat(token_start_time)
            except ValueError as e:
                print(f"Error parsing token_start_time '{token_start_time}': {e}")
            
            # Check if 1 minute has passed
            if datetime.now() - token_start_time > timedelta(minutes=1):
                current_token = tokens.pop(0)  # Remove from front
                tokens.append(current_token)  # Push to the end

                # Update the counter with new token order and reset timer
                supabase.table('counters').update({
                    'allocated_tokens': tokens,
                    'token_start_time': datetime.now().isoformat()  # Convert to string
                }).eq('counter_id', counter['counter_id']).execute()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_counters, 'interval', minutes=1)
    scheduler.start()
    # Prevent the thread from exiting
    while True:
        time.sleep(1)

# Run the scheduler in a separate thread
scheduler_thread = threading.Thread(target=start_scheduler)
scheduler_thread.daemon = True  # This allows the thread to exit when the main program exits
scheduler_thread.start()