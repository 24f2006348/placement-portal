from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import get_db

company_bp = Blueprint("company", __name__)

def company_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'company':
            flash("Company access required.", "danger")
            return redirect(url_for('auth.login'))
        conn = get_db()
        company = conn.execute(
            "SELECT approval_status FROM company WHERE user_id = ?",
            (current_user.id,)
        ).fetchone()
        conn.close()
        if not company or company["approval_status"] != "approved":
            flash("Your account is pending admin approval.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def get_company():
    conn = get_db()
    company = conn.execute(
        "SELECT * FROM company WHERE user_id = ?",
        (current_user.id,)
    ).fetchone()
    conn.close()
    return company


@company_bp.route("/dashboard")
@login_required
@company_required
def company_dashboard():
    company = get_company()
    conn = get_db()

    
    drives = conn.execute(
        """SELECT pd.*,
           (SELECT COUNT(*) FROM application a WHERE a.drive_id = pd.id) as applicant_count
           FROM placement_drive pd
           WHERE pd.company_id = ?
           ORDER BY pd.created_at DESC""",
        (company["id"],)
    ).fetchall()

    conn.close()
    return render_template("company/dashboard.html",
        company=company,
        drives=drives
    )



@company_bp.route("/drives/create", methods=["GET", "POST"])
@login_required
@company_required
def create_drive():
    company = get_company()

    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        eligibility = request.form.get("eligibility_criteria", "").strip()
        deadline = request.form.get("application_deadline", "").strip()
        salary = request.form.get("salary", "").strip()
        location = request.form.get("location", "").strip()

        if not job_title or not deadline:
            flash("Job title and deadline are required.", "danger")
            return redirect(url_for("company.create_drive"))

        conn = get_db()
        conn.execute(
            """INSERT INTO placement_drive
               (company_id, job_title, job_description, eligibility_criteria,
                application_deadline, salary, location)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (company["id"], job_title, job_description, eligibility,
             deadline, salary, location)
        )
        conn.commit()
        conn.close()

        flash("Drive submitted for admin approval.", "success")
        return redirect(url_for("company.company_dashboard"))

    return render_template("company/create_drive.html", company=company)


@company_bp.route("/drives/<int:drive_id>/edit", methods=["GET", "POST"])
@login_required
@company_required
def edit_drive(drive_id):
    company = get_company()
    conn = get_db()

    drive = conn.execute(
        "SELECT * FROM placement_drive WHERE id = ? AND company_id = ?",
        (drive_id, company["id"])
    ).fetchone()

    if not drive:
        conn.close()
        flash("Drive not found.", "danger")
        return redirect(url_for("company.company_dashboard"))

    if drive["status"] == "approved":
        conn.close()
        flash("Approved drives cannot be edited.", "warning")
        return redirect(url_for("company.company_dashboard"))

    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        eligibility = request.form.get("eligibility_criteria", "").strip()
        deadline = request.form.get("application_deadline", "").strip()
        salary = request.form.get("salary", "").strip()
        location = request.form.get("location", "").strip()

        conn.execute(
            """UPDATE placement_drive
               SET job_title=?, job_description=?, eligibility_criteria=?,
                   application_deadline=?, salary=?, location=?, status='pending'
               WHERE id=? AND company_id=?""",
            (job_title, job_description, eligibility, deadline,
             salary, location, drive_id, company["id"])
        )
        conn.commit()
        conn.close()

        flash("Drive updated and resubmitted for approval.", "success")
        return redirect(url_for("company.company_dashboard"))

    conn.close()
    return render_template("company/edit_drive.html", drive=drive)



@company_bp.route("/drives/<int:drive_id>/close", methods=["POST"])
@login_required
@company_required
def close_drive(drive_id):
    company = get_company()
    conn = get_db()

    conn.execute(
        """UPDATE placement_drive SET status = 'closed'
           WHERE id = ? AND company_id = ?""",
        (drive_id, company["id"])
    )
    conn.commit()
    conn.close()

    flash("Drive closed successfully.", "success")
    return redirect(url_for("company.company_dashboard"))



@company_bp.route("/drives/<int:drive_id>/reopen", methods=["POST"])
@login_required
@company_required
def reopen_drive(drive_id):
    company = get_company()
    conn = get_db()

    drive = conn.execute(
        "SELECT * FROM placement_drive WHERE id = ? AND company_id = ?",
        (drive_id, company["id"])
    ).fetchone()

    if not drive or drive["status"] != "closed":
        conn.close()
        flash("Only closed drives can be reopened.", "warning")
        return redirect(url_for("company.company_dashboard"))

    conn.execute(
        "UPDATE placement_drive SET status = 'pending' WHERE id = ? AND company_id = ?",
        (drive_id, company["id"])
    )
    conn.commit()
    conn.close()

    flash("Drive resubmitted for admin approval.", "success")
    return redirect(url_for("company.company_dashboard"))

@company_bp.route("/drives/<int:drive_id>/applicants")
@login_required
@company_required
def view_applicants(drive_id):
    company = get_company()
    conn = get_db()

    drive = conn.execute(
        "SELECT * FROM placement_drive WHERE id = ? AND company_id = ?",
        (drive_id, company["id"])
    ).fetchone()

    if not drive:
        conn.close()
        flash("Drive not found.", "danger")
        return redirect(url_for("company.company_dashboard"))

    applicants = conn.execute(
        """SELECT a.id as application_id, a.status, a.applied_at, a.remarks,
                  s.id as student_id, s.full_name, s.roll_no,
                  s.department, s.cgpa, s.skills, s.resume_path
           FROM application a
           JOIN student s ON a.student_id = s.id
           WHERE a.drive_id = ?
           ORDER BY a.applied_at DESC""",
        (drive_id,)
    ).fetchall()

    conn.close()
    return render_template("company/applicants.html",
        drive=drive,
        applicants=applicants,
        company=company
    )


@company_bp.route("/applications/<int:application_id>/update", methods=["POST"])
@login_required
@company_required
def update_application(application_id):
    status = request.form.get("status")
    remarks = request.form.get("remarks", "").strip()
    drive_id = request.form.get("drive_id")

    valid_statuses = ["applied", "shortlisted", "selected", "rejected"]
    if status not in valid_statuses:
        flash("Invalid status.", "danger")
        return redirect(url_for("company.company_dashboard"))

    company = get_company()
    conn = get_db()

    # verify this application belongs to a drive owned by current company
    valid = conn.execute(
        """SELECT a.id FROM application a
           JOIN placement_drive pd ON a.drive_id = pd.id
           WHERE a.id = ? AND pd.company_id = ?""",
        (application_id, company["id"])
    ).fetchone()

    if not valid:
        conn.close()
        flash("Unauthorized action.", "danger")
        return redirect(url_for("company.company_dashboard"))

    conn.execute(
        "UPDATE application SET status = ?, remarks = ? WHERE id = ?",
        (status, remarks, application_id)
    )
    conn.commit()
    conn.close()

    flash(f"Application status updated to {status}.", "success")
    return redirect(url_for("company.view_applicants", drive_id=drive_id))