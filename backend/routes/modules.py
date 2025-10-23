from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from models import db, Module, LearningResource, LearningPath
from utils.role_required import role_required

modules_bp = Blueprint("modules_bp", __name__)

#Get all modules for a specific learning path
@modules_bp.route("/learning-paths/<int:path_id>/modules", methods=["GET"])
@jwt_required()
def get_modules_by_path(path_id):
    """Fetch all modules under a specific learning path."""
    learning_path = LearningPath.query.get(path_id)
    if not learning_path:
        return jsonify({"error": "Learning path not found"}), 404

    modules = Module.query.filter_by(path_id=path_id).all()
    return jsonify([m.to_dict() for m in modules]), 200


#Get all resources for a specific module
@modules_bp.route("/modules/<int:module_id>/resources", methods=["GET"])
@jwt_required()
def get_module_resources(module_id):
    """Fetch all learning resources under a specific module."""
    module = Module.query.get(module_id)
    if not module:
        return jsonify({"error": "Module not found"}), 404

    resources = LearningResource.query.filter_by(module_id=module_id).all()
    return jsonify([r.to_dict() for r in resources]), 200


#Create a new resource for a module (Admin or Contributor)
@modules_bp.route("/modules/<int:module_id>/resources", methods=["POST"])
@role_required(["admin", "contributor"])
def create_resource(module_id):
    """Add a new learning resource to a module."""
    data = request.get_json() or {}
    title = data.get("title")
    url = data.get("url")

    if not title or not url:
        return jsonify({"error": "Both title and URL are required"}), 400

    module = Module.query.get(module_id)
    if not module:
        return jsonify({"error": "Module not found"}), 404

    new_resource = LearningResource(title=title, url=url, module_id=module_id)
    db.session.add(new_resource)
    db.session.commit()

    return jsonify(new_resource.to_dict()), 201
