from flask import Flask, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash
import os
from models import init_db, get_db
from user import User
# note:
# Flask(__name__) creates the flask app
# __name__ tells flask where to look for templates/ and static/ folders
# secret_key is required for session and flask-login to work
# os.urandom(24) generates a random 24 byte secret key
# WARNING: os.urandom changes every restart — logged in users get
# logged out when server restarts. Fine for development.

app = Flask(__name__)
app.secret_key = os.urandom(24)

# note:
# LoginManager is the object that manages the entire login system
# init_app(app) connects it to our flask app
# login_view = 'auth.login' means:
#   if someone tries to access a @login_required route without logging in,
#   flask-login automatically redirects them to the 'login' function
#   inside the 'auth' blueprint (routes/auth.py)
# login_message and login_message_category control the flash message shown

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"

# note:
# User class represents whoever is currently logged in
# UserMixin automatically provides:
#   is_authenticated → True (they have valid credentials)
#   is_anonymous     → False (they are a real user not a guest)
#   get_id()         → returns str(self.id) stored in session cookie
# We define our own is_active property to handle blacklisted users
# self._active stores the is_active value from the DB (1 or 0)
# if is_active = 0, flask-login blocks them from logging in
# self.role stores user_type from DB ('admin','company','student')
# we use current_user.role throughout the app to check permissions
# note:
# @login_manager.user_loader decorator connects this function to Flask-Login
# Flask-Login calls load_user() automatically on EVERY request
# it reads user_id from the session cookie and fetches fresh data from DB
# this is how current_user works on every page
# must return a User object if found, None if not found
# if None is returned, current_user becomes anonymous

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return User(row["id"], row["email"], row["user_type"], row["is_active"])
    return None

# note:
# index route just redirects to login page
# if already logged in, auth.login will handle redirecting
# to the correct dashboard based on role

@app.route("/")
def index():
    return redirect(url_for('auth.login'))

# note:
# Blueprints are imported here at the bottom AFTER app and login_manager
# are defined — this avoids circular imports
# (routes/auth.py imports login_manager from app.py,
#  so app.py must define login_manager before importing auth)
# url_prefix means:
#   admin blueprint routes start with /admin/...
#   company blueprint routes start with /company/...
#   student blueprint routes start with /student/...
#   auth blueprint has no prefix so /login, /register, /logout

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.company import company_bp
from routes.student import student_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(company_bp, url_prefix="/company")
app.register_blueprint(student_bp, url_prefix="/student")

# note:
# init_db() runs every time app.py starts
# it creates tables if they don't exist (safe to call multiple times)
# and seeds admin if not already there

if __name__ == "__main__":
    init_db()
    app.run(debug=True)