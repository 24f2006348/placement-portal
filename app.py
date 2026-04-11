from flask import Flask, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash
import os
from models import init_db, get_db
from user import User


app = Flask(__name__)
app.secret_key = os.urandom(24)



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"



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



@app.route("/")
def index():
    return redirect(url_for('auth.login'))



from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.company import company_bp
from routes.student import student_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(company_bp, url_prefix="/company")
app.register_blueprint(student_bp, url_prefix="/student")



if __name__ == "__main__":
    init_db()
    app.run(debug=True)

