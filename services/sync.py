# services/sync.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, Progress, UserSurvey, db
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_URL = f"sqlite:///{os.path.join(os.path.dirname(BASE_DIR), 'offline.db')}"
SUPABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres.ixebkkaigbkdkaqruoio:SaHiLBoonyEnglish@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
)

# Engines + sessions
sqlite_engine = create_engine(SQLITE_URL)
# Supabase engine with optimized pool settings for Session mode
supa_engine = create_engine(
    SUPABASE_URL,
    pool_pre_ping=True,
    pool_size=1,  # Reduced for Session mode
    max_overflow=0,  # No overflow connections
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=30,  # Connection timeout
    echo=False
)

SQLiteSession = sessionmaker(bind=sqlite_engine)
SupabaseSession = sessionmaker(bind=supa_engine)


def sync_users():
    sqlite_sess = SQLiteSession()
    supa_sess = SupabaseSession()

    try:
        users = sqlite_sess.query(User).all()
        for u in users:
            existing = supa_sess.query(User).filter_by(user_id=u.user_id).first()
            if not existing:
                supa_sess.merge(u)   # merge = upsert
        supa_sess.commit()
        print("✅ Users synced")
    except Exception as e:
        print("❌ Error syncing users:", e)
    finally:
        sqlite_sess.close()
        supa_sess.close()


def sync_progress():
    sqlite_sess = SQLiteSession()
    supa_sess = SupabaseSession()

    try:
        progresses = sqlite_sess.query(Progress).all()
        for p in progresses:
            existing = supa_sess.query(Progress).filter_by(id=p.id).first()
            if not existing or (existing.updated_at < p.updated_at):
                supa_sess.merge(p)
        supa_sess.commit()
        print("✅ Progress synced")
    except Exception as e:
        print("❌ Error syncing progress:", e)
    finally:
        sqlite_sess.close()
        supa_sess.close()


def sync_surveys():
    sqlite_sess = SQLiteSession()
    supa_sess = SupabaseSession()

    try:
        surveys = sqlite_sess.query(UserSurvey).all()
        for s in surveys:
            existing = supa_sess.query(UserSurvey).filter_by(id=s.id).first()
            if not existing:
                supa_sess.merge(s)
        supa_sess.commit()
        print("✅ Surveys synced")
    except Exception as e:
        print("❌ Error syncing surveys:", e)
    finally:
        sqlite_sess.close()
        supa_sess.close()


def run_full_sync():
    """Call this when internet is back or at app startup."""
    print("🔄 Starting sync...")
    sync_users()
    sync_progress()
    sync_surveys()
    print("✅ Sync complete")
