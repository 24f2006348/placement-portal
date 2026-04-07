from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import get_db

admin_bp = Blueprint("admin", __name__)

# note:
# this decorator is reused on every admin route
# it checks two things:
#   1. is the user logged in? (login_required handles this)
#   2. is the user actually an admin? (we check current_user.role)
# if not admin, we redirect them away — prevents students/companies
# from accessing admin pages by typing the URL directly

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# note:
# admin dashboard shows aggregate counts
# and lists pending company approvals prominently
# so admin knows what needs attention immediately

@admin_bp.route("/dashboard")
@login_required
@admin_required
def admin_dashboard():
    conn = get_db()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM student"
    ).fetchone()[0]

    total_companies = conn.execute(
        "SELECT COUNT(*) FROM company"
    ).fetchone()[0]

    total_drives = conn.execute(
        "SELECT COUNT(*) FROM placement_drive"
    ).fetchone()[0]

    total_applications = conn.execute(
        "SELECT COUNT(*) FROM application"
    ).fetchone()[0]

    # pending company approvals — shown prominently on dashboard
    pending_companies = conn.execute(
        """SELECT c.id, c.company_name, c.hr_name, c.hr_email, c.created_at
           FROM company c
           WHERE c.approval_status = 'pending'
           ORDER BY c.created_at DESC"""
    ).fetchall()

    # pending drive approvals
    pending_drives = conn.execute(
        """SELECT pd.id, pd.job_title, pd.location, pd.salary,
                  pd.application_deadline, c.company_name
           FROM placement_drive pd
           JOIN company c ON pd.company_id = c.id
           WHERE pd.status = 'pending'
           ORDER BY pd.created_at DESC"""
    ).fetchall()

    conn.close()

    return render_template("admin/dashboard.html",
        total_students=total_students,
        total_companies=total_companies,
        total_drives=total_drives,
        total_applications=total_applications,
        pending_companies=pending_companies,
        pending_drives=pending_drives
    )


# note:
# view all companies with their approval status
# search by company name if query param provided

@admin_bp.route("/companies")
@login_required
@admin_required
def companies():
    search = request.args.get("search", "").strip()
    conn = get_db()

    if search:
        rows = conn.execute(
            """SELECT c.*, u.email, u.is_active
               FROM company c
               JOIN user u ON c.user_id = u.id
               WHERE c.company_name LIKE ?
               ORDER BY c.created_at DESC""",
            (f"%{search}%",)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT c.*, u.email, u.is_active
               FROM company c
               JOIN user u ON c.user_id = u.id
               ORDER BY c.created_at DESC"""
        ).fetchall()

    conn.close()
    return render_template("admin/companies.html", companies=rows, search=search)


# note:
# approve or reject a company registration
# action comes from the form as a hidden field: 'approve' or 'reject'
# if blacklisted, we also set is_active=0 in user table

@admin_bp.route("/companies/<int:company_id>/action", methods=["POST"])
@login_required
@admin_required
def company_action(company_id):
    action = request.form.get("action")
    conn = get_db()

    if action == "approve":
        conn.execute(
            "UPDATE company SET approval_status = 'approved' WHERE id = ?",
            (company_id,)
        )
        flash("Company approved successfully.", "success")

    elif action == "reject":
        conn.execute(
            "UPDATE company SET approval_status = 'rejected' WHERE id = ?",
            (company_id,)
        )
        flash("Company rejected.", "warning")

    elif action == "blacklist":
        reason = request.form.get("reason", "No reason provided")
        # get user_id for this company
        company = conn.execute(
            "SELECT user_id FROM company WHERE id = ?", (company_id,)
        ).fetchone()

        conn.execute(
            "UPDATE company SET approval_status = 'blacklisted' WHERE id = ?",
            (company_id,)
        )
        # deactivate login
        conn.execute(
            "UPDATE user SET is_active = 0 WHERE id = ?",
            (company["user_id"],)
        )
        # log it
        conn.execute(
            """INSERT INTO blacklist_log (user_id, reason, blacklisted_by)
               VALUES (?, ?, ?)""",
            (company["user_id"], reason, current_user.id)
        )
        flash("Company blacklisted.", "danger")

    elif action == "reactivate":
        conn.execute(
            "UPDATE company SET approval_status = 'approved' WHERE id = ?",
            (company_id,)
        )
        company = conn.execute(
            "SELECT user_id FROM company WHERE id = ?", (company_id,)
        ).fetchone()
        conn.execute(
            "UPDATE user SET is_active = 1 WHERE id = ?",
            (company["user_id"],)
        )
        flash("Company reactivated.", "success")

    conn.commit()
    conn.close()
    return redirect(url_for("admin.companies"))


# note:
# view all students with search by name, roll_no, or email

@admin_bp.route("/students")
@login_required
@admin_required
def students():
    search = request.args.get("search", "").strip()
    conn = get_db()

    if search:
        rows = conn.execute(
            """SELECT s.*, u.email, u.is_active
               FROM student s
               JOIN user u ON s.user_id = u.id
               WHERE s.full_name LIKE ?
               OR s.roll_no LIKE ?
               OR u.email LIKE ?
               ORDER BY s.full_name""",
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT s.*, u.email, u.is_active
               FROM student s
               JOIN user u ON s.user_id = u.id
               ORDER BY s.full_name"""
        ).fetchall()

    conn.close()
    return render_template("admin/students.html", students=rows, search=search)


# note:
# blacklist or reactivate a student
# same pattern as company action

@admin_bp.route("/students/<int:student_id>/action", methods=["POST"])
@login_required
@admin_required
def student_action(student_id):
    action = request.form.get("action")
    conn = get_db()

    student = conn.execute(
        "SELECT user_id FROM student WHERE id = ?", (student_id,)
    ).fetchone()

    if action == "blacklist":
        reason = request.form.get("reason", "No reason provided")
        conn.execute(
            "UPDATE user SET is_active = 0 WHERE id = ?",
            (student["user_id"],)
        )
        conn.execute(
            """INSERT INTO blacklist_log (user_id, reason, blacklisted_by)
               VALUES (?, ?, ?)""",
            (student["user_id"], reason, current_user.id)
        )
        flash("Student blacklisted.", "danger")

    elif action == "reactivate":
        conn.execute(
            "UPDATE user SET is_active = 1 WHERE id = ?",
            (student["user_id"],)
        )
        flash("Student reactivated.", "success")

    conn.commit()
    conn.close()
    return redirect(url_for("admin.students"))


# note:
# view all placement drives with their status
# admin can approve or reject drives here

@admin_bp.route("/drives")
@login_required
@admin_required
def drives():
    conn = get_db()
    rows = conn.execute(
        """SELECT pd.*, c.company_name
           FROM placement_drive pd
           JOIN company c ON pd.company_id = c.id
           ORDER BY pd.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin/drives.html", drives=rows)


# note:
# approve or reject a placement drive

@admin_bp.route("/drives/<int:drive_id>/action", methods=["POST"])
@login_required
@admin_required
def drive_action(drive_id):
    action = request.form.get("action")
    conn = get_db()

    if action == "approve":
        conn.execute(
            "UPDATE placement_drive SET status = 'approved' WHERE id = ?",
            (drive_id,)
        )
        flash("Drive approved. Students can now see it.", "success")

    elif action == "reject":
        conn.execute(
            "UPDATE placement_drive SET status = 'rejected' WHERE id = ?",
            (drive_id,)
        )
        flash("Drive rejected.", "warning")

    conn.commit()
    conn.close()
    return redirect(url_for("admin.drives"))


# note:
# view all applications across all drives
# admin can see the full picture of all placements

@admin_bp.route("/applications")
@login_required
@admin_required
def applications():
    conn = get_db()
    rows = conn.execute(
        """SELECT a.*, s.full_name, s.roll_no, s.department,
                  pd.job_title, c.company_name
           FROM application a
           JOIN student s ON a.student_id = s.id
           JOIN placement_drive pd ON a.drive_id = pd.id
           JOIN company c ON pd.company_id = c.id
           ORDER BY a.applied_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin/applications.html", applications=rows)