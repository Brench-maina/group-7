from flask import Blueprint
from .auth import auth_bp
from .user import user_bp
from .community import community_bp
from .learning import learning_bp
# from .leaderboard import leaderboard_bp



def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(learning_bp)
    # app.register_blueprint(leaderboard_bp, url_prefix="/leaderboard")
