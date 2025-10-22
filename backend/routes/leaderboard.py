from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from models import db, Leaderboard, User, PointsLog
from services.core_services import LeaderboardService
from utils.role_required import role_required

leaderboard_bp = Blueprint('leaderboard_bp', __name__)

# GET Global Leaderboard
@leaderboard_bp.route('/global', methods=['GET'])
def get_global_leaderboard():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    leaderboard = Leaderboard.query.join(User).order_by(
        Leaderboard.rank.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "leaderboard": [
            {
                "rank": entry.rank,
                "user_id": entry.user_id,
                "username": entry.user.username,
                "points": entry.total_points,
                "xp": entry.user.xp,
                "badges_count": entry.user.badges.count()
            } for entry in leaderboard.items
        ],
        "page": page,
        "total_pages": leaderboard.pages,
        "total_players": leaderboard.total
    }), 200

# GET Current User's Rank
@leaderboard_bp.route('/my-rank', methods=['GET'])
@jwt_required()
def get_my_rank():
    current_user = get_jwt_identity()
    user_id = current_user["id"]
    
    leaderboard_entry = Leaderboard.query.filter_by(user_id=user_id).first()
    user = User.query.get(user_id)
    
    if not leaderboard_entry:
        return jsonify({
            "message": "Not ranked yet",
            "user": {
                "username": user.username,
                "points": user.points,
                "xp": user.xp
            }
        }), 200
    
    # Get users above and below for context
    rank = leaderboard_entry.rank
    nearby_players = Leaderboard.query.join(User).filter(
        Leaderboard.rank.between(max(1, rank - 2), rank + 2)
    ).order_by(Leaderboard.rank.asc()).all()
    
    return jsonify({
        "rank": rank,
        "points": leaderboard_entry.total_points,
        "user": {
            "username": user.username,
            "points": user.points,
            "xp": user.xp,
            "streak_days": user.streak_days,
            "badges_count": user.badges.count()
        },
        "nearby_players": [
            {
                "rank": entry.rank,
                "username": entry.user.username,
                "points": entry.total_points
            } for entry in nearby_players
        ]
    }), 200

# GET Top 10 Players
@leaderboard_bp.route('/top', methods=['GET'])
def get_top_players():
    limit = request.args.get('limit', 10, type=int)
    
    top_players = Leaderboard.query.join(User).order_by(
        Leaderboard.rank.asc()
    ).limit(limit).all()
    
    return jsonify({
        "top_players": [
            {
                "rank": entry.rank,
                "username": entry.user.username,
                "points": entry.total_points,
                "xp": entry.user.xp,
                "badges_count": entry.user.badges.count(),
                "streak_days": entry.user.streak_days
            } for entry in top_players
        ]
    }), 200


# GET Leaderboard by Category (points from specific activities)
@leaderboard_bp.route('/category/<category>', methods=['GET'])
def get_category_leaderboard(category):
    valid_categories = ['learning', 'community', 'content', 'quizzes']
    
    if category not in valid_categories:
        return jsonify({"error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}), 400
    
    # Map categories to point reasons
    category_filters = {
        'learning': ['complete_module', 'complete_quiz', 'daily_login'],
        'community': ['create_post', 'add_comment', 'rate_resource'],
        'content': ['create_learning_path', 'learning_path_approved', 'add_resource'],
        'quizzes': ['complete_quiz', 'perfect_quiz_score']
    }
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    category_leaders = db.session.query(
        User.id,
        User.username,
        func.coalesce(func.sum(PointsLog.points_change), 0).label('category_points')
    ).join(
        PointsLog, 
        (User.id == PointsLog.user_id) & (PointsLog.reason.in_(category_filters[category]))
    ).group_by(
        User.id, User.username
    ).order_by(
        desc('category_points')
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    ranked_players = []
    for rank, (user_id, username, category_points) in enumerate(category_leaders.items, start=1):
        ranked_players.append({
            "rank": rank,
            "user_id": user_id,
            "username": username,
            "category_points": category_points,
            "category": category
        })
    
    return jsonify({
        "category_leaderboard": ranked_players,
        "category": category,
        "page": page,
        "total_pages": category_leaders.pages,
        "total_players": category_leaders.total
    }), 200

# ADMIN: Force Leaderboard Update
@leaderboard_bp.route('/admin/update', methods=['POST'])
@jwt_required()
@role_required("admin")
def force_leaderboard_update():
    try:
        LeaderboardService.update_all_ranks()
        return jsonify({
            "message": "Leaderboard updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to update leaderboard"}), 500

# ADMIN: Get Leaderboard Statistics
@leaderboard_bp.route('/admin/stats', methods=['GET'])
@jwt_required()
@role_required("admin")
def get_leaderboard_stats():
    total_players = User.query.count()
    ranked_players = Leaderboard.query.count()
    average_points = db.session.query(func.avg(User.points)).scalar() or 0
    top_player = Leaderboard.query.join(User).order_by(Leaderboard.rank.asc()).first()
    
    # Points distribution
    points_ranges = [
        (0, 100, '0-100'),
        (101, 500, '101-500'),
        (501, 1000, '501-1000'),
        (1001, 5000, '1001-5000'),
        (5001, None, '5000+')
    ]
    
    distribution = []
    for min_points, max_points, label in points_ranges:
        query = User.query
        if min_points is not None:
            query = query.filter(User.points >= min_points)
        if max_points is not None:
            query = query.filter(User.points <= max_points)
        count = query.count()
        distribution.append({
            "range": label,
            "players": count,
            "percentage": round((count / total_players) * 100, 2) if total_players > 0 else 0
        })
    
    return jsonify({
        "statistics": {
            "total_players": total_players,
            "ranked_players": ranked_players,
            "unranked_players": total_players - ranked_players,
            "average_points": round(average_points, 2),
            "top_player": {
                "username": top_player.user.username if top_player else None,
                "points": top_player.total_points if top_player else 0,
                "rank": top_player.rank if top_player else None
            } if top_player else None
        },
        "points_distribution": distribution
    }), 200

# GET User's Points History (for charts)
@leaderboard_bp.route('/my-points-history', methods=['GET'])
@jwt_required()
def get_my_points_history():
    current_user = get_jwt_identity()
    user_id = current_user["id"]
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily points accumulation
    daily_points = db.session.query(
        func.date(PointsLog.created_at).label('date'),
        func.sum(PointsLog.points_change).label('daily_points')
    ).filter(
        PointsLog.user_id == user_id,
        PointsLog.created_at >= start_date
    ).group_by(
        func.date(PointsLog.created_at)
    ).order_by(
        'date'
    ).all()
    
    # Create cumulative points
    cumulative_data = []
    running_total = 0
    
    for date, daily_point in daily_points:
        running_total += daily_point
        cumulative_data.append({
            "date": date.isoformat(),
            "daily_points": daily_point,
            "cumulative_points": running_total
        })
    
    return jsonify({
        "points_history": cumulative_data,
        "time_period_days": days,
        "total_points_earned": running_total
    }), 200