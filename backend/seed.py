from app import app, db
from models import (
    User, RoleEnum, Badge, LearningPath, Module, Quiz, Question, Choice,
    CommunityPost, CommunityComment, UserProgress, UserBadge, Leaderboard,
    ContentStatusEnum
)
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():
    # Drop and recreate all tables
    db.drop_all()
    db.create_all()

    # USERS
    users = [
        User(
            username="admin",
            email="admin@learnplatform.com",
            password_hash=generate_password_hash("admin123"),
            role=RoleEnum.admin,
            points=1500,
            xp=2500
        ),
        User(
            username="creator",
            email="creator@learnplatform.com",
            password_hash=generate_password_hash("creator123"),
            role=RoleEnum.contributor,
            points=700,
            xp=1200
        ),
        User(
            username="learner",
            email="learner@learnplatform.com",
            password_hash=generate_password_hash("learner123"),
            role=RoleEnum.learner,
            points=350,
            xp=600
        )
    ]
    db.session.add_all(users)
    db.session.commit()

    admin = users[0]
    contributor = users[1]
    learner = users[2]

    # BADGES
    badges = [
        Badge(key="first_login", name="First Login", description="Welcome!"),
        Badge(key="first_module", name="Module Explorer", description="Completed first module"),
        Badge(key="streak_7_days", name="Weekly Warrior", description="7-day streak")
    ]
    db.session.add_all(badges)
    db.session.commit()

    # LEARNING PATHS
    paths = [
        LearningPath(
            title="Python Fundamentals",
            description="Learn Python basics",
            creator_id=contributor.id,
            status=ContentStatusEnum.approved,
            is_published=True
        )
    ]
    db.session.add_all(paths)
    db.session.commit()

    # MODULES
    modules = [
        Module(
            title="Intro to Python",
            description="Variables, data types, syntax",
            learning_path_id=paths[0].id
        )
    ]
    db.session.add_all(modules)
    db.session.commit()

    # QUIZZES
    quizzes = [
        Quiz(
            title="Python Basics Quiz",
            module_id=modules[0].id
        )
    ]
    db.session.add_all(quizzes)
    db.session.commit()

    # QUESTIONS + CHOICES
    questions = [
        Question(
            quiz_id=quizzes[0].id,
            text="What is the correct way to declare a variable in Python?"
        ),
        Question(
            quiz_id=quizzes[0].id,
            text="Which keyword is used to define a function?"
        )
    ]
    db.session.add_all(questions)
    db.session.commit()

    choices = [
        Choice(question_id=questions[0].id, text="x = 5", is_correct=True),
        Choice(question_id=questions[0].id, text="int x = 5", is_correct=False),
        Choice(question_id=questions[1].id, text="def", is_correct=True),
        Choice(question_id=questions[1].id, text="function", is_correct=False)
    ]
    db.session.add_all(choices)
    db.session.commit()

    # COMMUNITY POSTS + COMMENTS
    posts = [
        CommunityPost(
            title="How to learn Flask?",
            content="Any tips for beginners?",
            author_id=learner.id
        )
    ]
    db.session.add_all(posts)
    db.session.commit()

    comments = [
        CommunityComment(
            content="Check Flask documentation and tutorials!",
            author_id=contributor.id,
            post_id=posts[0].id
        )
    ]
    db.session.add_all(comments)
    db.session.commit()

    # USER PROGRESS
    progress = [
        UserProgress(user_id=learner.id, module_id=modules[0].id, completion_percent=50)
    ]
    db.session.add_all(progress)
    db.session.commit()

    # USER BADGES
    user_badges = [
        UserBadge(user_id=learner.id, badge_id=badges[0].id)
    ]
    db.session.add_all(user_badges)
    db.session.commit()

    # LEADERBOARD
    leaderboard_entries = [
        Leaderboard(user_id=u.id, total_points=u.points)
        for u in users
    ]
    db.session.add_all(leaderboard_entries)
    db.session.commit()
    Leaderboard.update_leaderboard()

    print("Database seeded successfully!")
