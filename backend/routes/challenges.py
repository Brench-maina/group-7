from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import db, UserChallenge, ChallengeParticipation, PlatformEvent, User, PointsLog
from services.core_services import PointsService
from utils.role_required import role_required

challenges_bp = Blueprint('challenges_bp', __name__)

# get active challenges
@challenges_bp.route('/challenges/active', methods=['GET'])
def get_active_challenges():
    try:
        current_time = datetime.utcnow()
        
        active_challenges = UserChallenge.query.filter(
            UserChallenge.created_at >= current_time - timedelta(days=UserChallenge.duration_days)
        ).all()
        
        challenges_data = []
        for challenge in active_challenges:
            participants_count = ChallengeParticipation.query.filter_by(
                challenge_id=challenge.id
            ).count()
            
            challenges_data.append({
                "id": challenge.id,
                "title": challenge.title,
                "description": challenge.description,
                "xp_reward": challenge.xp_reward,
                "points_reward": challenge.points_reward,
                "duration_days": challenge.duration_days,
                "created_at": challenge.created_at.isoformat(),
                "participants_count": participants_count,
                "days_remaining": max(0, challenge.duration_days - (current_time - challenge.created_at).days)
            })
        
        return jsonify({
            "active_challenges": challenges_data,
            "total_active": len(challenges_data)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load challenges: {str(e)}"}), 500

# get active platform events
@challenges_bp.route('/events/active', methods=['GET'])
def get_active_events():
    try:
        current_time = datetime.utcnow()
        
        active_events = PlatformEvent.query.filter(
            PlatformEvent.start_date <= current_time.date(),
            PlatformEvent.end_date >= current_time.date()
        ).all()
        
        events_data = []
        for event in active_events:
            participants_count = ChallengeParticipation.query.filter_by(
                event_id=event.id
            ).count()
            
            events_data.append({
                "id": event.id,
                "name": event.name,
                "description": event.description,
                "start_date": event.start_date.isoformat(),
                "end_date": event.end_date.isoformat(),
                "reward_points": event.reward_points,
                "participants_count": participants_count,
                "days_remaining": (event.end_date - current_time.date()).days
            })
        
        return jsonify({
            "active_events": events_data,
            "total_active": len(events_data)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load events: {str(e)}"}), 500

#join a challenge
@challenges_bp.route('/challenges/<int:challenge_id>/join', methods=['POST'])
@jwt_required()
def join_challenge(challenge_id):
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]
        
        challenge = UserChallenge.query.get_or_404(challenge_id)
        
        # Check if challenge is still active
        challenge_end = challenge.created_at + timedelta(days=challenge.duration_days)
        if datetime.utcnow() > challenge_end:
            return jsonify({"error": "This challenge has ended"}), 400
        
        # Check if user already joined
        existing_participation = ChallengeParticipation.query.filter_by(
            user_id=user_id,
            challenge_id=challenge_id
        ).first()
        
        if existing_participation:
            return jsonify({"error": "Already joined this challenge"}), 400
        
        # Create participation
        participation = ChallengeParticipation(
            user_id=user_id,
            challenge_id=challenge_id,
            started_at=datetime.utcnow(),
            progress_percent=0,
            is_completed=False
        )
        
        db.session.add(participation)
        db.session.commit()
        
        return jsonify({
            "message": f"Joined challenge: {challenge.title}",
            "challenge": {
                "id": challenge.id,
                "title": challenge.title,
                "points_reward": challenge.points_reward,
                "xp_reward": challenge.xp_reward
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to join challenge: {str(e)}"}), 500

# join an event
@challenges_bp.route('/events/<int:event_id>/join', methods=['POST'])
@jwt_required()
def join_event(event_id):
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]
        
        event = PlatformEvent.query.get_or_404(event_id)
        current_time = datetime.utcnow()
        
        # Check if event is active
        if current_time.date() < event.start_date or current_time.date() > event.end_date:
            return jsonify({"error": "This event is not currently active"}), 400
        
        # Check if user already joined
        existing_participation = ChallengeParticipation.query.filter_by(
            user_id=user_id,
            event_id=event_id
        ).first()
        
        if existing_participation:
            return jsonify({"error": "Already joined this event"}), 400
        
        # Create participation
        participation = ChallengeParticipation(
            user_id=user_id,
            event_id=event_id,
            started_at=current_time
        )
        
        db.session.add(participation)
        db.session.commit()
        
        return jsonify({
            "message": f"Joined event: {event.name}",
            "event": {
                "id": event.id,
                "name": event.name,
                "reward_points": event.reward_points,
                "end_date": event.end_date.isoformat()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to join event: {str(e)}"}), 500

# GET user's challenge participations
@challenges_bp.route('/my-challenges', methods=['GET'])
@jwt_required()
def get_my_challenges():
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]
        
        participations = ChallengeParticipation.query.filter_by(
            user_id=user_id
        ).join(UserChallenge).join(PlatformEvent, isouter=True).all()
        
        participations_data = []
        for participation in participations:
            challenge_data = {
                "participation_id": participation.id,
                "started_at": participation.started_at.isoformat(),
                "progress_percent": participation.progress_percent,
                "is_completed": participation.is_completed,
                "completed_at": participation.completed_at.isoformat() if participation.completed_at else None
            }
            
            if participation.challenge:
                challenge_data.update({
                    "type": "challenge",
                    "id": participation.challenge.id,
                    "title": participation.challenge.title,
                    "description": participation.challenge.description,
                    "points_reward": participation.challenge.points_reward,
                    "xp_reward": participation.challenge.xp_reward
                })
            elif participation.event:
                challenge_data.update({
                    "type": "event",
                    "id": participation.event.id,
                    "name": participation.event.name,
                    "description": participation.event.description,
                    "reward_points": participation.event.reward_points,
                    "end_date": participation.event.end_date.isoformat()
                })
            
            participations_data.append(challenge_data)
        
        return jsonify({
            "participations": participations_data,
            "total_participations": len(participations_data)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load participations: {str(e)}"}), 500

# update challenge progress
@challenges_bp.route('/participations/<int:participation_id>/progress', methods=['PUT'])
@jwt_required()
def update_challenge_progress(participation_id):
    try:
        current_user = get_jwt_identity()
        user_id = current_user["id"]
        
        participation = ChallengeParticipation.query.filter_by(
            id=participation_id,
            user_id=user_id
        ).first_or_404()
        
        data = request.get_json()
        progress_percent = data.get('progress_percent', 0)
        mark_completed = data.get('mark_completed', False)
        
        if mark_completed:
            participation.progress_percent = 100
            participation.is_completed = True
            participation.completed_at = datetime.utcnow()
            
            # Award rewards
            user = User.query.get(user_id)
            if participation.challenge:
                PointsService.award_points(user, 'complete_challenge', 
                                         f"Challenge: {participation.challenge.title}")
            elif participation.event:
                PointsService.award_points(user, 'complete_event',
                                         f"Event: {participation.event.name}")
        else:
            participation.progress_percent = min(100, max(0, progress_percent))
        
        db.session.commit()
        
        return jsonify({
            "message": "Progress updated successfully",
            "progress_percent": participation.progress_percent,
            "is_completed": participation.is_completed
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update progress: {str(e)}"}), 500

#Create new challenge
@challenges_bp.route('/admin/challenges', methods=['POST'])
@jwt_required()
@role_required("admin")
def create_challenge():
    try:
        data = request.get_json()
        
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        xp_reward = data.get("xp_reward", 50)
        points_reward = data.get("points_reward", 20)
        duration_days = data.get("duration_days", 7)
        
        if not title:
            return jsonify({"error": "Challenge title is required"}), 400
        
        new_challenge = UserChallenge(
            title=title,
            description=description,
            xp_reward=xp_reward,
            points_reward=points_reward,
            duration_days=duration_days
        )
        
        db.session.add(new_challenge)
        db.session.commit()
        
        return jsonify({
            "message": "Challenge created successfully",
            "challenge": {
                "id": new_challenge.id,
                "title": new_challenge.title,
                "description": new_challenge.description,
                "points_reward": new_challenge.points_reward,
                "duration_days": new_challenge.duration_days
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create challenge: {str(e)}"}), 500

#  Create new event
@challenges_bp.route('/admin/events', methods=['POST'])
@jwt_required()
@role_required("admin")
def create_event():
    try:
        data = request.get_json()
        
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        reward_points = data.get("reward_points", 100)
        
        if not all([name, start_date_str, end_date_str]):
            return jsonify({"error": "Name, start_date, and end_date are required"}), 400
        
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).date()
        
        if start_date >= end_date:
            return jsonify({"error": "End date must be after start date"}), 400
        
        new_event = PlatformEvent(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            reward_points=reward_points
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        return jsonify({
            "message": "Event created successfully",
            "event": {
                "id": new_event.id,
                "name": new_event.name,
                "description": new_event.description,
                "start_date": new_event.start_date.isoformat(),
                "end_date": new_event.end_date.isoformat(),
                "reward_points": new_event.reward_points
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create event: {str(e)}"}), 500

# GET challenge/event leaderboard
@challenges_bp.route('/<int:challenge_id>/leaderboard', methods=['GET'])
def get_challenge_leaderboard(challenge_id):
    try:
        challenge = UserChallenge.query.get_or_404(challenge_id)
        
        leaderboard = db.session.query(
            User.username,
            ChallengeParticipation.progress_percent,
            ChallengeParticipation.started_at
        ).join(
            User, ChallengeParticipation.user_id == User.id
        ).filter(
            ChallengeParticipation.challenge_id == challenge_id
        ).order_by(
            ChallengeParticipation.progress_percent.desc(),
            ChallengeParticipation.started_at.asc()
        ).limit(20).all()
        
        leaderboard_data = []
        for rank, (username, progress, started_at) in enumerate(leaderboard, start=1):
            leaderboard_data.append({
                "rank": rank,
                "username": username,
                "progress_percent": progress,
                "started_at": started_at.isoformat()
            })
        
        return jsonify({
            "challenge_id": challenge_id,
            "challenge_title": challenge.title,
            "leaderboard": leaderboard_data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load leaderboard: {str(e)}"}), 500