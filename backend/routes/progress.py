from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, User, Module, UserProgress, LearningPath
from services.core_services import PointsService


progress_bp = Blueprint('progress_bp', __name__)

# MARK module as completed
@progress_bp.route('/modules/<int:module_id>/complete', methods=['POST'])
@jwt_required()
def complete_module(module_id):
    try:
        current_user = get_jwt_identity()
        module = Module.query.get_or_404(module_id)
        user = User.query.get(current_user["id"])

        if module.learning_path not in user.followed_paths:
            return jsonify({"error": "You must follow the path"}), 400

        progress = UserProgress.query.filter_by(user_id=user.id, module_id=module_id).first()
        if not progress:
            progress = UserProgress(user_id=user.id, module_id=module_id, completion_percent=100, completed_at=datetime.utcnow())
            db.session.add(progress)
        else:
            progress.completion_percent = 100
            progress.completed_at = datetime.utcnow()

        db.session.commit()
        PointsService.award_points(user, 'complete_module')
        return jsonify({
            "message": "Module completed",
            "progress": {"module_id": module.id, "completion_percent": 100}
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to complete module"}), 500

# GET path progress
@progress_bp.route('/paths/<int:path_id>/progress', methods=['GET'])
@jwt_required()
def get_path_progress(path_id):
    current_user = get_jwt_identity()
    path = LearningPath.query.get_or_404(path_id)
    total_completion = 0
    progress_data = []

    for m in path.modules:
        user_progress = UserProgress.query.filter_by(user_id=current_user["id"], module_id=m.id).first()
        completion = user_progress.completion_percent if user_progress else 0
        total_completion += completion
        progress_data.append({
            "module_id": m.id,
            "module_title": m.title,
            "completion_percent": completion,
            "completed_at": user_progress.completed_at.isoformat() if user_progress and user_progress.completed_at else None
        })

    overall = total_completion / len(path.modules) if path.modules.count() > 0 else 0
    return jsonify({
        "path_id": path.id,
        "path_title": path.title,
        "overall_completion": round(overall, 2),
        "progress": progress_data
    }), 200
