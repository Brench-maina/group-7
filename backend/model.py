from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy. This object needs to be configured 
# and attached to the main Flask application instance (app) in server.py.
db = SQLAlchemy()

class User(db.Model):
    """
    User model for authentication and basic profile information.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    streak_days = db.Column(db.Integer, default=0)
    
    # Relationships for content created by the user (Crowd-Sourcing)
    created_courses = db.relationship('Course', back_populates='creator', lazy=True)
    
    # --- NEW COMMUNITY RELATIONSHIPS ---
    topics = db.relationship('DiscussionTopic', back_populates='author', lazy=True)
    comments = db.relationship('Comment', back_populates='author', lazy=True)
    reactions = db.relationship('Reaction', back_populates='user', lazy=True)
    # -----------------------------------
    
    # Relationships for tracking user activity
    enrolled_courses = db.relationship('UserCourse', back_populates='user', lazy=True)
    user_badges = db.relationship('UserBadge', back_populates='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username} (Level {self.level})>"

class Course(db.Model):
    """
    Model for learning content. Enhanced with creator and publication status 
    to support crowd-sourcing.
    """
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    xp_value = db.Column(db.Integer, default=100)
    
    # Crowdsourcing fields
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_published = db.Column(db.Boolean, default=False) # Used for moderation/approval
    
    # Relationships
    creator = db.relationship('User', back_populates='created_courses')
    lessons = db.relationship('Lesson', back_populates='course', lazy=True)
    enrollments = db.relationship('UserCourse', back_populates='course', lazy=True)
    topics = db.relationship('DiscussionTopic', back_populates='course', lazy=True) # Link topics to a specific course
    
    def __repr__(self):
        return f"<Course {self.title}>"

class Lesson(db.Model):
    """
    New model representing a single content unit within a Course.
    Crucial for organizing crowd-sourced content modules.
    """
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False) # Actual lesson content (e.g., Markdown/HTML)
    order = db.Column(db.Integer, nullable=False, default=1) # Display order
    is_published = db.Column(db.Boolean, default=False) # Lesson-level moderation

    # Relationships
    course = db.relationship('Course', back_populates='lessons')

    def __repr__(self):
        return f"<Lesson {self.order}: {self.title} in Course {self.course_id}>"

# --- NEW COMMUNITY MODELS START HERE ---

class DiscussionTopic(db.Model):
    """
    Represents a forum post or discussion thread started by a user.
    Can be general or linked to a specific Course.
    """
    __tablename__ = 'discussion_topics'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True) # Optional link to a course
    
    # Relationships
    author = db.relationship('User', back_populates='topics')
    course = db.relationship('Course', back_populates='topics')
    comments = db.relationship('Comment', back_populates='topic', lazy=True)

    def __repr__(self):
        return f"<Topic {self.id}: {self.title[:30]}>"

class Comment(db.Model):
    """
    Represents a comment or reply within a discussion topic.
    Supports nesting via parent_id.
    """
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('discussion_topics.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True) # For nested replies

    # Relationships
    author = db.relationship('User', back_populates='comments')
    topic = db.relationship('DiscussionTopic', back_populates='comments')
    
    # Self-referencing relationship for nesting (e.g., reply to a comment)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    reactions = db.relationship('Reaction', back_populates='comment', lazy=True)

    def __repr__(self):
        return f"<Comment {self.id} on Topic {self.topic_id}>"

class Reaction(db.Model):
    """
    Allows users to react (e.g., 'Like', 'Upvote') to various types of content.
    Uses nullable foreign keys to link to either a Lesson or a Comment.
    """
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Optional: A type field if you wanted reactions other than 'like' (e.g., 'star', 'clap')
    # type = db.Column(db.String(20), default='like') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='reactions')
    lesson = db.relationship('Lesson', backref='reactions')
    comment = db.relationship('Comment', back_populates='reactions')

    # Note: Application logic or database constraints must ensure that ONLY ONE of 
    # lesson_id or comment_id is populated for any given reaction record.

    def __repr__(self):
        return f"<Reaction {self.id} by User {self.user_id}>"
        
# --- END NEW COMMUNITY MODELS ---

class UserCourse(db.Model):
    """
    Junction table to track user enrollment and progress in a specific course.
    """
    __tablename__ = 'user_courses'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    
    # Progress tracking
    completion_percentage = db.Column(db.Integer, default=0)
    current_lesson = db.Column(db.String(100), nullable=True) # Could be a Lesson ID in a more complex setup
    is_completed = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='enrolled_courses')
    course = db.relationship('Course', back_populates='enrollments')

    def __repr__(self):
        return f"<User {self.user_id} - Course {self.course_id} ({self.completion_percentage}%)>"


class Badge(db.Model):
    """
    Gamification model for achievements (e.g., 'Async Champion').
    """
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    
    # Relationships
    awarded_to = db.relationship('UserBadge', back_populates='badge', lazy=True)

    def __repr__(self):
        return f"<Badge {self.name}>"

class UserBadge(db.Model):
    """
    Junction table to track which user has earned which badge.
    """
    __tablename__ = 'user_badges'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), primary_key=True)
    
    # Metadata
    awarded_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='user_badges')
    badge = db.relationship('Badge', back_populates='awarded_to')

    def __repr__(self):
        return f"<Awarded Badge: User {self.user_id} - Badge {self.badge_id}>"
