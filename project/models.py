from flask_login import UserMixin
from .__init__ import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    admin = db.Column(db.Boolean)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(1000))
    email_address = db.Column(db.String(1000))
    feedback = db.Column(db.String(10000))


'''
from project import db, create_app, models
db.create_all(app=create_app())
'''
