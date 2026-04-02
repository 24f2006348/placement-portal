from flask import Blueprint
company_bp = Blueprint('company', __name__)

@company_bp.route("/dashboard")
def company_dashboard():
    return "Company dashboard coming soon"