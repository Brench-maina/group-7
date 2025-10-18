from flask import Flask 
from models import db
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from routes import register_blueprints
from flask_jwt_extended import JWTManager
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crowd.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'supersecret')

CORS(app)
migrate = Migrate(app, db)
db.init_app(app)

jwt = JWTManager(app)

#register routes
register_blueprints(app)

@app.route("/")
def home():
    return {"message": "Crowd Sourced Learning Backend is running!"}

if __name__ == "__main__":
    app.run(port=5555, debug=True)
    