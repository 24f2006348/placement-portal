# Placement Portal — MAD I Project (Jan 2026)

A web-based placement portal built with Flask, SQLite, and Bootstrap.
Allows Admin, Company, and Student roles to manage campus recruitment.

## Tech Stack
- Flask, Flask-Login, Werkzeug
- SQLite3 (raw)
- Jinja2 templates, Bootstrap 5

## Setup & Run

1. Install dependencies:
   pip install -r requirements.txt

2. Run the app:
   python app.py

3. Open in browser:
   http://127.0.0.1:5000

## Admin Login
Email: admin@portal.com
Password: admin123

## Roles
- Admin: pre-seeded, manages companies, students, drives
- Company: registers and waits for admin approval, then posts drives
- Student: registers, applies to approved drives, tracks status

## Project Structure
placement-portal/
├── app.py
├── models.py
├── user.py
├── requirements.txt
├── routes/
│   ├── auth.py
│   ├── admin.py
│   ├── company.py
│   └── student.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register_student.html
│   ├── register_company.html
│   ├── admin/
│   ├── company/
│   └── student/
└── static/
    └── uploads/