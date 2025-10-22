from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, CommunityPost, CommunityComment, RoleEnum
from utils.role_required import role_required

community_bp = Blueprint("community_bp", __name__)

# Create a community post
@community_bp.route("/posts", methods=["POST"])
@jwt_required()
@role_required("admin", "contributor")  # individual args
def create_post():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()

        title = data.get("title", "").strip()
        content = data.get("content", "").strip()

        if not title or not content:
            return jsonify({"error": "Title and content are required"}), 400
        
        if len(title) < 5:
            return jsonify({"error": "Title must be at least 5 characters"}), 400
        if len(content) < 10:
            return jsonify({"error": "Content must be at least 10 characters"}), 400

        post = CommunityPost(
            title=title,
            content=content,
            author_id=current_user["id"]
        )
        db.session.add(post)
        db.session.commit()

        return jsonify({
            "message": "Post created successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author_id": post.author_id,
                "author_username": post.author.username,
                "created_at": post.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create post"}), 500

# Get all posts (with pagination) 
@community_bp.route("/posts", methods=["GET"])
def get_posts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    pagination = CommunityPost.query.order_by(CommunityPost.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    posts = []
    for post in pagination.items:
        posts.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": post.author.username,
            "created_at": post.created_at.isoformat(),
            "comments_count": post.comments.count()
        })

    return jsonify({
        "posts": posts,
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": pagination.page
    }), 200

# Get a single post and its comments 
@community_bp.route("/posts/<int:post_id>", methods=["GET"])
def get_single_post(post_id):
    post = CommunityPost.query.get_or_404(post_id)

    return jsonify({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.author.username,
        "created_at": post.created_at.isoformat(),
        "comments": [
            {
                "id": c.id,
                "content": c.content,
                "author": c.author.username,
                "created_at": c.created_at.isoformat()
            } for c in post.comments.order_by(CommunityComment.created_at.asc()).all()
        ]
    }), 200

#Add a comment to a post
@community_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@jwt_required()
def add_comment(post_id):
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        content = data.get("content", "").strip()

        if not content:
            return jsonify({"error": "Comment content required"}), 400
        
        if len(content) < 3:
            return jsonify({"error": "Comment must be at least 3 characters"}), 400

        post = CommunityPost.query.get_or_404(post_id)
        comment = CommunityComment(
            content=content,
            post_id=post.id,
            author_id=current_user["id"]
        )
        db.session.add(comment)
        db.session.commit()

        return jsonify({
            "message": "Comment added",
            "comment": {
                "id": comment.id,
                "content": comment.content,
                "author_id": comment.author_id,
                "author_username": comment.author.username,
                "created_at": comment.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add comment"}), 500

# Delete a post (admin or post owner) 
@community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id):
    current_user = get_jwt_identity()
    post = CommunityPost.query.get_or_404(post_id)

    if current_user["role"] != "admin" and post.author_id != current_user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted"}), 200

# Delete a comment (admin or comment owner) 
@community_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment(comment_id):
    current_user = get_jwt_identity()
    comment = CommunityComment.query.get_or_404(comment_id)

    if current_user["role"] != "admin" and comment.author_id != current_user["id"]:
        return jsonify({"error": "Not authorized"}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "Comment deleted"}), 200
