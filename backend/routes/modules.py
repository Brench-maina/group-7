
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, LearningPath, Module, LearningResource
from utils.role_required import role_required

modules_bp = Blueprint('modules_bp', __name__)

# GET Modules for a Path
@modules_bp.route('/paths/<int:path_id>/modules', methods=['GET'])
def get_modules_for_path(path_id):
    path = LearningPath.query.get_or_404(path_id)
    current_user = get_jwt_identity()
    if not path.is_published and (not current_user or current_user.get("role") != "admin"):
        return jsonify({"error": "Learning path not found"}), 404

    return jsonify({
        "id": path.id,
        "title": path.title,
        "modules": [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "resource_count": m.resources.count(),
                "quiz_count": m.quizzes.count()
            } for m in path.modules
        ]
    }), 200


# Create Module
@modules_bp.route('/paths/<int:path_id>/modules', methods=['POST'])
@jwt_required()
@role_required("admin", "contributor")
def add_module(path_id):
    try:
        path = LearningPath.query.get_or_404(path_id)
        current_user = get_jwt_identity()
        if path.creator_id != current_user["id"] and current_user["role"] != "admin":
            return jsonify({"error": "Not authorized"}), 403

        data = request.get_json()
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400

        new_module = Module(title=title, description=description, learning_path=path)
        db.session.add(new_module)
        db.session.commit()
        return jsonify({"message": "Module added", "module": {"id": new_module.id, "title": new_module.title}}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to add module"}), 500


# Add Resource
@modules_bp.route('/modules/<int:module_id>/resources', methods=['POST'])
@jwt_required()
@role_required("admin", "contributor")
def add_resource(module_id):
    try:
        module = Module.query.get_or_404(module_id)
        current_user = get_jwt_identity()
        if module.learning_path.creator_id != current_user["id"] and current_user["role"] != "admin":
            return jsonify({"error": "Not authorized"}), 403

        data = request.get_json()
        title, resource_type, url = data.get("title", "").strip(), data.get("type", "").strip(), data.get("url", "").strip()
        description = data.get("description", "").strip()
        if not all([title, resource_type, url]):
            return jsonify({"error": "Title, type, and URL are required"}), 400

        new_resource = LearningResource(title=title, type=resource_type, url=url, description=description, module=module)
        db.session.add(new_resource)
        db.session.commit()

        return jsonify({"message": "Resource added", "resource": {"id": new_resource.id, "title": new_resource.title}}), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to add resource"}), 500


# GET Resources
@modules_bp.route('/modules/<int:module_id>/resources', methods=['GET'])
@jwt_required()
def get_resources_for_module(module_id):
    module = Module.query.get_or_404(module_id)
    if not module.learning_path.is_published:
        current_user = get_jwt_identity()
        if not current_user or current_user.get("role") != "admin":
            return jsonify({"error": "Module not found"}), 404

    resources = [{"id": r.id, "title": r.title, "type": r.type, "url": r.url, "description": r.description} for r in module.resources]
    return jsonify({"module_id": module.id, "module_title": module.title, "resources": resources}), 200
