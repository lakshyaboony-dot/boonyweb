import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

basedir = os.path.abspath(os.path.dirname(__file__))
sqlite_path = os.path.join(basedir, "offline.db")

class Config:
    # Default to Supabase if available
    SUPABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:SaHiLBoonyEnglish@db.apbkobhfnmcqqzqeeqss.supabase.co:5432/postgres"
    )
    SQLITE_URL = f"sqlite:///{sqlite_path}"

    try:
        # Try Supabase with improved connection pool settings
        engine = create_engine(
            SUPABASE_URL, 
            pool_pre_ping=True,  # Test connections before use
            pool_size=5,  # Increased pool size
            max_overflow=10,  # Allow overflow connections
            pool_recycle=1800,  # Recycle connections every 30 minutes
            pool_timeout=60,  # Increased connection timeout
            connect_args={
                "connect_timeout": 30,
                "application_name": "boony_web_app",
                "options": "-c statement_timeout=30000"  # 30 second statement timeout
            },
            echo=False
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        SQLALCHEMY_DATABASE_URI = SUPABASE_URL
        print("✅ Using Supabase Database with improved connection pool settings")
    except Exception as e:
        # Fallback to SQLite
        os.makedirs(basedir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = SQLITE_URL
        print("⚠️ Supabase not reachable, using offline SQLite DB:", e)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
    UPLOAD_FOLDER = os.path.join(basedir, "user_data")  # <-- recommended path