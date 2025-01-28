from flask import Blueprint, render_template, redirect, url_for, flash, request, session, send_file, jsonify, render_template_string
from flask_login import login_required, current_user
from flask_mail import Mail, Message
import os
from datetime import datetime, time as dt_time
from .__init__ import db
from .__init__ import create_app, flash_messages
from dotenv import load_dotenv
from .models import User, Feedback
from sqlalchemy import desc, func
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
import pytz
from itsdangerous.serializer import Serializer
from itsdangerous.url_safe import URLSafeSerializer
from itsdangerous import BadSignature
from passlib.hash import sha256_crypt
from markupsafe import Markup


load_dotenv()
env_suffix = os.getenv('ENVIRONMENT')

main = Blueprint('main', __name__)
app = create_app()
app.config['ENV_VAR'] = env_suffix
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_EMAIL')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)
application = app
zurich_tz = timezone('Europe/Zurich')
utc_tz = timezone('UTC')

reset_password_email_html_content = """
<p>Hello,</p>
<p>You are receiving this email because you requested a password reset for your account.</p>
<p>
    To reset your password
    <a href="{{ reset_password_url }}">click here</a>.
</p>
<p>
    Alternatively, you can paste the following link in your browser's address bar: <br>
    {{ reset_password_url }}
</p>
<p>If you have not requested a password reset please contact someone from the development team.</p>
<p>
    Thank you!
</p>
"""



@app.route('/')
def index():
    session['flash_messages'] = []
    return render_template('index.html')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != current_user.id:
            session['flash_messages'].append(('That email already exist.', 'danger'))
        else:
            name = request.form.get('name')

            current_user.name = name if name else ''
            current_user.email = email if email else ''
            db.session.commit()
            session['flash_messages'].append(('Details Updated', 'success'))
        flash_messages()
        return redirect(url_for('profile'))
    return render_template('profile.html', user=current_user)

@app.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name')
        email_address = request.form.get('email_address')
        feedback_text = request.form.get('feedback')

        if name and email_address and feedback_text:  # Check if all fields are filled
            max_feedback_id = Feedback.query.order_by(desc(Feedback.id)).first()
            new_feedback = Feedback(
                id=max_feedback_id.id + 1 if max_feedback_id else 1,
                name=name,
                email_address=email_address,
                feedback=feedback_text
            )
            db.session.add(new_feedback)
            db.session.commit()

            # Flash a success message
            flash('Feedback submitted successfully!', 'success')

            msg = Message(
                subject='New Feedback Form Submitted',
                sender=os.getenv('MAIL_EMAIL'),
                recipients=[os.getenv('MAIL_EMAIL')]
            )
            msg.body = f"Name: {name}\nEmail address: {email_address}\nFeedback: {feedback_text}"
            send_mail(msg)
            return redirect(url_for('feedback'))
        else:
            flash('All fields are required.', 'danger')
            return redirect(url_for('feedback'))
    return render_template('feedback.html')


def send_mail(message):
    mail.send(message)
    return


def generate_reset_password_token(self):
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(self.email, salt=self.password)


def send_reset_password_email(user):
    reset_password_url = url_for('reset_password', token=generate_reset_password_token(user), user_id=user.id, _external=True)
    safe_reset_password_url = Markup(reset_password_url)

    msg = Message(
        subject='Reset your password',
        sender=os.getenv('MAIL_EMAIL'),
        recipients=[user.email]
    )
    msg.html = render_template_string(reset_password_email_html_content, reset_password_url=safe_reset_password_url)
    send_mail(msg)
    return


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            session['flash_messages'].append(('Email not found', 'error'))
            flash_messages()
            return redirect(url_for('reset_password_request'))
        send_reset_password_email(user)
        session['flash_messages'].append(('Instructions sent if the email exists', 'success'))
        flash_messages()
    return render_template('reset_password_request.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        token = request.args.get('token')
        user_id = request.args.get('user_id')
    else:
        token = request.form.get('token')
        user_id = request.form.get('user_id')
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        session['flash_messages'].append(("Did not find user", "error"))
        flash_messages()
        return render_template('login.html')
    serializer = URLSafeSerializer(app.config['SECRET_KEY'])
    try:
        token_user_email = serializer.loads(
            token,
            salt=user.password
        )
    except BadSignature:
        session['flash_messages'].append(("Bad token", "error"))
        flash_messages()
        return render_template('login.html')
    if token_user_email != user.email:
        session['flash_messages'].append(("Email doesn't match", "error"))
        flash_messages()
        return render_template('login.html')
    if request.method == 'POST':
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if not password1 or not password2:
            session['flash_messages'].append(("Password can't be empty", "error"))
            flash_messages()
        if password1 != password2:
            session['flash_messages'].append(('Passwords do not match', 'error'))
            flash_messages()
        password = sha256_crypt.hash(password1)
        user.password = password
        db.session.commit()
        session['flash_messages'].append(('Password reset', 'success'))
        flash_messages()
        return render_template('index.html')
    return render_template('reset_password.html', token=token, user_id=user_id)


'''
waitress-serve --listen=*:8000 project.main:application
'''
