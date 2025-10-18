from flask import Blueprint, jsonify

learning_bp = Blueprint('learning_bp', __name__)

@learning_bp.route('/learning/test')
def test_learning():
    return jsonify({"message": "Learning route working!"})
