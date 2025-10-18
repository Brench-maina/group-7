from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from models import db, User, UserProgress

user_bp = Blueprint("user", __name__)

# GET Current User Profile
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    progress = UserProgress.query.filter_by(user_id=user.id).all()
    

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "joined_on": user.created_at.strftime("%Y-%m-%d"),
        "progress": [{"module": p.module_id, "completed": p.completed} for p in progress],
        "streak_days": user.streak_days
    }), 200


# UPDATE Profile (username or email)
@user_bp.route("/profile/update", methods=["PUT"])
@jwt_required()
def update_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    data = request.get_json()

    new_username = data.get("username")
    new_email = data.get("email")

    if new_username:
        # Check if username is taken by someone else
        if User.query.filter(User.username == new_username, User.id != user.id).first():
            return jsonify({"error": "Username already taken"}), 409
        user.username = new_username

    if new_email:
        if User.query.filter(User.email == new_email, User.id != user.id).first():
            return jsonify({"error": "Email already in use"}), 409
        user.email = new_email

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200



# DELETE Account
@user_bp.route("/delete", methods=["DELETE"])
@jwt_required()
def delete_account():
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])

    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Account deleted successfully"}), 200


# ADMIN — View All Users (Optional)
@user_bp.route("/all", methods=["GET"])
@jwt_required()
def get_all_users():
    current_user = get_jwt_identity()
    if current_user["role"] != "admin":
        return jsonify({"error": "Access denied"}), 403

    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role
        } for u in users
    ]), 200
