from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func
from models import db, ContentFlag, CommunityPost, CommunityComment, User, ContentStatusEnum
from utils.role_required import role_required

moderation_bp = Blueprint('moderation_bp', __name__)

#flag content (post or comment)
@moderation_bp.route('/flag', methods=['POST'])
@jwt_required()
def flag_content():
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]
        
        data = request.get_json()
        post_id = data.get("post_id")
        comment_id = data.get("comment_id")
        reason = data.get("reason", "").strip()
        
        if not reason:
            return jsonify({"error": "Reason is required for flagging content"}), 400
        
        if not post_id and not comment_id:
            return jsonify({"error": "Either post_id or comment_id is required"}), 400
        
        # Check if content exists
        if post_id:
            post = CommunityPost.query.get(post_id)
            if not post:
                return jsonify({"error": "Post not found"}), 404
        if comment_id:
            comment = CommunityComment.query.get(comment_id)
            if not comment:
                return jsonify({"error": "Comment not found"}), 404
        
        # Check if user already flagged this content
        existing_flag = ContentFlag.query.filter_by(
            reporter_id=user_id,
            post_id=post_id,
            comment_id=comment_id
        ).first()
        
        if existing_flag:
            return jsonify({"error": "You have already flagged this content"}), 400
        
        # Create flag
        flag = ContentFlag(
            reporter_id=user_id,
            post_id=post_id,
            comment_id=comment_id,
            reason=reason,
            status=ContentStatusEnum.pending
        )
        
        db.session.add(flag)
        db.session.commit()
        
        return jsonify({
            "message": "Content flagged successfully for review",
            "flag_id": flag.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag content: {str(e)}"}), 500

# ADMIN: Get flagged content
@moderation_bp.route('/admin/flagged', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_flagged_content():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status', 'pending')  # pending, reviewed, all
        
        query = ContentFlag.query
        
        if status_filter == 'pending':
            query = query.filter(ContentFlag.status == ContentStatusEnum.pending)
        elif status_filter == 'reviewed':
            query = query.filter(ContentFlag.status.in_([ContentStatusEnum.approved, ContentStatusEnum.rejected]))
        
        flagged_content = query.order_by(ContentFlag.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        content_data = []
        for flag in flagged_content.items:
            flag_data = {
                "flag_id": flag.id,
                "reporter_username": flag.reporter.username,
                "reason": flag.reason,
                "status": flag.status.value,
                "created_at": flag.created_at.isoformat(),
                "content_type": "post" if flag.post_id else "comment"
            }
            
            if flag.post:
                flag_data.update({
                    "content_id": flag.post.id,
                    "content_title": flag.post.title,
                    "content_preview": flag.post.content[:100] + "..." if len(flag.post.content) > 100 else flag.post.content,
                    "author_username": flag.post.author.username
                })
            elif flag.comment:
                flag_data.update({
                    "content_id": flag.comment.id,
                    "content_preview": flag.comment.content[:100] + "..." if len(flag.comment.content) > 100 else flag.comment.content,
                    "author_username": flag.comment.author.username,
                    "post_title": flag.comment.post.title if flag.comment.post else "Unknown Post"
                })
            
            content_data.append(flag_data)
        
        return jsonify({
            "flagged_content": content_data,
            "page": page,
            "total_pages": flagged_content.pages,
            "total_items": flagged_content.total
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load flagged content: {str(e)}"}), 500

# ADMIN: Resolve flag
@moderation_bp.route('/admin/flags/<int:flag_id>/resolve', methods=['PUT'])
@jwt_required()
@role_required("admin")
def resolve_flag(flag_id):
    try:
        current_user = get_jwt_identity()
        admin_id = current_user["id"]
        
        flag = ContentFlag.query.get_or_404(flag_id)
        data = request.get_json()
        
        action = data.get("action")  # "approve" or "reject"
        admin_notes = data.get("admin_notes", "").strip()
        
        if action not in ["approve", "reject"]:
            return jsonify({"error": "Action must be 'approve' or 'reject'"}), 400
        
        if action == "approve":
            flag.status = ContentStatusEnum.approved
            # Take action on the content (remove/hide it)
            if flag.post:
                # For posts, you might want to hide or remove them
                flag.post.status = ContentStatusEnum.rejected
            elif flag.comment:
                # For comments, remove them
                db.session.delete(flag.comment)
            
            message = "Flag approved and content action taken"
        else:
            flag.status = ContentStatusEnum.rejected
            message = "Flag rejected - content remains published"
        
        # Add admin notes if provided
        if admin_notes:
            flag.reason += f" | Admin Notes: {admin_notes}"
        
        db.session.commit()
        
        return jsonify({
            "message": message,
            "flag_id": flag.id,
            "action_taken": action,
            "content_type": "post" if flag.post else "comment"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to resolve flag: {str(e)}"}), 500

# ADMIN: Get moderation statistics
@moderation_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_moderation_stats():
    try:
        total_flags = ContentFlag.query.count()
        pending_flags = ContentFlag.query.filter_by(status=ContentStatusEnum.pending).count()
        approved_flags = ContentFlag.query.filter_by(status=ContentStatusEnum.approved).count()
        rejected_flags = ContentFlag.query.filter_by(status=ContentStatusEnum.rejected).count()
        
        # Top reporters
        top_reporters = db.session.query(
            User.username,
            func.count(ContentFlag.id).label('flags_count')
        ).join(ContentFlag, User.id == ContentFlag.reporter_id).group_by(
            User.id, User.username
        ).order_by(func.count(ContentFlag.id).desc()).limit(10).all()
        
        # Recent moderation activity
        recent_activity = ContentFlag.query.filter(
            ContentFlag.status.in_([ContentStatusEnum.approved, ContentStatusEnum.rejected])
        ).order_by(ContentFlag.created_at.desc()).limit(10).all()
        
        return jsonify({
            "statistics": {
                "total_flags": total_flags,
                "pending_flags": pending_flags,
                "approved_flags": approved_flags,
                "rejected_flags": rejected_flags,
                "approval_rate": round((approved_flags / total_flags) * 100, 2) if total_flags > 0 else 0
            },
            "top_reporters": [
                {"username": username, "flags_count": count}
                for username, count in top_reporters
            ],
            "recent_activity": [
                {
                    "flag_id": flag.id,
                    "reporter": flag.reporter.username,
                    "action": flag.status.value,
                    "resolved_at": flag.created_at.isoformat()
                }
                for flag in recent_activity
            ]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load moderation stats: {str(e)}"}), 500

# ADMIN: Bulk action on multiple flags
@moderation_bp.route('/admin/bulk-action', methods=['POST'])
@jwt_required()
@role_required("admin")
def bulk_action_flags():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        flag_ids = data.get("flag_ids", [])
        action = data.get("action")  # "approve" or "reject"
        admin_notes = data.get("admin_notes", "")
        
        if not flag_ids:
            return jsonify({"error": "No flag IDs provided"}), 400
        
        if action not in ["approve", "reject"]:
            return jsonify({"error": "Action must be 'approve' or 'reject'"}), 400
        
        flags = ContentFlag.query.filter(ContentFlag.id.in_(flag_ids)).all()
        
        processed = 0
        for flag in flags:
            if action == "approve":
                flag.status = ContentStatusEnum.approved
                if flag.post:
                    flag.post.status = ContentStatusEnum.rejected
                elif flag.comment:
                    db.session.delete(flag.comment)
            else:
                flag.status = ContentStatusEnum.rejected
            
            if admin_notes:
                flag.reason += f" | Bulk Action Notes: {admin_notes}"
            
            processed += 1
        
        db.session.commit()
        
        return jsonify({
            "message": f"Processed {processed} flags with action: {action}",
            "processed_count": processed,
            "action": action
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process bulk action: {str(e)}"}), 500