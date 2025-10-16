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
    
    # Relationships for content created by the user
    created_courses = db.relationship('Course', back_populates='creator', lazy=True)
    
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
