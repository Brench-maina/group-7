from flask import Blueprint
from .auth import auth_bp
from .user import user_bp
from .community import community_bp
from .learning_paths import learning_paths_bp
from .modules import modules_bp
from .progress import progress_bp
from .leaderboard import leaderboard_bp
from .badges import badges_bp
from .moderation import moderation_bp
from .challenges import challenges_bp



def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(community_bp, url_prefix="/community")
    app.register_blueprint(learning_paths_bp, url_prefix="/learning-paths")
    app.register_blueprint(modules_bp)
    app.register_blueprint(progress_bp, url_prefix="/progress")
    app.register_blueprint(leaderboard_bp, url_prefix="/leaderboard")
    app.register_blueprint(badges_bp, url_prefix="/badges")
    app.register_blueprint(moderation_bp, url_prefix="/moderation")
    app.register_blueprint(challenges_bp, url_prefix="/challenges")
