import json, os
from core.resource_helper import resource_path

SESSION_FILE = resource_path("data/session/last_session.json")

def save_last_session(user_id, day, stage, statement_index):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    data = {
        "user_id": user_id,
        "day": str(day),
        "stage": stage,
        "statement_index": int(statement_index)
    }
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_last_session():
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def clear_last_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
