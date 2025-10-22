from datetime import datetime
from sqlalchemy import func
from models import (
    db,
    User,
    Badge,
    UserBadge,
    PointsLog,
    LearningResource,
    UserProgress,
    LearningPath,
    Module,
    Leaderboard
)
from utils.constants import POINTS_CONFIG, XP_CONFIG, BADGE_RULES


class PointsService:
    """Handles awarding of points and XP for user actions."""

    @staticmethod
    def award_points(user, action, metadata=None):
        """Award points and XP for a given user action."""
        if action not in POINTS_CONFIG:
            raise ValueError(f"Unknown action: {action}")

        points = POINTS_CONFIG[action]
        xp = XP_CONFIG.get(action, 0)

        # Update user stats
        user.points = (user.points or 0) + points
        if xp > 0:
            user.xp = (user.xp or 0) + xp

        # Log the transaction
        points_log = PointsLog(
            user_id=user.id,
            points_change=points,
            reason=f"{action}: {metadata}" if metadata else action
        )
        db.session.add(points_log)

        # Check for badge unlocks
        awarded_badges = BadgeService.check_badges(user, action)

        # Update leaderboard
        LeaderboardService.update_user_rank(user)

        db.session.commit()

        return {
            "points": points,
            "xp": xp,
            "action": action,
            "badges_awarded": awarded_badges
        }

    @staticmethod
    def award_xp_only(user, action, metadata=None):
        xp = XP_CONFIG.get(action, 0)
        if xp > 0:
            user.xp = (user.xp or 0) + xp
            db.session.commit()
        return {"xp": xp, "action": action}

    @staticmethod
    def award_daily_login(user):
        user.update_streak()  # Ensure User model has this method
        
        result = PointsService.award_points(user, 'daily_login')

        # Handle streak milestones
        if user.streak_days == 7:
            PointsService.award_xp_only(user, 'daily_streak_7_days')
        elif user.streak_days == 30:
            PointsService.award_xp_only(user, 'daily_streak_30_days')
            
        return result


class BadgeService:

    @staticmethod
    def check_badges(user, action):
       

        awarded_badges = []

        # Direct trigger badges
        trigger_map = {
            "complete_module": "first_module",
            "complete_quiz": "first_quiz",
            "create_learning_path": "first_learning_path",
            "daily_login": "first_login"
        }

        if action in trigger_map:
            badge_key = trigger_map[action]
            if not BadgeService.has_badge(user, badge_key):
                BadgeService.award_badge(user, badge_key)
                awarded_badges.append(badge_key)

        # Check milestone badges
        awarded_badges.extend(BadgeService._check_milestone_badges(user))

        return awarded_badges

    @staticmethod
    def _check_milestone_badges(user):
        """Evaluate milestone-based badges."""
        badges = []

        # Module Explorer: 5 completed modules
        completed_modules = UserProgress.query.filter_by(
            user_id=user.id, completion_percent=100
        ).count()
        if completed_modules >= 5 and not BadgeService.has_badge(user, "module_explorer"):
            BadgeService.award_badge(user, "module_explorer")
            badges.append("module_explorer")

        # Streak badge
        if user.streak_days >= 30 and not BadgeService.has_badge(user, "streak_30_days"):
            BadgeService.award_badge(user, "streak_30_days")
            badges.append("streak_30_days")

        # Path Completer
        if BadgeService._get_completed_learning_paths(user) >= 1 and not BadgeService.has_badge(user, "path_completer"):
            BadgeService.award_badge(user, "path_completer")
            badges.append("path_completer")

        # Quiz Master: 10 perfect quizzes
        perfect_quizzes = UserProgress.query.filter_by(
            user_id=user.id, completion_percent=100
        ).count()
        if perfect_quizzes >= 10 and not BadgeService.has_badge(user, "quiz_master"):
            BadgeService.award_badge(user, "quiz_master")
            badges.append("quiz_master")

        # Subject Master: all modules in a path completed
        if BadgeService._has_completed_full_path(user):
            BadgeService.award_badge(user, "subject_master")
            badges.append("subject_master")

        return badges

    @staticmethod
    def _get_completed_learning_paths(user):
        """Count completed learning paths (all modules complete)."""
        user_paths = (
            db.session.query(LearningPath.id)
            .join(Module)
            .join(UserProgress)
            .filter(
                UserProgress.user_id == user.id,
                UserProgress.completion_percent == 100
            )
            .group_by(LearningPath.id)
            .having(
                func.count(Module.id)
                == db.session.query(func.count(Module.id))
                .filter(Module.learning_path_id == LearningPath.id)
                .correlate(LearningPath)
                .scalar_subquery()
            )
            .count()
        )
        return user_paths

    @staticmethod
    def _has_completed_full_path(user):
        return BadgeService._get_completed_learning_paths(user) > 0

    @staticmethod
    def has_badge(user, badge_key):
        return (
            UserBadge.query.join(Badge)
            .filter(UserBadge.user_id == user.id, Badge.key == badge_key)
            .first()
            is not None
        )

    @staticmethod
    def award_badge(user, badge_key):
        """Grant a badge to a user."""
        rule = BADGE_RULES.get(badge_key)
        if not rule:
            raise ValueError(f"Badge '{badge_key}' not defined in BADGE_RULES")

        badge = Badge.query.filter_by(key=badge_key).first()
        if not badge:
            badge = Badge(
                key=badge_key,
                name=rule["name"],
                description=rule["description"]
            )
            db.session.add(badge)
            db.session.flush()

        user_badge = UserBadge(
            user_id=user.id,
            badge_id=badge.id,
            awarded_at=datetime.utcnow()
        )
        db.session.add(user_badge)

        # Award points for earning a badge
        PointsService.award_points(user, 'earn_badge', f"Badge: {badge_key}")

        return badge_key

    @staticmethod
    def get_user_badge_progress(user_id):
        """Return a user's progress toward each badge."""
        user = User.query.get(user_id)
        progress = {}

        # Module badges
        completed_modules = UserProgress.query.filter_by(
            user_id=user_id, completion_percent=100
        ).count()
        progress["first_module"] = completed_modules >= 1
        progress["module_explorer"] = {
            "current": completed_modules,
            "target": 5,
            "completed": completed_modules >= 5
        }

        # Quiz badges
        completed_quizzes = UserProgress.query.filter_by(
            user_id=user_id, completion_percent=100
        ).count()
        progress["first_quiz"] = completed_quizzes >= 1
        progress["quiz_master"] = {
            "current": completed_quizzes,
            "target": 10,
            "completed": completed_quizzes >= 10
        }

        # Learning path badges
        created_paths = LearningPath.query.filter_by(creator_id=user_id).count()
        completed_paths = BadgeService._get_completed_learning_paths(user)
        progress["first_learning_path"] = created_paths >= 1
        progress["path_completer"] = completed_paths >= 1
        progress["subject_master"] = BadgeService._has_completed_full_path(user)

        # Streak badges
        progress["streak_30_days"] = user.streak_days >= 30

        return progress


class LeaderboardService:
    @staticmethod
    def update_user_rank(user):
        entry = Leaderboard.query.filter_by(user_id=user.id).first()
        if not entry:
            entry = Leaderboard(user_id=user.id, total_points=user.points)
            db.session.add(entry)
        else:
            entry.total_points = user.points

        LeaderboardService.update_all_ranks()

    @staticmethod
    def update_all_ranks():
        entries = Leaderboard.query.order_by(Leaderboard.total_points.desc()).all()
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank
        db.session.commit()

    @staticmethod
    def get_top_users(limit=10):
        return (
            Leaderboard.query.join(User)
            .order_by(Leaderboard.rank)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_user_rank(user_id):
        entry = Leaderboard.query.filter_by(user_id=user_id).first()
        return entry.rank if entry else None

    @staticmethod
    def get_leaderboard_page(page=1, per_page=20):
        return (
            Leaderboard.query.join(User)
            .order_by(Leaderboard.rank)
            .paginate(page=page, per_page=per_page, error_out=False)
        )
