from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
from models import db, LearningPath, ContentStatusEnum, User, UserProgress
from utils.role_required import role_required
from services.core_services import PointsService

learning_paths_bp = Blueprint('learning_paths_bp', __name__)

@learning_paths_bp.route('/test')
def test_learning():
    return jsonify({"message": "Learning route working!"})

# GET All Published Learning Paths
@learning_paths_bp.route("/paths", methods=["GET"])
def get_learning_paths():
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    status_filter = request.args.get("status")

    # Optional JWT check
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        current_user_identity = get_jwt_identity()
        if current_user_identity:
            # Handle both dict and simple ID
            user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
            current_user = User.query.get(user_id)
    except:
        current_user = None

    # Base query
    query = LearningPath.query

    # Only admins can see unpublished paths
    if not (current_user and current_user.role == "admin"):
        query = query.filter(LearningPath.is_published == True)

    # Admin can filter by status
    if current_user and current_user.role == "admin":
        if status_filter == "published":
            query = query.filter(LearningPath.is_published == True)
        elif status_filter == "pending":
            query = query.filter(LearningPath.is_published == False)

    # Pagination
    paths_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    paths_list = [
        {
            "id": lp.id,
            "title": lp.title,
            "description": lp.description,
            "is_published": lp.is_published
        }
        for lp in paths_paginated.items
    ]

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": paths_paginated.total,
        "paths": paths_list
    })


# GET a single Learning Path with modules
@learning_paths_bp.route('/paths/<int:path_id>', methods=['GET'])
def get_single_learning_path(path_id):
    path = LearningPath.query.get_or_404(path_id)
    
    # Optional JWT check
    current_user = None
    try:
        verify_jwt_in_request(optional=True)
        current_user_identity = get_jwt_identity()
        if current_user_identity:
            user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
            current_user = User.query.get(user_id)
    except:
        current_user = None
    
    if not path.is_published and (not current_user or current_user.role != "admin"):
        return jsonify({"error": "Learning path not found"}), 404

    return jsonify({
        "id": path.id,
        "title": path.title,
        "description": path.description,
        "status": path.status.value,
        "is_published": path.is_published,
        "creator": path.creator.username if path.creator else None,
        "created_at": path.created_at.isoformat(),
        "modules": [
            {
                "id": module.id,
                "title": module.title,
                "description": module.description,
                "resource_count": module.resources.count(),
                "quiz_count": module.quizzes.count()
            } for module in path.modules
        ]
    }), 200

# Create a new learning path
@learning_paths_bp.route('/paths', methods=['POST'])
@jwt_required()
@role_required("admin", "contributor")
def create_learning_path():
    try:
        current_user_identity = get_jwt_identity()
        # Handle both dict and simple ID
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()

        if not title:
            return jsonify({"error": "Title is required"}), 400
        if len(title) < 5:
            return jsonify({"error": "Title must be at least 5 characters"}), 400

        new_path = LearningPath(
            title=title,
            description=description,
            creator=user,
            status=ContentStatusEnum.pending,
            is_published=False
        )

        db.session.add(new_path)
        db.session.commit()
        PointsService.award_points(user, 'create_learning_path')

        return jsonify({
            "message": "Learning path created successfully and submitted for review",
            "path": {
                "id": new_path.id,
                "title": new_path.title,
                "status": new_path.status.value,
                "is_published": new_path.is_published
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create learning path"}), 500


# Follow Learning Path
@learning_paths_bp.route('/paths/<int:path_id>/follow', methods=['POST'])
@jwt_required()
def follow_path(path_id):
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get_or_404(path_id)
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        if not path.is_published:
            return jsonify({"error": "Cannot follow an unpublished learning path"}), 400
        if path in user.followed_paths:
            return jsonify({"error": "Already following this path"}), 400

        user.followed_paths.append(path)
        db.session.commit()
        return jsonify({
            "message": "Now following learning path",
            "path": {"id": path.id, "title": path.title}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to follow learning path"}), 500


# Unfollow Learning Path
@learning_paths_bp.route('/paths/<int:path_id>/unfollow', methods=['POST'])
@jwt_required()
def unfollow_path(path_id):
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get_or_404(path_id)
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        if path not in user.followed_paths:
            return jsonify({"error": "Not following this path"}), 400

        user.followed_paths.remove(path)
        db.session.commit()
        return jsonify({
            "message": "Unfollowed learning path",
            "path": {"id": path.id, "title": path.title}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to unfollow learning path"}), 500


# GET user's followed paths (FIXED)
@learning_paths_bp.route("/my-paths", methods=["GET"])
@jwt_required()
def get_my_learning_paths():
    try:
        # Get current user identity from JWT
        current_user_identity = get_jwt_identity()
        # Handle both dict and simple ID formats
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        followed_paths = []

        for path in user.followed_paths:
            # Only include published paths
            if path.is_published:
                # Count completed modules
                completed_modules = sum(
                    1 for module in path.modules if module in user.completed_modules
                )
                total_modules = len(path.modules)
                completion_percentage = (
                    int((completed_modules / total_modules) * 100) if total_modules > 0 else 0
                )

                followed_paths.append({
                    "id": path.id,
                    "title": path.title,
                    "description": path.description,
                    "completion_percentage": completion_percentage
                })

        return jsonify(followed_paths), 200
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve followed paths", "details": str(e)}), 500


# Admin Review Learning Paths
@learning_paths_bp.route('/admin/paths/<int:path_id>/review', methods=['PUT'])
@jwt_required()
@role_required("admin")
def review_learning_path(path_id):
    try:
        current_user_identity = get_jwt_identity()
        user_id = current_user_identity["id"] if isinstance(current_user_identity, dict) else current_user_identity
        
        path = LearningPath.query.get_or_404(path_id)
        data = request.get_json()
        action = data.get("action")
        reason = data.get("reason", "")

        if action == "approve":
            path.status = ContentStatusEnum.approved
            path.is_published = True
            path.reviewed_by = user_id
            path.rejection_reason = None
            PointsService.award_points(path.creator, 'learning_path_approved')
        elif action == "reject":
            path.status = ContentStatusEnum.rejected
            path.is_published = False
            path.rejection_reason = reason
            path.reviewed_by = user_id
        else:
            return jsonify({"error": "Invalid action"}), 400

        db.session.commit()
        return jsonify({
            "message": f"Learning path {action}d",
            "path": {
                "id": path.id,
                "title": path.title,
                "status": path.status.value,
                "is_published": path.is_published
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to review learning path"}), 500


# Admin Get pending paths
@learning_paths_bp.route('/admin/paths/pending', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_pending_paths():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    pending_paths = LearningPath.query.filter_by(status=ContentStatusEnum.pending).paginate(page=page, per_page=per_page, error_out=False)

    data = [
        {
            "id": path.id,
            "title": path.title,
            "description": path.description,
            "creator": path.creator.username if path.creator else "Unknown",
            "module_count": path.modules.count(),
            "created_at": path.created_at.isoformat()
        } for path in pending_paths.items
    ]

    return jsonify({
        "pending_paths": data,
        "page": page,
        "total_pages": pending_paths.pages,
        "total_items": pending_paths.total
    }), 200