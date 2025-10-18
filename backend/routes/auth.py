from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from models import db, User
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
        role = data.get('role', 'learner')

        if not username or not email or not password:
            return jsonify({'error': "Missing required fields"}), 400
        
        #check for existing user with same username 
        if User.query.filter_by(email=email).first():
            return jsonify({'error': "Email already registered"}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({'error': "Username already taken"}), 400
        
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_pw,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully',
                         'user': {
                            'id': new_user.id,
                            'username': new_user.username,
                            'email': new_user.email,
                            'role': new_user.role
                         }}), 201
        
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
   
   #create token 
   access_token = create_access_token(
       identity={'id': user.id, 'role': user.role},
       expires_delta=timedelta(hours=8)
   )
   return jsonify({
       'message': 'Login successful',
       'access_token': access_token,
       'user': {
           'id': user.id,
           'username': user.username,
           'email': user.email,
           'role': user.role
       }
        }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout successful'})