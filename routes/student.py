from flask import Blueprint
student_bp = Blueprint('student', __name__)

@student_bp.route("/dashboard")
def student_dashboard():
    return "Student dashboard coming soon"