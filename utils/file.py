import os
import json
from config import CONFIG

def get_path(filename):
    return os.path.join(CONFIG["output"]["path"], filename)

def save_json(filename, data):
    filepath = os.path.join(CONFIG["output"]["path"], filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_json(filename):
    filepath = os.path.join(CONFIG["output"]["path"], filename)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)