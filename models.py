import sqlite3          #to read write in .db file using .py
import os               #interact with os (fetch dir path, filenames etc)
from werkzeug.security import generate_password_hash



BASE_DIR = os.path.dirname(os.path.abspath(__file__))  #path_of_dir_of_self/models.py[path_of_dironly(full_path_of(self))]  so even if we change the location of models.py, it will retrive that location
DB_PATH = os.path.join(BASE_DIR, "placement.db") #attaches placement.db with models.py ka folder no matter if the folder location is changed

def get_db():                            #def of fn which is used to connect to .db file and talk to it
    conn = sqlite3.connect(DB_PATH)      #opens the DB_PATH while it fetches DB_PATH checks the name in line 12 and create the file named there (if name already exists then it just connects to that file)
    conn.row_factory = sqlite3.Row       #implements the .row function from sqlite3 lib to not fetch rows in a tuple but rather ina neat format (e.g. row["email"] instead of row[0])
    conn.execute("PRAGMA foreign_keys = ON")  #enforces relationship for using foregn keys by one table from another only if that key exists in another key (is strangly not a feature of SQlite)
    return conn

# note:
# row_factory = sqlite3.Row lets us access columns by name
# e.g. row["email"] instead of row[0]
# PRAGMA foreign_keys = ON activates foreign key enforcement in SQLite
# SQLite has it OFF by default which is weird but true

def init_db():
    conn = get_db()
    c = conn.cursor()

    # TABLE 1 - user
    # stores login credentials for ALL roles (admin, company, student)
    # is_active = 0 means blacklisted/deactivated, they cannot login
    # user_type CHECK ensures only valid roles can be inserted
    c.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            user_type TEXT NOT NULL CHECK(user_type IN ('admin','company','student')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # TABLE 2 - student
    # stores student profile info, separate from login
    # user_id links back to user table (one student = one user account)
    # UNIQUE(user_id) ensures one profile per account
    # resume_path stores the file path of uploaded resume in static/uploads/
    c.execute("""
        CREATE TABLE IF NOT EXISTS student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            full_name TEXT,
            roll_no TEXT,
            degree TEXT,
            department TEXT,
            year INTEGER,
            cgpa REAL,
            phone TEXT,
            skills TEXT,
            resume_path TEXT,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    """)

    # TABLE 3 - company
    # stores company profile info, separate from login
    # approval_status: pending → admin approves → approved
    # blacklisted companies cannot create drives
    # CHECK constraint means DB itself rejects invalid status values
    c.execute("""
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            company_name TEXT NOT NULL,
            hr_name TEXT NOT NULL,
            hr_email TEXT,
            hr_phone TEXT,
            website TEXT,
            approval_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(approval_status IN ('pending','approved','rejected','blacklisted')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
    """)

    # TABLE 4 - placement_drive
    # job postings created by approved companies
    # company_id links to company table (not user table)
    # status pending → admin approves → students can see it
    # salary and location visible on drive detail page (from wireframe)
    c.execute("""
        CREATE TABLE IF NOT EXISTS placement_drive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            job_description TEXT,
            eligibility_criteria TEXT,
            application_deadline DATE NOT NULL,
            salary TEXT,
            location TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected','closed')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES company(id)
        )
    """)

    # TABLE 5 - application
    # record of a student applying to a drive
    # UNIQUE(student_id, drive_id) prevents duplicate applications
    # at the DATABASE level, not just python code level
    # remarks = notes company adds when shortlisting/rejecting
    # student_id references student table, drive_id references placement_drive
    c.execute("""
        CREATE TABLE IF NOT EXISTS application (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            drive_id INTEGER NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'applied'
                CHECK(status IN ('applied','shortlisted','selected','rejected')),
            remarks TEXT,
            UNIQUE(student_id, drive_id),
            FOREIGN KEY (student_id) REFERENCES student(id),
            FOREIGN KEY (drive_id) REFERENCES placement_drive(id)
        )
    """)

    # TABLE 6 - blacklist_log
    # every time admin blacklists someone, a record is stored here
    # user_id = who got blacklisted
    # blacklisted_by = always the admin's user id
    # reason = admin must give a reason
    # useful for admin to see full blacklist history
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            blacklisted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            blacklisted_by INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (blacklisted_by) REFERENCES user(id)
        )
    """)

    # seed admin
    # admin cannot register through the website per project rules
    # so we insert admin directly into DB on first run
    # checks first so we don't insert twice if init_db() is called again
    existing_admin = c.execute(
        "SELECT id FROM user WHERE user_type = 'admin'"
    ).fetchone()

    if not existing_admin:
        c.execute(
            "INSERT INTO user (email, password, user_type) VALUES (?, ?, ?)",
            ("admin@portal.com", generate_password_hash("admin123"), "admin")
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")