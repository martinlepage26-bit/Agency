import json, os, logging
from jsonschema import validate
from flowerapp.core.engine import calculate_agency

def save_project(data, path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "session.json"), "w") as f:
        json.dump(data, f, indent=4)

def load_project(path):
    fpath = os.path.join(path, "session.json")
    if not os.path.exists(fpath): return None
    with open(fpath, "r") as f: return json.load(f)
