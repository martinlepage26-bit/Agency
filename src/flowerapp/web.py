from __future__ import annotations

import os

from fastapi import FastAPI

from flowerapp.core.storage import load_project

app = FastAPI(title="Lotus")


@app.get("/")
def home():
    project = load_project(os.getenv("PROJ_PATH", "data/default"))
    project_name = None
    if project:
        project_name = project.get("metadata", {}).get("project_name")
    return {"status": "Lotus Online", "project": project_name or "None"}
