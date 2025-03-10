from flask import Flask, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os


db = SQLAlchemy(engine_options={"pool_pre_ping": True})
load_dotenv()
database_uri = os.getenv('DATABASE_URI')


def create_app():
    app = Flask(__name__)
    no_wifi = os.getenv('NO_WIFI')
    if no_wifi != 'true':
        app.config.update(
            SQLALCHEMY_DATABASE_URI=database_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False
        )
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    app.config['SECRET_KEY'] = 'secret-key-goes-here'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app


def flash_messages():
    messages = session.get('flash_messages', [])
    for message in messages:
        flash(message[0], message[1])
    session['flash_messages'] = []
