
from datetime import datetime, date, timedelta
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()


# Enums 
class RoleEnum(enum.Enum):
    admin = "admin"
    contributor = "contributor"
    learner = "learner"


class ContentStatusEnum(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

# Association Tables 
path_contributors = db.Table(
    "path_contributors",
    db.Column("path_id", db.Integer, db.ForeignKey("learning_path.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True)
)

path_followers = db.Table(
    "path_followers",
    db.Column("path_id", db.Integer, db.ForeignKey("learning_path.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True)
)


# Core Models
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False, default=RoleEnum.learner)
    points = db.Column(db.Integer, default=0, nullable=False, index=True)
    xp = db.Column(db.Integer, default=0, nullable=False)
    streak_days = db.Column(db.Integer, default=0)
    last_streak_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_paths = db.relationship("LearningPath",back_populates="creator",lazy="dynamic",cascade="all, delete-orphan",foreign_keys="LearningPath.creator_id")
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    contributions = db.relationship("LearningPath", secondary=path_contributors, back_populates="contributors")
    followed_paths = db.relationship("LearningPath", secondary=path_followers, back_populates="followers")
    badges = db.relationship("UserBadge", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    progress = db.relationship("UserProgress", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    posts = db.relationship("CommunityPost", back_populates="author", cascade="all, delete-orphan", lazy="dynamic")
    comments = db.relationship("CommunityComment", back_populates="author", cascade="all, delete-orphan", lazy="dynamic")
    leaderboard_entry = db.relationship("Leaderboard", back_populates="user", uselist=False, cascade="all, delete-orphan")

    #  Methods 
    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "points": self.points,
            "xp": self.xp,
            "streak_days": self.streak_days,
            "badges": [badge.badge.name for badge in self.badges],
        }

    def update_streak(self):
        """Update daily login/activity streaks."""
        today = date.today()
        if self.last_streak_date == today:
            return
        if self.last_streak_date == today - timedelta(days=1):
            self.streak_days += 1
        else:
            self.streak_days = 1
        self.last_streak_date = today
        db.session.commit()

    @validates("email")
    def validate_email(self, key, email):
        if "@" not in email:
            raise ValueError("Invalid email format.")
        return email

class LearningPath(db.Model):
    __tablename__ = "learning_path"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(ContentStatusEnum), default=ContentStatusEnum.pending)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship("User", foreign_keys=[creator_id], back_populates="created_paths")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    contributors = db.relationship("User", secondary=path_contributors, back_populates="contributions")
    followers = db.relationship("User", secondary=path_followers, back_populates="followed_paths")
    modules = db.relationship("Module", back_populates="learning_path", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LearningPath {self.title}>"
    
class LearningResource(db.Model):
    __tablename__ = "learning_resource"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., video, article, book
    url = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))

    module = db.relationship("Module", back_populates="resources")
     
    def __repr__(self):
        return f"<LearningResource {self.title}>"    


class Module(db.Model):
    __tablename__ = "module"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    learning_path_id = db.Column(db.Integer, db.ForeignKey("learning_path.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    learning_path = db.relationship("LearningPath", back_populates="modules")
    quizzes = db.relationship("Quiz", back_populates="module", lazy="dynamic", cascade="all, delete-orphan")
    progress_records = db.relationship("UserProgress", back_populates="module", lazy="dynamic", cascade="all, delete-orphan")
    resources = db.relationship("LearningResource", back_populates="module", lazy="dynamic")
    
    def __repr__(self):
        return f"<Module {self.title}>"


class Quiz(db.Model):
    __tablename__ = "quiz"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))
    passing_score = db.Column(db.Integer, default=70)

    module = db.relationship("Module", back_populates="quizzes")
    questions = db.relationship("Question", back_populates="quiz", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz {self.title}>"


class Question(db.Model):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"))
    text = db.Column(db.Text, nullable=False)

    quiz = db.relationship("Quiz", back_populates="questions")
    choices = db.relationship("Choice", back_populates="question", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.id}>"


class Choice(db.Model):
    __tablename__ = "choice"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"))
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    question = db.relationship("Question", back_populates="choices")

    def __repr__(self):
        return f"<Choice {self.id}>"


class UserProgress(db.Model):
    __tablename__ = "user_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    module_id = db.Column(db.Integer, db.ForeignKey("module.id"))
    completion_percent = db.Column(db.Integer, default=0)
    last_score = db.Column(db.Integer, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="progress")
    module = db.relationship("Module", back_populates="progress_records")

    def __repr__(self):
        return f"<UserProgress user={self.user_id} module={self.module_id}>"


# Community 
class CommunityPost(db.Model):
    __tablename__ = "community_post"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("CommunityComment", back_populates="post", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<CommunityPost {self.title}>"


class CommunityComment(db.Model):
    __tablename__ = "community_comment"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("community_post.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship("CommunityPost", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<CommunityComment {self.id}>"


class Badge(db.Model):
    __tablename__ = "badge"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("UserBadge", back_populates="badge", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Badge {self.name}>"


class UserBadge(db.Model):
    __tablename__ = "user_badge"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    badge_id = db.Column(db.Integer, db.ForeignKey("badge.id"))
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="badges")
    badge = db.relationship("Badge", back_populates="users")

    def __repr__(self):
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"


class Leaderboard(db.Model):
    __tablename__ = "leaderboard"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    total_points = db.Column(db.Integer, default=0, nullable=False)
    rank = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="leaderboard_entry")

    def __repr__(self):
        return f"<Leaderboard user={self.user.username if self.user else 'Unknown'} points={self.total_points}>"

    @staticmethod
    def update_leaderboard():
        """Recalculate ranks whenever points change."""
        entries = Leaderboard.query.order_by(Leaderboard.total_points.desc()).all()
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank
        db.session.commit()

class PlatformEvent(db.Model):
    __tablename__ = "platform_event"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reward_points = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participations = db.relationship("ChallengeParticipation", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PlatformEvent {self.name}>"

class UserChallenge(db.Model):
    __tablename__ = "user_challenge"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    xp_reward = db.Column(db.Integer, default=50)
    points_reward = db.Column(db.Integer, default=20)
    duration_days = db.Column(db.Integer, default=7)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participations = db.relationship("ChallengeParticipation", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserChallenge {self.title}>"

class ChallengeParticipation(db.Model):
    __tablename__ = "challenge_participation"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    challenge_id = db.Column(db.Integer, db.ForeignKey("user_challenge.id"))
    event_id = db.Column(db.Integer, db.ForeignKey("platform_event.id"), nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    progress_percent = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)

    user = db.relationship("User")
    challenge = db.relationship("UserChallenge", back_populates="participations")
    event = db.relationship("PlatformEvent", back_populates="participations")

    def __repr__(self):
        return f"<ChallengeParticipation user={self.user_id} challenge={self.challenge_id}>"


class PointsLog(db.Model):
    __tablename__ = "points_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    points_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def __repr__(self):
        return f"<PointsLog user={self.user_id} points={self.points_change}>"

class ContentFlag(db.Model):
    __tablename__ = "content_flag"

    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("community_post.id"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("community_comment.id"), nullable=True)
    reason = db.Column(db.String(255))
    status = db.Column(db.Enum(ContentStatusEnum), default=ContentStatusEnum.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reporter = db.relationship("User")
    post = db.relationship("CommunityPost")
    comment = db.relationship("CommunityComment")

    def __repr__(self):
        return f"<ContentFlag reporter={self.reporter_id} status={self.status.value}>"

class UserModeration(db.Model):
    __tablename__ = "user_moderation"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    target_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50))  
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("User", foreign_keys=[admin_id])
    target_user = db.relationship("User", foreign_keys=[target_user_id])

    def __repr__(self):
        return f"<UserModeration admin={self.admin_id} target={self.target_user_id} action={self.action}>"
