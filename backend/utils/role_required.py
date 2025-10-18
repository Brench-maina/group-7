from functools import wraps
from flask_jwt_extended import get_jwt_identity
from flask import jsonify
from models import User

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            if not user_id:
                return jsonify({"error": "Unauthorized"}), 401

            user = User.query.get(user_id)
            if not user or user.role.value not in roles:
                return jsonify({"error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper
