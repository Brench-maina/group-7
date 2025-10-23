from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, UserProgress
from utils.role_required import role_required

user_bp = Blueprint("user", __name__)

# GET Current User Profile
@user_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    current_user_id = int(get_jwt_identity())  
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    progress = UserProgress.query.filter_by(user_id=user.id).all()

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "joined_on": user.created_at.strftime("%Y-%m-%d"),
        "progress": [
            {
                "module_id": p.module_id,
                "completion_percent": p.completion_percent,
                "last_score": p.last_score,
                "completed_at": p.completed_at.strftime("%Y-%m-%d") if p.completed_at else None
            } for p in progress
        ],
        "streak_days": user.streak_days,
        "points": user.points,
        "xp": user.xp
    }), 200


# UPDATE Profile
@user_bp.route("/profile/update", methods=["PUT"])
@jwt_required()
def update_profile():
    current_user_id = int(get_jwt_identity()) 
    user = User.query.get(current_user_id)
    data = request.get_json() or {}

    new_username = data.get("username")
    new_email = data.get("email")

    if new_username:
        if len(new_username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400

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
    current_user_id = int(get_jwt_identity())  
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Account deleted successfully"}), 200


# ADMIN can View All Users
@user_bp.route("/all", methods=["GET"])
@jwt_required()
@role_required("admin")
def get_all_users():
    users = User.query.all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role.value,
            "points": u.points,
            "xp": u.xp
        } for u in users
    ]), 200
