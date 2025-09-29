# core/progress_manager.py
import json
import os
from core.resource_helper import resource_path

PROGRESS_FILE = resource_path("data/syllabus/user_last_progress.json")

def save_progress(user_id, day, stage, statement_index):
    """Save user progress globally"""
    data = {}
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}

    data[user_id] = {
        "day": day,
        "stage": stage,
        "statement_index": statement_index
    }

    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_progress(user_id):
    """Load last progress of a user"""
    if not os.path.exists(PROGRESS_FILE):
        return None
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(user_id, None)
    except:
        return None
