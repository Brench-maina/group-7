# app/models.py
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
    created_paths = db.relationship("LearningPath", back_populates="creator", lazy="dynamic", cascade="all, delete-orphan")
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
    reviewers = db.relationship("User", foreign_keys=[reviewed_by])
    contributors = db.relationship("User", secondary=path_contributors, back_populates="contributions")
    followers = db.relationship("User", secondary=path_followers, back_populates="followed_paths")
    modules = db.relationship("Module", back_populates="learning_path", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LearningPath {self.title}>"


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


#  Badges & Leaderboard 
class Badge(db.Model):
    __tablename__ = "badge"

    id = db.Column(db.Integer, primary_key=True)
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
        return f"<Leaderboard user={self.user.username} points={self.total_points}>"

    @staticmethod
    def update_leaderboard():
        """Recalculate ranks whenever points change."""
        entries = Leaderboard.query.order_by(Leaderboard.total_points.desc()).all()
        for rank, entry in enumerate(entries, start=1):
            entry.rank = rank
        db.session.commit()
