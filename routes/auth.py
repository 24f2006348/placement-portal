from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import get_db
from user import User
import os

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif current_user.role == "company":
            return redirect(url_for("company.company_dashboard"))
        else:
            return redirect(url_for("student.student_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("auth.login"))

        conn = get_db()
        row = conn.execute(
            "SELECT * FROM user WHERE email = ?",
            (email,)
        ).fetchone()

        if not row:
            conn.close()
            flash("No account found with that email.", "danger")
            return redirect(url_for("auth.login"))

        if not check_password_hash(row["password"], password):
            conn.close()
            flash("Incorrect password.", "danger")
            return redirect(url_for("auth.login"))

        if not row["is_active"]:
            conn.close()
            flash("Your account has been blacklisted. Contact admin.", "danger")
            return redirect(url_for("auth.login"))

        if row["user_type"] == "company":
            company = conn.execute(
                "SELECT approval_status FROM company WHERE user_id = ?",
                (row["id"],)
            ).fetchone()

            if not company or company["approval_status"] != "approved":
                conn.close()
                status = company["approval_status"] if company else "pending"
                if status == "rejected":
                    flash("Your company registration has been rejected by admin.", "danger")
                elif status == "blacklisted":
                    flash("Your company has been blacklisted. Contact admin.", "danger")
                else:
                    flash("Your company registration is pending admin approval.", "warning")
                return redirect(url_for("auth.login"))

        conn.close()

        user_obj = User(
            row["id"],
            row["email"],
            row["user_type"],
            row["is_active"]
        )
        login_user(user_obj)

        if user_obj.role == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        elif user_obj.role == "company":
            return redirect(url_for("company.company_dashboard"))
        else:
            return redirect(url_for("student.student_dashboard"))

    return render_template("login.html")


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        degree = request.form.get("degree", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "").strip()

        if not email or not password or not confirm or not full_name or not roll_no:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("auth.register_student"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register_student"))

        if not year.isdigit():
            flash("Year must be a valid number.", "danger")
            return redirect(url_for("auth.register_student"))

        year = int(year)

        try:
            cgpa_value = float(cgpa) if cgpa else None
        except ValueError:
            flash("CGPA must be a valid number.", "danger")
            return redirect(url_for("auth.register_student"))

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:
            conn.close()
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("auth.register_student"))

        # handle optional resume upload at registration
        resume_path = None
        file = request.files.get("resume")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Only PDF, DOC, DOCX files allowed for resume.", "danger")
                return redirect(url_for("auth.register_student"))
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filename = secure_filename(f"resume_{email}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            resume_path = filename

        conn.execute(
            "INSERT INTO user (email, password, user_type) VALUES (?, ?, ?)",
            (email, generate_password_hash(password), "student")
        )
        conn.commit()

        new_user = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            (email,)
        ).fetchone()
        user_id = new_user["id"]

        conn.execute(
            """
            INSERT INTO student
            (user_id, full_name, roll_no, degree, department, year, cgpa, phone, skills, resume_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name, roll_no, degree, department, year, cgpa_value, phone, skills, resume_path)
        )
        conn.commit()
        conn.close()

        flash("Student registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_student.html")


@auth_bp.route("/register/company", methods=["GET", "POST"])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        hr_name = request.form.get("hr_name", "").strip()
        hr_email = request.form.get("hr_email", "").strip()
        hr_phone = request.form.get("hr_phone", "").strip()
        website = request.form.get("website", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not company_name or not hr_name or not hr_email or not password or not confirm:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("auth.register_company"))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register_company"))

        conn = get_db()

        existing_user = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            (hr_email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered. Please log in.", "danger")
            return redirect(url_for("auth.register_company"))

        existing_company = conn.execute(
            "SELECT id FROM company WHERE company_name = ?",
            (company_name,)
        ).fetchone()

        if existing_company:
            conn.close()
            flash("Company already registered.", "danger")
            return redirect(url_for("auth.register_company"))

        conn.execute(
            "INSERT INTO user (email, password, user_type) VALUES (?, ?, ?)",
            (hr_email, generate_password_hash(password), "company")
        )
        conn.commit()

        new_user = conn.execute(
            "SELECT id FROM user WHERE email = ?",
            (hr_email,)
        ).fetchone()
        user_id = new_user["id"]

        conn.execute(
            """
            INSERT INTO company
            (user_id, company_name, hr_name, hr_email, hr_phone, website)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, company_name, hr_name, hr_email, hr_phone, website)
        )
        conn.commit()
        conn.close()

        flash("Company registered! Please wait for admin approval before logging in.", "warning")
        return redirect(url_for("auth.login"))

    return render_template("register_company.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))