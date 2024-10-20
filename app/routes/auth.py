from flask import Blueprint, request, jsonify
from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

bp = Blueprint('auth', __name__)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        # Attempt to sign up the user
        response = supabase.auth.sign_up({"email":email, "password":password})
        
        # Access the user object and check if it exists
        if not hasattr(response, 'user') or response.user is None:
            error_message = getattr(response, 'error', {}).get('message', 'Sign-up failed')
            return jsonify({"error": error_message}), 400

        # Return success response if sign-up was successful
        return jsonify({
            "message": "User signed up successfully",
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "confirmed_at": response.user.confirmed_at
            }
        }), 201

    except Exception as e:
        # Catch any error that occurs during the sign-up operation
        return jsonify({"error": "An error occurred during sign-up", "details": str(e)}), 500


@bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({ "email": email, "password": password })

        # Extract the necessary data from the response
        user = response.user
        session = response.session
        access_token = session.access_token

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "confirmed_at": user.confirmed_at.isoformat() if user.confirmed_at else None,
                "last_sign_in_at": user.last_sign_in_at.isoformat() if user.last_sign_in_at else None,
                "role": user.role
            },
            "token_type": "bearer"
        }), 200

    except Exception as e:
        return jsonify({"error": "An error occurred during login", "details": str(e)}), 500



@bp.route('/logout', methods=['POST'])
def logout():
    try:
        supabase.auth.sign_out()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Logout failed", "details": str(e)}), 400
