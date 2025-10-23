from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from models import db, User, RoleEnum
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/test')
def test_auth():
    return jsonify({"message": "auth route working!"})

 
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role_str = data.get('role', 'learner')

    if not username or not email or not password:
        return jsonify({'error': "Missing required fields"}), 400

    # Validate role
    try:
        role_enum = RoleEnum[role_str]
    except KeyError:
        return jsonify({'error': "Invalid role"}), 400

    if len(password) < 8:
        return jsonify({'error': "Password must be at least 8 characters"}), 400

    # Check for existing user
    if User.query.filter_by(email=email).first():
        return jsonify({'error': "Email already registered"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': "Username already taken"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_pw,
        role=role_enum
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'role': new_user.role.value
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid username or password'}), 401

    # Update streak
    user.update_streak()

    # Create JWT token (identity as string to avoid errors)
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=8)
    )

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'points': user.points,
            'xp': user.xp,
            'streak_days': user.streak_days
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    # Convert back to integer
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "points": user.points,
        "xp": user.xp,
        "streak_days": user.streak_days
    })


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout successful'})
