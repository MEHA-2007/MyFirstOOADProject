# HomeEase — AI-Powered Local Home Services Booking Platform

Responsive college project prototype using Flask, MySQL, HTML, CSS, JavaScript and Bootstrap.

## Abstract and features

HomeEase lets customers describe household issues, receive a keyword-based service suggestion and approximate estimate, choose a service date, and track a local provider booking. It includes registration/login with bcrypt password hashing, profiles, booking history, urgent requests, simulated payments, completed-service reports, warranty fields, and an urgent-first admin dashboard.

The “AI” recommendation is a simple local keyword matcher. Providers and cost estimates use demo rules/data; matching is based on skill, rating and experience, not live location or availability. GPS tracking and external payment processing are not connected. Payment is simulated and collects no financial details. Report and warranty fields are stored; admin maintenance functions can be expanded.

## Project structure

```text
homeease/
├── app.py
├── schema.sql
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/ (base, home, auth, dashboard, booking, providers, tracking, history, payment, report, profile, admin, error)
└── static/css/style.css, static/js/app.js
```

## Install and run (Windows / VS Code)

1. Install Python 3.10+ and MySQL 8+ using their official installers. Start the MySQL service.
2. Open a terminal in this folder and create a virtual environment: `py -m venv .venv` then `\.venv\Scripts\Activate.ps1`.
3. Create the database and demo services/providers: `mysql -u root -p < schema.sql`.
4. Copy `.env.example` to `.env`. Set `SECRET_KEY` to a long random value and provide local `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB`. Never commit `.env`.
5. Install requirements: `pip install -r requirements.txt`.
6. Start: `python -m flask --app app run --debug`; open http://127.0.0.1:5000.
7. Register a normal account. To enable admin, run `USE homeease; UPDATE users SET role='admin' WHERE email='your-address@example.com';` in MySQL, then sign out/in.

## Manual module walkthrough

- Register/login; visit Profile to save phone and address.
- Book a service by describing a problem and choosing date/time. Try “the kitchen tap is leaking” and inspect category and estimate.
- Mark a request urgent; admin will see urgent jobs first.
- Admin can move status through Requested, Confirmed, Provider on the Way, In Progress, Completed. Completion creates a starter report.
- Customer opens History to track a booking, view its report, and record a demo payment. No real transaction occurs.
- Provider directory and history maintenance reminder use sample data and prototype logic.

## Troubleshooting

- Missing Python package: activate `.venv`, run `pip install -r requirements.txt`.
- MySQL connection refused: start MySQL and verify credentials/database in `.env`.
- Unknown database/tables: rerun `mysql -u root -p < schema.sql`.
- Admin link absent after role update: sign out and back in.
- MySQLdb build/import issue on Windows: use a supported Python version and install the MySQL development/runtime components, then reinstall requirements.

## Screenshots

Add screenshots here after running: home page, booking form, customer dashboard, tracking and admin dashboard.

## Push to GitHub

Create an empty GitHub repository, then in the project folder:

```powershell
git init
git add .
git status   # verify .env is not listed
git commit -m "Build HomeEase service booking prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Never add secrets, passwords, or database credentials to the repository. If a secret is committed, rotate it immediately.
