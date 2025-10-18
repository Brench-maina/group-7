from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity # pyright: ignore[reportMissingImports]
from model import db, User, Enrollment, Course, CommunityPost, StudyGroupMember, Follow, StudyGroup
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user = get_jwt_identity()
        return jsonify({'user': user.to_dict()})
    except Exception as e:
        return jsonify({'error': 'Failed to get profile'}), 500

@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user = get_jwt_identity()
        data = request.get_json()
        
        allowed_fields = ['first_name', 'last_name', 'bio', 'avatar_url', 'location', 'website']
        
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

@user_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    try:
        user = get_jwt_identity()
        
        enrolled_courses = Enrollment.query.filter_by(user_id=user.id).count()
        completed_courses = Enrollment.query.filter_by(user_id=user.id, is_completed=True).count()
        community_posts = CommunityPost.query.filter_by(author_id=user.id).count()
        study_groups = StudyGroupMember.query.filter_by(user_id=user.id).count()
        
        stats = {
            'enrolled_courses': enrolled_courses,
            'completed_courses': completed_courses,
            'community_posts': community_posts,
            'study_groups': study_groups,
            'reputation_score': user.reputation_score,
            'contribution_count': user.contribution_count
        }
        
        return jsonify({'stats': stats})
        
    except Exception as e:
        return jsonify({'error': 'Failed to get stats'}), 500

@user_bp.route('/enrollments', methods=['GET'])
@jwt_required()
def get_enrollments():
    try:
        user = get_jwt_identity()
        enrollments = Enrollment.query.filter_by(user_id=user.id).all()
        
        enrollment_data = []
        for enrollment in enrollments:
            course = Course.query.get(enrollment.course_id)
            if course:
                course_data = course.to_dict()
                course_data['enrollment'] = {
                    'progress': enrollment.progress_percentage,
                    'is_completed': enrollment.is_completed,
                    'enrolled_at': enrollment.enrolled_at.isoformat()
                }
                enrollment_data.append(course_data)
        
        return jsonify({'enrollments': enrollment_data})
        
    except Exception as e:
        return jsonify({'error': 'Failed to get enrollments'}), 500

@user_bp.route('/posts', methods=['GET'])
@jwt_required()
def get_user_posts():
    try:
        user = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        posts = CommunityPost.query.filter_by(author_id=user.id)\
            .order_by(CommunityPost.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        posts_data = [post.to_dict() for post in posts.items]
        
        return jsonify({
            'posts': posts_data,
            'total': posts.total,
            'pages': posts.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get posts'}), 500

@user_bp.route('/search', methods=['GET'])
def search_users():
    try:
        query = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query must be at least 2 characters'}), 400
        
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) |
            (User.first_name.ilike(f'%{query}%')) |
            (User.last_name.ilike(f'%{query}%'))
        ).filter_by(is_active=True)\
         .paginate(page=page, per_page=per_page, error_out=False)
        
        users_data = [user.to_dict() for user in users.items]
        
        return jsonify({
            'users': users_data,
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': 'Search failed'}), 500

@user_bp.route('/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    try:
        user = User.query.filter_by(id=user_id, is_active=True).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()})
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user'}), 500

@user_bp.route('/follow', methods=['POST'])
@jwt_required()
def follow_user():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        if user_id == current_user.id:
            return jsonify({'error': 'Cannot follow yourself'}), 400
        
        target_user = User.query.filter_by(id=user_id, is_active=True).first()
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        existing_follow = Follow.query.filter_by(
            follower_id=current_user.id,
            following_id=user_id
        ).first()
        
        if existing_follow:
            return jsonify({'error': 'Already following this user'}), 400
        
        follow = Follow(
            follower_id=current_user.id,
            following_id=user_id
        )
        
        current_user.following_count += 1
        target_user.follower_count += 1
        
        db.session.add(follow)
        db.session.commit()
        
        return jsonify({'message': f'Now following {target_user.username}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to follow user'}), 500

@user_bp.route('/unfollow', methods=['POST'])
@jwt_required()
def unfollow_user():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        follow = Follow.query.filter_by(
            follower_id=current_user.id,
            following_id=user_id
        ).first()
        
        if not follow:
            return jsonify({'error': 'Not following this user'}), 400
        
        current_user.following_count -= 1
        target_user = User.query.get(user_id)
        if target_user:
            target_user.follower_count -= 1
        
        db.session.delete(follow)
        db.session.commit()
        
        return jsonify({'message': f'Unfollowed {target_user.username if target_user else "user"}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to unfollow user'}), 500

@user_bp.route('/followers', methods=['GET'])
@jwt_required()
def get_followers():
    try:
        user = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        followers = Follow.query.filter_by(following_id=user.id)\
            .join(User, Follow.follower_id == User.id)\
            .with_entities(User)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        followers_data = [follower.to_dict() for follower in followers.items]
        
        return jsonify({
            'followers': followers_data,
            'total': followers.total,
            'pages': followers.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get followers'}), 500

@user_bp.route('/following', methods=['GET'])
@jwt_required()
def get_following():
    try:
        user = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        following = Follow.query.filter_by(follower_id=user.id)\
            .join(User, Follow.following_id == User.id)\
            .with_entities(User)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        following_data = [user.to_dict() for user in following.items]
        
        return jsonify({
            'following': following_data,
            'total': following.total,
            'pages': following.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to get following'}), 500