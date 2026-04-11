from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import get_db
import os

student_bp = Blueprint("student", __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash("Student access required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def get_student():
    conn = get_db()
    student = conn.execute(
        "SELECT * FROM student WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()
    conn.close()
    return student


@student_bp.route("/dashboard")
@login_required
@student_required
def student_dashboard():
    student = get_student()
    conn = get_db()
    search = request.args.get("search", "").strip()

    if search:
        available_drives = conn.execute(
            """SELECT pd.*, c.company_name, c.website
               FROM placement_drive pd
               JOIN company c ON pd.company_id = c.id
               WHERE pd.status = 'approved'
               AND pd.id NOT IN (
                   SELECT drive_id FROM application WHERE student_id = ?
               )
               AND (
                   c.company_name LIKE ?
                   OR pd.job_title LIKE ?
                   OR pd.eligibility_criteria LIKE ?
               )
               ORDER BY pd.created_at DESC""",
            (student["id"], f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        available_drives = conn.execute(
            """SELECT pd.*, c.company_name, c.website
               FROM placement_drive pd
               JOIN company c ON pd.company_id = c.id
               WHERE pd.status = 'approved'
               AND pd.id NOT IN (
                   SELECT drive_id FROM application WHERE student_id = ?
               )
               ORDER BY pd.created_at DESC""",
            (student["id"],)
        ).fetchall()

    applied_drives = conn.execute(
        """SELECT a.id as application_id, a.status, a.applied_at, a.remarks,
                  pd.job_title, pd.location, pd.salary,
                  pd.application_deadline, pd.status as drive_status,
                  c.company_name
           FROM application a
           JOIN placement_drive pd ON a.drive_id = pd.id
           JOIN company c ON pd.company_id = c.id
           WHERE a.student_id = ?
           ORDER BY a.applied_at DESC""",
        (student["id"],)
    ).fetchall()

    conn.close()
    return render_template("student/dashboard.html",
        student=student,
        available_drives=available_drives,
        applied_drives=applied_drives,
        search=search
    )


@student_bp.route("/drives/<int:drive_id>")
@login_required
@student_required
def drive_detail(drive_id):
    student = get_student()
    conn = get_db()

    drive = conn.execute(
        """SELECT pd.*, c.company_name, c.hr_name,
                  c.hr_email, c.website
           FROM placement_drive pd
           JOIN company c ON pd.company_id = c.id
           WHERE pd.id = ? AND pd.status = 'approved'""",
        (drive_id,)
    ).fetchone()

    if not drive:
        conn.close()
        flash("Drive not found or not available.", "danger")
        return redirect(url_for("student.student_dashboard"))

    already_applied = conn.execute(
        """SELECT id FROM application
           WHERE student_id = ? AND drive_id = ?""",
        (student["id"], drive_id)
    ).fetchone()

    conn.close()
    return render_template("student/drive_detail.html",
        drive=drive,
        already_applied=already_applied,
        student=student
    )


@student_bp.route("/drives/<int:drive_id>/apply", methods=["POST"])
@login_required
@student_required
def apply(drive_id):
    student = get_student()
    conn = get_db()

    drive = conn.execute(
        "SELECT id FROM placement_drive WHERE id = ? AND status = 'approved'",
        (drive_id,)
    ).fetchone()

    if not drive:
        conn.close()
        flash("This drive is no longer available.", "danger")
        return redirect(url_for("student.student_dashboard"))

    existing = conn.execute(
        """SELECT id FROM application
           WHERE student_id = ? AND drive_id = ?""",
        (student["id"], drive_id)
    ).fetchone()

    if existing:
        conn.close()
        flash("You have already applied to this drive.", "warning")
        return redirect(url_for("student.student_dashboard"))

    from datetime import date
    conn.execute(
        """INSERT INTO application (student_id, drive_id, applied_at)
           VALUES (?, ?, ?)""",
        (student["id"], drive_id, date.today().isoformat())
    )
    conn.commit()
    conn.close()

    flash("Application submitted successfully!", "success")
    return redirect(url_for("student.student_dashboard"))


@student_bp.route("/history")
@login_required
@student_required
def history():
    student = get_student()
    conn = get_db()

    applications = conn.execute(
        """SELECT a.id, a.status, a.applied_at, a.remarks,
                  pd.job_title, pd.location, pd.salary,
                  pd.application_deadline, pd.status as drive_status,
                  c.company_name
           FROM application a
           JOIN placement_drive pd ON a.drive_id = pd.id
           JOIN company c ON pd.company_id = c.id
           WHERE a.student_id = ?
           ORDER BY a.applied_at DESC""",
        (student["id"],)
    ).fetchall()

    conn.close()
    return render_template("student/history.html",
        student=student,
        applications=applications
    )


@student_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
@student_required
def edit_profile():
    student = get_student()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        degree = request.form.get("degree", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "").strip()

        if not full_name:
            flash("Full name is required.", "danger")
            return redirect(url_for("student.edit_profile"))

        try:
            year_val = int(year) if year else None
            cgpa_val = float(cgpa) if cgpa else None
        except ValueError:
            flash("Year and CGPA must be valid numbers.", "danger")
            return redirect(url_for("student.edit_profile"))

        resume_path = student["resume_path"]
        file = request.files.get("resume")

        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(
                    f"resume_{current_user.id}_{file.filename}"
                )
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                resume_path = filename
            else:
                flash("Only PDF, DOC, DOCX files allowed for resume.", "danger")
                return redirect(url_for("student.edit_profile"))

        conn = get_db()
        conn.execute(
            """UPDATE student
               SET full_name=?, roll_no=?, degree=?, department=?,
                   year=?, cgpa=?, phone=?, skills=?, resume_path=?
               WHERE user_id=?""",
            (full_name, roll_no, degree, department, year_val,
             cgpa_val, phone, skills, resume_path, current_user.id)
        )
        conn.commit()
        conn.close()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("student.student_dashboard"))

    return render_template("student/edit_profile.html", student=student)


@student_bp.route("/company/<int:company_id>")
@login_required
@student_required
def company_detail(company_id):
    conn = get_db()

    company = conn.execute(
        "SELECT * FROM company WHERE id = ?", (company_id,)
    ).fetchone()

    if not company:
        conn.close()
        flash("Company not found.", "danger")
        return redirect(url_for("student.student_dashboard"))

    drives = conn.execute(
        """SELECT * FROM placement_drive
           WHERE company_id = ? AND status = 'approved'
           ORDER BY created_at DESC""",
        (company_id,)
    ).fetchall()

    conn.close()
    return render_template("student/company_detail.html",
        company=company,
        drives=drives
    )