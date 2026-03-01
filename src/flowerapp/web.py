from fastapi import FastAPI
import os
from flowerapp.core.storage import load_project
app = FastAPI()
@app.get("/")
def home():
    p = load_project(os.getenv("PROJ_PATH", "data/default"))
    return {"status": "Online", "project": p["metadata"]["project_name"] if p else "None"}
