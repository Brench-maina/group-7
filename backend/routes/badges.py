from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from models import db, Badge, User, UserBadge
from services.core_services import BadgeService
from utils.role_required import role_required
from datetime import datetime

badges_bp = Blueprint('badges_bp', __name__)


#GET all badges
@badges_bp.route('/', methods=['GET'])
def get_all_badges():
    try:
        badges = Badge.query.all()
        return jsonify([
            {
                "id": b.id,
                "key": b.key,
                "name": b.name,
                "description": b.description,
                "created_at": b.created_at.isoformat() if b.created_at else None
            } for b in badges
        ]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load badges: {str(e)}"}), 500


#GET single badge
@badges_bp.route('/<string:badge_key>', methods=['GET'])
def get_badge(badge_key):
    try:
        badge = Badge.query.filter_by(key=badge_key).first_or_404()
        earners_count = UserBadge.query.filter_by(badge_id=badge.id).count()

        return jsonify({
            "id": badge.id,
            "key": badge.key,
            "name": badge.name,
            "description": badge.description,
            "created_at": badge.created_at.isoformat() if badge.created_at else None,
            "total_earners": earners_count
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load badge: {str(e)}"}), 500


#GET user's earned badges & progress
@badges_bp.route('/my-badges', methods=['GET'])
@jwt_required()
def get_my_badges():
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]

        all_badges = Badge.query.all()
        earned_badge_ids = {b.badge_id for b in UserBadge.query.filter_by(user_id=user_id).all()}

        # Get badge progress from BadgeService
        badge_progress = BadgeService.get_user_badge_progress(user_id)

        badges_data = []
        for badge in all_badges:
            is_earned = badge.id in earned_badge_ids
            progress = badge_progress.get(badge.key, {})

            badges_data.append({
                "id": badge.id,
                "key": badge.key,
                "name": badge.name,
                "description": badge.description,
                "is_earned": is_earned,
                "progress": progress if not is_earned and progress else None,
                "created_at": badge.created_at.isoformat() if badge.created_at else None
            })

        return jsonify({
            "total_badges": len(badges_data),
            "earned_badges": len(earned_badge_ids),
            "badges": badges_data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load user badges: {str(e)}"}), 500


#Admin manually awards badge
@badges_bp.route('/award', methods=['POST'])
@jwt_required()
@role_required("admin")
def award_badge():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        badge_key = data.get("badge_key")

        if not user_id or not badge_key:
            return jsonify({"error": "user_id and badge_key required"}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check if user already has this badge
        existing = (
            db.session.query(UserBadge)
            .join(Badge)
            .filter(UserBadge.user_id == user.id, Badge.key == badge_key)
            .first()
        )
        if existing:
            return jsonify({"error": f"User already has badge '{badge_key}'"}), 400

        # Award the badge using your existing service
        BadgeService.award_badge(user, badge_key)

        return jsonify({
            "message": f"Badge '{badge_key}' awarded to {user.username}",
            "user": {"id": user.id, "username": user.username},
            "badge_key": badge_key
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to award badge: {str(e)}"}), 500


#Global Badge Leaderboard
@badges_bp.route('/leaderboard', methods=['GET'])
def get_badge_leaderboard():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        leaderboard = (
            db.session.query(
                User.id, User.username, func.count(UserBadge.id).label('badge_count')
            )
            .join(UserBadge, User.id == UserBadge.user_id)
            .group_by(User.id, User.username)
            .order_by(func.count(UserBadge.id).desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        #Handle empty leaderboard gracefully
        if leaderboard.total == 0:
            return jsonify({
                "message": "No badge earners yet - be the first!",
                "leaderboard": [],
                "page": page,
                "total_pages": 0,
                "total_players": 0
            }), 200

        leaders_data = [
            {
                "rank": rank,
                "user_id": user_id,
                "username": username,
                "badge_count": badge_count
            }
            for rank, (user_id, username, badge_count) in enumerate(leaderboard.items, start=1)
        ]

        return jsonify({
            "leaderboard": leaders_data,
            "page": page,
            "total_pages": leaderboard.pages,
            "total_players": leaderboard.total
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load leaderboard: {str(e)}"}), 500


#Create new badge (Admin only)
@badges_bp.route('/admin/badges', methods=['POST'])
@jwt_required()
@role_required("admin")
def create_badge():
    try:
        data = request.get_json()

        key = data.get("key", "").strip()
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()

        if not all([key, name, description]):
            return jsonify({"error": "key, name, and description are required"}), 400

        # Check if badge key already exists
        if Badge.query.filter_by(key=key).first():
            return jsonify({"error": "Badge key already exists"}), 400

        new_badge = Badge(
            key=key, 
            name=name, 
            description=description
        )
        db.session.add(new_badge)
        db.session.commit()

        return jsonify({
            "message": "Badge created successfully",
            "badge": {
                "id": new_badge.id,
                "key": new_badge.key,
                "name": new_badge.name,
                "description": new_badge.description
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create badge: {str(e)}"}), 500


#Admin summary
@badges_bp.route('/admin/summary', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_admin_summary():
    try:
        total_badges = Badge.query.count()
        total_earned = UserBadge.query.count()
        total_users = User.query.count()

        # Top badges by number of earners
        top_badges = (
            db.session.query(
                Badge.key, Badge.name, func.count(UserBadge.id).label('earner_count')
            )
            .join(UserBadge, Badge.id == UserBadge.badge_id)
            .group_by(Badge.id, Badge.key, Badge.name)
            .order_by(func.count(UserBadge.id).desc())
            .limit(10)
            .all()
        )

        # Recent badge awards
        recent_awards = (
            UserBadge.query.join(User).join(Badge)
            .order_by(UserBadge.awarded_at.desc())
            .limit(10)
            .all()
        )

        return jsonify({
            "statistics": {
                "total_badges": total_badges,
                "total_earned_badges": total_earned,
                "total_users": total_users,
                "average_badges_per_user": round(total_earned / total_users, 2) if total_users else 0
            },
            "top_badges": [
                {"key": key, "name": name, "earner_count": count}
                for key, name, count in top_badges
            ],
            "recent_awards": [
                {
                    "username": award.user.username,
                    "badge_name": award.badge.name,
                    "awarded_at": award.awarded_at.isoformat()
                }
                for award in recent_awards
            ]
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load summary: {str(e)}"}), 500