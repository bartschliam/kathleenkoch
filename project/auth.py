from flask import Blueprint, render_template, redirect, url_for, request, flash, session
# from werkzeug.security import generate_password_hash, check_password_hash
from passlib.hash import sha256_crypt
from flask_login import login_user, login_required, logout_user, current_user
from .models import User
from .__init__ import db, flash_messages
import stripe
import os
import json


auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    # if 'email' in session:
    #     return redirect(url_for('main.profile'))
    email = request.args.get('email', '')
    return render_template('login.html', email=email)


@auth.route('/login', methods=['POST'])
def login_post():
    if request.method == 'POST':
        session.permanent = True
        email = request.form.get('email')
        session['email'] = email
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(email=email).first()
        if not user or not sha256_crypt.verify(password, user.password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))
        login_user(user, remember=remember)
        if not os.path.exists('project/json'):
            os.makedirs('project/json')
        file_path = f'project/json/{current_user.id}.json'
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                json.dump({}, file)
        return redirect(url_for('index'))
    return render_template('login.html')


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    subscription = request.args.get('subscription')
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists')
            return redirect(url_for('auth.signup'))
        password = request.form.get('password')
        if not password:
            flash('Password is required')
            return redirect(url_for('auth.signup'))
        name = request.form.get('name')
        password = sha256_crypt.hash(password)

        new_user = User(email=email,
                        name=name,
                        password=password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Successfully signed up with email: {email}', 'success')
        login_user(new_user)
        return redirect(url_for('profile'))
    return render_template('signup.html', subscription=subscription)


@auth.route('/logout')
@login_required
def logout():
    session.pop('token', None)
    session.pop('email', None)
    logout_user()
    return redirect(url_for('index'))


@auth.route('/delete')
@login_required
def delete():
    return render_template('delete.html')


@auth.route('/delete', methods=['POST'])
@login_required
def delete_post():
    try:
        if current_user.stripe_subscription_id is not None:
            stripe.Subscription.cancel(current_user.stripe_subscription_id)
        if current_user.stripe_customer_id is not None:
            stripe.Customer.delete(current_user.stripe_customer_id)
    except Exception as e:
        print(e)
    db.session.delete(current_user)
    db.session.commit()
    flash('Your account has been deleted successfully.', 'success')
    return redirect(url_for('index'))


@auth.route('/reset_password_logged_in', methods=['POST'])
@login_required
def reset_password_logged_in():
    # Find the user by their email
    user_email = current_user.email
    new_password = request.form.get('new_password')
    user = User.query.filter_by(email=user_email).first()
    if not user:
        session['flash_messages'].append(('No user', 'error'))
        flash_messages()
        return render_template('profile.html')

    # Hash the new password
    hashed_password = sha256_crypt.hash(new_password)

    # Update the user's password
    user.password = hashed_password

    # Commit the changes to the database
    db.session.commit()
    session['flash_messages'].append(('Password reset successfuly', 'success'))
    flash_messages()
    return render_template('profile.html', user=current_user)