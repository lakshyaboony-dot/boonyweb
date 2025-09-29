# services/load_config.py
import json
import os

CONFIG_PATH = os.path.join("services", "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError("config.json not found!")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()
OPENAI_API_KEY = config.get("openai_api_key")
