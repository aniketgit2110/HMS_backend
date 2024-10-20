from flask import Blueprint, request, jsonify
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY
import requests

bp = Blueprint('todos', __name__)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_supabase_token(token):
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_KEY
    }
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else None

@bp.route('/todos', methods=['GET'])
def get_todos():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch todos for the authenticated user
    todos = supabase.table("todo").select("*").eq("user_id", user_info['id']).execute()
    return jsonify(todos.data), 200

@bp.route('/todos', methods=['POST'])
def create_todo():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"error": "Authorization header is missing"}), 401

    # Extract the token from the header
    token = token.split(" ")[1]  # Get token from "Bearer <token>"
    user_info = verify_supabase_token(token)
    
    if user_info is None:
        return jsonify({"error": "Unauthorized"}), 401

    # Create a new todo for the authenticated user
    data = request.json
    new_todo = {
        "user_id": user_info['id'],  # Use user ID from verified token
        "task": data.get('task'),
        "completed": data.get('completed', False)  # Default to False if not provided
    }
    
    # Insert the new todo into the Supabase table
    try:
        response = supabase.table("todo").insert(new_todo).execute()

        # Return success response if insertion is successful
        return jsonify(response.data[0]), 201

    except Exception as e:
        # Catch any error that occurs during the insert operation
        return jsonify({"error": "Failed to create todo", "details": str(e)}), 500
