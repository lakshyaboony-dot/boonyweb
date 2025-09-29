# scripts/import_excel_to_db.py
import os
import pandas as pd
from werkzeug.security import generate_password_hash

from flask import Flask
from config import Config
from models import db, User, Progress

# === Configure a minimal Flask app context for the script ===
def create_app():
    app = Flask(__name__, instance_relative_config=True, static_url_path="/static")
    app.config.from_object(Config)
    db.init_app(app)
    return app

# === Paths to your Excel files ===
USER_XLSX = os.path.join("data", "syllabus", "boony_user_data.xlsx")
PROG_XLSX = os.path.join("data", "syllabus", "boony_user_progress.xlsx")

def upsert_user(session, row):
    """
    Map Excel row to User fields.
    Excel columns we expect (from your desktop app):
      "User ID", "Full Name", "Password", "Mobile Number", "Email ID",
      "Date of Birth", "State", "City", "Language", "Gender", "Timestamp"
    """
    user_id = str(row.get("User ID", "")).strip() or None
    full_name = str(row.get("Full Name", "")).strip() or None
    password_plain = str(row.get("Password", "")).strip() or ""
    mobile = str(row.get("Mobile Number", "")).strip() or None
    email = str(row.get("Email ID", "")).strip() or None
    dob = str(row.get("Date of Birth", "")).strip() or None
    state = str(row.get("State", "")).strip() or None
    city = str(row.get("City", "")).strip() or None
    gender = str(row.get("Gender", "Male")).strip() or "Male"
    voice = gender  # default voice = chosen gender

    # Choose a username for web login:
    username = user_id or (full_name or "user").replace(" ", "_").lower()

    # Try to find an existing user by username, user_id, or email
    q = session.query(User)
    existing = None
    if user_id:
        existing = q.filter((User.user_id == user_id) | (User.username == username)).first()
    if not existing and email:
        existing = q.filter(User.email == email).first()
    if not existing:
        existing = q.filter(User.username == username).first()

    if existing:
        # Update fields if missing
        existing.full_name = existing.full_name or full_name
        existing.user_id = existing.user_id or user_id
        existing.mobile = existing.mobile or mobile
        existing.email = existing.email or email
        existing.dob = existing.dob or dob
        existing.state = existing.state or state
        existing.city = existing.city or city
        existing.gender = existing.gender or gender
        existing.voice = existing.voice or voice

        # If there is a plaintext password in Excel and no password yet, set it
        if password_plain and (not existing.password_hash):
            existing.password_hash = generate_password_hash(password_plain)
        print(f"Updated user: {username}")
        return existing

    # New user
    password_hash = generate_password_hash(password_plain or (user_id or "password123"))
    u = User(
        username=username,
        user_id=user_id,
        full_name=full_name or username,
        password_hash=password_hash,
        mobile=mobile,
        email=email,
        dob=dob,
        state=state,
        city=city,
        gender=gender,
        voice=voice
    )
    session.add(u)
    print(f"Inserted user: {username}")
    return u

def import_users(session):
    if not os.path.exists(USER_XLSX):
        print(f"User file not found: {USER_XLSX}")
        return

    df = pd.read_excel(USER_XLSX)
    # drop unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]

    for _, row in df.iterrows():
        upsert_user(session, row)

def find_user_by_sheet(session, sheet_name):
    # Try to match by user_id first, then username
    u = session.query(User).filter(
        (User.user_id == sheet_name) | (User.username == sheet_name)
    ).first()
    return u

def upsert_progress(session, user, rec):
    """
    rec is a row from progress Excel with columns:
      "Date", "Day", "Listen", "Speak", "Vocabulary", "Total Credits", "LastStage", "LastStatement"
    We aggregate by (user, day) — last row wins.
    """
    day = str(rec.get("Day", "Day-1")).strip()
    listen = int(rec.get("Listen", 0)) if pd.notna(rec.get("Listen", 0)) else 0
    speak = int(rec.get("Speak", 0)) if pd.notna(rec.get("Speak", 0)) else 0
    vocabulary = int(rec.get("Vocabulary", 0)) if pd.notna(rec.get("Vocabulary", 0)) else 0
    last_stage = str(rec.get("LastStage", "")).strip()
    last_statement = int(rec.get("LastStatement", 0)) if pd.notna(rec.get("LastStatement", 0)) else 0

    existing = session.query(Progress).filter_by(user_id=user.id, day=day).first()
    if not existing:
        existing = Progress(user_id=user.id, day=day)

    # Keep the latest numbers (simple rule)
    existing.listen = listen
    existing.speak = speak
    existing.vocabulary = vocabulary
    existing.last_stage = last_stage
    existing.last_statement = last_statement

    session.add(existing)

def import_progress(session):
    if not os.path.exists(PROG_XLSX):
        print(f"Progress file not found: {PROG_XLSX}")
        return

    # Each sheet is a user (as per your desktop app)
    xls = pd.ExcelFile(PROG_XLSX)
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(PROG_XLSX, sheet_name=sheet_name)
        except Exception as e:
            print(f"Skipping sheet {sheet_name}: {e}")
            continue

        # Resolve user
        user = find_user_by_sheet(session, sheet_name)
        if not user:
            print(f"No matching user for sheet '{sheet_name}'. Create the user first in users.xlsx.")
            continue

        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        for _, rec in df.iterrows():
            upsert_progress(session, user, rec)
        print(f"Imported progress for user: {sheet_name}")

def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        session = db.session

        import_users(session)
        import_progress(session)

        session.commit()
        print("✅ Import complete.")

if __name__ == "__main__":
    main()
