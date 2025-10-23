from functools import wraps
from flask_jwt_extended import get_jwt_identity
from flask import jsonify
from models import User

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            # get_jwt_identity() returns a string (user id)
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Unauthorized"}), 401

            # Convert to int just to be safe
            user = User.query.get(int(user_id))
            if not user:
                return jsonify({"error": "User not found"}), 404

            if user.role.value not in roles:
                return jsonify({"error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper
